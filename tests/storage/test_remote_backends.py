"""
Tests for remote storage backends (S3/R2, WebDAV, Cloudinary, Google Drive,
Dropbox, HTTP, Unibo File Manager).

These tests verify two contracts that MUST hold regardless of whether the
underlying third-party SDKs (boto3, webdav3, dropbox, cloudinary,
googleapiclient, requests) are installed:

1. StorageManager routes URL schemes to the correct backend class.
2. Importing a backend module never raises even when its SDK is absent,
   and connect() returns False gracefully (no exception) when the SDK
   can't be imported.
"""
import builtins
import importlib

import pytest

from pyarchinit_mini.storage.storage_manager import StorageManager


def test_manager_routes_scheme_to_backend_class():
    mgr = StorageManager()
    # get_backend with connect=False just instantiates the right class from the scheme
    b = mgr.get_backend("s3://bucket/key.png", connect=False)
    assert type(b).__name__ == "S3Backend"
    u = mgr.get_backend("unibo://Proj/folder/x.png", connect=False)
    assert type(u).__name__ == "UniboFileManagerBackend"


def test_missing_sdk_disables_backend_gracefully(monkeypatch):
    # simulate boto3 absent -> connect() returns False, no crash
    real_import = builtins.__import__

    def fake(name, *a, **k):
        if name == "boto3" or name.startswith("boto3."):
            raise ImportError("no boto3")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake)
    mgr = StorageManager()
    b = mgr.get_backend("s3://bucket/key.png", connect=False)
    assert b.connect() is False  # graceful, no exception


@pytest.mark.parametrize(
    "scheme,url,class_name",
    [
        ("s3", "s3://bucket/key.png", "S3Backend"),
        ("r2", "r2://bucket/key.png", "S3Backend"),
        ("webdav", "webdav://server.example.com/folder/file.png", "WebDAVBackend"),
        ("cloudinary", "cloudinary://folder/file.png", "CloudinaryBackend"),
        ("gdrive", "gdrive://folder/file.png", "GDriveBackend"),
        ("dropbox", "dropbox://folder/file.png", "DropboxBackend"),
        ("http", "http://server.example.com/file.png", "HTTPBackend"),
        ("https", "https://server.example.com/file.png", "HTTPBackend"),
        ("unibo", "unibo://Proj/folder/x.png", "UniboFileManagerBackend"),
    ],
)
def test_manager_routes_all_schemes(scheme, url, class_name):
    mgr = StorageManager()
    backend = mgr.get_backend(url, connect=False)
    assert type(backend).__name__ == class_name


@pytest.mark.parametrize(
    "module_name",
    [
        "pyarchinit_mini.storage.backends.s3_backend",
        "pyarchinit_mini.storage.backends.webdav_backend",
        "pyarchinit_mini.storage.backends.cloudinary_backend",
        "pyarchinit_mini.storage.backends.gdrive_backend",
        "pyarchinit_mini.storage.backends.dropbox_backend",
        "pyarchinit_mini.storage.backends.http_backend",
        "pyarchinit_mini.storage.backends.unibo_filemanager_backend",
    ],
)
def test_backend_module_imports_without_sdk(module_name):
    # Every backend module must import cleanly even though none of the
    # optional third-party SDKs are guaranteed to be installed in this env.
    module = importlib.import_module(module_name)
    assert module is not None


def test_connect_returns_false_without_credentials():
    # With no credentials configured, connect() must fail gracefully
    # (return False) rather than raising, for every remote backend.
    mgr = StorageManager()
    for url in (
        "s3://bucket/key.png",
        "webdav://server.example.com/folder/file.png",
        "cloudinary://folder/file.png",
        "gdrive://folder/file.png",
        "dropbox://folder/file.png",
    ):
        backend = mgr.get_backend(url, connect=False)
        assert backend.connect() is False
