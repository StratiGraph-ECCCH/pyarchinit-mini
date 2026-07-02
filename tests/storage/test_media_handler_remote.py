from PIL import Image
from pyarchinit_mini.media_manager.media_handler import MediaHandler


class FakeManager:
    def __init__(self):
        self.written = {}

    def write(self, path, data):
        self.written[path] = data if isinstance(data, bytes) else open(data, "rb").read()
        return True


def _png(tmp_path, name="p.png"):
    p = tmp_path / name
    Image.new("RGB", (50, 50)).save(p)
    return str(p)


def test_store_original_writes_to_remote_and_returns_scheme_path(tmp_path):
    fm = FakeManager()
    h = MediaHandler(media_root="s3://bucket/media", thumb_path="s3://bucket/thumb",
                     thumb_resize="s3://bucket/resize", storage_manager=fm)
    info = h.store_original(_png(tmp_path))
    assert info["dest_path"] == "s3://bucket/media/p.png"
    assert "s3://bucket/media/p.png" in fm.written


def test_local_unchanged(tmp_path):
    h = MediaHandler(media_root=str(tmp_path/"m"), thumb_path=str(tmp_path/"t"),
                     thumb_resize=str(tmp_path/"r"))
    info = h.store_original(_png(tmp_path))
    assert info["dest_path"].endswith("p.png") and "://" not in info["dest_path"]


def test_make_thumbnails_writes_to_remote_and_returns_scheme_paths(tmp_path):
    fm = FakeManager()
    h = MediaHandler(media_root="s3://bucket/media", thumb_path="s3://bucket/thumb",
                     thumb_resize="s3://bucket/resize", storage_manager=fm)
    src = _png(tmp_path)
    t = h.make_thumbnails(src, id_media=7, filename="p.png")
    assert t["media_thumb_filename"] == "thumb_7_p.png"
    assert t["thumb_path"] == "s3://bucket/thumb/thumb_7_p.png"
    assert t["resize_path"] == "s3://bucket/resize/thumb_7_p.png"
    assert t["thumb_path"] in fm.written and t["resize_path"] in fm.written
    assert len(fm.written[t["thumb_path"]]) > 0
    assert len(fm.written[t["resize_path"]]) > 0


def test_make_thumbnails_local_unchanged(tmp_path):
    h = MediaHandler(media_root=str(tmp_path/"m"), thumb_path=str(tmp_path/"t"),
                     thumb_resize=str(tmp_path/"r"))
    src = _png(tmp_path)
    t = h.make_thumbnails(src, id_media=7, filename="p.png")
    import os
    assert os.path.isfile(t["thumb_path"]) and os.path.isfile(t["resize_path"])
    assert "://" not in t["thumb_path"] and "://" not in t["resize_path"]
