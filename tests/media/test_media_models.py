from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.media import Media, MediaThumb, MediaToEntity

def _engine():
    eng = create_engine("sqlite:///:memory:")
    @event.listens_for(eng, "connect")
    def _fk(dbapi_con, _):
        dbapi_con.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(eng)
    return eng

def test_media_table_has_plugin_columns():
    cols = {c["name"] for c in inspect(_engine()).get_columns("media_table")}
    assert cols == {"id_media", "mediatype", "filename", "filetype", "filepath",
                    "descrizione", "tags", "entity_uuid"}

def test_thumb_pk_is_id_media_thumb():
    cols = {c["name"] for c in inspect(_engine()).get_columns("media_thumb_table")}
    assert "id_media_thumb" in cols and "path_resize" in cols and "thumb_data" not in cols

def test_link_table_shape():
    cols = {c["name"] for c in inspect(_engine()).get_columns("media_to_entity_table")}
    assert cols == {"id_mediaToEntity", "id_entity", "entity_type", "table_name",
                    "id_media", "filepath", "media_name", "entity_uuid"}

def test_entity_uuid_autofilled():
    Session = sessionmaker(bind=_engine())
    s = Session()
    m = Media(id_media=1, mediatype="image", filename="x.jpg", filetype="jpg",
              filepath="/m/x.jpg", descrizione="", tags="")
    s.add(m); s.commit()
    assert m.entity_uuid and len(m.entity_uuid) == 36

def test_no_basemodel_sync_columns():
    cols = {c["name"] for c in inspect(_engine()).get_columns("media_table")}
    assert "version_number" not in cols and "created_at" not in cols
