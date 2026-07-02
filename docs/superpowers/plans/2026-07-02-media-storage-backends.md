# Media Storage Backends (SP1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give pyarchinit-mini web configurable media storage backends (Local, WebDAV, S3/R2, Cloudinary, Google Drive, Dropbox, HTTP, Unibo) with full parity + DB interop with the classic pyarchinit plugin.

**Architecture:** Port the plugin's headless-ready `modules/storage/` package into `pyarchinit_mini/storage/`, feed credentials from a DB-backed (encrypted) config instead of QGIS settings, add a `/settings/storage` UI, and route media upload (write) and `/media/serve` (read) through the `StorageManager`. Scheme-prefixed `filepath` strings (e.g. `unibo://…`, `s3://bucket/…`) are written exactly as the plugin writes them so the shared festos DB interoperates.

**Tech Stack:** Python 3.12, Flask, SQLAlchemy, Pillow, cryptography (Fernet), and optional per-backend SDKs (boto3, webdavclient3, dropbox, cloudinary, google-api-python-client) imported lazily.

## Global Constraints

- Backends + `filepath` scheme formats (write these EXACTLY for DB interop): Local=abs path; `unibo://{project}/{folder}/.../file`; `webdav://{server}/{path}`; `s3://{bucket}/{key}`; `r2://{bucket}/{key}`; `cloudinary://{folder}/.../file` (public_id has NO extension); `gdrive://{folder}/.../file`; `dropbox://{folder}/.../file`; `http(s)://{server}/{path}`.
- Uniform backend contract: `__init__(base_path, credentials)`, `read(rel)->bytes|None`, `write(rel, data)->bool`, `exists(rel)->bool`, `delete(rel)->bool`, `list(path="")->list`, `get_url(rel)->str|None`, `connect()->bool`.
- SDK libs imported ONLY inside the backend that needs them; a missing lib disables that backend gracefully (no crash, clear message). Core mini must not hard-require them.
- **SFTP is out of scope** (the plugin declares but never implemented it).
- Credentials encrypted at rest with Fernet; key from env `PYARCHINIT_SECRET_KEY`. Never log credentials in cleartext.
- Serving matrix: local→`send_file`; `http/https`→redirect; `cloudinary`→redirect to `https://res.cloudinary.com/{cloud}/image/upload/{path}` (strip `_thumb`); `unibo/webdav/s3/r2/gdrive/dropbox`→proxy (`StorageManager.read` → stream).
- Credential field names per backend (persist these exact names): Unibo `server_url,username,password,project_code,base_folder,verify_ssl`; Cloudinary `cloud_name,api_key,api_secret,folder,auto_tagging`; GDrive `client_id,client_secret,refresh_token`; Dropbox `access_token,app_key,app_secret`; S3/R2 `access_key,secret_key,region,endpoint,account_id`; WebDAV `username,password,verify_ssl`; HTTP `api_key,username,password,bearer_token`.
- Plugin source to copy from (read-only): `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/pyarchinit/modules/storage/`.
- Local media flow must be UNCHANGED when no remote backend is configured (no regression).
- Run tests with `.venv/bin/pytest`. TDD, DRY, YAGNI, frequent commits. No `Co-Authored-By`/AI-attribution trailer on commits.

## Scope / phases
Phase 1 (core, no deps): Tasks 1-2. Phase 2 (crypto+config): 3-6. Phase 3 (remote backends): 7. Phase 4 (integration): 8-9. Phase 5 (UI): 10. Phase 6 (deps/docs/release): 11-12.

---

## File Structure
- Create `pyarchinit_mini/storage/__init__.py`, `base_backend.py`, `storage_manager.py`, `credentials.py`, `crypto.py`, and `backends/{local,s3,webdav,cloudinary,gdrive,dropbox,http,unibo}_backend.py` (ported).
- Create `pyarchinit_mini/models/storage_config.py`, `pyarchinit_mini/services/storage_config_service.py`.
- Modify `pyarchinit_mini/media_manager/media_handler.py` (remote write), `pyarchinit_mini/web_interface/app.py` (serve matrix + `/settings/storage`).
- Create `pyarchinit_mini/web_interface/templates/settings/storage.html`.
- Modify `requirements.txt`, `pyarchinit_mini/models/__init__.py`, `pyarchinit_mini/database/migrations/__init__.py`.
- Tests under `tests/storage/`.

---

### Task 1: Storage core — base contract + manager (port, pure-python)

**Files:**
- Create: `pyarchinit_mini/storage/__init__.py`, `pyarchinit_mini/storage/base_backend.py`, `pyarchinit_mini/storage/storage_manager.py`
- Test: `tests/storage/test_storage_manager.py`

**Port instructions:** Copy the plugin's `modules/storage/base_backend.py` and `modules/storage/storage_manager.py` verbatim into the new paths. Then apply ONLY these adaptations:
- In `storage_manager.py`, change backend imports in `_load_backend` to the new package path `from .backends.<x>_backend import <X>Backend` (the backends live in `pyarchinit_mini/storage/backends/`, added in later tasks). Wrap each in the existing try/except ImportError so a missing backend/lib disables only that scheme.
- Remove the `SFTP` entry from `SCHEME_MAP` and any `_load_backend` sftp branch (out of scope).
- No other logic changes. `parse_path()` must keep returning `(StorageType, base_path, relative)` exactly as the plugin does.

**Interfaces:**
- Produces: `StorageManager` with `parse_path(path)->(StorageType,str,str)`, `detect_storage_type(path)->StorageType`, `get_backend(path, connect=True)`, `read/write/exists/delete(path)`, `get_available_backends()`, `clear_cache()`. `StorageBackend` ABC (contract in Global Constraints). `StorageType`, `StorageFile`, `StorageConfig` from `base_backend`.

- [ ] **Step 1: Write the failing test**

```python
# tests/storage/test_storage_manager.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/storage/test_storage_manager.py -v`
Expected: FAIL (`ModuleNotFoundError: pyarchinit_mini.storage...`)

- [ ] **Step 3: Port the two files + create `__init__.py`**

Copy `base_backend.py` and `storage_manager.py` from the plugin `modules/storage/` per the Port instructions above. Create an empty `pyarchinit_mini/storage/__init__.py`. Ensure the backend imports in `_load_backend` point at `.backends.<x>_backend` and are try/except-guarded, and SFTP is removed.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/storage/test_storage_manager.py -v`
Expected: PASS (6 passed). (`get_backend` for schemes whose backend file doesn't exist yet returns None/raises-caught — that's fine; these tests only exercise `parse_path`/`detect_storage_type`.)

- [ ] **Step 5: Commit**

```bash
git add pyarchinit_mini/storage/__init__.py pyarchinit_mini/storage/base_backend.py pyarchinit_mini/storage/storage_manager.py tests/storage/__init__.py tests/storage/test_storage_manager.py
git commit -m "feat(storage): port StorageManager + backend contract (pure-python core)"
```

---

### Task 2: Local backend (port) + read/write contract

**Files:**
- Create: `pyarchinit_mini/storage/backends/__init__.py`, `pyarchinit_mini/storage/backends/local_backend.py`
- Test: `tests/storage/test_local_backend.py`

**Port instructions:** Copy the plugin's `modules/storage/local_backend.py` into `pyarchinit_mini/storage/backends/local_backend.py` verbatim (stdlib only, no adaptation needed beyond the import of `..base_backend`). Create `backends/__init__.py` (empty).

**Interfaces:**
- Consumes: `StorageBackend` (Task 1).
- Produces: `LocalBackend(base_path, credentials=None)` implementing the contract; `StorageManager.get_backend("/abs/path")` returns a working LocalBackend.

- [ ] **Step 1: Write the failing test**

```python
# tests/storage/test_local_backend.py
from pyarchinit_mini.storage.backends.local_backend import LocalBackend

def test_write_read_exists_delete(tmp_path):
    b = LocalBackend(str(tmp_path)); b.connect()
    assert b.write("sub/x.txt", b"hello") is True
    assert b.exists("sub/x.txt") is True
    assert b.read("sub/x.txt") == b"hello"
    assert b.delete("sub/x.txt") is True
    assert b.exists("sub/x.txt") is False

def test_read_missing_returns_none(tmp_path):
    b = LocalBackend(str(tmp_path)); b.connect()
    assert b.read("nope.txt") is None
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/storage/test_local_backend.py -v` → FAIL (import error).
- [ ] **Step 3:** Port the file per instructions.
- [ ] **Step 4: Run** the test → PASS (2 passed).
- [ ] **Step 5: Commit**

```bash
git add pyarchinit_mini/storage/backends/__init__.py pyarchinit_mini/storage/backends/local_backend.py tests/storage/test_local_backend.py
git commit -m "feat(storage): local backend (ported) with read/write contract"
```

---

### Task 3: Credential encryption (Fernet)

**Files:**
- Create: `pyarchinit_mini/storage/crypto.py`
- Test: `tests/storage/test_crypto.py`

**Interfaces:**
- Produces: `get_fernet() -> Fernet | None` (None if no key); `encrypt_dict(d: dict) -> str`; `decrypt_dict(token: str) -> dict`; `has_key() -> bool`. Key source: env `PYARCHINIT_SECRET_KEY` (a urlsafe base64 32-byte Fernet key). If absent, `has_key()` is False and encrypt/decrypt raise `RuntimeError`.

- [ ] **Step 1: Write the failing test**

```python
# tests/storage/test_crypto.py
import pytest
from pyarchinit_mini.storage import crypto

def test_roundtrip(monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setenv("PYARCHINIT_SECRET_KEY", Fernet.generate_key().decode())
    tok = crypto.encrypt_dict({"password": "s3cr3t", "user": "u"})
    assert isinstance(tok, str) and "s3cr3t" not in tok
    assert crypto.decrypt_dict(tok) == {"password": "s3cr3t", "user": "u"}

def test_no_key(monkeypatch):
    monkeypatch.delenv("PYARCHINIT_SECRET_KEY", raising=False)
    assert crypto.has_key() is False
    with pytest.raises(RuntimeError):
        crypto.encrypt_dict({"a": 1})
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**

```python
# pyarchinit_mini/storage/crypto.py
"""Symmetric encryption for storage credentials at rest (Fernet)."""
import os
import json
from cryptography.fernet import Fernet

def has_key() -> bool:
    return bool(os.environ.get("PYARCHINIT_SECRET_KEY"))

def get_fernet():
    key = os.environ.get("PYARCHINIT_SECRET_KEY")
    return Fernet(key.encode()) if key else None

def encrypt_dict(d: dict) -> str:
    f = get_fernet()
    if f is None:
        raise RuntimeError("PYARCHINIT_SECRET_KEY not set; cannot encrypt credentials")
    return f.encrypt(json.dumps(d).encode()).decode()

def decrypt_dict(token: str) -> dict:
    f = get_fernet()
    if f is None:
        raise RuntimeError("PYARCHINIT_SECRET_KEY not set; cannot decrypt credentials")
    return json.loads(f.decrypt(token.encode()).decode())
```

- [ ] **Step 4: Run** → PASS (2 passed).
- [ ] **Step 5: Commit** `git add pyarchinit_mini/storage/crypto.py tests/storage/test_crypto.py && git commit -m "feat(storage): Fernet credential encryption"`

---

### Task 4: StorageConfig model (global, one row)

**Files:**
- Create: `pyarchinit_mini/models/storage_config.py`
- Modify: `pyarchinit_mini/models/__init__.py` (export `StorageConfig`)
- Test: `tests/storage/test_storage_config_model.py`

**Interfaces:**
- Produces: `StorageConfig(Base)` → table `storage_config` with columns: `id` (Integer PK), `media_root` (Text, nullable), `thumb_path` (Text), `thumb_resize` (Text), `credentials_encrypted` (Text, nullable), `updated_at` (DateTime). Single-row (id=1) global config.

- [ ] **Step 1: Write the failing test**

```python
# tests/storage/test_storage_config_model.py
from sqlalchemy import create_engine, inspect
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.storage_config import StorageConfig

def test_table_shape():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    cols = {c["name"] for c in inspect(eng).get_columns("storage_config")}
    assert {"id","media_root","thumb_path","thumb_resize","credentials_encrypted","updated_at"} <= cols
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**

```python
# pyarchinit_mini/models/storage_config.py
"""Global (single-row) media storage configuration."""
from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func
from .base import Base

class StorageConfig(Base):
    __tablename__ = "storage_config"
    id = Column(Integer, primary_key=True)          # always 1
    media_root = Column(Text)                        # upload target (may be scheme-prefixed)
    thumb_path = Column(Text)
    thumb_resize = Column(Text)
    credentials_encrypted = Column(Text)             # Fernet token of {backend: {field: val}}
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

Add to `pyarchinit_mini/models/__init__.py`: `from .storage_config import StorageConfig` and add `"StorageConfig"` to `__all__`.

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `git add pyarchinit_mini/models/storage_config.py pyarchinit_mini/models/__init__.py tests/storage/test_storage_config_model.py && git commit -m "feat(storage): StorageConfig model (global media storage settings)"`

---

### Task 5: StorageConfigService (load/save, encrypt/decrypt, build a configured StorageManager)

**Files:**
- Create: `pyarchinit_mini/services/storage_config_service.py`
- Test: `tests/storage/test_storage_config_service.py`

**Interfaces:**
- Consumes: `StorageConfig` (Task 4), `crypto` (Task 3), `StorageManager` (Task 1).
- Produces: `StorageConfigService(db_manager)` with:
  - `get() -> dict` → `{"media_root","thumb_path","thumb_resize","credentials": {backend: {...}}}` (credentials decrypted; `{}` if unset/no key).
  - `save(media_root, thumb_path, thumb_resize, credentials: dict) -> None` (encrypts credentials, upserts row id=1).
  - `build_manager() -> StorageManager` → a StorageManager whose credential provider returns the decrypted per-backend creds (via `set_credentials`).

- [ ] **Step 1: Write the failing test**

```python
# tests/storage/test_storage_config_service.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from cryptography.fernet import Fernet
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.services.storage_config_service import StorageConfigService

class _Conn:
    def __init__(s, e): s._S = sessionmaker(bind=e)
    def get_session(s): return s._S()
class _DBM:
    def __init__(s, e): s.connection = _Conn(e)

@pytest.fixture
def svc(monkeypatch):
    monkeypatch.setenv("PYARCHINIT_SECRET_KEY", Fernet.generate_key().decode())
    eng = create_engine("sqlite:///:memory:"); Base.metadata.create_all(eng)
    return StorageConfigService(_DBM(eng))

def test_save_then_get_roundtrips_and_encrypts(svc):
    svc.save("s3://bucket/media", "s3://bucket/thumb", "s3://bucket/resize",
             {"s3": {"access_key": "AK", "secret_key": "SK"}})
    got = svc.get()
    assert got["media_root"] == "s3://bucket/media"
    assert got["credentials"]["s3"]["access_key"] == "AK"
    # stored form is encrypted
    with svc.db_manager.connection.get_session() as s:
        from pyarchinit_mini.models.storage_config import StorageConfig
        row = s.get(StorageConfig, 1)
        assert "AK" not in (row.credentials_encrypted or "")

def test_build_manager_feeds_credentials(svc):
    svc.save("s3://b/m", "s3://b/t", "s3://b/r", {"s3": {"access_key": "AK", "secret_key": "SK"}})
    mgr = svc.build_manager()
    from pyarchinit_mini.storage.base_backend import StorageType
    assert mgr.credentials_manager.get_credentials(StorageType.S3).get("access_key") == "AK"
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** (uses the CredentialsManager `set_credentials` API from Task 6; if Task 6 not yet done, `build_manager` may be stubbed to set creds via a dict — but sequence Task 6 BEFORE finalizing this. For TDD here, implement `get`/`save` fully and `build_manager` against the ported `CredentialsManager.set_credentials(StorageType, dict)`.)

```python
# pyarchinit_mini/services/storage_config_service.py
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
```

- [ ] **Step 4: Run** → PASS (2 passed). (Requires Task 6's `set_credentials`; do Task 6 first if red.)
- [ ] **Step 5: Commit** `git add pyarchinit_mini/services/storage_config_service.py tests/storage/test_storage_config_service.py && git commit -m "feat(storage): StorageConfigService (encrypted config + configured manager)"`

---

### Task 6: Credentials manager (port + DB-friendly)

**Files:**
- Create: `pyarchinit_mini/storage/credentials.py`
- Test: `tests/storage/test_credentials.py`

**Port instructions:** Copy the plugin's `modules/storage/credentials.py` into the new path. Apply ONLY: **delete** the `_load_from_qgis_settings` method and its call in `get_credentials` (and the guarded `from qgis.core import QgsSettings` import). Keep `_load_from_environment`, `_load_from_json_file`, `set_credentials`, `REQUIRED_CREDENTIALS`, `ENV_NAMES`. The DB-backed creds arrive via `set_credentials(StorageType, dict)` (called by StorageConfigService), which is highest priority.

**Interfaces:**
- Produces: `CredentialsManager` with `get_credentials(StorageType)->dict`, `set_credentials(StorageType, dict)`, `REQUIRED_CREDENTIALS`, `ENV_NAMES`.

- [ ] **Step 1: Write the failing test**

```python
# tests/storage/test_credentials.py
from pyarchinit_mini.storage.credentials import CredentialsManager
from pyarchinit_mini.storage.base_backend import StorageType

def test_set_and_get(monkeypatch):
    monkeypatch.delenv("PYARCHINIT_S3_ACCESS_KEY", raising=False)
    cm = CredentialsManager()
    cm.set_credentials(StorageType.S3, {"access_key": "AK", "secret_key": "SK"})
    assert cm.get_credentials(StorageType.S3)["access_key"] == "AK"

def test_env_fallback(monkeypatch):
    monkeypatch.setenv("PYARCHINIT_S3_ACCESS_KEY", "ENVAK")
    cm = CredentialsManager()
    assert cm.get_credentials(StorageType.S3).get("access_key") == "ENVAK"

def test_no_qgis_import():
    import pyarchinit_mini.storage.credentials as m
    src = open(m.__file__).read()
    assert "QgsSettings" not in src and "from qgis" not in src
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Port + adapt per instructions.
- [ ] **Step 4: Run** → PASS (3 passed).
- [ ] **Step 5: Commit** `git add pyarchinit_mini/storage/credentials.py tests/storage/test_credentials.py && git commit -m "feat(storage): credentials manager (ported, QGIS-free, DB/env/json sources)"`

---

### Task 7: Remote backends (port, lazy SDK imports)

**Files:**
- Create: `pyarchinit_mini/storage/backends/{s3,webdav,cloudinary,gdrive,dropbox,http,unibo_filemanager}_backend.py`
- Test: `tests/storage/test_remote_backends.py`

**Port instructions:** Copy each plugin backend file (`s3_backend.py`, `webdav_backend.py`, `cloudinary_backend.py`, `gdrive_backend.py`, `dropbox_backend.py`, `http_backend.py`, `unibo_filemanager_backend.py`) into `pyarchinit_mini/storage/backends/`. Fix relative imports to `..base_backend`. Ensure each third-party import (`boto3`, `webdav3`, `dropbox`, `cloudinary`, `googleapiclient`/`google.*`) is **inside** `connect()`/methods or wrapped so that importing the module never fails when the SDK is absent — if it's a top-level import in the plugin file, move it into the method or guard with try/except and set an `_available=False` flag that makes `connect()` return False with a logged reason. Unibo is stdlib-only → copy verbatim (it already builds `UniboFileManagerBackend(base_path, credentials)`).

**Interfaces:**
- Consumes: `StorageBackend`, `StorageManager` (`_load_backend` now finds these).
- Produces: each `<X>Backend(base_path, credentials)` per the contract; `StorageManager.get_backend("s3://...")` returns an S3Backend, etc.

- [ ] **Step 1: Write the failing test**

```python
# tests/storage/test_remote_backends.py
import builtins, importlib, pytest
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
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Port the 7 files per instructions (lazy SDK imports; `connect()` returns False when the SDK is missing).
- [ ] **Step 4: Run** → PASS (2 passed). Also run the full storage suite: `.venv/bin/pytest tests/storage/ -v` → green.
- [ ] **Step 5: Commit** `git add pyarchinit_mini/storage/backends/ tests/storage/test_remote_backends.py && git commit -m "feat(storage): port remote backends (s3/r2,webdav,cloudinary,gdrive,dropbox,http,unibo) with lazy SDK imports"`

---

### Task 8: MediaHandler — write to the configured backend

**Files:**
- Modify: `pyarchinit_mini/media_manager/media_handler.py`
- Test: `tests/storage/test_media_handler_remote.py`

**Interfaces:**
- Consumes: `StorageManager` (via an injected `manager`), the `media_root`/`thumb_path`/`thumb_resize` (which may be scheme-prefixed).
- Produces: `MediaHandler(..., storage_manager=None)`; `store_original` returns `filepath` = the scheme-prefixed target when `media_root` has a remote scheme (writing bytes via `storage_manager.write(target, data)`); local behavior unchanged when `media_root` is a local path. Same for `make_thumbnails` (writes thumb files to `thumb_path`/`thumb_resize` targets).

- [ ] **Step 1: Write the failing test**

```python
# tests/storage/test_media_handler_remote.py
from PIL import Image
from pyarchinit_mini.media_manager.media_handler import MediaHandler

class FakeManager:
    def __init__(self): self.written = {}
    def write(self, path, data): self.written[path] = data if isinstance(data, bytes) else open(data,"rb").read(); return True

def _png(tmp_path, name="p.png"):
    p = tmp_path/name; Image.new("RGB",(50,50)).save(p); return str(p)

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
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** In `MediaHandler.__init__` accept `storage_manager=None` and store it; add a helper `_is_remote(root)` = root contains `://` and scheme in the known set (reuse `path_resolver.is_remote_url`). In `store_original`: if `_is_remote(self.media_root)`, compute `target = f"{media_root.rstrip('/')}/{filename}"`, read the source bytes, `self.storage_manager.write(target, data)`, set `dest_path=target` (do NOT shutil.copy locally). Else current local copy. Same pattern in `make_thumbnails` for `thumb_path`/`thumb_resize` (generate the JPEG in a temp buffer, write via manager). Keep filenames identical.
- [ ] **Step 4: Run** → PASS (2 passed); also `.venv/bin/pytest tests/media/test_media_handler_plugin.py -v` (local path) still green.
- [ ] **Step 5: Commit** `git add pyarchinit_mini/media_manager/media_handler.py tests/storage/test_media_handler_remote.py && git commit -m "feat(storage): MediaHandler writes originals+thumbnails to configured backend"`

---

### Task 9: `/media/serve` — proxy/redirect matrix

**Files:**
- Modify: `pyarchinit_mini/web_interface/app.py` (the `serve_media` route)
- Test: `tests/storage/test_media_serve_backends.py`

**Interfaces:**
- Consumes: `StorageManager` (from `current_app.storage_service.build_manager()`), `path_resolver.is_remote_url`, `cloudinary_to_url`.
- Produces: `/media/serve?p=<filepath>` behavior: local abs path→`send_file` (existing guard); `http(s)://`→`redirect`; `cloudinary://`→`redirect(cloudinary_to_url)`; `unibo/webdav/s3/r2/gdrive/dropbox`→proxy: `mgr.read(p)` → `send_file(BytesIO(bytes), download_name=..., mimetype=guessed)`; read failure→404.

- [ ] **Step 1: Write the failing test** (unit-test the routing helper, not the whole app)

Extract the decision into a testable helper `serve_decision(p) -> ("file"|"redirect"|"proxy"|"forbidden", value)` in app.py (or a small `web_interface/media_serve.py` module) and test it:
```python
# tests/storage/test_media_serve_backends.py
from pyarchinit_mini.web_interface.media_serve import serve_decision

def test_cloudinary_redirects_stripping_thumb():
    kind, val = serve_decision("cloudinary://f/2446_x_thumb.png")
    assert kind == "redirect" and val == "https://res.cloudinary.com/dkioeufik/image/upload/f/2446_x.png"

def test_http_redirects():
    assert serve_decision("https://h/x.png") == ("redirect", "https://h/x.png")

def test_s3_is_proxy():
    kind, _ = serve_decision("s3://bucket/x.png"); assert kind == "proxy"

def test_unibo_is_proxy():
    kind, _ = serve_decision("unibo://P/f/x.png"); assert kind == "proxy"

def test_local_is_file():
    kind, _ = serve_decision("/data/x.png"); assert kind == "file"
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `pyarchinit_mini/web_interface/media_serve.py`:

```python
from pyarchinit_mini.media_manager.path_resolver import is_remote_url, cloudinary_to_url

_PROXY = ("unibo://", "webdav://", "s3://", "r2://", "gdrive://", "dropbox://")

def serve_decision(p: str):
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
```
Then in `app.py`'s `serve_media`, call `serve_decision`; for `proxy`, do `mgr = current_app.storage_service.build_manager(); data = mgr.read(p);` if None → `abort(404)` else `send_file(io.BytesIO(data), mimetype=mimetypes.guess_type(p)[0] or "application/octet-stream")`; for `file`, keep the existing realpath-under-roots guard + `send_file`.

- [ ] **Step 4: Run** → PASS (5 passed).
- [ ] **Step 5: Commit** `git add pyarchinit_mini/web_interface/media_serve.py pyarchinit_mini/web_interface/app.py tests/storage/test_media_serve_backends.py && git commit -m "feat(storage): /media/serve proxy for backends + redirect for cloudinary/http"`

---

### Task 10: Settings UI `/settings/storage`

**Files:**
- Modify: `pyarchinit_mini/web_interface/app.py` (routes `GET/POST /settings/storage`, `POST /settings/storage/test/<backend>`; instantiate `app.storage_service = StorageConfigService(db_manager)` at startup)
- Create: `pyarchinit_mini/web_interface/templates/settings/storage.html`
- Test: `tests/storage/test_settings_storage_route.py`

**Interfaces:**
- Consumes: `StorageConfigService` (Task 5), the backends (Task 7).
- Produces: admin-only page listing per-backend credential forms (field names from Global Constraints) + `media_root`/`thumb_path`/`thumb_resize`; POST saves via `storage_service.save(...)`; `test/<backend>` builds the backend from posted creds and returns JSON `{ok: bool, message}` via `backend.connect()`.

- [ ] **Step 1: Write the failing test** (route-level, reuse the app/login fixtures from `tests/` web harness; assert: GET 200 for an admin; POST persists via the service; test endpoint returns JSON). Fill using the existing web test harness (search `tests/` for the app/client/login fixtures).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the routes + template (per-backend `<fieldset>` with the exact field names; `media_root`/`thumb_path`/`thumb_resize` inputs with scheme hints from the spec; a "Test" button per backend calling the test endpoint). Guard with the existing admin/write permission decorator. Store via `storage_service.save`. Never render stored secret values back in cleartext (show placeholders).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `git add pyarchinit_mini/web_interface/app.py pyarchinit_mini/web_interface/templates/settings/storage.html tests/storage/test_settings_storage_route.py && git commit -m "feat(storage): /settings/storage UI with per-backend credentials + test-connection"`

---

### Task 11: Dependencies + migration wiring + docs

**Files:**
- Modify: `requirements.txt`, `pyarchinit_mini/database/migrations/__init__.py` (ensure `storage_config` table is created by create_all — it is, via the model; no data migration needed), `docs/` (a short storage-config runbook)
- Test: `tests/storage/test_optional_deps_absent.py`

- [ ] **Step 1:** Add to `requirements.txt` (as documented optional extras with a comment block): `cryptography` (REQUIRED — used by crypto.py), and optional `boto3`, `webdavclient3`, `dropbox`, `cloudinary`, `google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`. `Pillow`/`requests` already present.
- [ ] **Step 2: Test** that importing `pyarchinit_mini.storage.storage_manager` and instantiating `StorageManager()` works even if optional SDKs are absent (write `tests/storage/test_optional_deps_absent.py` that imports the manager and asserts `get_available_backends()` at least includes local/unibo). Run → PASS.
- [ ] **Step 3:** Add `docs/superpowers/runbooks/media-storage-backends.md` (how to set `PYARCHINIT_SECRET_KEY`, configure a backend in `/settings/storage`, the path formats, and that missing SDKs disable a backend).
- [ ] **Step 4: Commit** `git add requirements.txt docs/superpowers/runbooks/media-storage-backends.md tests/storage/test_optional_deps_absent.py && git commit -m "chore(storage): optional backend deps + storage runbook"`

---

### Task 12: Full suite + release gating

- [ ] **Step 1:** `.venv/bin/pytest tests/storage/ tests/media/ -v` → green; `.venv/bin/pytest tests/ -q` → no NEW failures (the pre-existing `test_delete_site` failure is unrelated).
- [ ] **Step 2:** Manual smoke: set `PYARCHINIT_SECRET_KEY`, configure a local `media_root` via `/settings/storage`, upload→serve works; configure an S3/WebDAV backend (or a mock) and confirm upload writes a scheme-prefixed `filepath` and `/media/serve` proxies it.
- [ ] **Step 3: Commit** any fixups. Release = version bump + build + PyPI + push (Railway) + Adarte deploy (per [[deploy-workflow]]). `PYARCHINIT_SECRET_KEY` must be set in each deployment's env before the storage UI can save credentials.

---

## Self-Review

**Spec coverage:** §3 backends/paths/deps → Tasks 1,2,7,11; §4.1 storage package → 1,2,6,7; §4.2 config+UI → 4,5,10; §4.3 crypto → 3; §4.4 upload → 8; §4.5 serving → 9; §4.6 resolver → 9; §5 deps → 11; §6 cred fields → 10 (+ Global Constraints); §7 testing → each task's tests; §8 rollout → 12.

**Placeholder scan:** Port tasks say "copy plugin file X + these specific adaptations" (concrete, with the exact edits) rather than reproducing ~5k LOC verbatim — this is a deliberate, actionable port instruction, not a vague placeholder. Tasks 10's test says "fill using existing web harness" — a pointer to the repo's real fixtures with the assertions enumerated. All new-code steps show full code.

**Type consistency:** `parse_path(path)->(StorageType,str,str)`, `StorageManager.read/write(path)`, `backend.read(rel)/write(rel,data)`, `CredentialsManager.get_credentials(StorageType)/set_credentials(StorageType,dict)`, `StorageConfigService.get()/save(...)/build_manager()`, `crypto.encrypt_dict/decrypt_dict/has_key`, `serve_decision(p)->(kind,value)`, `MediaHandler(..., storage_manager=)` — used consistently across tasks.
