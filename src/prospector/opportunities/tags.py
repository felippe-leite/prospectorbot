"""Groups rule codes into the service areas used to filter leads."""

from collections.abc import Iterable
from enum import StrEnum


class OpportunityTag(StrEnum):
    LANDING_PAGE = "landing_page"
    WEBSITE_REDESIGN = "website_redesign"
    PERFORMANCE = "performance"
    WHATSAPP = "whatsapp"
    BOOKING = "booking"
    SEO = "seo"


RULE_TAGS = {
    "no_website": OpportunityTag.LANDING_PAGE,
    "website_not_listed": OpportunityTag.LANDING_PAGE,
    "missing_viewport": OpportunityTag.WEBSITE_REDESIGN,
    "no_cta": OpportunityTag.WEBSITE_REDESIGN,
    "no_https": OpportunityTag.WEBSITE_REDESIGN,
    "broken_links": OpportunityTag.WEBSITE_REDESIGN,
    "http_error": OpportunityTag.WEBSITE_REDESIGN,
    "slow_site": OpportunityTag.PERFORMANCE,
    "poor_mobile_performance": OpportunityTag.PERFORMANCE,
    "no_whatsapp_cta": OpportunityTag.WHATSAPP,
    "no_booking": OpportunityTag.BOOKING,
    "missing_title": OpportunityTag.SEO,
    "missing_description": OpportunityTag.SEO,
}


def tags_for(rule_codes: Iterable[str]) -> list[OpportunityTag]:
    found = {RULE_TAGS[code] for code in rule_codes if code in RULE_TAGS}
    return [tag for tag in OpportunityTag if tag in found]
