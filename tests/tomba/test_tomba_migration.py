"""
Concurrency-columns migration must also cover tomba_table.

tomba_table is a plugin table (added by the pyarchinit_tomba plugin) that
pre-exists on the shared DB without mini's sync/concurrency columns
(version_number, sync_status, editing_by, last_modified_*, editing_since,
entity_uuid). mini's `DatabaseMigrations.migrate_concurrency_columns()`
ALTER-adds those columns to a fixed list of record tables; tomba_table must
be in that list so a pre-existing plugin tomba_table gets them too, exactly
like us_table does.
"""
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

from pyarchinit_mini.database.migrations import DatabaseMigrations
from pyarchinit_mini.models.base import Base
import pyarchinit_mini.models.pottery  # noqa: F401  (registers on Base for create_all)


class _Conn:
    """Minimal stand-in for pyarchinit_mini.database.connection.DatabaseConnection."""

    def __init__(self, engine):
        self.engine = engine
        self._Session = sessionmaker(bind=engine)

    def get_session(self):
        return self._Session()


class _DBM:
    """Minimal stand-in for the db_manager DatabaseMigrations expects
    (mirrors tests/media/test_media_migration.py's _DBM)."""

    def __init__(self, engine):
        self.connection = _Conn(engine)


def test_sync_columns_added_to_existing_plugin_tomba_table():
    eng = create_engine("sqlite:///:memory:")
    # migrate_concurrency_columns() ALTERs a fixed list of tables and raises
    # if any of them is missing, so build the full current mini schema first
    # (mini's own Tomba model already has the sync columns baked in — that's
    # fine, we overwrite tomba_table below with the bare plugin-style shape).
    Base.metadata.create_all(eng)
    with eng.begin() as c:
        c.execute(text("DROP TABLE tomba_table"))
        # A bare plugin-style tomba_table WITHOUT mini's sync columns —
        # this is what the pyarchinit_tomba plugin creates on the shared DB.
        c.execute(text(
            "CREATE TABLE tomba_table ("
            "id_tomba INTEGER PRIMARY KEY, sito TEXT, rito TEXT, entity_uuid TEXT)"
        ))

    DatabaseMigrations(_DBM(eng)).migrate_concurrency_columns()

    cols = {c["name"] for c in inspect(eng).get_columns("tomba_table")}
    assert {"version_number", "sync_status", "editing_by"} <= cols
