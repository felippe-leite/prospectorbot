"""HTTP payloads. Domain models are reused as-is wherever they fit."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator

from prospector.enrichment.manual import parse_instagram, parse_phone, parse_website, parse_whatsapp
from prospector.models import (
    Business, LeadStatus, LeadTracking, Opportunity, Scan, ScoreClassification, ScoreContribution,
    WebsiteAnalysis, WebsiteDiscoveryStatus,
)
from prospector.opportunities.tags import OpportunityTag
from prospector.service import ScanStage


class Health(BaseModel):
    status: str = "ok"
    version: str
    discovery_configured: bool
    performance_configured: bool


class ScanRequest(BaseModel):
    query: Annotated[str, Field(min_length=1, max_length=120)]
    location: Annotated[str, Field(min_length=1, max_length=120)]
    limit: Annotated[int, Field(ge=1, le=50)] = 30


class ScanProgress(BaseModel):
    """Live state of a scan running in this API process."""

    stage: ScanStage
    analyzed: int
    total: int | None
    current_business: str | None
    has_website: bool | None


class ScanSummary(BaseModel):
    scan: Scan
    analyzed: int
    gold_nuggets: int
    progress: ScanProgress | None = None


class LeadSummary(BaseModel):
    business_id: UUID
    scan_id: UUID
    name: str
    category: str | None
    address: str | None
    query: str
    location: str
    website: HttpUrl | None
    website_status: WebsiteDiscoveryStatus
    rating: float | None
    review_count: int | None
    score: int
    classification: ScoreClassification
    opportunity_count: int
    tags: list[OpportunityTag]
    status: LeadStatus
    analyzed_at: datetime


class OpportunityDetail(Opportunity):
    points: int = Field(description="Score points from the same rule; 0 when the rule is not weighted.")


class Appearance(BaseModel):
    scan_id: UUID
    query: str
    location: str
    created_at: datetime
    score: int
    classification: ScoreClassification


class LeadDetail(BaseModel):
    scan: Scan
    business: Business
    score: int
    classification: ScoreClassification
    scoring_version: str
    contributions: list[ScoreContribution]
    analysis: WebsiteAnalysis | None
    opportunities: list[OpportunityDetail]
    tracking: LeadTracking
    appearances: list[Appearance]


class TrackingUpdate(BaseModel):
    """Partial update: omitted fields are kept; null or "" clears a contact field."""

    status: LeadStatus | None = None
    notes: Annotated[str | None, Field(max_length=10_000)] = None
    website: HttpUrl | None = None
    no_website: bool | None = None
    phone: str | None = None
    whatsapp: HttpUrl | None = None
    instagram: HttpUrl | None = None

    @field_validator("website", "phone", "whatsapp", "instagram", mode="before")
    @classmethod
    def parse_contact(cls, value, info):
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        if not isinstance(value, str) or len(value) > 500:
            raise ValueError("Invalid value.")
        parser = {"website": parse_website, "phone": parse_phone,
                  "whatsapp": parse_whatsapp, "instagram": parse_instagram}[info.field_name]
        return parser(value)


class Stats(BaseModel):
    businesses: int
    opportunities: int
    gold_nuggets: int
    average_score: float | None
    scans: int
