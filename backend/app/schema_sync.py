"""Lightweight "poor man's migration": adds any model column missing from
the live database without a full drop-and-recreate, so an additive schema
change (a new nullable column, a new table) doesn't cost the forecast
history already sitting in the volume the way `docker compose down -v` does.

This is intentionally NOT a full migration system (no Alembic, no versioned
migration files, no downgrade path) -- it only handles the pattern every
schema change in this project has actually been so far: a brand new table
(already handled for free by Base.metadata.create_all, which only creates
tables that don't exist yet) or a new column on an existing table. A column
rename, drop, or type change still needs manual handling; this never
attempts anything destructive -- at worst, a NOT NULL column with no usable
default gets added as nullable instead of failing the whole startup.
"""

import logging

from sqlalchemy import MetaData, UniqueConstraint, inspect, text
from sqlalchemy.engine import Engine

from app.database import Base

logger = logging.getLogger(__name__)


def _literal_default_clause(column) -> str | None:
    """Best-effort SQL DEFAULT clause for backfilling existing rows.

    Only handles simple literal defaults (int/float/bool/str) -- a callable
    default (e.g. `default=lambda: datetime.now(timezone.utc)`, used for
    timestamp columns) can't be embedded in a single ALTER TABLE statement,
    so those fall through to None.
    """
    if column.server_default is not None:
        return str(column.server_default.arg)
    if column.default is not None and not column.default.is_callable:
        value = column.default.arg
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, str):
            return f"'{value}'"
        return str(value)
    return None


def _sync_unique_constraints(conn, table, inspector) -> None:
    """Replaces a table's unique constraint(s) when the model's declared
    column set has changed (e.g. Race's uq_races_state_office ->
    uq_races_state_office_district, adding `district` to the key) --
    a genuine constraint change, not just a new column, so it needs its own
    step alongside the column-add loop above.

    Postgres-only: it's the only dialect this project actually runs against
    in production (see app.config.Settings.database_url), and SQLite (used
    by the test suite) doesn't support ALTER TABLE ... DROP CONSTRAINT for a
    table-level unique constraint the same way -- rather than reimplement
    the "rebuild the table" dance SQLite would need, this step is simply
    skipped there, logged, and left for a fresh `create_all()` (a brand new
    test DB every run) to get right from scratch.
    """
    if conn.dialect.name != "postgresql":
        return

    declared_uniques = [c for c in table.constraints if isinstance(c, UniqueConstraint)]
    if not declared_uniques:
        return

    existing = inspector.get_unique_constraints(table.name)
    existing_column_sets = {frozenset(e["column_names"]): e["name"] for e in existing}

    for constraint in declared_uniques:
        declared_columns = frozenset(c.name for c in constraint.columns)
        if declared_columns in existing_column_sets:
            continue  # already matches -- no-op, same as the column-add loop

        # Drop any existing unique constraint that overlaps on columns
        # (the stale predecessor of this one, e.g. the old 2-column
        # constraint this 3-column one replaces) before adding the new one.
        for existing_columns, existing_name in existing_column_sets.items():
            if existing_columns & declared_columns:
                ddl = f'ALTER TABLE {table.name} DROP CONSTRAINT "{existing_name}"'
                logger.info("sync_schema: %s", ddl)
                conn.execute(text(ddl))

        column_list = ", ".join(c.name for c in constraint.columns)
        ddl = (
            f'ALTER TABLE {table.name} ADD CONSTRAINT "{constraint.name}" '
            f"UNIQUE ({column_list})"
        )
        logger.info("sync_schema: %s", ddl)
        conn.execute(text(ddl))


def sync_schema(engine: Engine, metadata: MetaData | None = None) -> None:
    """Adds any column present on a model but missing from the live table.

    Safe to call on every startup: a no-op once the DB has caught up.
    `metadata` defaults to the real app's Base.metadata; overridable for
    isolated testing.
    """
    metadata = metadata if metadata is not None else Base.metadata
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # brand new table -- create_all() already made it

            existing_columns = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue

                col_type = column.type.compile(dialect=engine.dialect)
                default_clause = _literal_default_clause(column)
                nullable = column.nullable
                if not nullable and default_clause is None:
                    # No safe literal default to backfill existing rows with
                    # -- add it nullable rather than fail the whole startup
                    # on a NOT NULL constraint violation.
                    logger.warning(
                        "sync_schema: %s.%s has no usable literal default -- "
                        "adding as nullable instead of NOT NULL",
                        table.name, column.name,
                    )
                    nullable = True

                ddl = f"ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type}"
                if default_clause is not None:
                    ddl += f" DEFAULT {default_clause}"
                if not nullable:
                    ddl += " NOT NULL"

                logger.info("sync_schema: %s", ddl)
                conn.execute(text(ddl))

            _sync_unique_constraints(conn, table, inspector)
