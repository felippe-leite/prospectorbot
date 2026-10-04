import pytest

from prospector.config import Settings
from prospector.database.session import create_database_engine, create_session_factory, initialize_database


@pytest.fixture
def session_factory(tmp_path):
    engine = create_database_engine(Settings(database_path=tmp_path / "data" / "test.db"))
    initialize_database(engine)
    yield create_session_factory(engine)
    engine.dispose()
