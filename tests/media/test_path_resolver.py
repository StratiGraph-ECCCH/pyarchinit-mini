from pyarchinit_mini.media_manager.path_resolver import (
    is_remote_url, resolve_media_path, cloudinary_to_url,
)

def test_local_filename_joins_base():
    import os
    assert resolve_media_path("/srv/thumb", "thumb_1_x.jpg") == os.path.join("/srv/thumb", "thumb_1_x.jpg")

def test_absolute_stored_path_passthrough_when_base_empty():
    assert resolve_media_path("", "/srv/media/x.jpg") == "/srv/media/x.jpg"

def test_remote_uri_filepath_passthrough():
    assert resolve_media_path("/srv/thumb", "unibo://KTM/original/x.png") == "unibo://KTM/original/x.png"
    assert resolve_media_path("/srv/thumb", "https://h/x.png") == "https://h/x.png"

def test_is_remote_url_detects_schemes():
    assert is_remote_url("unibo://a/b")
    assert is_remote_url("cloudinary://a/b")
    assert is_remote_url("https://h/x")
    assert not is_remote_url("/local/path.jpg")
    assert not is_remote_url("")

def test_cloudinary_to_url_strips_thumb_suffix():
    url = cloudinary_to_url("cloudinary://folder/2446_DSC02076_thumb.png")
    assert url == "https://res.cloudinary.com/dkioeufik/image/upload/folder/2446_DSC02076.png"

def test_remote_base_path_joins_with_forward_slash():
    assert resolve_media_path("https://cdn.example/img", "a.jpg") == "https://cdn.example/img/a.jpg"
    assert resolve_media_path("unibo://KTM/original", "a.jpg") == "unibo://KTM/original/a.jpg"

def test_cloudinary_to_url_passthrough_for_non_cloudinary():
    assert cloudinary_to_url("/local/x.png") == "/local/x.png"

def test_cloudinary_to_url_without_thumb_suffix():
    assert cloudinary_to_url("cloudinary://folder/pic.png") == "https://res.cloudinary.com/dkioeufik/image/upload/folder/pic.png"
