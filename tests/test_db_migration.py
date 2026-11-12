"""
Regression test for a real bug hit while building Phase 11 (budget-aware
flight/transportation recommendations): adding Trip.traveler_count with
Column(..., nullable=False, default=1) looked safe, but SQLite's `ALTER
TABLE ADD COLUMN` always backfills existing rows with NULL - it never
applies a Python-side SQLAlchemy `default`. A row created before this
column existed then serialized as `traveler_count: null`, which FastAPI's
non-Optional `int` response field rejected with a 500
(ResponseValidationError). _add_missing_sqlite_columns() in app/db.py was
fixed to also backfill NULLs for any column with a simple scalar default.
"""
import os
import tempfile

from sqlalchemy import create_engine

from app.db import Base, _add_missing_sqlite_columns
from app import models_db  # noqa: F401 - registers Trip on Base.metadata


def test_stale_null_column_is_backfilled_with_its_python_default(monkeypatch):
    db_path = os.path.join(tempfile.gettempdir(), "voyager_migration_test.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    db_url = f"sqlite:///{db_path}"

    # Simulate the real failure mode: a trips table that predates
    # traveler_count entirely (so PRAGMA table_info won't see it).
    old_engine = create_engine(db_url)
    old_metadata_columns = [c for c in Base.metadata.tables["trips"].columns if c.name != "traveler_count"]
    with old_engine.connect() as conn:
        cols_sql = ", ".join(f"{c.name} {c.type.compile(old_engine.dialect)}" for c in old_metadata_columns)
        conn.exec_driver_sql(f"CREATE TABLE trips ({cols_sql})")
        conn.exec_driver_sql(
            "INSERT INTO trips (id, destination, days, trip_type, budget, dietary_preferences, status, "
            "errors, trace) VALUES ('t1', 'Goa', 3, 'foodie', 'mid-range', '[]', 'complete', '[]', '[]')"
        )
        conn.commit()
    old_engine.dispose()

    test_engine = create_engine(db_url)
    monkeypatch.setattr("app.db.DATABASE_URL", db_url)
    monkeypatch.setattr("app.db.engine", test_engine)

    _add_missing_sqlite_columns()

    with test_engine.connect() as conn:
        row = conn.exec_driver_sql("SELECT traveler_count FROM trips WHERE id = 't1'").fetchone()
    assert row[0] == 1  # backfilled from Column(default=1), not left NULL

    test_engine.dispose()
    os.remove(db_path)
