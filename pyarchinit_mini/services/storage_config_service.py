"""Loads/saves the global media StorageConfig and builds a configured StorageManager."""
from ..models.storage_config import StorageConfig
from ..storage import crypto
from ..storage.storage_manager import StorageManager
from ..storage.base_backend import StorageType


class StorageConfigService:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get(self) -> dict:
        with self.db_manager.connection.get_session() as s:
            row = s.get(StorageConfig, 1)
            if not row:
                return {"media_root": None, "thumb_path": None, "thumb_resize": None, "credentials": {}}
            creds = {}
            if row.credentials_encrypted and crypto.has_key():
                try:
                    creds = crypto.decrypt_dict(row.credentials_encrypted)
                except Exception:
                    creds = {}
            return {"media_root": row.media_root, "thumb_path": row.thumb_path,
                    "thumb_resize": row.thumb_resize, "credentials": creds}

    def save(self, media_root, thumb_path, thumb_resize, credentials: dict) -> None:
        enc = crypto.encrypt_dict(credentials or {})
        with self.db_manager.connection.get_session() as s:
            row = s.get(StorageConfig, 1)
            if not row:
                row = StorageConfig(id=1)
                s.add(row)
            row.media_root, row.thumb_path, row.thumb_resize = media_root, thumb_path, thumb_resize
            row.credentials_encrypted = enc
            s.commit()

    def build_manager(self) -> StorageManager:
        cfg = self.get()
        mgr = StorageManager()
        for backend, fields in (cfg.get("credentials") or {}).items():
            try:
                mgr.credentials_manager.set_credentials(StorageType(backend), fields)
            except ValueError:
                continue  # unknown backend key
        return mgr
