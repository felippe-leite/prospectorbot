from uuid import uuid4

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from prospector.config import Settings
from prospector.database import models as tables
from prospector.database.repository import Repository
from prospector.database.session import create_database_engine, initialize_database, session_scope
from prospector.models import (
    Business, Evidence, Opportunity, Scan, ScanStatus, Score, ScoreContribution, WebsiteAnalysis,
)


def test_settings_defaults_and_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PROSPECTOR_DATABASE_PATH", raising=False)
    assert str(Settings.from_env().database_path) == "data/prospector.db"
    monkeypatch.setenv("PROSPECTOR_DATABASE_PATH", "/tmp/custom.db")
    assert str(Settings.from_env().database_path) == "/tmp/custom.db"
    monkeypatch.setenv("PROSPECTOR_DATABASE_PATH", " ")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_initialization_creates_tables_and_enforces_foreign_keys(tmp_path):
    path = tmp_path / "nested" / "database.db"
    engine = create_database_engine(Settings(database_path=path))
    try:
        initialize_database(engine)
        initialize_database(engine)
        assert path.exists()
        assert set(inspect(engine).get_table_names()) == {
            "businesses", "scans", "scan_businesses", "website_analyses", "opportunities", "scores",
        }
        with engine.connect() as connection:
            assert connection.scalar(text("PRAGMA foreign_keys")) == 1
    finally:
        engine.dispose()


def test_roundtrip_all_records_and_rankings(session_factory):
    scan = Scan(query="barbearias", location="Campinas, SP")
    business = Business(name="Alpha", source="manual", website="https://example.com", review_count=192)
    evidence = Evidence(code="reviews", description="192 reviews", source="manual")
    analysis = WebsiteAnalysis(
        business_id=business.id, scan_id=scan.id, requested_url=business.website,
        status="completed", status_code=200, title="Alpha", title_status="present",
        redirect_chain=["https://example.com"], evidence=[evidence],
    )
    opportunity = Opportunity(
        business_id=business.id, scan_id=scan.id, rule_code="example",
        title="Example", description="Test evidence", evidence=[evidence],
        suggested_services=["Landing page"],
    )
    score = Score(
        business_id=business.id, scan_id=scan.id, scoring_version="0.1",
        contributions=[ScoreContribution(rule_code="example", points=85, evidence=[evidence])],
    )
    other = Business(name="Beta", source="manual")
    with session_scope(session_factory) as session:
        repo = Repository(session)
        repo.save_scan(scan)
        repo.save_business(business, scan.id)
        repo.save_business(other, scan.id)
        repo.save_analysis(analysis)
        repo.save_opportunity(opportunity)
        repo.save_score(score)
        repo.save_score(Score(business_id=other.id, scan_id=scan.id, scoring_version="0.1"))
    # A new session verifies that data really reached disk, not only memory.
    with session_scope(session_factory) as session:
        repo = Repository(session)
        assert repo.get_scan(scan.id) == scan
        assert repo.list_scans() == [scan]
        assert repo.get_business(business.id) == business
        assert repo.list_analyses(business.id, scan.id) == [analysis]
        assert repo.list_opportunities(business.id, scan.id) == [opportunity]
        assert repo.get_score(business.id, scan.id) == score
        assert [item.value for item in repo.list_scores(scan.id)] == [85, 0]
        assert repo.get_score(business.id, scan.id).classification == "Gold Nugget"


def test_histories_are_separated_by_scan(session_factory):
    business = Business(name="Alpha", source="test", source_id="123")
    scans = [Scan(query="barbearias", location="Campinas") for _ in range(2)]
    with session_scope(session_factory) as session:
        repo = Repository(session)
        for scan in scans:
            repo.save_scan(scan)
            saved = repo.save_business(business, scan.id)
            repo.save_analysis(WebsiteAnalysis(
                business_id=saved.id, scan_id=scan.id,
                requested_url="https://example.com", status="failed", errors=["Timeout"],
            ))
            repo.save_score(Score(business_id=saved.id, scan_id=scan.id, scoring_version="0.1"))
    with session_scope(session_factory) as session:
        repo = Repository(session)
        assert len(repo.list_analyses(business.id)) == 2
        for scan in scans:
            assert len(repo.list_analyses(business.id, scan.id)) == 1
            assert len(repo.list_scores(scan.id)) == 1


def test_transaction_rolls_back_all_writes(session_factory):
    scan = Scan(query="barbearias", location="Campinas")
    with pytest.raises(RuntimeError):
        with session_scope(session_factory) as session:
            repo = Repository(session)
            repo.save_scan(scan)
            repo.save_business(Business(name="Alpha", source="test"), scan.id)
            raise RuntimeError("Abort")
    with session_scope(session_factory) as session:
        repo = Repository(session)
        assert repo.get_scan(scan.id) is None
        assert repo.list_businesses() == []


def test_records_require_business_membership_in_scan(session_factory):
    scan = Scan(query="barbearias", location="Campinas")
    business = Business(name="Alpha", source="manual")
    with session_scope(session_factory) as session:
        repo = Repository(session)
        with pytest.raises(ValueError, match="Save the scan"):
            repo.save_business(business, scan.id)
        repo.save_scan(scan)
        with pytest.raises(ValueError, match="registered in this scan"):
            repo.save_score(Score(business_id=business.id, scan_id=scan.id, scoring_version="0.1"))


def test_database_rejects_analysis_for_unregistered_scan_business(session_factory):
    scan = Scan(query="barbearias", location="Campinas")
    business = Business(name="Alpha", source="manual")
    with session_scope(session_factory) as session:
        repo = Repository(session)
        repo.save_scan(scan)
        repo.save_business(business, scan.id)
        other_scan = Scan(query="cafes", location="Campinas")
        repo.save_scan(other_scan)
    with pytest.raises(IntegrityError):
        with session_scope(session_factory) as session:
            session.add(tables.WebsiteAnalysis(
                id=str(uuid4()), scan_id=str(other_scan.id), business_id=str(business.id), payload={},
            ))


def test_existing_score_cannot_be_overwritten(session_factory):
    scan = Scan(query="barbearias", location="Campinas")
    business = Business(name="Alpha", source="manual")
    score = Score(business_id=business.id, scan_id=scan.id, scoring_version="0.1")
    with session_scope(session_factory) as session:
        repo = Repository(session)
        repo.save_scan(scan)
        repo.save_business(business, scan.id)
        repo.save_score(score)
        assert repo.save_score(score) == score
        with pytest.raises(ValueError, match="already exists"):
            repo.save_score(score.model_copy(update={"scoring_version": "0.2"}))


def test_scan_status_can_be_updated(session_factory):
    scan = Scan(query="barbearias", location="Campinas")
    with session_scope(session_factory) as session:
        repo = Repository(session)
        repo.save_scan(scan)
        updated = scan.model_copy(update={"status": ScanStatus.COMPLETED})
        repo.save_scan(updated)
    with session_scope(session_factory) as session:
        assert Repository(session).get_scan(scan.id).status == "completed"
