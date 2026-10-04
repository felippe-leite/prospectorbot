"""Scan orchestration independent from the CLI and discovery vendor."""

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from prospector.analyzers.website import WebsiteAnalyzer
from prospector.database.repository import Repository
from prospector.database.session import session_scope
from prospector.discovery.base import BusinessProvider, DiscoveryError
from prospector.models import AnalysisStatus, Business, Scan, ScanStatus, WebsiteAnalysis, utc_now
from prospector.opportunities.rules import OpportunityEngine
from prospector.scoring.engine import ScoreEngine
from prospector.scoring.weights import ScoringConfig


def analyze_safely(analyzer: WebsiteAnalyzer, business: Business, scan_id: UUID) -> WebsiteAnalysis:
    # One unexpected page must not discard the rest of the scan.
    try:
        return analyzer.analyze(business, scan_id)
    except Exception:
        return WebsiteAnalysis(business_id=business.id, scan_id=scan_id, requested_url=business.website,
                               status=AnalysisStatus.FAILED,
                               errors=["Falha interna ao analisar o website; sinais permanecem desconhecidos."])


def run_scan(query: str, location: str, limit: int, provider: BusinessProvider,
             analyzer: WebsiteAnalyzer, factory: sessionmaker[Session],
             scoring: ScoringConfig | None = None,
             progress: Callable[[int, int], None] | None = None) -> Scan:
    if not 1 <= limit <= 50:
        raise ValueError("O limite do MVP deve estar entre 1 e 50.")
    config = scoring or ScoringConfig()
    scan = Scan(query=query, location=location, limit=limit, status=ScanStatus.RUNNING)
    with session_scope(factory) as session:
        Repository(session).save_scan(scan)
    try:
        businesses = provider.search(query, location, limit)[:limit]
        opportunity_engine = OpportunityEngine(config)
        score_engine = ScoreEngine(config)
        seen = set()
        for position, business in enumerate(businesses, 1):
            # Commit discovery separately: failures leave a useful historical record.
            with session_scope(factory) as session:
                business = Repository(session).save_business(business, scan.id)
            if business.id in seen:
                continue
            seen.add(business.id)
            analysis = analyze_safely(analyzer, business, scan.id) if business.website else None
            opportunities = opportunity_engine.evaluate(business, analysis, scan.id)
            score = score_engine.calculate(business, analysis, scan.id)
            with session_scope(factory) as session:
                repo = Repository(session)
                if analysis is not None:
                    repo.save_analysis(analysis)
                for opportunity in opportunities:
                    repo.save_opportunity(opportunity)
                repo.save_score(score)
            if progress:
                progress(position, len(businesses))
        scan.status = ScanStatus.COMPLETED
        scan.finished_at = utc_now()
        with session_scope(factory) as session:
            Repository(session).save_scan(scan)
        return scan
    except BaseException as exc:
        scan.status = ScanStatus.FAILED
        scan.finished_at = utc_now()
        scan.error = str(exc) if isinstance(exc, DiscoveryError) else "Scan interrompido ou falha interna; resultados anteriores preservados."
        with session_scope(factory) as session:
            Repository(session).save_scan(scan)
        if isinstance(exc, (DiscoveryError, KeyboardInterrupt, SystemExit)):
            raise
        raise RuntimeError(scan.error) from None
