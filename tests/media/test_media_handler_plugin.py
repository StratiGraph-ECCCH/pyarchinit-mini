import os
from PIL import Image
from pyarchinit_mini.media_manager.media_handler import MediaHandler

def _png(tmp_path, name="pic.png", color=(200, 30, 30)):
    p = tmp_path / name
    Image.new("RGB", (1000, 800), color).save(p)
    return str(p)

def test_store_original_copies_and_reports(tmp_path):
    h = MediaHandler(media_root=str(tmp_path / "media"),
                     thumb_path=str(tmp_path / "thumb"),
                     thumb_resize=str(tmp_path / "resize"))
    src = _png(tmp_path)
    info = h.store_original(src)
    assert info["filename"] == "pic.png"
    assert info["filetype"] == "png"
    assert info["mediatype"] == "image"
    assert os.path.isfile(info["dest_path"])
    assert info["dest_path"].endswith(os.path.join("media", "pic.png"))

def test_make_thumbnails_creates_two_files(tmp_path):
    h = MediaHandler(media_root=str(tmp_path / "media"),
                     thumb_path=str(tmp_path / "thumb"),
                     thumb_resize=str(tmp_path / "resize"))
    src = _png(tmp_path)
    t = h.make_thumbnails(src, id_media=7, filename="pic.png")
    assert t["media_thumb_filename"] == "thumb_7_pic.png"
    assert os.path.isfile(t["thumb_path"]) and os.path.isfile(t["resize_path"])
    assert Image.open(t["thumb_path"]).size[0] <= 200
    assert Image.open(t["resize_path"]).size[0] <= 600

def test_make_thumbnails_none_for_non_image(tmp_path):
    h = MediaHandler(media_root=str(tmp_path / "media"),
                     thumb_path=str(tmp_path / "thumb"),
                     thumb_resize=str(tmp_path / "resize"))
    doc = tmp_path / "d.pdf"; doc.write_bytes(b"%PDF-1.4")
    assert h.make_thumbnails(str(doc), id_media=1, filename="d.pdf") is None
