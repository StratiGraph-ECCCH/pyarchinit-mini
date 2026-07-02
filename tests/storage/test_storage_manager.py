import pytest
from pyarchinit_mini.storage.storage_manager import StorageManager
from pyarchinit_mini.storage.base_backend import StorageType

@pytest.fixture
def mgr():
    return StorageManager()

def test_parse_s3(mgr):
    t, base, rel = mgr.parse_path("s3://my-bucket/thumbs/img.png")
    assert t == StorageType.S3 and base == "my-bucket" and rel == "thumbs/img.png"

def test_parse_webdav(mgr):
    t, base, rel = mgr.parse_path("webdav://cloud.ex.com/dav/files/u/f/img.png")
    assert t == StorageType.WEBDAV and base == "https://cloud.ex.com" and rel == "dav/files/u/f/img.png"

def test_parse_unibo_puts_all_in_base(mgr):
    t, base, rel = mgr.parse_path("unibo://ProjX/photolog/original/img.png")
    assert t == StorageType.UNIBO and base == "ProjX/photolog/original/img.png" and rel == ""

def test_parse_local_fallback(mgr):
    t, base, rel = mgr.parse_path("/data/thumbs/x.jpg")
    assert t == StorageType.LOCAL

def test_detect_cloudinary(mgr):
    assert mgr.detect_storage_type("cloudinary://folder/x.png") == StorageType.CLOUDINARY

def test_sftp_scheme_not_registered(mgr):
    # SFTP is out of scope; must fall back to LOCAL, never raise
    assert mgr.detect_storage_type("sftp://u@h/x") == StorageType.LOCAL
