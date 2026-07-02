from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from pyarchinit_mini.database.migrations.m_2026_07_media_plugin_schema import migrate
from pyarchinit_mini.models.base import Base
import pyarchinit_mini.models.pottery  # noqa: F401  (registers on Base for create_all)
from pyarchinit_mini.models.media import Media, MediaThumb, MediaToEntity  # noqa: F401 (registers on Base)

def _old_schema(engine):
    """Minimal old-schema tables (matches the pre-plugin inline schema), empty."""
    with engine.begin() as c:
        c.execute(text("CREATE TABLE media_table (id_media INTEGER PRIMARY KEY, "
                       "entity_type TEXT, entity_id INTEGER, media_path TEXT)"))
        c.execute(text("CREATE TABLE media_thumb_table (id_thumb INTEGER PRIMARY KEY, id_media INTEGER)"))

def _old_schema_full(engine, rows, thumb_rows=1):
    """Full old-schema media_table (with the legacy columns real installs have),
    populated with `rows` (list of dicts), plus an old media_thumb_table."""
    with engine.begin() as c:
        c.execute(text(
            "CREATE TABLE media_table ("
            "id_media INTEGER PRIMARY KEY, entity_type TEXT, entity_id INTEGER, "
            "media_name TEXT, media_filename TEXT, media_path TEXT, "
            "media_type TEXT, description TEXT, tags TEXT)"
        ))
        c.execute(text("CREATE TABLE media_thumb_table (id_thumb INTEGER PRIMARY KEY, id_media INTEGER)"))
        for i in range(thumb_rows):
            c.execute(text("INSERT INTO media_thumb_table (id_thumb, id_media) VALUES (:i, 1)"), {"i": i + 1})
        for row in rows:
            cols = ", ".join(row.keys())
            placeholders = ", ".join(f":{k}" for k in row.keys())
            c.execute(text(f"INSERT INTO media_table ({cols}) VALUES ({placeholders})"), row)

def test_migrates_when_empty():
    eng = create_engine("sqlite:///:memory:")
    _old_schema(eng)
    res = migrate(eng)
    assert res["status"] == "migrated"
    cols = {c["name"] for c in inspect(eng).get_columns("media_table")}
    assert "filepath" in cols and "entity_id" not in cols
    assert "media_to_entity_table" in inspect(eng).get_table_names()

def test_old_schema_with_rows_data_migrates():
    """An OLD-schema media_table with rows must now be DATA-migrated (rows
    preserved), not skipped — this supersedes the old 'skipped' behavior."""
    eng = create_engine("sqlite:///:memory:")
    _old_schema(eng)
    with eng.begin() as c:
        c.execute(text("INSERT INTO media_table (id_media) VALUES (1)"))
    res = migrate(eng)
    assert res["status"] == "data_migrated"
    assert res["media"] == 1
    assert res["links"] == 0
    assert res["links_skipped"] == 1
    cols = {c["name"] for c in inspect(eng).get_columns("media_table")}
    assert "filepath" in cols
    legacy_cols = {c["name"] for c in inspect(eng).get_columns("media_table_legacy")}
    assert "media_path" in legacy_cols  # legacy backup preserves the old schema

def test_new_schema_with_rows_is_already_migrated():
    """A NEW-schema media_table with rows must be left alone: already_migrated,
    never touched/converted (idempotency guard)."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng, tables=[Media.__table__, MediaThumb.__table__, MediaToEntity.__table__])
    with eng.begin() as c:
        c.execute(text(
            "INSERT INTO media_table (id_media, mediatype, filename, filetype, filepath) "
            "VALUES (1, 'image', 'a.jpg', 'jpg', '/m/a.jpg')"
        ))
    res = migrate(eng)
    assert res["status"] == "already_migrated"
    with eng.connect() as c:
        count = c.execute(text("SELECT COUNT(*) FROM media_table")).scalar()
        assert count == 1

def test_data_migration_preserves_and_converts():
    eng = create_engine("sqlite:///:memory:")
    rows = [
        {
            "id_media": 1, "entity_type": "us", "entity_id": 10,
            "media_name": "a.jpg", "media_filename": "a.jpg", "media_path": "/m/a.jpg",
            "media_type": "image", "description": "d", "tags": "t",
        },
        {
            "id_media": 2, "entity_type": "inventario", "entity_id": 7,
            "media_name": None, "media_filename": "b.pdf", "media_path": "/m/b.pdf",
            "media_type": "document", "description": None, "tags": None,
        },
    ]
    _old_schema_full(eng, rows, thumb_rows=1)

    res = migrate(eng)

    assert res["status"] == "data_migrated"
    assert res["media"] == 2
    assert res["links"] == 2
    assert res["links_skipped"] == 0

    present = set(inspect(eng).get_table_names())
    assert "media_table_legacy" in present
    assert "media_thumb_table_legacy" in present
    assert "media_thumb_table" in present

    cols = {c["name"] for c in inspect(eng).get_columns("media_table")}
    assert "filepath" in cols

    with eng.connect() as c:
        media_rows = c.execute(text(
            "SELECT id_media, mediatype, filename, filetype, filepath, descrizione, tags "
            "FROM media_table ORDER BY id_media"
        )).mappings().all()
        assert len(media_rows) == 2
        assert media_rows[0]["mediatype"] == "image"
        assert media_rows[0]["filename"] == "a.jpg"
        assert media_rows[0]["filetype"] == "jpg"
        assert media_rows[0]["filepath"] == "/m/a.jpg"
        assert media_rows[0]["descrizione"] == "d"
        assert media_rows[0]["tags"] == "t"
        assert media_rows[1]["filename"] == "b.pdf"
        assert media_rows[1]["filetype"] == "pdf"
        assert media_rows[1]["filepath"] == "/m/b.pdf"

        link_rows = c.execute(text(
            "SELECT id_entity, entity_type, table_name, id_media FROM media_to_entity_table ORDER BY id_entity"
        )).mappings().all()
        assert len(link_rows) == 2
        by_entity = {r["id_entity"]: r for r in link_rows}
        assert by_entity[10]["entity_type"] == "US"
        assert by_entity[10]["table_name"] == "us_table"
        assert by_entity[10]["id_media"] == 1
        assert by_entity[7]["entity_type"] == "REPERTO"
        assert by_entity[7]["table_name"] == "inventario_materiali_table"
        assert by_entity[7]["id_media"] == 2

        legacy_media_count = c.execute(text("SELECT COUNT(*) FROM media_table_legacy")).scalar()
        assert legacy_media_count == 2

        thumb_count = c.execute(text("SELECT COUNT(*) FROM media_thumb_table")).scalar()
        assert thumb_count == 0

        legacy_thumb_count = c.execute(text("SELECT COUNT(*) FROM media_thumb_table_legacy")).scalar()
        assert legacy_thumb_count == 1

def test_unmappable_entity_type_keeps_media_skips_link():
    eng = create_engine("sqlite:///:memory:")
    rows = [
        {
            "id_media": 1, "entity_type": "bogus", "entity_id": 99,
            "media_name": "x.png", "media_filename": "x.png", "media_path": "/m/x.png",
            "media_type": "image", "description": None, "tags": None,
        },
    ]
    _old_schema_full(eng, rows, thumb_rows=0)

    res = migrate(eng)

    assert res["status"] == "data_migrated"
    assert res["media"] == 1
    assert res["links"] == 0
    assert res["links_skipped"] == 1

    with eng.connect() as c:
        media_count = c.execute(text("SELECT COUNT(*) FROM media_table")).scalar()
        assert media_count == 1
        link_count = c.execute(text("SELECT COUNT(*) FROM media_to_entity_table")).scalar()
        assert link_count == 0

def test_dedup_on_filepath():
    """Two legacy rows sharing the same media_path must produce exactly one
    new media row; both links should point at the same (deduped) id_media."""
    eng = create_engine("sqlite:///:memory:")
    rows = [
        {
            "id_media": 1, "entity_type": "us", "entity_id": 1,
            "media_name": "dup.jpg", "media_filename": "dup.jpg", "media_path": "/m/dup.jpg",
            "media_type": "image", "description": None, "tags": None,
        },
        {
            "id_media": 2, "entity_type": "tomba", "entity_id": 2,
            "media_name": "dup.jpg", "media_filename": "dup.jpg", "media_path": "/m/dup.jpg",
            "media_type": "image", "description": None, "tags": None,
        },
    ]
    _old_schema_full(eng, rows, thumb_rows=0)

    res = migrate(eng)

    assert res["status"] == "data_migrated"
    assert res["media"] == 1
    assert res["links"] == 2

    with eng.connect() as c:
        media_count = c.execute(text("SELECT COUNT(*) FROM media_table")).scalar()
        assert media_count == 1
        id_medias = c.execute(text("SELECT DISTINCT id_media FROM media_to_entity_table")).scalars().all()
        assert id_medias == [1]

def test_empty_old_schema_still_drops_recreates():
    eng = create_engine("sqlite:///:memory:")
    _old_schema(eng)
    res = migrate(eng)
    assert res["status"] == "migrated"
    present = set(inspect(eng).get_table_names())
    assert "media_table_legacy" not in present
    assert "media_thumb_table_legacy" not in present
    assert "media_to_entity_table_legacy" not in present
    cols = {c["name"] for c in inspect(eng).get_columns("media_table")}
    assert "filepath" in cols

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

def test_data_migration_idempotent_on_rerun():
    """Running migrate() again after a data-migration must not re-convert or
    touch the _legacy backup tables."""
    eng = create_engine("sqlite:///:memory:")
    rows = [{
        "id_media": 1, "entity_type": "us", "entity_id": 10,
        "media_name": "a.jpg", "media_filename": "a.jpg", "media_path": "/m/a.jpg",
        "media_type": "image", "description": None, "tags": None,
    }]
    _old_schema_full(eng, rows, thumb_rows=0)
    res1 = migrate(eng)
    assert res1["status"] == "data_migrated"
    res2 = migrate(eng)
    assert res2["status"] == "already_migrated"
    with eng.connect() as c:
        count = c.execute(text("SELECT COUNT(*) FROM media_table")).scalar()
        assert count == 1
        legacy_count = c.execute(text("SELECT COUNT(*) FROM media_table_legacy")).scalar()
        assert legacy_count == 1

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
