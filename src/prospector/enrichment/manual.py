"""Contact data the user verified and typed in, applied on top of discovered data."""

import re

from pydantic import HttpUrl

from prospector.database.repository import Repository
from prospector.enrichment.normalization import (
    SOCIAL_HOSTS, WHATSAPP_HOSTS, host_matches, normalize_phone, normalize_website,
)
from prospector.models import Business, Evidence, LeadTracking, WebsiteDiscoveryStatus, utc_now


SOURCE = "manual"
INSTAGRAM_HANDLE = re.compile(r"@?([A-Za-z0-9._]{1,30})")


def parse_website(value: str) -> HttpUrl:
    url = normalize_website(value)
    if url is None:
        raise ValueError("Invalid website URL.")
    if host_matches(url.host, SOCIAL_HOSTS | WHATSAPP_HOSTS):
        raise ValueError("Social or WhatsApp links are not a website; use the Instagram or WhatsApp fields.")
    return url


def parse_phone(value: str) -> str:
    phone = normalize_phone(value)
    if phone is None:
        raise ValueError("Invalid phone number.")
    if not phone.startswith("+") and len(phone) in {10, 11}:
        phone = "+55" + phone  # Brazilian number typed with area code but no country code
    return phone


def parse_whatsapp(value: str) -> HttpUrl:
    digits = re.sub(r"\D", "", value)
    if len(digits) in {10, 11}:
        digits = "55" + digits  # Brazilian number typed without the country code
    if not 12 <= len(digits) <= 15:
        raise ValueError("Invalid WhatsApp number; include the area code (DDD).")
    return HttpUrl(f"https://wa.me/{digits}")


def parse_instagram(value: str) -> HttpUrl:
    value = value.strip()
    if match := INSTAGRAM_HANDLE.fullmatch(value):
        handle = match.group(1)
    else:
        url = normalize_website(value)
        if url is None or not host_matches(url.host, {"instagram.com"}) or not (url.path or "").strip("/"):
            raise ValueError("Use an Instagram profile URL or @handle.")
        handle = url.path.strip("/").split("/")[0]
    return HttpUrl(f"https://www.instagram.com/{handle}/")


def apply_enrichment(repo: Repository, business: Business) -> Business:
    """Merge the user's verified data into a stored (canonical) business for scoring."""
    tracking = repo.get_tracking(business.id)
    return enrich_business(business, tracking) if tracking.has_enrichment else business


def enrich_business(business: Business, tracking: LeadTracking) -> Business:
    observed = tracking.updated_at or utc_now()
    evidence = list(business.evidence)
    changes: dict = {}

    def add(code: str, description: str, url: HttpUrl | None = None) -> None:
        evidence.append(Evidence(code=code, description=description, source=SOURCE, source_url=url, observed_at=observed))

    if tracking.website is not None:
        evidence = [item for item in evidence if item.code != "website_not_found"]
        changes.update(website=tracking.website, website_status=WebsiteDiscoveryStatus.FOUND)
        add("website_found", "Website informado manualmente pelo usuário.", tracking.website)
    elif business.website is None and tracking.no_website:
        # The only path to a confirmed absence: a person checked and said so.
        changes.update(website_status=WebsiteDiscoveryStatus.CONFIRMED_ABSENT)
        add("website_absent_confirmed", "Usuário verificou manualmente que o negócio não tem website próprio.")
    if tracking.phone:
        changes["phone"] = tracking.phone
    if tracking.whatsapp and not any(item.code == "whatsapp_present" for item in evidence):
        add("whatsapp_present", "WhatsApp verificado e informado manualmente pelo usuário.", tracking.whatsapp)
    if tracking.instagram and not any(item.code == "social_present" for item in evidence):
        add("social_present", "Instagram verificado e informado manualmente pelo usuário.", tracking.instagram)
    return Business.model_validate({**business.model_dump(), **changes, "evidence": evidence})
