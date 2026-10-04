from uuid import uuid4

import pytest

from prospector.models import Business, Evidence, Score, ScoreContribution, WebsiteAnalysis
from prospector.scoring.engine import ScoreEngine
from prospector.scoring.weights import ScoringConfig, Weights


@pytest.mark.parametrize("value, classification", [(0, "Low"), (29, "Low"), (30, "Moderate"), (49, "Moderate"), (50, "Good"), (69, "Good"), (70, "High"), (84, "High"), (85, "Gold Nugget"), (100, "Gold Nugget")])
def test_classification_boundaries(value, classification):
    evidence = Evidence(code="test", description="Observed", source="test")
    score = Score(business_id=uuid4(), scan_id=uuid4(), scoring_version="test",
                  contributions=[ScoreContribution(rule_code="test", points=value, evidence=[evidence])])
    assert score.classification == classification


def test_rules_are_deterministic_and_configurable():
    scan_id = uuid4()
    business = Business(name="Alpha", source="test", category="service.beauty.hairdresser", review_count=100)
    analysis = WebsiteAnalysis(business_id=business.id, scan_id=scan_id, requested_url="https://example.com",
                               status="completed", status_code=200, mobile_viewport="absent", cta="absent",
                               booking="absent", whatsapp="present", social_presence="present", response_time_ms=4000,
                               evidence=[Evidence(code="whatsapp", description="WhatsApp link found", source="test"),
                                         Evidence(code="social_presence", description="Social link found", source="test")])
    engine = ScoreEngine()
    first = engine.calculate(business, analysis, scan_id)
    second = engine.calculate(business, analysis, scan_id)
    assert first.value == second.value == 65
    assert first.contributions == second.contributions
    assert all(item.evidence for item in first.contributions)
    config = ScoringConfig(weights=Weights(no_cta=0))
    assert ScoreEngine(config).calculate(business, analysis, scan_id).value == 55
    assert config.version != engine.config.version


def test_missing_information_scores_zero():
    business = Business(name="Alpha", source="test", website_status="not_found")
    assert ScoreEngine().calculate(business, None, uuid4()).value == 0


def test_viewport_does_not_imply_poor_mobile_performance():
    scan_id = uuid4()
    business = Business(name="Alpha", source="test")
    analysis = WebsiteAnalysis(business_id=business.id, scan_id=scan_id, requested_url="https://example.com", status="completed", status_code=200, mobile_viewport="absent")
    score = ScoreEngine().calculate(business, analysis, scan_id)
    assert [item.rule_code for item in score.contributions] == ["missing_viewport"]


def test_confirmed_absence_requires_evidence():
    business = Business(name="Alpha", source="test", website_status="confirmed_absent")
    scan_id = uuid4()
    assert ScoreEngine().calculate(business, None, scan_id).value == 0
    business.evidence.append(Evidence(code="website_absent_confirmed", description="Confirmed by authorized source", source="manual"))
    assert ScoreEngine().calculate(business, None, scan_id).value == 25


def test_thresholds_and_mobile_measurement_source():
    scan_id = uuid4()
    business = Business(name="Alpha", source="test", review_count=49)
    analysis = WebsiteAnalysis(business_id=business.id, scan_id=scan_id, requested_url="https://example.com", status="completed", status_code=200, response_time_ms=3000, mobile_performance_score=30)
    assert ScoreEngine().calculate(business, analysis, scan_id).value == 0
    analysis.mobile_performance_source = "lighthouse_mobile"
    assert ScoreEngine().calculate(business, analysis, scan_id).value == 20


def test_total_is_capped_at_100():
    business = Business(name="Alpha", source="test", review_count=100,
                        evidence=[Evidence(code="social_present", description="Known social page", source="test")])
    config = ScoringConfig(weights=Weights(established_reviews=80, social_present=80))
    assert ScoreEngine(config).calculate(business, None, uuid4()).value == 100
