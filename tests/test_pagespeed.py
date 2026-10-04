from uuid import uuid4

import httpx
import pytest

from prospector.analyzers.fetcher import PublicFetcher
from prospector.analyzers.pagespeed import PageSpeedError, PageSpeedProvider
from prospector.analyzers.website import HtmlWebsiteAnalyzer
from prospector.config import Settings
from prospector.models import Business
from prospector.opportunities.rules import OpportunityEngine
from prospector.scoring.engine import ScoreEngine


HTML = ("<html><head><title>Alpha</title></head><body><p>" + "Cortes de cabelo e barba para clientes. " * 4
        + "</p></body></html>")
SETTINGS = Settings(pagespeed_api_key="secret-key")


def provider(handler):
    return PageSpeedProvider(SETTINGS, httpx.Client(transport=httpx.MockTransport(handler)))


def lighthouse(score):
    return httpx.Response(200, json={"lighthouseResult": {"categories": {"performance": {"score": score}}}})


def test_measure_requests_mobile_performance_and_hides_key_from_evidence():
    def handler(request):
        assert request.url.host == "www.googleapis.com"
        assert request.url.params["strategy"] == "mobile" and request.url.params["url"] == "https://example.com/"
        return lighthouse(0.37)
    result = provider(handler).measure("https://example.com/")
    assert result.score == 37
    assert result.evidence.source == "pagespeed_insights"
    assert "secret-key" not in str(result.evidence.source_url)
    assert result.evidence.source_url.host == "pagespeed.web.dev"


@pytest.mark.parametrize("response", [httpx.Response(429), httpx.Response(500), httpx.Response(200, json={}),
                                      lighthouse(None)])
def test_measure_failures_raise_without_leaking_key(response):
    with pytest.raises(PageSpeedError) as error:
        provider(lambda request: response).measure("https://example.com/")
    assert "secret-key" not in str(error.value)


def test_provider_requires_key():
    with pytest.raises(ValueError):
        PageSpeedProvider(Settings(), httpx.Client())


def test_analyzer_records_measurement_that_scores_poor_performance(monkeypatch):
    monkeypatch.setattr("prospector.analyzers.fetcher.time.sleep", lambda _: None)

    def site(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text=HTML, headers={"content-type": "text/html"})

    fetcher = PublicFetcher(httpx.Client(transport=httpx.MockTransport(site)), Settings(), validator=lambda _: None)
    analyzer = HtmlWebsiteAnalyzer(fetcher, 0, provider(lambda request: lighthouse(0.31)))
    business = Business(name="Alpha", source="test", website="https://example.com")
    scan_id = uuid4()
    analysis = analyzer.analyze(business, scan_id)
    assert (analysis.mobile_performance_score, analysis.mobile_performance_source) == (31, "pagespeed_insights")
    score = ScoreEngine().calculate(business, analysis, scan_id)
    assert "poor_mobile_performance" in {item.rule_code for item in score.contributions}
    assert "poor_mobile_performance" in {item.rule_code for item in OpportunityEngine().evaluate(business, analysis, scan_id)}

    failing = HtmlWebsiteAnalyzer(fetcher, 0, provider(lambda request: httpx.Response(429)))
    analysis = failing.analyze(business, scan_id)
    assert analysis.mobile_performance_score is None and analysis.status == "completed"
    assert any("PageSpeed" in error for error in analysis.errors)
