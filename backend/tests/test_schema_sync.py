from sqlalchemy import Column, Integer, MetaData, String, create_engine, inspect, text
from sqlalchemy import Table as SATable

from app.schema_sync import sync_schema


def _engine():
    return create_engine("sqlite:///:memory:")


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
