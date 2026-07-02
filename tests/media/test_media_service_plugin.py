import os
import pytest
from PIL import Image
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.media import Media, MediaToEntity, MediaThumb
from pyarchinit_mini.media_manager.media_handler import MediaHandler
from pyarchinit_mini.services.media_service import MediaService

class _Conn:
    def __init__(self, engine): self._Session = sessionmaker(bind=engine)
    def get_session(self): return self._Session()

class _DBM:
    def __init__(self, engine): self.connection = _Conn(engine)

@pytest.fixture
def svc(tmp_path):
    eng = create_engine("sqlite:///:memory:")
    @event.listens_for(eng, "connect")
    def _fk(c, _): c.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(eng)
    handler = MediaHandler(media_root=str(tmp_path/"media"),
                           thumb_path=str(tmp_path/"thumb"),
                           thumb_resize=str(tmp_path/"resize"))
    return MediaService(_DBM(eng), handler)

def _png(tmp_path, name):
    p = tmp_path / name; Image.new("RGB", (300, 300)).save(p); return str(p)

def test_add_media_creates_media_thumb_and_link(svc, tmp_path):
    m = svc.add_media(_png(tmp_path, "a.png"), "us", 42, descrizione="d", tags="t")
    assert m.id_media == 1 and m.filepath.endswith("a.png") and m.mediatype == "image"
    got = svc.get_media_for_entity("us", 42)
    assert [x.id_media for x in got] == [1]

def test_add_same_file_twice_reuses_media_row(svc, tmp_path):
    src = _png(tmp_path, "b.png")
    m1 = svc.add_media(src, "us", 1, )
    m2 = svc.add_media(src, "us", 2, )   # same filepath, different entity
    assert m1.id_media == m2.id_media     # reused media row
    assert len(svc.get_media_for_entity("us", 1)) == 1
    assert len(svc.get_media_for_entity("us", 2)) == 1

def test_link_dedup(svc, tmp_path):
    src = _png(tmp_path, "c.png")
    svc.add_media(src, "us", 5)
    svc.add_media(src, "us", 5)           # identical link -> no duplicate
    assert len(svc.get_media_for_entity("us", 5)) == 1

def test_unlink_keeps_media(svc, tmp_path):
    m = svc.add_media(_png(tmp_path, "d.png"), "us", 9)
    assert svc.unlink_media(m.id_media, "us", 9) is True
    assert svc.get_media_for_entity("us", 9) == []
    assert svc.get_media_by_id(m.id_media) is not None

def test_delete_media_cascades(svc, tmp_path):
    m = svc.add_media(_png(tmp_path, "e.png"), "us", 3)
    assert svc.delete_media(m.id_media) is True
    assert svc.get_media_by_id(m.id_media) is None
    with svc.db_manager.connection.get_session() as s:
        assert s.query(MediaToEntity).count() == 0
        assert s.query(MediaThumb).count() == 0

def test_public_url_encodes_spaces(svc):
    assert "%20" in svc.public_url("/media/a b.jpg")
