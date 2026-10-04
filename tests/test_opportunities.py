from uuid import uuid4

from prospector.models import Business, Evidence, LinkCheck, WebsiteAnalysis
from prospector.opportunities.rules import OpportunityEngine


def test_unknown_website_is_not_an_opportunity():
    business = Business(name="Alpha", source="test", website_status="not_found")
    assert OpportunityEngine().evaluate(business, None, uuid4()) == []


def test_failed_analysis_does_not_invent_missing_features():
    scan_id = uuid4()
    business = Business(name="Alpha", source="test", category="service.beauty.hairdresser")
    analysis = WebsiteAnalysis(business_id=business.id, scan_id=scan_id, requested_url="https://example.com", status="failed", errors=["Timeout"])
    assert OpportunityEngine().evaluate(business, analysis, scan_id) == []


def test_opportunities_include_scoped_evidence_and_inferences():
    scan_id = uuid4()
    business = Business(name="Alpha", source="test", category="service.beauty.hairdresser")
    analysis = WebsiteAnalysis(business_id=business.id, scan_id=scan_id, requested_url="https://example.com", status="completed", status_code=200,
                               cta="absent", booking="absent", mobile_viewport="absent", link_checks=[LinkCheck(url="https://example.com/broken", status_code=404), LinkCheck(url="https://example.com/timeout", error="Timeout")])
    opportunities = OpportunityEngine().evaluate(business, analysis, scan_id)
    assert {item.rule_code for item in opportunities} == {"no_cta", "no_booking", "missing_viewport", "broken_links"}
    booking = next(item for item in opportunities if item.rule_code == "no_booking")
    assert "Inferência" in booking.evidence[0].description
    broken = next(item for item in opportunities if item.rule_code == "broken_links")
    assert len(broken.evidence) == 1


def test_explicitly_non_appointment_business_does_not_get_booking_opportunity():
    scan_id = uuid4()
    business = Business(name="Alpha", source="test", category="service.beauty.hairdresser", appointment_based="absent")
    analysis = WebsiteAnalysis(business_id=business.id, scan_id=scan_id, requested_url="https://example.com", status="completed", status_code=200, booking="absent")
    assert OpportunityEngine().evaluate(business, analysis, scan_id) == []
