import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from prospector.database import models as tables
from prospector.database.repository import Repository
from prospector.database.session import session_scope
from prospector.models import Business, Scan


def make_scan():
    return Scan(query="barbearias", location="Campinas, SP")


def test_same_source_identity_reuses_id_and_preserves_snapshots(session_factory):
    first_scan, second_scan = make_scan(), make_scan()
    first = Business(name="Alpha", source="test", source_id="123", review_count=10)
    updated = Business(name="Alpha Updated", source="test", source_id="123", review_count=20)
    with session_scope(session_factory) as session:
        repo = Repository(session)
        repo.save_scan(first_scan)
        repo.save_scan(second_scan)
        saved_first = repo.save_business(first, first_scan.id)
        saved_second = repo.save_business(updated, second_scan.id)
        assert saved_first.id == saved_second.id
    with session_scope(session_factory) as session:
        repo = Repository(session)
        assert len(repo.list_businesses()) == 1
        assert repo.get_business(first.id).review_count == 20
        assert repo.get_business(first.id, first_scan.id).review_count == 10
        assert repo.get_business(first.id, second_scan.id).name == "Alpha Updated"


@pytest.mark.parametrize("sources", [("test", "test"), ("first", "second")])
def test_missing_id_or_different_source_does_not_merge(session_factory, sources):
    scan = make_scan()
    source_id = None if sources[0] == sources[1] else "123"
    with session_scope(session_factory) as session:
        repo = Repository(session)
        repo.save_scan(scan)
        for source in sources:
            repo.save_business(Business(name="Same name", source=source, source_id=source_id), scan.id)
        assert len(repo.list_businesses(scan.id)) == 2


def test_same_business_twice_in_scan_preserves_first_snapshot(session_factory):
    scan = make_scan()
    with session_scope(session_factory) as session:
        repo = Repository(session)
        repo.save_scan(scan)
        original = repo.save_business(Business(name="First", source="test", source_id="123"), scan.id)
        repeated = repo.save_business(Business(name="Second", source="test", source_id="123"), scan.id)
        assert repeated == original
        assert len(repo.list_businesses(scan.id)) == 1
        assert repo.get_business(original.id).name == "First"


def test_reusing_uuid_with_different_source_identity_is_rejected(session_factory):
    scan = make_scan()
    with session_scope(session_factory) as session:
        repo = Repository(session)
        repo.save_scan(scan)
        original = repo.save_business(Business(name="Alpha", source="test", source_id="123"), scan.id)
        with pytest.raises(ValueError, match="different source identity"):
            repo.save_business(Business(id=original.id, name="Other", source="test", source_id="456"), scan.id)


def test_database_enforces_unique_source_identity(session_factory):
    scan = make_scan()
    with session_scope(session_factory) as session:
        repo = Repository(session)
        repo.save_scan(scan)
        repo.save_business(Business(name="Alpha", source="test", source_id="123"), scan.id)
    with pytest.raises(IntegrityError):
        with session_scope(session_factory) as session:
            session.add(tables.Business(id="another", source="test", source_id="123", name="Duplicate", payload={}))
    with session_scope(session_factory) as session:
        assert len(list(session.scalars(select(tables.Business)))) == 1
