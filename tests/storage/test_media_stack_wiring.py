"""Regression test for the media-storage-backends integration bug: the web
upload path (create_app / settings_storage / switch_database) must build
MediaHandler/MediaService from the *configured* storage backend, not a bare
MediaHandler() that always writes to the local default.

See pyarchinit_mini.web_interface.app.build_media_stack.
"""
import pytest

from pyarchinit_mini.web_interface.app import build_media_stack
from pyarchinit_mini.services.media_service import MediaService
from pyarchinit_mini.media_manager.media_handler import MediaHandler


class _StorageServiceStub:
    """Stand-in for StorageConfigService with a canned .get()/.build_manager()."""

    def __init__(self, cfg, manager_sentinel):
        self._cfg = cfg
        self._manager_sentinel = manager_sentinel

    def get(self):
        return dict(self._cfg)

    def build_manager(self):
        return self._manager_sentinel


def test_build_media_stack_wires_remote_backend():
    sentinel = object()
    storage_service = _StorageServiceStub(
        {
            "media_root": "s3://bucket/media",
            "thumb_path": "s3://bucket/thumb",
            "thumb_resize": "s3://bucket/resize",
            "credentials": {},
        },
        sentinel,
    )
    db_manager = object()

    handler, service = build_media_stack(db_manager, storage_service)

    assert isinstance(handler, MediaHandler)
    assert isinstance(service, MediaService)
    # Remote roots must stay plain strings — Path() would collapse
    # "s3://bucket/media" into "s3:/bucket/media", destroying the scheme.
    assert handler.media_root == "s3://bucket/media"
    assert isinstance(handler.media_root, str)
    assert "//" in handler.media_root
    assert handler.storage_manager is sentinel
    assert service.media_handler is handler


def test_build_media_stack_falls_back_to_local_default():
    storage_service = _StorageServiceStub(
        {"media_root": None, "thumb_path": None, "thumb_resize": None, "credentials": {}},
        object(),
    )
    db_manager = object()

    handler, service = build_media_stack(db_manager, storage_service)

    assert isinstance(handler, MediaHandler)
    assert "://" not in str(handler.media_root)
    assert service.media_handler is handler
