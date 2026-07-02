"""Port of the pyarchinit plugin's media path resolution (remote_image_loader).

Only local + already-a-URL resolution is implemented here. Fetching bytes from
StorageManager backends (unibo://, webdav://, s3://, …) is a follow-up plan; such
URIs are returned unchanged so callers/serving can decide how to handle them."""
import os
import re

REMOTE_SCHEMES = (
    "gdrive://", "dropbox://", "s3://", "r2://", "sftp://", "webdav://",
    "http://", "https://", "cloudinary://", "unibo://",
)

CLOUDINARY_CLOUD_NAME = "dkioeufik"
CLOUDINARY_BASE_URL = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/image/upload"


def is_remote_url(path: str) -> bool:
    if not path:
        return False
    return path.lower().startswith(REMOTE_SCHEMES)


def cloudinary_to_url(cloudinary_path: str) -> str:
    """cloudinary://folder/file_thumb.png -> https://res.cloudinary.com/<cloud>/image/upload/folder/file.png"""
    if not cloudinary_path or not cloudinary_path.lower().startswith("cloudinary://"):
        return cloudinary_path
    path_part = cloudinary_path[len("cloudinary://"):].strip("/")
    path_part = re.sub(r"_thumb(\.[^.]+)$", r"\1", path_part)
    return f"{CLOUDINARY_BASE_URL}/{path_part}"


def resolve_media_path(base_path: str, filepath: str) -> str:
    """Return a full path/URL for a stored media/thumb path (plugin get_image_path)."""
    if not filepath:
        return ""
    # Already a full URL/URI → return as-is.
    if is_remote_url(filepath):
        return filepath
    if not base_path:
        return filepath
    base_path = base_path.rstrip("/\\")
    filepath = filepath.lstrip("/\\")
    if is_remote_url(base_path):
        return f"{base_path}/{filepath}"
    return os.path.join(base_path, filepath)
