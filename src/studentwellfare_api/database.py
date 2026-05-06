from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from studentwellfare_api.config import settings


class Base(DeclarativeBase):
    pass


def _normalize_database_url(url: str) -> str:
    # Supabase / Heroku style "postgres://" → SQLAlchemy needs "postgresql+psycopg://"
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


database_url = _normalize_database_url(settings.database_url)
is_sqlite = database_url.startswith("sqlite")

connect_args = {"check_same_thread": False} if is_sqlite else {}
engine_kwargs = {"connect_args": connect_args}
if not is_sqlite:
    # Postgres: keep connections fresh, recycle before idle-timeout in pooled hosts.
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 280

engine = create_engine(database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
