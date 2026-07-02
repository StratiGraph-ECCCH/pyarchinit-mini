# Media Plugin-Schema Alignment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite pyarchinit-mini's media layer to read/write the classic pyarchinit plugin's media tables (`media_table`, `media_thumb_table`, `media_to_entity_table`) so the two tools share the same rows on one database.

**Architecture:** Swap mini's inline media schema for the plugin's schema (M:N link table + on-disk thumbnails). Media models stop inheriting `BaseModel` (the plugin tables have only `entity_uuid` as a sync column). A small entity-map and path-resolver module port the plugin's conventions. Existing (empty) mini media tables on Adarte/Railway are dropped and recreated.

**Tech Stack:** Python 3.12, SQLAlchemy (classic `Column`/`declarative_base`), Pillow (PIL), Flask, pytest.

## Global Constraints

- Reference schema is the plugin branch `Stratigraph_00001` at
  `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/pyarchinit`.
- PK/FK id columns are **BIGINT** in the real Postgres DB (ORM may say Integer); use `BigInteger`.
- `media_table.filepath` is **UNIQUE** — never insert a duplicate `filepath`; reuse the existing row.
- `media_to_entity_table` PK is the quoted mixed-case identifier `"id_mediaToEntity"`.
- The two FKs are **ON DELETE CASCADE**: `fk_media_thumb_to_media`, `fk_mte_to_media`.
- The only sync column on the three media tables is `entity_uuid` (text/UUID4). No `version_number`,
  `created_at`, `updated_at`, `sync_status`, `last_modified_*`, `editing_*`.
- IDs are assigned as `max(id)+1` (the plugin does this, not `nextval`) — mirror it to coexist.
- **No DDL against festos** (another university's DB): mini maps the existing columns only.
- entity_type/table_name values (UPPERCASE): `US`/`us_table`, `REPERTO`/`inventario_materiali_table`,
  `CERAMICA`/`pottery_table`, `STRUTTURA`/`struttura_table`, `TOMBA`/`tomba_table`, `TMA`/`tma_table`,
  `UT`/`ut_table`. `SITE`/`site_table` is mini-only (plugin never links sites).
- TDD, DRY, YAGNI, frequent commits. Do not add a `Co-Authored-By`/AI-attribution trailer to commits.

## Scope

**In scope (this plan):** models, entity-map, path-resolver (local + already-a-URL passthrough),
MediaHandler (plugin storage convention + thumbnails), MediaService (CRUD via the link table),
DB migration for the empty mini media tables, web-route + MCP-tool adaptation, tests.

**Out of scope → follow-up plan `2026-07-xx-media-remote-backends.md`:** serving/uploading
`unibo://` and other StorageManager-backend schemes (`webdav://`, `s3://`, `gdrive://`, `dropbox://`,
`r2://`, `sftp://`). These need the plugin's credentialed `UniboFileManagerBackend`/StorageManager
ported plus a proxy route, and depend on **Passo 0** (below). This plan makes mini store/pass those
URIs correctly and serve **local paths + http/https/cloudinary** URLs; unibo bytes-serving is deferred.

## Passo 0 — Prerequisite live verification (before Task 8 deploy; blocks nothing earlier)

Not a code task. When festos (or Adarte v1) is reachable, confirm on the real DB:
1. Column names/types of the three media tables match §3 of the spec.
2. Which `(entity_type, table_name)` pairs actually occur, and that `id_entity` uses `id_invmat` for
   inventario and `id_rep` for pottery.
3. The `filepath` convention on real rows: local absolute vs `unibo://…` (determines whether the
   follow-up remote-backend plan is required for festos to display media).

Command template (read-only), run from the repo with `.adarte_secrets.sh` sourced or festos creds:
```bash
psql "$FESTOS_DSN" -c "\d+ media_table" -c "\d+ media_thumb_table" -c "\d+ media_to_entity_table"
psql "$FESTOS_DSN" -c "SELECT DISTINCT entity_type, table_name FROM media_to_entity_table;"
psql "$FESTOS_DSN" -c "SELECT id_media, filepath FROM media_table LIMIT 20;"
```

---

## File Structure

- Create `pyarchinit_mini/media_manager/entity_map.py` — mini entity key ↔ (entity_type, table_name, id_column).
- Create `pyarchinit_mini/media_manager/path_resolver.py` — remote-scheme detection + `resolve_media_path`.
- Modify `pyarchinit_mini/models/media.py` — `Media`, `MediaThumb`, new `MediaToEntity` on `Base` (plugin schema).
- Modify `pyarchinit_mini/models/__init__.py` — export `MediaToEntity`.
- Modify `pyarchinit_mini/database/concurrency_manager.py` — drop media tables from `ID_FIELD_MAPPINGS`.
- Modify `pyarchinit_mini/media_manager/media_handler.py` — plugin storage convention + thumbnails.
- Modify `pyarchinit_mini/services/media_service.py` — CRUD on plugin schema + link table.
- Modify `pyarchinit_mini/web_interface/app.py` — media routes/serving over the new service.
- Modify `pyarchinit_mini/mcp_server/tools/media_management_tool.py` — new entity_type enum + service calls.
- Create migration `pyarchinit_mini/database/migrations/m_2026_07_media_plugin_schema.py`.
- Tests under `tests/media/`.

---

### Task 1: Entity map

**Files:**
- Create: `pyarchinit_mini/media_manager/entity_map.py`
- Test: `tests/media/test_entity_map.py`

**Interfaces:**
- Produces: `ENTITY_MAP: dict[str, tuple[str, str, str]]`;
  `resolve_entity(key: str) -> tuple[str, str, str]` returning `(entity_type, table_name, id_column)`;
  `RemoteMediaEntity` not used. Raises `KeyError` for unknown key.

- [ ] **Step 1: Write the failing test**

```python
# tests/media/test_entity_map.py
import pytest
from pyarchinit_mini.media_manager.entity_map import ENTITY_MAP, resolve_entity

def test_us_maps_to_plugin_values():
    assert resolve_entity("us") == ("US", "us_table", "id_us")

def test_inventario_uses_id_invmat():
    assert resolve_entity("inventario") == ("REPERTO", "inventario_materiali_table", "id_invmat")

def test_pottery_uses_ceramica_and_id_rep():
    assert resolve_entity("pottery") == ("CERAMICA", "pottery_table", "id_rep")

def test_site_is_mini_only_but_mapped():
    assert resolve_entity("site") == ("SITE", "site_table", "id_sito")

def test_unknown_key_raises():
    with pytest.raises(KeyError):
        resolve_entity("nope")

def test_map_has_all_expected_keys():
    assert set(ENTITY_MAP) == {"us", "inventario", "pottery", "struttura", "tomba", "tma", "ut", "site"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/media/test_entity_map.py -v`
Expected: FAIL with `ModuleNotFoundError: pyarchinit_mini.media_manager.entity_map`

- [ ] **Step 3: Write minimal implementation**

```python
# pyarchinit_mini/media_manager/entity_map.py
"""Mapping between pyarchinit-mini entity keys and the classic plugin's
media_to_entity_table (entity_type, table_name) values, plus the entity PK column."""

# key -> (entity_type, table_name, id_column)
ENTITY_MAP: dict[str, tuple[str, str, str]] = {
    "us":         ("US",        "us_table",                   "id_us"),
    "inventario": ("REPERTO",   "inventario_materiali_table", "id_invmat"),
    "pottery":    ("CERAMICA",  "pottery_table",              "id_rep"),
    "struttura":  ("STRUTTURA", "struttura_table",            "id_struttura"),
    "tomba":      ("TOMBA",     "tomba_table",                "id_tomba"),
    "tma":        ("TMA",       "tma_table",                  "id_tma"),
    "ut":         ("UT",        "ut_table",                   "id_ut"),
    # mini-only: the plugin never links media to sites, so these rows are
    # invisible in QGIS but valid.
    "site":       ("SITE",      "site_table",                 "id_sito"),
}

def resolve_entity(key: str) -> tuple[str, str, str]:
    """Return (entity_type, table_name, id_column) for a mini entity key."""
    return ENTITY_MAP[key]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/media/test_entity_map.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add pyarchinit_mini/media_manager/entity_map.py tests/media/test_entity_map.py
git commit -m "feat(media): entity map to classic plugin (entity_type, table_name, id_column)"
```

---

### Task 2: Path resolver

**Files:**
- Create: `pyarchinit_mini/media_manager/path_resolver.py`
- Test: `tests/media/test_path_resolver.py`

**Interfaces:**
- Produces:
  `REMOTE_SCHEMES: tuple[str, ...]`;
  `is_remote_url(path: str) -> bool`;
  `resolve_media_path(base_path: str, filepath: str) -> str` (ports the plugin's `get_image_path`);
  `cloudinary_to_url(path: str) -> str` (cloudinary:// → https URL).

- [ ] **Step 1: Write the failing test**

```python
# tests/media/test_path_resolver.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/media/test_path_resolver.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Ported faithfully from `modules/utility/remote_image_loader.py:167-223,432-464,225-258` of the plugin.

```python
# pyarchinit_mini/media_manager/path_resolver.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/media/test_path_resolver.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add pyarchinit_mini/media_manager/path_resolver.py tests/media/test_path_resolver.py
git commit -m "feat(media): port plugin path resolver (local + URL passthrough)"
```

---

### Task 3: Media models (plugin schema)

**Files:**
- Modify: `pyarchinit_mini/models/media.py`
- Modify: `pyarchinit_mini/models/__init__.py:12,30-32`
- Test: `tests/media/test_media_models.py`

**Interfaces:**
- Produces SQLAlchemy models on `pyarchinit_mini.models.base.Base`:
  - `Media(id_media, mediatype, filename, filetype, filepath, descrizione, tags, entity_uuid)` → `media_table`
  - `MediaThumb(id_media_thumb, id_media, mediatype, media_filename, media_thumb_filename, filetype, filepath, path_resize, entity_uuid)` → `media_thumb_table`
  - `MediaToEntity(id_mediaToEntity, id_entity, entity_type, table_name, id_media, filepath, media_name, entity_uuid)` → `media_to_entity_table`
  - `Documentation` unchanged.

- [ ] **Step 1: Write the failing test**

```python
# tests/media/test_media_models.py
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.media import Media, MediaThumb, MediaToEntity

def _engine():
    eng = create_engine("sqlite:///:memory:")
    @event.listens_for(eng, "connect")
    def _fk(dbapi_con, _):
        dbapi_con.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(eng)
    return eng

def test_media_table_has_plugin_columns():
    cols = {c["name"] for c in inspect(_engine()).get_columns("media_table")}
    assert cols == {"id_media", "mediatype", "filename", "filetype", "filepath",
                    "descrizione", "tags", "entity_uuid"}

def test_thumb_pk_is_id_media_thumb():
    cols = {c["name"] for c in inspect(_engine()).get_columns("media_thumb_table")}
    assert "id_media_thumb" in cols and "path_resize" in cols and "thumb_data" not in cols

def test_link_table_shape():
    cols = {c["name"] for c in inspect(_engine()).get_columns("media_to_entity_table")}
    assert cols == {"id_mediaToEntity", "id_entity", "entity_type", "table_name",
                    "id_media", "filepath", "media_name", "entity_uuid"}

def test_entity_uuid_autofilled():
    Session = sessionmaker(bind=_engine())
    s = Session()
    m = Media(id_media=1, mediatype="image", filename="x.jpg", filetype="jpg",
              filepath="/m/x.jpg", descrizione="", tags="")
    s.add(m); s.commit()
    assert m.entity_uuid and len(m.entity_uuid) == 36

def test_no_basemodel_sync_columns():
    cols = {c["name"] for c in inspect(_engine()).get_columns("media_table")}
    assert "version_number" not in cols and "created_at" not in cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/media/test_media_models.py -v`
Expected: FAIL (`ImportError: cannot import name 'MediaToEntity'`)

- [ ] **Step 3: Write minimal implementation**

Replace the `Media` and `MediaThumb` classes in `pyarchinit_mini/models/media.py` and add
`MediaToEntity`. Keep `Documentation` exactly as-is (it stays on `BaseModel`). New top of file:

```python
"""
Media management models — aligned to the classic pyarchinit plugin schema.
The three media tables are shared with the QGIS plugin, so they do NOT inherit
BaseModel (the plugin tables have only entity_uuid as a sync column).
"""
import uuid
from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
from .base import Base, BaseModel


def _uuid():
    return str(uuid.uuid4())


class Media(Base):
    """media_table — file catalog (shared with the QGIS plugin)."""
    __tablename__ = 'media_table'

    id_media = Column(BigInteger, primary_key=True, autoincrement=True)
    mediatype = Column(Text)                       # "image" | "document" | "video" | ...
    filename = Column(Text)
    filetype = Column(String(10))
    filepath = Column(Text, unique=True)           # UNIQUE natural key; absolute path or remote URI
    descrizione = Column(Text)
    tags = Column(Text)
    entity_uuid = Column(Text, default=_uuid)

    def __repr__(self):
        return f"<Media(id_media={self.id_media}, filepath={self.filepath!r})>"


class MediaThumb(Base):
    """media_thumb_table — on-disk thumbnails (no DB blob)."""
    __tablename__ = 'media_thumb_table'

    id_media_thumb = Column(BigInteger, primary_key=True, autoincrement=True)
    id_media = Column(BigInteger, ForeignKey('media_table.id_media', ondelete='CASCADE'))
    mediatype = Column(Text)
    media_filename = Column(Text)
    media_thumb_filename = Column(Text, unique=True)
    filetype = Column(String(10))
    filepath = Column(Text)                        # 200x200 thumb file
    path_resize = Column(Text)                     # 600x600 resize file
    entity_uuid = Column(Text, default=_uuid)

    def __repr__(self):
        return f"<MediaThumb(id_media_thumb={self.id_media_thumb}, id_media={self.id_media})>"


class MediaToEntity(Base):
    """media_to_entity_table — M:N link between a media file and an archaeological entity."""
    __tablename__ = 'media_to_entity_table'

    id_mediaToEntity = Column(BigInteger, primary_key=True, autoincrement=True)
    id_entity = Column(BigInteger)
    entity_type = Column(Text)                     # 'US','REPERTO','CERAMICA',...
    table_name = Column(Text)                      # 'us_table','pottery_table',...
    id_media = Column(BigInteger, ForeignKey('media_table.id_media', ondelete='CASCADE'))
    filepath = Column(Text)                        # denormalized copy of media_table.filepath
    media_name = Column(Text)                      # denormalized filename
    entity_uuid = Column(Text, default=_uuid)

    def __repr__(self):
        return f"<MediaToEntity({self.entity_type}:{self.id_entity} -> media {self.id_media})>"
```

Keep the existing `Documentation` class below unchanged (it still does `class Documentation(BaseModel)`).

Then update `pyarchinit_mini/models/__init__.py`:
- line 12: `from .media import Media, MediaThumb, MediaToEntity, Documentation`
- add `"MediaToEntity",` to `__all__` (after `"MediaThumb",`).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/media/test_media_models.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add pyarchinit_mini/models/media.py pyarchinit_mini/models/__init__.py tests/media/test_media_models.py
git commit -m "feat(media): models to plugin schema (media_table, media_thumb_table, media_to_entity_table)"
```

---

### Task 4: Drop media tables from the concurrency map

**Files:**
- Modify: `pyarchinit_mini/database/concurrency_manager.py:20-21`
- Test: `tests/media/test_concurrency_media_excluded.py`

**Rationale:** The plugin media tables lack `version_number`/`editing_by`, so optimistic locking must
not run against them. `_get_id_field` must return `None` for media tables.

**Interfaces:**
- Consumes: `ConcurrencyManager._get_id_field` (Task-independent existing method).

- [ ] **Step 1: Write the failing test**

```python
# tests/media/test_concurrency_media_excluded.py
from pyarchinit_mini.database.concurrency_manager import ID_FIELD_MAPPINGS

def test_media_tables_not_lockable():
    assert "media_table" not in ID_FIELD_MAPPINGS
    assert "media_thumb_table" not in ID_FIELD_MAPPINGS
    assert "media_to_entity_table" not in ID_FIELD_MAPPINGS

def test_documentation_still_lockable():
    assert ID_FIELD_MAPPINGS["documentation_table"] == "id_documentazione"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/media/test_concurrency_media_excluded.py -v`
Expected: FAIL (`media_table` still present)

- [ ] **Step 3: Write minimal implementation**

In `pyarchinit_mini/database/concurrency_manager.py`, delete these two lines from `ID_FIELD_MAPPINGS`:
```python
    'media_table': 'id_media',
    'media_thumb_table': 'id_media_thumb',
```
(Leave `documentation_table` and all others.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/media/test_concurrency_media_excluded.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add pyarchinit_mini/database/concurrency_manager.py tests/media/test_concurrency_media_excluded.py
git commit -m "fix(media): exclude plugin media tables from optimistic-locking map"
```

---

### Task 5: MediaHandler — plugin storage convention + thumbnails

**Files:**
- Modify: `pyarchinit_mini/media_manager/media_handler.py` (rewrite `__init__`, `store_file`, thumbnail; keep `_analyze_file`, `_determine_media_type`, `_calculate_file_hash`)
- Test: `tests/media/test_media_handler_plugin.py`

**Interfaces:**
- Produces:
  - `MediaHandler(media_root=None, thumb_path=None, thumb_resize=None)`; env fallbacks
    `PYARCHINIT_MEDIA_ROOT`, `PYARCHINIT_THUMB_PATH`, `PYARCHINIT_THUMB_RESIZE`.
  - `store_original(file_path: str) -> dict` returns `{filename, filetype, mediatype, dest_path}`
    (copies the file into the media folder; `dest_path` is absolute and becomes `media_table.filepath`).
  - `make_thumbnails(source_file: str, id_media: int, filename: str) -> dict | None` returns
    `{media_thumb_filename, thumb_path, resize_path}` (both absolute paths) or `None` for non-images.
  - `thumb_base` property = the configured thumb dir (used by serving to resolve relative thumb paths).

**Interfaces consumed by Task 6.**

- [ ] **Step 1: Write the failing test**

```python
# tests/media/test_media_handler_plugin.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/media/test_media_handler_plugin.py -v`
Expected: FAIL (`MediaHandler` has no `store_original`)

- [ ] **Step 3: Write minimal implementation**

Replace `__init__`, `store_file`, and `_generate_thumbnail` with the below (keep `_analyze_file`,
`_determine_media_type`, `_calculate_file_hash`, and drop the now-unused entity-subdir helpers
`get_file_path`/`organize_media_by_entity`/`create_media_archive`/`delete_file` OR leave them — they
are unused by the new service; leaving them is fine, this task only adds the new methods).

```python
    def __init__(self, media_root: str = None, thumb_path: str = None, thumb_resize: str = None):
        home = os.environ.get("PYARCHINIT_HOME")
        default_media = (os.path.join(home, "pyarchinit_Media_folder") if home
                         else str(Path.home() / ".pyarchinit_mini" / "media"))
        self.media_root = Path(media_root or os.environ.get("PYARCHINIT_MEDIA_ROOT") or default_media)
        self.thumb_path = Path(thumb_path or os.environ.get("PYARCHINIT_THUMB_PATH")
                               or (self.media_root / "thumb"))
        self.thumb_resize = Path(thumb_resize or os.environ.get("PYARCHINIT_THUMB_RESIZE")
                                 or (self.media_root / "thumb_resize"))
        for p in (self.media_root, self.thumb_path, self.thumb_resize):
            p.mkdir(parents=True, exist_ok=True)

    @property
    def thumb_base(self) -> str:
        return str(self.thumb_path)

    def store_original(self, file_path: str) -> Dict[str, Any]:
        """Copy the source file into the media folder (plugin convention) and describe it."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        src = Path(file_path)
        filename = src.name
        filetype = src.suffix.lower().lstrip(".")
        info = self._analyze_file(src)
        dest_path = self.media_root / filename
        shutil.copy2(src, dest_path)
        return {
            "filename": filename,
            "filetype": filetype,
            "mediatype": info["media_type"],
            "dest_path": str(dest_path),
        }

    def make_thumbnails(self, source_file: str, id_media: int, filename: str) -> Optional[Dict[str, str]]:
        """Generate 200x200 + 600x600 thumbnails named thumb_<id_media>_<filename>."""
        try:
            if self._determine_media_type(None, Path(filename)) != "image" and \
               not (mimetypes.guess_type(filename)[0] or "").startswith("image/"):
                return None
            thumb_filename = f"thumb_{id_media}_{filename}"
            thumb_full = self.thumb_path / thumb_filename
            resize_full = self.thumb_resize / thumb_filename
            with Image.open(source_file) as im:
                small = im.copy(); small.thumbnail((200, 200), Image.Resampling.LANCZOS)
                small.save(thumb_full)
            with Image.open(source_file) as im:
                big = im.copy(); big.thumbnail((600, 600), Image.Resampling.LANCZOS)
                big.save(resize_full)
            return {
                "media_thumb_filename": thumb_filename,
                "thumb_path": str(thumb_full),
                "resize_path": str(resize_full),
            }
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            return None
```

(Improvement over the plugin: the 600px resize is regenerated from the original, not from the already-200px image. Same filenames/columns → fully compatible.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/media/test_media_handler_plugin.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add pyarchinit_mini/media_manager/media_handler.py tests/media/test_media_handler_plugin.py
git commit -m "feat(media): MediaHandler stores to plugin media folder + thumb/thumb_resize"
```

---

### Task 6: MediaService — CRUD via the link table

**Files:**
- Modify: `pyarchinit_mini/services/media_service.py` (rewrite `MediaService`; keep `DocumentationService`)
- Test: `tests/media/test_media_service_plugin.py`

**Interfaces:**
- Consumes: `resolve_entity` (Task 1), `MediaHandler.store_original`/`make_thumbnails` (Task 5),
  models `Media`/`MediaThumb`/`MediaToEntity` (Task 3).
- Produces on `MediaService`:
  - `add_media(file_path, entity_key, id_entity, descrizione="", tags="") -> Media`
  - `get_media_for_entity(entity_key, id_entity) -> list[Media]`
  - `get_media_for_entity_ids(entity_key, ids) -> dict[int, list[dict]]` (descriptors with `url`/`thumb_url`)
  - `unlink_media(id_media, entity_key, id_entity) -> bool`
  - `delete_media(id_media, delete_files=True) -> bool`

Design notes baked into the code below:
- id = `max(id)+1` via `_next_id`, retried once on `IntegrityError` (mirrors plugin, coexists safely).
- `add_media` reuses an existing `media_table` row when `filepath` already exists (UNIQUE), then
  dedups the link on `(id_entity, entity_type, id_media)`.
- `delete_media` relies on the CASCADE FKs to remove thumbs+links, then removes physical files.

- [ ] **Step 1: Write the failing test**

```python
# tests/media/test_media_service_plugin.py
import os
import pytest
from PIL import Image
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.media import Media, MediaToEntity, MediaThumb
from pyarchinit_mini.media_manager.media_handler import MediaHandler
from pyarchinit_mini.services.media_service import MediaService

class _Conn:
    def __init__(self, engine): self._Session = sessionmaker(bind=engine)
    def get_session(self): return self._Session()

class _DBM:
    def __init__(self, engine): self.connection = _Conn(engine)

@pytest.fixture
def svc(tmp_path):
    eng = create_engine("sqlite:///:memory:")
    @event.listens_for(eng, "connect")
    def _fk(c, _): c.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(eng)
    handler = MediaHandler(media_root=str(tmp_path/"media"),
                           thumb_path=str(tmp_path/"thumb"),
                           thumb_resize=str(tmp_path/"resize"))
    return MediaService(_DBM(eng), handler)

def _png(tmp_path, name):
    p = tmp_path / name; Image.new("RGB", (300, 300)).save(p); return str(p)

def test_add_media_creates_media_thumb_and_link(svc, tmp_path):
    m = svc.add_media(_png(tmp_path, "a.png"), "us", 42, descrizione="d", tags="t")
    assert m.id_media == 1 and m.filepath.endswith("a.png") and m.mediatype == "image"
    got = svc.get_media_for_entity("us", 42)
    assert [x.id_media for x in got] == [1]

def test_add_same_file_twice_reuses_media_row(svc, tmp_path):
    src = _png(tmp_path, "b.png")
    m1 = svc.add_media(src, "us", 1, )
    m2 = svc.add_media(src, "us", 2, )   # same filepath, different entity
    assert m1.id_media == m2.id_media     # reused media row
    assert len(svc.get_media_for_entity("us", 1)) == 1
    assert len(svc.get_media_for_entity("us", 2)) == 1

def test_link_dedup(svc, tmp_path):
    src = _png(tmp_path, "c.png")
    svc.add_media(src, "us", 5)
    svc.add_media(src, "us", 5)           # identical link -> no duplicate
    assert len(svc.get_media_for_entity("us", 5)) == 1

def test_unlink_keeps_media(svc, tmp_path):
    m = svc.add_media(_png(tmp_path, "d.png"), "us", 9)
    assert svc.unlink_media(m.id_media, "us", 9) is True
    assert svc.get_media_for_entity("us", 9) == []
    assert svc.get_media_by_id(m.id_media) is not None

def test_delete_media_cascades(svc, tmp_path):
    m = svc.add_media(_png(tmp_path, "e.png"), "us", 3)
    assert svc.delete_media(m.id_media) is True
    assert svc.get_media_by_id(m.id_media) is None
    with svc.db_manager.connection.get_session() as s:
        assert s.query(MediaToEntity).count() == 0
        assert s.query(MediaThumb).count() == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/media/test_media_service_plugin.py -v`
Expected: FAIL (`MediaService` has no `add_media`)

- [ ] **Step 3: Write minimal implementation**

Replace the `MediaService` class body (keep the module imports + `DocumentationService`). New imports at
top: `from sqlalchemy.exc import IntegrityError`, `from ..models.media import Media, MediaThumb, MediaToEntity`,
`from .._` … and `from ..media_manager.entity_map import resolve_entity`,
`from ..media_manager.path_resolver import resolve_media_path, is_remote_url, cloudinary_to_url`.

```python
class MediaService:
    """Media operations over the classic-plugin media schema (shared DB)."""

    def __init__(self, db_manager, media_handler=None):
        self.db_manager = db_manager
        self.media_handler = media_handler or MediaHandler()

    def _next_id(self, session, model, id_col):
        cur = session.query(func.max(getattr(model, id_col))).scalar()
        return (cur or 0) + 1

    def get_media_by_id(self, media_id):
        with self.db_manager.connection.get_session() as s:
            return s.get(Media, media_id)

    def add_media(self, file_path, entity_key, id_entity, descrizione="", tags=""):
        entity_type, table_name, _ = resolve_entity(entity_key)
        stored = self.media_handler.store_original(file_path)
        dest_path, filename = stored["dest_path"], stored["filename"]
        for attempt in range(2):
            try:
                with self.db_manager.connection.get_session() as s:
                    media = s.query(Media).filter(Media.filepath == dest_path).first()
                    if media is None:
                        media = Media(
                            id_media=self._next_id(s, Media, "id_media"),
                            mediatype=stored["mediatype"], filename=filename,
                            filetype=stored["filetype"], filepath=dest_path,
                            descrizione=descrizione, tags=tags,
                        )
                        s.add(media); s.flush()
                        thumb = self.media_handler.make_thumbnails(dest_path, media.id_media, filename)
                        if thumb:
                            s.add(MediaThumb(
                                id_media_thumb=self._next_id(s, MediaThumb, "id_media_thumb"),
                                id_media=media.id_media, mediatype=stored["mediatype"],
                                media_filename=filename,
                                media_thumb_filename=thumb["media_thumb_filename"],
                                filetype=stored["filetype"], filepath=thumb["thumb_path"],
                                path_resize=thumb["resize_path"],
                            ))
                    exists = s.query(MediaToEntity).filter(
                        MediaToEntity.id_entity == id_entity,
                        MediaToEntity.entity_type == entity_type,
                        MediaToEntity.id_media == media.id_media,
                    ).first()
                    if exists is None:
                        s.add(MediaToEntity(
                            id_mediaToEntity=self._next_id(s, MediaToEntity, "id_mediaToEntity"),
                            id_entity=id_entity, entity_type=entity_type, table_name=table_name,
                            id_media=media.id_media, filepath=dest_path, media_name=filename,
                        ))
                    s.commit()
                    s.refresh(media)
                    s.expunge(media)
                    return media
            except IntegrityError:
                if attempt == 1:
                    raise
                continue

    def get_media_for_entity(self, entity_key, id_entity):
        entity_type, table_name, _ = resolve_entity(entity_key)
        with self.db_manager.connection.get_session() as s:
            q = (s.query(Media)
                 .join(MediaToEntity, MediaToEntity.id_media == Media.id_media)
                 .filter(MediaToEntity.table_name == table_name,
                         MediaToEntity.id_entity == id_entity)
                 .order_by(Media.id_media.desc()))
            rows = q.all()
            for r in rows:
                s.expunge(r)
            return rows

    def get_media_for_entity_ids(self, entity_key, entity_ids):
        result = {eid: [] for eid in entity_ids}
        for eid in entity_ids:
            try:
                items = self.get_media_for_entity(entity_key, eid)
            except Exception:
                items = []
            result[eid] = [{
                "id_media": m.id_media,
                "media_name": m.filename,
                "filepath": m.filepath,
                "media_type": m.mediatype,
                "url": self.public_url(m.filepath),
                "thumb_url": self.thumb_url(m.id_media),
            } for m in items]
        return result

    def public_url(self, filepath):
        """URL the browser can load for a stored media filepath."""
        if not filepath:
            return ""
        if filepath.lower().startswith("cloudinary://"):
            return cloudinary_to_url(filepath)
        if filepath.lower().startswith(("http://", "https://")):
            return filepath
        # local absolute path or unibo/other backend -> serve through mini's route
        return "/media/serve?p=" + filepath

    def thumb_url(self, id_media):
        with self.db_manager.connection.get_session() as s:
            t = s.query(MediaThumb).filter(MediaThumb.id_media == id_media).first()
            if not t or not t.filepath:
                return self.public_url(self._media_path(s, id_media))
            return self.public_url(t.filepath)

    def _media_path(self, session, id_media):
        m = session.get(Media, id_media)
        return m.filepath if m else ""

    def unlink_media(self, id_media, entity_key, id_entity):
        entity_type, _, _ = resolve_entity(entity_key)
        with self.db_manager.connection.get_session() as s:
            s.query(MediaToEntity).filter(
                MediaToEntity.id_media == id_media,
                MediaToEntity.entity_type == entity_type,
                MediaToEntity.id_entity == id_entity,
            ).delete()
            s.commit()
            return True

    def delete_media(self, id_media, delete_files=True):
        with self.db_manager.connection.get_session() as s:
            media = s.get(Media, id_media)
            if not media:
                return False
            files = []
            if delete_files:
                files.append(media.filepath)
                for t in s.query(MediaThumb).filter(MediaThumb.id_media == id_media).all():
                    files += [t.filepath, t.path_resize]
            s.delete(media)      # CASCADE removes thumbs + links
            s.commit()
        if delete_files:
            for f in files:
                try:
                    if f and not is_remote_url(f) and os.path.exists(f):
                        os.remove(f)
                except Exception:
                    pass
        return True
```

Add `from sqlalchemy import func` to the imports if not present.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/media/test_media_service_plugin.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add pyarchinit_mini/services/media_service.py tests/media/test_media_service_plugin.py
git commit -m "feat(media): MediaService CRUD over media_to_entity_table (dedup, cascade delete)"
```

---

### Task 7: Migration — recreate empty mini media tables

**Files:**
- Create: `pyarchinit_mini/database/migrations/m_2026_07_media_plugin_schema.py`
- Test: `tests/media/test_media_migration.py`

**Interfaces:**
- Produces: `migrate(engine) -> dict` — returns `{"status": "migrated"|"skipped", "reason": str}`.
  Drops `media_thumb_table`, `media_table`, `media_to_entity_table` and recreates them from the
  current models **only if all existing media tables are empty**; otherwise skips.

- [ ] **Step 1: Write the failing test**

```python
# tests/media/test_media_migration.py
from sqlalchemy import create_engine, text, inspect
from pyarchinit_mini.database.migrations.m_2026_07_media_plugin_schema import migrate

def _old_schema(engine):
    with engine.begin() as c:
        c.execute(text("CREATE TABLE media_table (id_media INTEGER PRIMARY KEY, "
                       "entity_type TEXT, entity_id INTEGER, media_path TEXT)"))
        c.execute(text("CREATE TABLE media_thumb_table (id_thumb INTEGER PRIMARY KEY, id_media INTEGER)"))

def test_migrates_when_empty():
    eng = create_engine("sqlite:///:memory:")
    _old_schema(eng)
    res = migrate(eng)
    assert res["status"] == "migrated"
    cols = {c["name"] for c in inspect(eng).get_columns("media_table")}
    assert "filepath" in cols and "entity_id" not in cols
    assert "media_to_entity_table" in inspect(eng).get_table_names()

def test_skips_when_media_has_rows():
    eng = create_engine("sqlite:///:memory:")
    _old_schema(eng)
    with eng.begin() as c:
        c.execute(text("INSERT INTO media_table (id_media) VALUES (1)"))
    res = migrate(eng)
    assert res["status"] == "skipped"
    cols = {c["name"] for c in inspect(eng).get_columns("media_table")}
    assert "media_path" in cols  # unchanged
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/media/test_media_migration.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write minimal implementation**

```python
# pyarchinit_mini/database/migrations/m_2026_07_media_plugin_schema.py
"""One-shot: replace mini's inline media schema with the classic-plugin schema.

Safe: only runs when the existing media tables are empty (Adarte v2 / Railway have
no media). Never touches a DB that already holds media rows."""
from sqlalchemy import inspect, text
from ...models.base import Base
from ...models.media import Media, MediaThumb, MediaToEntity  # noqa: F401  (register on Base)

_MEDIA_TABLES = ("media_thumb_table", "media_to_entity_table", "media_table")


def _count(conn, table):
    return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()


def migrate(engine) -> dict:
    insp = inspect(engine)
    present = set(insp.get_table_names())
    with engine.begin() as conn:
        for t in ("media_table", "media_thumb_table", "media_to_entity_table"):
            if t in present and _count(conn, t) > 0:
                return {"status": "skipped", "reason": f"{t} has rows"}
        for t in _MEDIA_TABLES:
            if t in present:
                conn.execute(text(f"DROP TABLE {t}"))
    Base.metadata.create_all(
        engine,
        tables=[Media.__table__, MediaThumb.__table__, MediaToEntity.__table__],
    )
    return {"status": "migrated", "reason": "recreated media tables from plugin schema"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/media/test_media_migration.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add pyarchinit_mini/database/migrations/m_2026_07_media_plugin_schema.py tests/media/test_media_migration.py
git commit -m "feat(media): migration recreating empty media tables in plugin schema"
```

---

### Task 8: Web routes over the new service

**Files:**
- Modify: `pyarchinit_mini/web_interface/app.py` (media routes ~2727-3081; upload ~2803-2990; serve ~3059-3081)
- Test: `tests/media/test_web_media_routes.py`

**Interfaces:**
- Consumes: `MediaService.add_media`, `get_media_for_entity`, `public_url`, `delete_media`,
  `unlink_media`; `resolve_media_path` (Task 2).

**Changes (each is a concrete edit, not a placeholder):**

1. **Upload** (`/media/upload`, `/media/upload/ajax`): replace the `media_handler.store_file(...)` +
   `media_service.create_media_record(...)` calls (app.py ~2889-2902) with a single call:
   ```python
   media = current_app.media_service.add_media(
       tmp_saved_path, entity_key, id_entity,
       descrizione=form.description.data or "", tags=form.tags.data or "",
   )
   ```
   where `entity_key` is the form's entity type already resolved to one of
   `us|inventario|pottery|tma|site` and `id_entity` is the numeric PK the route already computes
   (app.py ~2822-2875). The `MediaUploadForm` `entity_type` choices (app.py:303-309) stay the same
   keys (they are the mini keys, mapped by `resolve_entity`).

2. **Serve** (replace `serve_media` at app.py:3059-3072): media are now stored as absolute paths (or
   URIs). Add a route that resolves+streams local files and redirects http/https/cloudinary:
   ```python
   @app.route('/media/serve')
   @login_required
   def serve_media():
       from pyarchinit_mini.media_manager.path_resolver import is_remote_url, cloudinary_to_url
       p = request.args.get('p', '')
       if not p:
           abort(404)
       low = p.lower()
       if low.startswith('cloudinary://'):
           return redirect(cloudinary_to_url(p))
       if low.startswith(('http://', 'https://')):
           return redirect(p)
       if is_remote_url(p):           # unibo:// / storage-backend → follow-up plan
           abort(501)
       # local absolute path: restrict to the configured media/thumb roots
       h = current_app.media_service.media_handler
       roots = [str(h.media_root), str(h.thumb_path), str(h.thumb_resize)]
       real = os.path.realpath(p)
       if not any(real.startswith(os.path.realpath(r)) for r in roots):
           abort(403)
       if not os.path.isfile(real):
           abort(404)
       return send_file(real)
   ```
   Keep the legacy `/media/<path:filepath>` route returning 404/redirect to `/media/serve?p=` for
   backward-compatible links, or remove it (no media rows reference the old scheme).

3. **List** (`/media/list`, app.py ~2992-3057) and the per-entity galleries that call
   `media_service.get_media_by_entity('site'|'us'|'inventario'|'tma', ...)` (app.py 871,1518,1830,4676):
   rename calls to `get_media_for_entity(entity_key, id_entity)` and read `.filename`/`.filepath`
   instead of `.media_name`/`.media_path`; use `m.mediatype`; build URLs via
   `current_app.media_service.public_url(m.filepath)` and `thumb_url(m.id_media)`.

4. **Delete** (`/media/delete/<int:media_id>`, app.py ~3083): call
   `current_app.media_service.delete_media(media_id)`.

5. **API** (`/api/media/by-entity/<entity_type>/<int:entity_id>`, app.py ~2783-2801): return
   `get_media_for_entity_ids(entity_type, [entity_id])[entity_id]` (descriptors already carry
   `url`/`thumb_url`).

- [ ] **Step 1: Write the failing test** (route-level smoke over a temp app+DB)

```python
# tests/media/test_web_media_routes.py
# Build the Flask app test client with a temp sqlite created from Base.metadata and a
# MediaService wired to a tmp MediaHandler; log in a write user; then:
#  - POST an image to /media/upload for us id=1 -> 302/200
#  - GET /media/list -> 200 and the filename appears
#  - GET the media's /media/serve?p=<abs> -> 200 and image bytes
#  - POST /media/delete/<id> -> media gone from /media/list
# (Follow the existing web test harness in tests/ for app/client/login fixtures.)
```
Fill this test using the repo's existing web-test fixtures (search `tests/` for the current
`client`/`login` helpers and the app factory). Assert the four behaviors above.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/media/test_web_media_routes.py -v`
Expected: FAIL (routes still reference `media_path`/old service)

- [ ] **Step 3: Apply the edits** in changes 1–5 above.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/media/test_web_media_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyarchinit_mini/web_interface/app.py tests/media/test_web_media_routes.py
git commit -m "feat(media): web routes serve/upload over plugin schema + link table"
```

---

### Task 9: MCP tool adaptation

**Files:**
- Modify: `pyarchinit_mini/mcp_server/tools/media_management_tool.py`
- Test: `tests/media/test_mcp_media_tool.py`

**Changes:**
1. `entity_type` enum (currently `site|us|inventario`) → the mini keys used by `resolve_entity`:
   `us|inventario|pottery|struttura|tomba|tma|ut|site`.
2. `upload` op → `media_service.add_media(file_path, entity_type, int(id_entity), descrizione, tags)`.
3. `list` op → `media_service.get_media_for_entity(entity_type, int(id_entity))`, returning
   `{id_media, filename, filepath, mediatype, url}` per item.
4. `delete` op → `media_service.delete_media(int(media_id))`.
5. Remove `set_primary` op (out of scope) or make it a no-op returning "not supported".

- [ ] **Step 1: Write the failing test**

```python
# tests/media/test_mcp_media_tool.py
# Instantiate MediaManagementTool with a MediaService wired to a temp DB+handler.
# assert: upload returns the new id_media; list returns that item with 'filepath';
# delete removes it; entity_type schema enum contains 'pottery' and 'ut'.
```
Fill using the tool's existing construction pattern (see other tests under `tests/` for MCP tools).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/media/test_mcp_media_tool.py -v`
Expected: FAIL

- [ ] **Step 3: Apply the edits** (changes 1–5).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/media/test_mcp_media_tool.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyarchinit_mini/mcp_server/tools/media_management_tool.py tests/media/test_mcp_media_tool.py
git commit -m "feat(media): MCP media tool uses plugin schema + entity map"
```

---

### Task 10: Full suite + release gating

- [ ] **Step 1:** Run the whole media suite and the broader suite for regressions.

Run: `pytest tests/media/ -v && pytest tests/ -q`
Expected: media suite green; no new failures elsewhere (note pre-existing failures if any).

- [ ] **Step 2:** Manual smoke on a fresh empty DB (create from `Base.metadata`), run the migration,
  upload→list→serve→delete via the web client. Confirm files land in `media_root`/`thumb`/`thumb_resize`.

- [ ] **Step 3: Commit** any test-only fixups.

```bash
git add -A && git commit -m "test(media): full media suite green on plugin schema"
```

**Release (after Passo 0 confirms festos schema):** version bump + `python -m build` + `twine upload`,
then Adarte + Railway deploy (run the Task-7 migration there to recreate the empty tables), then the
festos deploy + bidirectional smoke test (create in QGIS → visible in web; create in web → visible in
QGIS; delete → cascade). If festos stores `unibo://` paths, media **display** needs the follow-up
remote-backends plan; record/link operations already work.

---

## Self-Review

**Spec coverage:** §3 schema → Task 3; §4 models/no-BaseModel → Task 3; §5 entity map → Task 1;
§6 M:N create/query/delete → Task 6; §7 path resolution (local + URL) → Task 2 + Task 8 serve
(unibo bytes = follow-up, per Scope); §8 thumbnails → Task 5; §9 service/handler/mcp → Tasks 5,6,9;
§10 web → Task 8; §12 migration → Task 7; §13 rollout/Passo 0 → Task 10 + Passo 0 section.
Concurrency-map cleanup (implied by "no BaseModel columns") → Task 4.

**Placeholder scan:** Tasks 8 and 9 tests say "fill using existing fixtures" — this is a pointer to
the repo's real web/MCP test harness (which the plan can't reproduce blind), not a vague requirement;
the assertions to make are enumerated. All code steps show real code.

**Type consistency:** `add_media(file_path, entity_key, id_entity, descrizione, tags)`,
`get_media_for_entity(entity_key, id_entity)`, `public_url(filepath)`, `thumb_url(id_media)`,
`resolve_entity(key)->(entity_type,table_name,id_column)`, `resolve_media_path(base,filepath)`,
`store_original(file_path)->{filename,filetype,mediatype,dest_path}`,
`make_thumbnails(source_file,id_media,filename)->{media_thumb_filename,thumb_path,resize_path}` — used
consistently across Tasks 1–9.
