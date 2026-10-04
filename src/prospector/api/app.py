"""HTTP API for the web frontend. Read-only over results, except personal lead tracking."""

from collections.abc import Iterator
from contextlib import asynccontextmanager
import logging
from typing import Annotated, Literal
from uuid import UUID

import httpx

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy.orm import Session

from prospector.api.leads import LeadFilters, latest_per_business, stats, summarize
from prospector.api.scans import Pipeline, ScanInProgress, ScanRunner
from prospector.api.schemas import (
    Appearance, Health, LeadDetail, LeadSummary, OpportunityDetail, ScanRequest, ScanSummary, Stats,
    TrackingUpdate,
)
from prospector.analyzers.fetcher import USER_AGENT
from prospector.config import Settings
from prospector.database.repository import Repository
from prospector.database.session import create_database_engine, create_session_factory, initialize_database, session_scope
from prospector.discovery.base import DiscoveryError
from prospector.discovery.categories import CATEGORIES
from prospector.discovery.geoapify import GeoapifyProvider, category_for
from prospector.models import LeadStatus, LeadTracking, Scan, ScanKind, ScoreClassification, utc_now
from prospector.opportunities.tags import OpportunityTag
from prospector.pipeline import scan_pipeline
from prospector.scoring.weights import ScoringConfig


VERSION = "0.1.0"


def create_app(settings: Settings | None = None, pipeline: Pipeline = scan_pipeline) -> FastAPI:
    settings = settings or Settings.from_env()
    scoring = ScoringConfig.load(settings.scoring_config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = create_database_engine(settings)
        initialize_database(engine)
        factory = create_session_factory(engine)
        app.state.factory = factory
        app.state.runner = ScanRunner(settings, factory, scoring, pipeline)
        # Separate client: location lookups never share a connection with business websites.
        with httpx.Client(trust_env=False, headers={"User-Agent": USER_AGENT}) as geo_client:
            app.state.locations = GeoapifyProvider(settings, geo_client)
            try:
                yield
            finally:
                app.state.runner.shutdown()
                engine.dispose()

    app = FastAPI(title="ProspectorBot API", version=VERSION, lifespan=lifespan)
    # No credentials or authentication: the API is meant to listen on localhost only.
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Content-Type"])

    def session(request: Request) -> Iterator[Session]:
        with session_scope(request.app.state.factory) as current:
            yield current

    def repository(current: Annotated[Session, Depends(session)]) -> Repository:
        return Repository(current)

    def runner(request: Request) -> ScanRunner:
        return request.app.state.runner

    Repo = Annotated[Repository, Depends(repository)]
    Runner = Annotated[ScanRunner, Depends(runner)]

    def summary(repo: Repository, scans: ScanRunner, scan: Scan, counts=None) -> ScanSummary:
        counts = counts if counts is not None else repo.scan_counts()
        analyzed, gold = counts.get(scan.id, (0, 0))
        return ScanSummary(scan=scan, analyzed=analyzed, gold_nuggets=gold, progress=scans.progress(scan.id))

    def all_leads(repo: Repository, scan_id: UUID | None = None) -> list[LeadSummary]:
        rows = repo.list_ranked(scan_id)
        tracking = repo.list_tracking()
        return [summarize(row, tracking.get(row.business.id)) for row in latest_per_business(rows)]

    @app.get("/api/health", response_model=Health)
    def health():
        return Health(version=VERSION, discovery_configured=settings.geoapify_api_key is not None,
                      performance_configured=settings.pagespeed_api_key is not None)

    @app.get("/api/categories", response_model=list[str])
    def categories():
        """Business types accepted by discovery, for autocomplete."""
        return sorted(CATEGORIES)

    @app.get("/api/locations", response_model=list[str])
    def locations(request: Request, q: Annotated[str, Query(min_length=2, max_length=80)]):
        """City/region suggestions for the prospecting form (Brazil)."""
        if settings.geoapify_api_key is None:
            return []
        try:
            return request.app.state.locations.suggest_locations(q.strip())
        except DiscoveryError as exc:
            logging.getLogger(__name__).info("Location suggestions unavailable: %s", exc)
            raise HTTPException(502, "Location suggestions are unavailable right now.")

    @app.delete("/api/data", status_code=204)
    def clear_data(repo: Repo, scans: Runner):
        """Remove all prospecting data, statuses and notes. Cannot be undone."""
        if scans.busy:
            raise HTTPException(409, "Wait for the running prospecting session to finish.")
        repo.clear_all()
        return Response(status_code=204)

    @app.get("/api/stats", response_model=Stats)
    def get_stats(repo: Repo):
        return stats(all_leads(repo), scans=sum(scan.kind == ScanKind.DISCOVERY for scan in repo.list_scans()))

    @app.get("/api/scans", response_model=list[ScanSummary])
    def list_scans(repo: Repo, scans: Runner):
        counts = repo.scan_counts()
        return [summary(repo, scans, scan, counts) for scan in repo.list_scans()]

    @app.post("/api/scans", response_model=ScanSummary, status_code=202)
    def start_scan(body: ScanRequest, repo: Repo, scans: Runner):
        if settings.geoapify_api_key is None:
            raise HTTPException(503, "GEOAPIFY_API_KEY is not configured on the server. See README.md.")
        try:
            category_for(body.query)
        except DiscoveryError:
            raise HTTPException(422, f"Unrecognized business type “{body.query.strip()}”. Pick one of the suggestions "
                                     "shown while typing, or use a Geoapify category (e.g. catering.restaurant).")
        try:
            scan = scans.start(body)
        except ScanInProgress as exc:
            raise HTTPException(409, str(exc))
        return summary(repo, scans, scan)

    @app.get("/api/scans/{scan_id}", response_model=ScanSummary)
    def get_scan(scan_id: UUID, repo: Repo, scans: Runner):
        scan = repo.get_scan(scan_id)
        if scan is None:
            raise HTTPException(404, "Scan not found.")
        return summary(repo, scans, scan)

    @app.get("/api/leads", response_model=list[LeadSummary])
    def list_leads(
        repo: Repo,
        scan_id: UUID | None = None,
        q: Annotated[str | None, Query(max_length=120)] = None,
        min_score: Annotated[int | None, Query(ge=0, le=100)] = None,
        classification: Annotated[list[ScoreClassification], Query()] = [],
        website: Literal["has", "none"] | None = None,
        tag: Annotated[list[OpportunityTag], Query()] = [],
        status: Annotated[list[LeadStatus], Query()] = [],
        sort: Literal["score", "recent"] = "score",
        limit: Annotated[int | None, Query(ge=1, le=1000)] = None,
    ):
        filters = LeadFilters(q=q, min_score=min_score, classifications=classification,
                              website=None if website is None else website == "has", tags=tag, statuses=status)
        leads = [lead for lead in all_leads(repo, scan_id) if filters.matches(lead)]
        if sort == "recent":
            leads.sort(key=lambda lead: lead.analyzed_at, reverse=True)
        else:
            leads.sort(key=lambda lead: (-lead.score, lead.name.casefold()))
        return leads[:limit]

    @app.get("/api/leads/{business_id}", response_model=LeadDetail)
    def get_lead(business_id: UUID, repo: Repo, scan_id: UUID | None = None):
        rows = repo.list_ranked(business_id=business_id)
        row = next((item for item in rows if scan_id is None or item.scan.id == scan_id), None)
        if row is None:
            raise HTTPException(404, "Lead not found.")
        points = {item.rule_code: item.points for item in row.score.contributions}
        analyses = repo.list_analyses(business_id, row.scan.id)
        return LeadDetail(
            scan=row.scan, business=row.business, score=row.score.value,
            classification=row.score.classification, scoring_version=row.score.scoring_version,
            contributions=sorted(row.score.contributions, key=lambda item: -item.points),
            analysis=analyses[-1] if analyses else None,
            opportunities=sorted((OpportunityDetail(**item.model_dump(), points=points.get(item.rule_code, 0))
                                  for item in row.opportunities), key=lambda item: -item.points),
            tracking=repo.get_tracking(business_id),
            appearances=[Appearance(scan_id=item.scan.id, query=item.scan.query, location=item.scan.location,
                                    created_at=item.scan.created_at, score=item.score.value,
                                    classification=item.score.classification) for item in rows],
        )

    @app.patch("/api/leads/{business_id}", response_model=LeadTracking)
    def update_tracking(business_id: UUID, body: TrackingUpdate, repo: Repo):
        if repo.get_business(business_id) is None:
            raise HTTPException(404, "Lead not found.")
        changes = body.model_dump(exclude_unset=True)
        for field in ("status", "notes", "no_website"):
            if changes.get(field, ...) is None:
                changes.pop(field)
        if changes.get("website"):
            changes.setdefault("no_website", False)
        if changes.get("no_website"):
            changes.setdefault("website", None)
        try:
            tracking = LeadTracking.model_validate(
                {**repo.get_tracking(business_id).model_dump(), **changes, "updated_at": utc_now()})
        except ValidationError:
            raise HTTPException(422, "A lead cannot have a website and be confirmed without one.")
        return repo.save_tracking(tracking)

    @app.post("/api/leads/{business_id}/rescore", response_model=ScanSummary, status_code=202)
    def rescore_lead(business_id: UUID, repo: Repo, scans: Runner):
        rows = repo.list_ranked(business_id=business_id)
        if not rows:
            raise HTTPException(404, "Lead not found.")
        try:
            scan = scans.start_manual(rows[0].business, rows[0].scan.location)
        except ScanInProgress as exc:
            raise HTTPException(409, str(exc))
        return summary(repo, scans, scan)

    return app
