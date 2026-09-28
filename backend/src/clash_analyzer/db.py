from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


def make_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    if url in ("sqlite://", "sqlite:///:memory:"):
        engine = create_engine(url, connect_args=connect_args, poolclass=StaticPool)
    else:
        if url.startswith("sqlite:///"):
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(url, connect_args=connect_args)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record) -> None:  # type: ignore[no-untyped-def]
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return engine


def init_db(engine: Engine) -> None:
    from . import models  # noqa: F401  (register tables)

    SQLModel.metadata.create_all(engine)


def session_scope(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session
