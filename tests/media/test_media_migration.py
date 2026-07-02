from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from pyarchinit_mini.database.migrations.m_2026_07_media_plugin_schema import migrate
from pyarchinit_mini.models.base import Base
import pyarchinit_mini.models.pottery  # noqa: F401  (registers on Base for create_all)
import pyarchinit_mini.models.media  # noqa: F401  (registers on Base for create_all)

def _old_schema(engine):
    with engine.begin() as c:
        c.execute(text("CREATE TABLE media_table (id_media INTEGER PRIMARY KEY, "
                       "entity_type TEXT, entity_id INTEGER, media_path TEXT)"))
        c.execute(text("CREATE TABLE media_thumb_table (id_thumb INTEGER PRIMARY KEY, id_media INTEGER)"))

def test_migrates_when_empty():
    eng = create_engine("sqlite:///:memory:")
    _old_schema(eng)
    res = migrate(eng)
    assert res["status"] == "migrated"
    cols = {c["name"] for c in inspect(eng).get_columns("media_table")}
    assert "filepath" in cols and "entity_id" not in cols
    assert "media_to_entity_table" in inspect(eng).get_table_names()

def test_skips_when_media_has_rows():
    eng = create_engine("sqlite:///:memory:")
    _old_schema(eng)
    with eng.begin() as c:
        c.execute(text("INSERT INTO media_table (id_media) VALUES (1)"))
    res = migrate(eng)
    assert res["status"] == "skipped"
    cols = {c["name"] for c in inspect(eng).get_columns("media_table")}
    assert "media_path" in cols  # unchanged

def test_migrate_idempotent_on_new_schema():
    eng = create_engine("sqlite:///:memory:")
    _old_schema(eng)
    res1 = migrate(eng)
    assert res1["status"] == "migrated"
    res2 = migrate(eng)
    assert res2["status"] == "already_migrated"
    cols = {c["name"] for c in inspect(eng).get_columns("media_table")}
    assert "filepath" in cols
    assert "media_path" not in cols

class _Conn:
    def __init__(self, engine):
        self.engine = engine
        self._Session = sessionmaker(bind=engine)
    def get_session(self):
        return self._Session()

class _DBM:
    def __init__(self, engine):
        self.connection = _Conn(engine)

def test_bootstrap_migrate_all_tables_invokes_media_migration():
    """The app's migration bootstrap (DatabaseMigrations.migrate_all_tables,
    called from DatabaseConnection.initialize_database) must actually run
    the plugin-schema migration — this is what Fix A wires up. Build a
    sqlite engine with the full current schema (so the other migrations in
    migrate_all_tables no-op cleanly) but swap in the OLD empty media
    tables, exactly like a pre-existing Adarte/Railway mini DB. Run the real
    migrate_all_tables() entry point and assert the media tables came out
    in the new plugin schema."""
    from pyarchinit_mini.database.migrations import DatabaseMigrations

    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    with eng.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS media_thumb_table"))
        c.execute(text("DROP TABLE IF EXISTS media_to_entity_table"))
        c.execute(text("DROP TABLE IF EXISTS media_table"))
    _old_schema(eng)

    migrations = DatabaseMigrations(_DBM(eng))
    migrations.migrate_all_tables()

    cols = {c["name"] for c in inspect(eng).get_columns("media_table")}
    assert "filepath" in cols
    assert "media_path" not in cols
    assert "media_to_entity_table" in inspect(eng).get_table_names()
