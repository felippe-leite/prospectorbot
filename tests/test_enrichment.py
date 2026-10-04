import pytest

from prospector.database.repository import Repository
from prospector.database.session import session_scope
from prospector.enrichment.manual import (
    apply_enrichment, enrich_business, parse_instagram, parse_phone, parse_website, parse_whatsapp,
)
from prospector.models import Business, Evidence, LeadTracking, Scan
from prospector.opportunities.rules import OpportunityEngine
from prospector.scoring.engine import ScoreEngine


def unlisted():
    return Business(name="Alpha", source="geoapify", source_id="1", website_status="not_found", evidence=[
        Evidence(code="website_not_found", description="Website oficial não informado pela fonte.", source="geoapify")])


def test_parsers_normalize_user_input():
    assert str(parse_website("alpha.com.br")) == "https://alpha.com.br/"
    assert str(parse_whatsapp("(61) 99999-0000")) == "https://wa.me/5561999990000"
    assert str(parse_whatsapp("https://wa.me/5561999990000")) == "https://wa.me/5561999990000"
    assert str(parse_instagram("@barbearia.alpha")) == "https://www.instagram.com/barbearia.alpha/"
    assert str(parse_instagram("https://instagram.com/barbearia.alpha?igsh=x")) == "https://www.instagram.com/barbearia.alpha/"
    assert parse_phone("+55 61 3333-4444") == "+556133334444"
    for parser, value in [(parse_website, "instagram.com/alpha"), (parse_website, "not a url"),
                          (parse_whatsapp, "123"), (parse_instagram, "https://facebook.com/alpha"), (parse_phone, "12")]:
        with pytest.raises(ValueError):
            parser(value)


def test_confirmed_absence_and_contacts_feed_existing_rules():
    business = unlisted()
    tracking = LeadTracking(business_id=business.id, no_website=True,
                            whatsapp="https://wa.me/5561999990000", instagram="https://www.instagram.com/alpha/")
    enriched = enrich_business(business, tracking)
    assert enriched.website_status == "confirmed_absent"
    score = ScoreEngine().calculate(enriched, None, Scan(query="q", location="l").id)
    assert {item.rule_code: item.points for item in score.contributions} == {
        "no_website": 25, "whatsapp_present": 5, "social_present": 5}
    assert [item.rule_code for item in OpportunityEngine().evaluate(enriched, None, score.scan_id)] == ["no_website"]


def test_manual_website_replaces_unlisted_status():
    business = unlisted()
    enriched = enrich_business(business, LeadTracking(business_id=business.id, website="https://alpha.com.br", phone="+5561999990000"))
    assert str(enriched.website) == "https://alpha.com.br/" and enriched.website_status == "found"
    assert enriched.phone == "+5561999990000"
    assert [item.code for item in enriched.evidence] == ["website_found"]


def test_source_website_wins_over_stale_absence_confirmation():
    business = Business(name="Alpha", source="geoapify", source_id="1", website="https://alpha.com.br")
    enriched = enrich_business(business, LeadTracking(business_id=business.id, no_website=True))
    assert enriched.website_status == "found"


def test_apply_enrichment_uses_tracking_of_stored_business(session_factory):
    scan = Scan(query="q", location="l")
    with session_scope(session_factory) as session:
        repo = Repository(session)
        repo.save_scan(scan)
        stored = repo.save_business(unlisted(), scan.id)
        repo.save_tracking(LeadTracking(business_id=stored.id, no_website=True))
    with session_scope(session_factory) as session:
        repo = Repository(session)
        assert apply_enrichment(repo, stored).website_status == "confirmed_absent"
        # The stored snapshot itself keeps only what the source reported.
        assert repo.get_business(stored.id, scan.id).website_status == "not_found"


def test_tracking_rejects_website_with_confirmed_absence():
    with pytest.raises(ValueError):
        LeadTracking(business_id=unlisted().id, website="https://alpha.com.br", no_website=True)
