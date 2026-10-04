"""Lead read models: one row per business, from its most recent scored scan."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from uuid import UUID

from prospector.api.schemas import LeadSummary, Stats
from prospector.database.repository import RankedLead
from prospector.enrichment.normalization import search_key
from prospector.models import LeadStatus, LeadTracking, ScoreClassification, WebsiteDiscoveryStatus
from prospector.opportunities.tags import OpportunityTag, tags_for


GOLD_NUGGET_SCORE = 85


def latest_per_business(rows: Iterable[RankedLead]) -> list[RankedLead]:
    """Rows arrive newest scan first, so the first one per business wins."""
    seen: set[UUID] = set()
    latest = []
    for row in rows:
        if row.business.id not in seen:
            seen.add(row.business.id)
            latest.append(row)
    return latest


def summarize(row: RankedLead, tracking: LeadTracking | None) -> LeadSummary:
    codes = [item.rule_code for item in row.opportunities] + [item.rule_code for item in row.score.contributions]
    business = row.business
    # Data the user verified takes precedence over what the source reported.
    website, website_status = business.website, business.website_status
    if tracking and tracking.website:
        website, website_status = tracking.website, WebsiteDiscoveryStatus.FOUND
    elif tracking and tracking.no_website and website is None:
        website_status = WebsiteDiscoveryStatus.CONFIRMED_ABSENT
    return LeadSummary(
        business_id=business.id, scan_id=row.scan.id, name=business.name, category=business.category,
        address=business.address, query=row.scan.query, location=row.scan.location,
        website=website, website_status=website_status, rating=business.rating,
        review_count=business.review_count, score=row.score.value, classification=row.score.classification,
        opportunity_count=len(row.opportunities), tags=tags_for(codes),
        status=tracking.status if tracking else LeadStatus.NEW, analyzed_at=row.score.calculated_at,
    )


@dataclass
class LeadFilters:
    q: str | None = None
    min_score: int | None = None
    classifications: list[ScoreClassification] = field(default_factory=list)
    website: bool | None = None
    tags: list[OpportunityTag] = field(default_factory=list)
    statuses: list[LeadStatus] = field(default_factory=list)

    def matches(self, lead: LeadSummary) -> bool:
        # Filters combine with AND; values inside one filter combine with OR.
        return ((not self.q or search_key(self.q) in search_key(lead.name))
                and (self.min_score is None or lead.score >= self.min_score)
                and (not self.classifications or lead.classification in self.classifications)
                and (self.website is None or (lead.website is not None) == self.website)
                and (not self.tags or any(tag in lead.tags for tag in self.tags))
                and (not self.statuses or lead.status in self.statuses))


def stats(leads: list[LeadSummary], scans: int) -> Stats:
    return Stats(
        businesses=len(leads), opportunities=sum(lead.opportunity_count for lead in leads),
        gold_nuggets=sum(lead.score >= GOLD_NUGGET_SCORE for lead in leads),
        average_score=round(sum(lead.score for lead in leads) / len(leads), 1) if leads else None,
        scans=scans,
    )
