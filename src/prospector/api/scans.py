"""Background scan execution with live, in-memory progress for the API."""

from collections.abc import Callable
from contextlib import AbstractContextManager
import logging
import threading
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from prospector.analyzers.website import WebsiteAnalyzer
from prospector.api.schemas import ScanProgress, ScanRequest
from prospector.config import Settings
from prospector.database.repository import Repository
from prospector.database.session import session_scope
from prospector.discovery.base import BusinessProvider, DiscoveryError
from prospector.enrichment.manual import apply_enrichment
from prospector.models import Business, Scan, ScanKind, ScanStatus, utc_now
from prospector.scoring.weights import ScoringConfig
from prospector.service import ScanEvent, ScanStage, run_scan


Pipeline = Callable[[Settings], AbstractContextManager[tuple[BusinessProvider, WebsiteAnalyzer]]]
logger = logging.getLogger(__name__)


class ScanInProgress(RuntimeError):
    pass


class StaticProvider:
    """Re-analyzes known businesses instead of discovering new ones."""

    def __init__(self, businesses: list[Business]):
        self.businesses = businesses

    def search(self, query: str, location: str, limit: int) -> list[Business]:
        return self.businesses[:limit]


class ScanRunner:
    """Runs one scan at a time: requests to sources stay sequential and rate-limited."""

    def __init__(self, settings: Settings, factory: sessionmaker[Session], scoring: ScoringConfig, pipeline: Pipeline):
        self.settings = settings
        self.factory = factory
        self.scoring = scoring
        self.pipeline = pipeline
        self._lock = threading.Lock()
        self._active: Scan | None = None
        self._progress: ScanProgress | None = None
        self._thread: threading.Thread | None = None

    def progress(self, scan_id: UUID) -> ScanProgress | None:
        with self._lock:
            if self._active is not None and self._active.id == scan_id:
                return self._progress
            return None

    def start(self, request: ScanRequest) -> Scan:
        return self._launch(Scan(query=request.query, location=request.location, limit=request.limit))

    def start_manual(self, business: Business, location: str) -> Scan:
        """Re-score one business with the data the user supplied (see apply_enrichment)."""
        scan = Scan(kind=ScanKind.MANUAL, query=business.name, location=location, limit=1)
        return self._launch(scan, StaticProvider([business]))

    def _launch(self, scan: Scan, provider: BusinessProvider | None = None) -> Scan:
        with self._lock:
            if self._active is not None:
                raise ScanInProgress("A prospecting session is already running.")
            with session_scope(self.factory) as session:
                Repository(session).save_scan(scan)
            self._active = scan
            self._progress = ScanProgress(stage=ScanStage.DISCOVERY, analyzed=0, total=None,
                                          current_business=None, has_website=None)
            self._thread = threading.Thread(target=self._run, args=(scan, provider), name=f"scan-{scan.id}", daemon=True)
            self._thread.start()
        return scan

    def _on_event(self, event: ScanEvent) -> None:
        with self._lock:
            analyzed = self._progress.analyzed if self._progress else 0
            self._progress = ScanProgress(stage=event.stage, analyzed=analyzed, total=event.total,
                                          current_business=event.business, has_website=event.has_website)

    def _on_progress(self, done: int, total: int) -> None:
        with self._lock:
            if self._progress is not None:
                self._progress = self._progress.model_copy(update={"analyzed": done, "total": total})

    def _run(self, scan: Scan, provider: BusinessProvider | None) -> None:
        try:
            with self.pipeline(self.settings) as (discovery, analyzer):
                run_scan(scan.query, scan.location, scan.limit, provider or discovery, analyzer, self.factory,
                         self.scoring, progress=self._on_progress, on_event=self._on_event, scan=scan,
                         enrich=apply_enrichment)
        except DiscoveryError as exc:
            logger.info("Scan %s stopped: %s", scan.id, exc)
        except Exception:
            # run_scan already stored a safe error message; this covers setup failures.
            logger.exception("Scan %s failed", scan.id)
            if scan.status != ScanStatus.FAILED:
                self._mark_failed(scan, "Falha ao preparar o scan; confira configuração e conexão.")
        finally:
            with self._lock:
                self._active = None
                self._progress = None

    def _mark_failed(self, scan: Scan, message: str) -> None:
        scan.status = ScanStatus.FAILED
        scan.finished_at = utc_now()
        scan.error = message
        with session_scope(self.factory) as session:
            Repository(session).save_scan(scan)

    def shutdown(self) -> None:
        """Record an interrupted scan instead of leaving it 'running' forever."""
        with self._lock:
            scan = self._active
        if scan is not None and scan.status == ScanStatus.RUNNING:
            self._mark_failed(scan, "Scan interrompido: a API foi encerrada; resultados anteriores preservados.")
