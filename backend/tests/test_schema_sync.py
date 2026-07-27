import uuid

import pytest
from sqlalchemy import Column, Integer, MetaData, String, UniqueConstraint, create_engine, inspect, text
from sqlalchemy import Table as SATable
from sqlalchemy.exc import OperationalError

from app.schema_sync import sync_schema


def _engine():
    return create_engine("sqlite:///:memory:")


def _postgres_engine():
    """A real Postgres connection (the docker-compose `db` service) --
    needed to test _sync_unique_constraints, which is deliberately a no-op
    on SQLite (see its docstring). Skips instead of failing when Postgres
    isn't reachable (e.g. CI without docker-compose running)."""
    engine = create_engine("postgresql://forecast:forecast@localhost:5432/pa_gov_forecast")
    try:
        with engine.connect():
            pass
    except OperationalError:
        pytest.skip("Postgres not reachable at localhost:5432 -- start docker-compose's db service")
    return engine


def test_sync_schema_adds_a_missing_nullable_column():
    engine = _engine()
    old = MetaData()
    SATable("widgets", old, Column("id", Integer, primary_key=True), Column("name", String(50)))
    old.create_all(engine)

    new = MetaData()
    SATable(
        "widgets", new,
        Column("id", Integer, primary_key=True),
        Column("name", String(50)),
        Column("color", String(20), nullable=True),
    )

    sync_schema(engine, metadata=new)

    columns = {c["name"] for c in inspect(engine).get_columns("widgets")}
    assert "color" in columns


def test_sync_schema_backfills_a_literal_default_for_not_null_columns():
    engine = _engine()
    old = MetaData()
    SATable("widgets", old, Column("id", Integer, primary_key=True))
    old.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO widgets (id) VALUES (1)"))

    new = MetaData()
    SATable(
        "widgets", new,
        Column("id", Integer, primary_key=True),
        Column("count", Integer, nullable=False, default=0),
    )

    sync_schema(engine, metadata=new)

    with engine.begin() as conn:
        row = conn.execute(text("SELECT count FROM widgets WHERE id=1")).first()
    assert row[0] == 0


def test_sync_schema_falls_back_to_nullable_when_no_default_is_available():
    engine = _engine()
    old = MetaData()
    SATable("widgets", old, Column("id", Integer, primary_key=True))
    old.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO widgets (id) VALUES (1)"))

    new = MetaData()
    SATable(
        "widgets", new,
        Column("id", Integer, primary_key=True),
        Column("required_thing", String(20), nullable=False),  # no default at all
    )

    sync_schema(engine, metadata=new)  # must not raise

    columns = {c["name"]: c["nullable"] for c in inspect(engine).get_columns("widgets")}
    assert columns["required_thing"] is True  # downgraded to nullable rather than crashing


def test_sync_schema_skips_brand_new_tables():
    # A table that doesn't exist yet is create_all()'s job, not sync_schema's
    # -- it must not try to ALTER a table that isn't there.
    engine = _engine()
    new = MetaData()
    SATable("brand_new", new, Column("id", Integer, primary_key=True))

    sync_schema(engine, metadata=new)  # must not raise

    assert "brand_new" not in inspect(engine).get_table_names()


def test_sync_schema_is_a_no_op_when_everything_is_current():
    engine = _engine()
    metadata = MetaData()
    SATable("widgets", metadata, Column("id", Integer, primary_key=True), Column("name", String(50)))
    metadata.create_all(engine)

    sync_schema(engine, metadata=metadata)  # must not raise or duplicate anything

    columns = [c["name"] for c in inspect(engine).get_columns("widgets")]
    assert columns.count("name") == 1


def test_sync_schema_replaces_a_changed_unique_constraint():
    # Mirrors Race's real migration: uq_races_state_office (state_code,
    # office) -> uq_races_state_office_district (state_code, office,
    # district), needed so a state can have many House rows sharing the
    # same (state_code, office) pair. A uniquely-named temp table is used
    # (not `races`) so this never touches real app data on the shared dev
    # Postgres instance.
    engine = _postgres_engine()
    table_name = f"widgets_{uuid.uuid4().hex[:8]}"
    try:
        old = MetaData()
        SATable(
            table_name, old,
            Column("id", Integer, primary_key=True),
            Column("state_code", String(2)),
            Column("office", String(20)),
            Column("district", Integer, default=0),
            UniqueConstraint("state_code", "office", name="uq_old_state_office"),
        )
        old.create_all(engine)
        with engine.begin() as conn:
            conn.execute(
                text(f"INSERT INTO {table_name} (state_code, office, district) VALUES ('ca', 'House', 1)")
            )

        new = MetaData()
        SATable(
            table_name, new,
            Column("id", Integer, primary_key=True),
            Column("state_code", String(2)),
            Column("office", String(20)),
            Column("district", Integer, default=0),
            UniqueConstraint("state_code", "office", "district", name="uq_new_state_office_district"),
        )

        sync_schema(engine, metadata=new)

        constraints = {c["name"] for c in inspect(engine).get_unique_constraints(table_name)}
        assert "uq_new_state_office_district" in constraints
        assert "uq_old_state_office" not in constraints

        # OLD constraint is really gone: a 2nd ca/House row (different
        # district) would have collided with it, but now succeeds.
        with engine.begin() as conn:
            conn.execute(
                text(f"INSERT INTO {table_name} (state_code, office, district) VALUES ('ca', 'House', 2)")
            )

        # NEW constraint is really enforced: a 3rd ca/House/1 row (same
        # full triple as the first row) now collides.
        with pytest.raises(Exception):
            with engine.begin() as conn:
                conn.execute(
                    text(f"INSERT INTO {table_name} (state_code, office, district) VALUES ('ca', 'House', 1)")
                )
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))


def test_sync_schema_preserves_existing_row_data():
    engine = _engine()
    old = MetaData()
    SATable("widgets", old, Column("id", Integer, primary_key=True), Column("name", String(50)))
    old.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO widgets (id, name) VALUES (1, 'gadget')"))

    new = MetaData()
    SATable(
        "widgets", new,
        Column("id", Integer, primary_key=True),
        Column("name", String(50)),
        Column("color", String(20), nullable=True),
    )

    sync_schema(engine, metadata=new)

    with engine.begin() as conn:
        row = conn.execute(text("SELECT id, name FROM widgets WHERE id=1")).first()
    assert row == (1, "gadget")
