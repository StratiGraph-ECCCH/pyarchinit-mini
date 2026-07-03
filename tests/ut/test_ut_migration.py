"""
Concurrency-columns migration must also cover ut_table.

ut_table is a core plugin-aligned table that pre-exists on the shared DB
without mini's sync/concurrency columns (version_number, sync_status,
editing_by, last_modified_*, editing_since, entity_uuid). mini's
`DatabaseMigrations.migrate_concurrency_columns()` ALTER-adds those columns
to a fixed list of record tables; ut_table must be in that list so a
pre-existing ut_table gets them too, exactly like us_table does.
"""
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

from pyarchinit_mini.database.migrations import DatabaseMigrations
from pyarchinit_mini.models.base import Base
import pyarchinit_mini.models.ut  # noqa: F401  (registers on Base for create_all)


class _Conn:
    """Minimal stand-in for pyarchinit_mini.database.connection.DatabaseConnection."""

    def __init__(self, engine):
        self.engine = engine
        self._Session = sessionmaker(bind=engine)

    def get_session(self):
        return self._Session()


class _DBM:
    """Minimal stand-in for the db_manager DatabaseMigrations expects
    (mirrors tests/fauna/test_fauna_migration.py's _DBM)."""

    def __init__(self, engine):
        self.connection = _Conn(engine)


def test_sync_columns_added_to_existing_plugin_ut_table():
    eng = create_engine("sqlite:///:memory:")
    # migrate_concurrency_columns() ALTERs a fixed list of tables and raises
    # if any of them is missing, so build the full current mini schema first
    # (mini's own UT model already has the sync columns baked in — that's
    # fine, we overwrite ut_table below with the bare plugin-style shape).
    Base.metadata.create_all(eng)
    with eng.begin() as c:
        c.execute(text("DROP TABLE ut_table"))
        # A bare plugin-style ut_table WITHOUT mini's sync columns —
        # this is what the pyarchinit_ut plugin creates on the shared DB.
        c.execute(text(
            "CREATE TABLE ut_table ("
            "id_ut INTEGER PRIMARY KEY, progetto TEXT, def_ut TEXT, entity_uuid TEXT)"
        ))

    DatabaseMigrations(_DBM(eng)).migrate_concurrency_columns()

    cols = {c["name"] for c in inspect(eng).get_columns("ut_table")}
    assert {"version_number", "sync_status", "editing_by"} <= cols
