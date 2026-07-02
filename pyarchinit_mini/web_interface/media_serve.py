"""Decision matrix for /media/serve: routes a stored media path/URI to the
right serving strategy (local file, redirect, proxy through a StorageManager
backend, or forbidden) without touching Flask request/response objects.

Kept as a small, dependency-light module so it's unit-testable in isolation
from the app.py monolith (see tests/storage/test_media_serve_backends.py).
"""
from pyarchinit_mini.media_manager.path_resolver import is_remote_url, cloudinary_to_url

_PROXY = ("unibo://", "webdav://", "s3://", "r2://", "gdrive://", "dropbox://")


def serve_decision(p: str):
    """Return (kind, value) for a stored media path/URI.

    kind is one of:
      - "redirect": value is the URL to redirect to (cloudinary/http(s)).
      - "proxy": value is the original path; caller must fetch bytes via a
        StorageManager backend (unibo/webdav/s3/r2/gdrive/dropbox).
      - "forbidden": value is the original path; a remote scheme we don't
        know how to proxy.
      - "file": value is the original (local) path; caller applies the
        existing realpath-under-roots guard and serves it directly.
    """
    low = (p or "").lower()
    if low.startswith("cloudinary://"):
        return ("redirect", cloudinary_to_url(p))
    if low.startswith(("http://", "https://")):
        return ("redirect", p)
    if low.startswith(_PROXY):
        return ("proxy", p)
    if is_remote_url(p):            # any other remote scheme we don't proxy → forbidden
        return ("forbidden", p)
    return ("file", p)
