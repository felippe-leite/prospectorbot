from uuid import uuid4

import pytest

from prospector.database.repository import Repository
from prospector.database.session import session_scope
from prospector.discovery.base import DiscoveryError
from prospector.models import Business, WebsiteAnalysis
from prospector.service import run_scan


class Provider:
    def __init__(self, businesses):
        self.businesses = businesses

    def search(self, query, location, limit):
        return self.businesses


class Analyzer:
    def __init__(self):
        self.calls = 0

    def analyze(self, business, scan_id):
        self.calls += 1
        return WebsiteAnalysis(business_id=business.id, scan_id=scan_id, requested_url=business.website,
                               status="failed", errors=["Timeout"])


def test_service_deduplicates_provider_results_and_preserves_unknowns(session_factory):
    businesses = [Business(name="Alpha", source="test", source_id="123"),
                  Business(name="Alpha", source="test", source_id="123"),
                  Business(name="Beta", source="test", website="https://example.com")]
    analyzer = Analyzer()
    scan = run_scan("barbearias", "Campinas", 30, Provider(businesses), analyzer, session_factory)
    assert scan.status == "completed"
    assert analyzer.calls == 1
    with session_scope(session_factory) as session:
        repo = Repository(session)
        assert len(repo.list_scores(scan.id)) == 2
        assert all(score.value == 0 for score in repo.list_scores(scan.id))


def test_service_marks_discovery_failure_without_empty_success(session_factory):
    class FailingProvider:
        def search(self, query, location, limit):
            raise DiscoveryError("Rate limit reached")
    with pytest.raises(DiscoveryError):
        run_scan("barbearias", "Campinas", 30, FailingProvider(), Analyzer(), session_factory)
    with session_scope(session_factory) as session:
        scans = Repository(session).list_scans()
        assert scans[0].status == "failed"
        assert scans[0].error == "Rate limit reached"


def test_service_enforces_limit_even_if_provider_returns_more(session_factory):
    businesses = [Business(name=str(index), source="test", source_id=str(index)) for index in range(4)]
    scan = run_scan("barbearias", "Campinas", 2, Provider(businesses), Analyzer(), session_factory)
    with session_scope(session_factory) as session:
        assert len(Repository(session).list_businesses(scan.id)) == 2


def test_service_isolates_unexpected_analyzer_errors(session_factory):
    class CrashingAnalyzer:
        def analyze(self, business, scan_id):
            raise TypeError("unexpected")
    businesses = [Business(name=str(index), source="test", source_id=str(index), website="https://example.com")
                  for index in range(3)]
    scan = run_scan("barbearias", "Campinas", 30, Provider(businesses), CrashingAnalyzer(), session_factory)
    assert scan.status == "completed"
    with session_scope(session_factory) as session:
        repo = Repository(session)
        assert len(repo.list_scores(scan.id)) == 3
        for business in repo.list_businesses(scan.id):
            [analysis] = repo.list_analyses(business.id, scan.id)
            assert analysis.status == "failed"
