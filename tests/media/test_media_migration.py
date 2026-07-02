from sqlalchemy import create_engine, text, inspect
from pyarchinit_mini.database.migrations.m_2026_07_media_plugin_schema import migrate

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
