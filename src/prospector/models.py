"""Validated data exchanged between discovery, analysis, and scoring."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, computed_field, model_validator


NonEmptyText = Annotated[str, Field(min_length=1)]


def utc_now() -> datetime:
    return datetime.now(UTC)


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class WebsiteDiscoveryStatus(StrEnum):
    UNKNOWN = "unknown"
    FOUND = "found"
    NOT_FOUND = "not_found"
    CONFIRMED_ABSENT = "confirmed_absent"


class CheckStatus(StrEnum):
    """UNKNOWN includes checks that were not performed or were inconclusive."""

    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"


class AnalysisStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class Evidence(DomainModel):
    code: NonEmptyText
    description: NonEmptyText
    source: NonEmptyText
    source_url: HttpUrl | None = None
    observed_at: datetime = Field(default_factory=utc_now)


class Business(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    discovered_at: datetime = Field(default_factory=utc_now)
    name: NonEmptyText
    category: NonEmptyText | None = None
    address: NonEmptyText | None = None
    website: HttpUrl | None = None
    website_status: WebsiteDiscoveryStatus = WebsiteDiscoveryStatus.UNKNOWN
    phone: NonEmptyText | None = None
    rating: float | None = Field(default=None, ge=0, le=5, allow_inf_nan=False)
    review_count: int | None = Field(default=None, ge=0)
    source: NonEmptyText
    source_id: NonEmptyText | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    appointment_based: CheckStatus = CheckStatus.UNKNOWN

    @model_validator(mode="after")
    def validate_website_status(self) -> "Business":
        if self.website is not None:
            if self.website_status in {WebsiteDiscoveryStatus.NOT_FOUND, WebsiteDiscoveryStatus.CONFIRMED_ABSENT}:
                raise ValueError("A website cannot be both supplied and not found")
            self.website_status = WebsiteDiscoveryStatus.FOUND
        elif self.website_status == WebsiteDiscoveryStatus.FOUND:
            raise ValueError("A found website requires a URL")
        return self


class ScanStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanKind(StrEnum):
    DISCOVERY = "discovery"
    MANUAL = "manual"  # one business re-analyzed with data the user supplied


class Scan(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    kind: ScanKind = ScanKind.DISCOVERY
    query: NonEmptyText
    location: NonEmptyText
    limit: int = Field(default=30, ge=1)
    status: ScanStatus = ScanStatus.PENDING
    created_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    error: NonEmptyText | None = None


class LinkCheck(DomainModel):
    url: HttpUrl
    status_code: int | None = Field(default=None, ge=100, le=599)
    error: NonEmptyText | None = None


class WebsiteAnalysis(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    business_id: UUID
    scan_id: UUID
    requested_url: HttpUrl
    final_url: HttpUrl | None = None
    analyzed_at: datetime = Field(default_factory=utc_now)
    status: AnalysisStatus
    status_code: int | None = Field(default=None, ge=100, le=599)
    redirect_chain: list[HttpUrl] = Field(default_factory=list)
    response_time_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    https: CheckStatus = CheckStatus.UNKNOWN
    title: NonEmptyText | None = None
    title_status: CheckStatus = CheckStatus.UNKNOWN
    meta_description: NonEmptyText | None = None
    meta_description_status: CheckStatus = CheckStatus.UNKNOWN
    mobile_viewport: CheckStatus = CheckStatus.UNKNOWN
    headings: list[NonEmptyText] = Field(default_factory=list)
    headings_status: CheckStatus = CheckStatus.UNKNOWN
    link_checks: list[LinkCheck] = Field(default_factory=list)
    phone: CheckStatus = CheckStatus.UNKNOWN
    whatsapp: CheckStatus = CheckStatus.UNKNOWN
    cta: CheckStatus = CheckStatus.UNKNOWN
    contact_form: CheckStatus = CheckStatus.UNKNOWN
    booking: CheckStatus = CheckStatus.UNKNOWN
    social_links: list[HttpUrl] = Field(default_factory=list)
    whatsapp_links: list[HttpUrl] = Field(default_factory=list)
    social_presence: CheckStatus = CheckStatus.UNKNOWN
    evidence: list[Evidence] = Field(default_factory=list)
    errors: list[NonEmptyText] = Field(default_factory=list)
    mobile_performance_score: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    mobile_performance_source: NonEmptyText | None = None


class Opportunity(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    business_id: UUID
    scan_id: UUID
    rule_code: NonEmptyText
    title: NonEmptyText
    description: NonEmptyText
    evidence: list[Evidence] = Field(min_length=1)
    suggested_services: list[NonEmptyText] = Field(default_factory=list)


class ScoreContribution(DomainModel):
    rule_code: NonEmptyText
    points: int = Field(ge=0, le=100)
    evidence: list[Evidence] = Field(min_length=1)


class ScoreClassification(StrEnum):
    LOW = "Low"
    MODERATE = "Moderate"
    GOOD = "Good"
    HIGH = "High"
    GOLD_NUGGET = "Gold Nugget"


class Score(DomainModel):
    business_id: UUID
    scan_id: UUID
    scoring_version: NonEmptyText
    calculated_at: datetime = Field(default_factory=utc_now)
    contributions: list[ScoreContribution] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_duplicate_rules(self) -> "Score":
        codes = [item.rule_code for item in self.contributions]
        if len(codes) != len(set(codes)):
            raise ValueError("A scoring rule can contribute only once")
        return self

    @computed_field
    @property
    def value(self) -> int:
        return min(100, sum(item.points for item in self.contributions))

    @computed_field
    @property
    def classification(self) -> ScoreClassification:
        if self.value < 30:
            return ScoreClassification.LOW
        if self.value < 50:
            return ScoreClassification.MODERATE
        if self.value < 70:
            return ScoreClassification.GOOD
        if self.value < 85:
            return ScoreClassification.HIGH
        return ScoreClassification.GOLD_NUGGET


class LeadStatus(StrEnum):
    """Manual, personal triage state; never triggers contact."""

    NEW = "new"
    REVIEWING = "reviewing"
    INTERESTING = "interesting"
    CONTACTED = "contacted"
    WON = "won"
    LOST = "lost"
    IGNORED = "ignored"


class LeadTracking(DomainModel):
    """Personal triage plus contact data the user verified and typed in themselves."""

    business_id: UUID
    status: LeadStatus = LeadStatus.NEW
    notes: Annotated[str, Field(max_length=10_000)] = ""
    website: HttpUrl | None = None
    no_website: bool = False
    phone: NonEmptyText | None = None
    whatsapp: HttpUrl | None = None
    instagram: HttpUrl | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_website(self) -> "LeadTracking":
        if self.website is not None and self.no_website:
            raise ValueError("A lead cannot have a website and be confirmed without one")
        return self

    @property
    def has_enrichment(self) -> bool:
        return bool(self.website or self.no_website or self.phone or self.whatsapp or self.instagram)
