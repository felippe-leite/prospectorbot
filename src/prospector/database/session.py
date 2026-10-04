"""SQLite setup and explicit transaction boundaries."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from prospector.config import Settings
from prospector.database.models import Base


def create_database_engine(settings: Settings | None = None) -> Engine:
    settings = settings if settings is not None else Settings.from_env()
    path = settings.database_path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        URL.create("sqlite", database=str(path)),
        connect_args={"timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    return engine


def initialize_database(engine: Engine) -> None:
    """Create missing tables; this is not a schema migration mechanism."""
    Base.metadata.create_all(engine)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Commit the entire unit of work, or roll it back on any exception."""
    with factory.begin() as session:
        yield session
