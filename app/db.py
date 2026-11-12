"""
Database engine and session management.

Defaults to a local SQLite file so the API runs with zero setup. Swapping to
PostgreSQL in a later phase is a one-line change: set DATABASE_URL to a
postgresql:// URL (SQLAlchemy handles the rest; no code here is SQLite-specific
except the connect_args check-same-thread flag, which is skipped for other backends).
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/voyager.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

if DATABASE_URL.startswith("sqlite:///./"):
    db_dir = os.path.dirname(DATABASE_URL.replace("sqlite:///./", ""))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _add_missing_sqlite_columns():
    """create_all() only creates missing tables, never adds columns to an
    existing one - so a column added to a model after the dev DB file already
    exists (e.g. Trip.origin, Phase 10) would otherwise silently never show up.
    No migration framework is in use, so this does the one thing actually
    needed: add any trips columns absent from the on-disk table. SQLite-only;
    a real Postgres deployment would use proper migrations instead.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return
    from app import models_db  # noqa: F401
    with engine.connect() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(trips)").fetchall()}
        for column in Base.metadata.tables["trips"].columns:
            if column.name not in existing:
                col_type = column.type.compile(engine.dialect)
                conn.exec_driver_sql(f"ALTER TABLE trips ADD COLUMN {column.name} {col_type}")

            # SQLite's ALTER TABLE ADD COLUMN always backfills existing rows
            # with NULL, never the Python-side Column(default=...) - that
            # default only applies to rows SQLAlchemy itself inserts. Backfill
            # any still-NULL rows for a simple scalar default (e.g.
            # traveler_count=1) every time, not just the run that added the
            # column, so a row left over from before this backfill existed
            # still gets fixed. A non-nullable response schema field would
            # otherwise choke on NULL from such a row.
            default = column.default.arg if column.default is not None else None
            if default is not None and not callable(default):
                conn.exec_driver_sql(
                    f"UPDATE trips SET {column.name} = ? WHERE {column.name} IS NULL", (default,)
                )
        conn.commit()


def init_db():
    from app import models_db  # noqa: F401  (ensure models are registered)
    Base.metadata.create_all(bind=engine)
    _add_missing_sqlite_columns()
