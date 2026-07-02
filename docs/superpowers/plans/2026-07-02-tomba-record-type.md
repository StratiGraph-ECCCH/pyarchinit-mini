# Tomba Record Type (SP2 first slice) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add the `tomba` (burial) record type to pyarchinit-mini web — full CRUD, plugin-schema-compatible (shared DB), integrated with thesaurus, media, dashboard, AI, MCP, and docs — as the proven template to replicate for struttura/fauna/UT.

**Architecture:** Mirror mini's newer TMA pattern: a `Tomba(BaseModel)` model mapping the plugin's `tomba_table` columns; table created by `create_all` (model registered) with sync columns ALTER-added to a pre-existing plugin table by the concurrency migration; a `TombaService` (mirror `tma_service.py`); TMA-style Flask routes with a generic `request.form` passthrough + client-side thesaurus `<datalist>` fed by a JSON API; media via the existing `entity_map` `tomba` key.

**Tech Stack:** Python 3.12, SQLAlchemy, Flask, WTForms-free generic form, pytest.

## Global Constraints

- Plugin `tomba_table` columns (map EXACTLY, types from plugin `Tomba_table.py`): `id_tomba`(Integer PK), `sito`(Text), `area`(Integer), `nr_scheda_taf`(Integer), `sigla_struttura`(Text), `nr_struttura`(Integer), `nr_individuo`(Text), `rito`(Text), `descrizione_taf`(Text), `interpretazione_taf`(Text), `segnacoli`(Text), `canale_libatorio_si_no`(Text), `oggetti_rinvenuti_esterno`(Text), `stato_di_conservazione`(Text), `copertura_tipo`(Text), `tipo_contenitore_resti`(Text), `tipo_deposizione`(Text), `tipo_sepoltura`(Text), `corredo_presenza`(Text), `corredo_tipo`(Text), `corredo_descrizione`(Text), `periodo_iniziale`(Integer), `fase_iniziale`(Integer), `periodo_finale`(Integer), `fase_finale`(Integer), `datazione_estesa`(String(300)). `entity_uuid` comes from `BaseModel` — do NOT redeclare it.
- Model inherits `BaseModel` (gets sync columns) like `US`/`InventarioMateriali` — so on the shared plugin DB the sync columns must be ALTER-added to `tomba_table` by mini's concurrency-columns migration (same as `us_table`).
- Thesaurus-controlled fields: `rito`, `tipo_sepoltura`, `tipo_deposizione`, `copertura_tipo`, `tipo_contenitore_resti`, `stato_di_conservazione`, `corredo_presenza`.
- Media key is `tomba` (already in `pyarchinit_mini/media_manager/entity_map.py` → `TOMBA`/`tomba_table`/`id_tomba`).
- Reference code to COPY/adapt (read these; do not reinvent): `pyarchinit_mini/services/tma_service.py`, the TMA routes block `pyarchinit_mini/web_interface/app.py:4831-4987`, `pyarchinit_mini/web_interface/templates/tma/{list,form}.html`, `pyarchinit_mini/models/tma.py`, `pyarchinit_mini/models/thesaurus.py::THESAURUS_MAPPINGS`, the `_media_gallery` helper `app.py:685`, dashboard `app.py:index` (~802-834) + `templates/dashboard.html:48-56`, `services/ai_assistant_service.py:39-79`, `mcp_server/tools/data_import_parser_tool.py` (`FIELD_MAPPINGS`, `_get_service_for_table`), `mcp_server/tools/pyarchinit_sync_tool.py:40`.
- Run tests with `.venv/bin/pytest`. TDD, DRY, YAGNI, frequent commits. No `Co-Authored-By`/AI-attribution trailer on commits.
- Do NOT modify the existing US/inventario/pottery/TMA entities. Harris matrix stays US-only (no change).

---

## File Structure
- Create `pyarchinit_mini/models/tomba.py`; modify `models/__init__.py`, `database/database_creator.py`.
- Modify `pyarchinit_mini/database/migrations/__init__.py` (concurrency-columns migration table list).
- Create `pyarchinit_mini/services/tomba_service.py`; modify `services/__init__.py`.
- Modify `pyarchinit_mini/web_interface/app.py` (instantiate service, routes, dashboard count).
- Create `pyarchinit_mini/web_interface/templates/tomba/{list,form}.html`; modify `templates/base.html` (nav), `templates/dashboard.html` (tile).
- Modify `models/thesaurus.py`, `services/ai_assistant_service.py`, `mcp_server/tools/data_import_parser_tool.py`, `mcp_server/tools/pyarchinit_sync_tool.py`.
- Create `docs/tomba.rst`, `docs/tomba_service.rst`; modify `docs/index.rst`, `docs/tutorials/web_interface_tutorial.rst`, `README.md`, `CHANGELOG.md`.
- Tests under `tests/tomba/`.

---

### Task 1: Tomba model

**Files:** Create `pyarchinit_mini/models/tomba.py`; Modify `models/__init__.py`, `database/database_creator.py`; Test `tests/tomba/test_tomba_model.py`

**Interfaces:** Produces `Tomba(BaseModel)` → table `tomba_table`, PK `id_tomba`, the 26 mapped columns + inherited BaseModel columns; `to_dict()`.

- [ ] **Step 1: Failing test**
```python
# tests/tomba/test_tomba_model.py
from sqlalchemy import create_engine, inspect
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.tomba import Tomba

def test_tomba_table_columns():
    eng = create_engine("sqlite:///:memory:"); Base.metadata.create_all(eng)
    cols = {c["name"] for c in inspect(eng).get_columns("tomba_table")}
    expected = {"id_tomba","sito","area","nr_scheda_taf","sigla_struttura","nr_struttura",
        "nr_individuo","rito","descrizione_taf","interpretazione_taf","segnacoli",
        "canale_libatorio_si_no","oggetti_rinvenuti_esterno","stato_di_conservazione",
        "copertura_tipo","tipo_contenitore_resti","tipo_deposizione","tipo_sepoltura",
        "corredo_presenza","corredo_tipo","corredo_descrizione","periodo_iniziale",
        "fase_iniziale","periodo_finale","fase_finale","datazione_estesa","entity_uuid"}
    assert expected <= cols
    # BaseModel sync columns present too
    assert {"version_number","sync_status","created_at"} <= cols

def test_to_dict():
    t = Tomba(id_tomba=1, sito="S", rito="inumazione")
    d = t.to_dict()
    assert d["id_tomba"] == 1 and d["rito"] == "inumazione"
```
- [ ] **Step 2: Run** `.venv/bin/pytest tests/tomba/test_tomba_model.py -v` → FAIL (no module). Create `tests/tomba/__init__.py` (empty) if needed.
- [ ] **Step 3: Implement** `pyarchinit_mini/models/tomba.py`:
```python
"""Tomba (burial) record — matches the classic pyarchinit tomba_table."""
from sqlalchemy import Column, Integer, String, Text
from .base import BaseModel

class Tomba(BaseModel):
    __tablename__ = 'tomba_table'
    id_tomba = Column(Integer, primary_key=True, autoincrement=True)
    sito = Column(Text)
    area = Column(Integer)
    nr_scheda_taf = Column(Integer)
    sigla_struttura = Column(Text)
    nr_struttura = Column(Integer)
    nr_individuo = Column(Text)
    rito = Column(Text)
    descrizione_taf = Column(Text)
    interpretazione_taf = Column(Text)
    segnacoli = Column(Text)
    canale_libatorio_si_no = Column(Text)
    oggetti_rinvenuti_esterno = Column(Text)
    stato_di_conservazione = Column(Text)
    copertura_tipo = Column(Text)
    tipo_contenitore_resti = Column(Text)
    tipo_deposizione = Column(Text)
    tipo_sepoltura = Column(Text)
    corredo_presenza = Column(Text)
    corredo_tipo = Column(Text)
    corredo_descrizione = Column(Text)
    periodo_iniziale = Column(Integer)
    fase_iniziale = Column(Integer)
    periodo_finale = Column(Integer)
    fase_finale = Column(Integer)
    datazione_estesa = Column(String(300))

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```
Register: in `models/__init__.py` add `from .tomba import Tomba` + `"Tomba"` in `__all__`; in `database/database_creator.py::_import_all_models` add `from ..models.tomba import Tomba  # noqa: F401`.
- [ ] **Step 4: Run** the focused test → PASS. Also `.venv/bin/python -c "import pyarchinit_mini.models; import pyarchinit_mini.database.database_creator"` → no error.
- [ ] **Step 5: Commit** `git add pyarchinit_mini/models/tomba.py pyarchinit_mini/models/__init__.py pyarchinit_mini/database/database_creator.py tests/tomba/ && git commit -m "feat(tomba): model mapping classic tomba_table"`

---

### Task 2: Concurrency-columns migration covers tomba_table

**Files:** Modify `pyarchinit_mini/database/migrations/__init__.py`; Test `tests/tomba/test_tomba_migration.py`

**Context:** On the shared plugin DB, `tomba_table` exists with the plugin columns but NOT mini's sync columns (`version_number`, `sync_status`, `editing_by`, `last_modified_*`). Mini's concurrency-columns migration adds these to record tables (us_table, inventario_materiali_table, …). Add `tomba_table` to that list.

- [ ] **Step 1:** Read `database/migrations/__init__.py` — find the concurrency/sync-columns migration (the one whose Railway log line is "Column version_number already exists in table us_table"; it iterates a list of table names and ALTER-adds the sync columns). Note the exact table-list variable/location.
- [ ] **Step 2: Failing test**
```python
# tests/tomba/test_tomba_migration.py
from sqlalchemy import create_engine, text, inspect

def test_sync_columns_added_to_existing_plugin_tomba_table():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as c:
        # a bare plugin-style tomba_table WITHOUT mini sync columns
        c.execute(text("CREATE TABLE tomba_table (id_tomba INTEGER PRIMARY KEY, sito TEXT, rito TEXT, entity_uuid TEXT)"))
    from pyarchinit_mini.database.migrations import DatabaseMigrations
    DatabaseMigrations(eng).migrate_concurrency_columns()   # use the REAL method name found in Step 1
    cols = {c["name"] for c in inspect(eng).get_columns("tomba_table")}
    assert {"version_number","sync_status","editing_by"} <= cols
```
(Adjust the method name/constructor to the real API discovered in Step 1; if the concurrency migration is only callable via `run_all_migrations`, call that instead and pre-create the other tables it expects, or call the specific method.)
- [ ] **Step 3: Run** → FAIL (tomba_table not in the list → columns absent).
- [ ] **Step 4: Implement** — add `'tomba_table'` to the concurrency migration's table list.
- [ ] **Step 5: Run** → PASS. Commit `git add pyarchinit_mini/database/migrations/__init__.py tests/tomba/test_tomba_migration.py && git commit -m "feat(tomba): concurrency migration adds sync columns to tomba_table (shared-DB)"`

---

### Task 3: TombaService (CRUD + thesaurus + sites)

**Files:** Create `pyarchinit_mini/services/tomba_service.py`; Test `tests/tomba/test_tomba_service.py`

**Interfaces:** Produces `TombaService(db_manager)` with `list_tomba(page,size,search,sito)->list[dict]`, `count_tomba(search,sito)->int`, `get_tomba(id)->dict|None`, `create_tomba(data)->int|None`, `update_tomba(id,data)->bool`, `delete_tomba(id)->bool`, `get_thesaurus_values(field)->list[dict]`, `get_distinct_sites()->list[str]`.

- [ ] **Step 1: Failing test** (mirror `tests/media/test_media_service_plugin.py` fixture style: a `_DBM` wrapping a sqlite engine with `Base.metadata.create_all`):
```python
# tests/tomba/test_tomba_service.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pyarchinit_mini.models.base import Base
from pyarchinit_mini.models.tomba import Tomba  # noqa
from pyarchinit_mini.services.tomba_service import TombaService

class _Conn:
    def __init__(s,e): s._S=sessionmaker(bind=e)
    def get_session(s): return s._S()
class _DBM:
    def __init__(s,e): s.connection=_Conn(e)

@pytest.fixture
def svc():
    e=create_engine("sqlite:///:memory:"); Base.metadata.create_all(e)
    return TombaService(_DBM(e))

def test_crud(svc):
    tid = svc.create_tomba({"sito":"Volterra","rito":"inumazione","nr_scheda_taf":"3"})
    assert tid and svc.get_tomba(tid)["rito"]=="inumazione"
    assert svc.update_tomba(tid, {"rito":"cremazione"}) is True
    assert svc.get_tomba(tid)["rito"]=="cremazione"
    assert [r["id_tomba"] for r in svc.list_tomba()]==[tid]
    assert svc.count_tomba()==1
    assert svc.get_distinct_sites()==["Volterra"]
    assert svc.delete_tomba(tid) is True and svc.get_tomba(tid) is None

def test_get_thesaurus_values_unknown_field_empty(svc):
    assert svc.get_thesaurus_values("nope")==[]
```
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `services/tomba_service.py` by copying `services/tma_service.py`'s structure, replacing `TmaMaterialiArcheologici`→`Tomba`, `.id`→`.id_tomba`, the search ilike fields → `sito`/`nr_scheda_taf`/`rito`/`sigla_struttura`, order_by `Tomba.id_tomba.desc()`, and drop the detail-record (materiali) methods (tomba has none). For `get_thesaurus_values(field)`: use the field→thesaurus lookup against `thesaurus_field` (table_name=`'tomba_table'`, field_name=field) returning `[{'value':..,'code':..}]`, empty for unknown; `get_distinct_sites()` queries `Tomba.sito`. Use `valid_keys = {c.name for c in Tomba.__table__.columns}` filtering in create/update. Register in `services/__init__.py` (import + `__all__`).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `git add pyarchinit_mini/services/tomba_service.py pyarchinit_mini/services/__init__.py tests/tomba/test_tomba_service.py && git commit -m "feat(tomba): TombaService CRUD + thesaurus + sites"`

---

### Task 4: Thesaurus seed for tomba

**Files:** Modify `pyarchinit_mini/models/thesaurus.py`; Test `tests/tomba/test_tomba_thesaurus_seed.py`

- [ ] **Step 1: Failing test**
```python
# tests/tomba/test_tomba_thesaurus_seed.py
from pyarchinit_mini.models.thesaurus import THESAURUS_MAPPINGS
def test_tomba_seed_present():
    t = THESAURUS_MAPPINGS.get("tomba_table", {})
    for f in ["rito","tipo_sepoltura","tipo_deposizione","copertura_tipo",
              "tipo_contenitore_resti","stato_di_conservazione","corredo_presenza"]:
        assert f in t and isinstance(t[f], list) and t[f]
```
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** — add a `'tomba_table'` block to `THESAURUS_MAPPINGS` (mirror the `'inventario_materiali_table'` block) with sensible initial vocab, e.g. `rito: ['Inumazione','Cremazione','Incinerazione']`, `tipo_sepoltura: ['Fossa terragna','Cassa','Sarcofago','Enchytrismos','A cappuccina']`, `tipo_deposizione: ['Primaria','Secondaria','Supina','Prona','Rannicchiata']`, `copertura_tipo: ['Tegole','Lastre','Laterizi','Assente']`, `tipo_contenitore_resti: ['Anfora','Olla','Cassa lignea','Assente']`, `stato_di_conservazione: ['Ottimo','Buono','Discreto','Cattivo','Frammentario']`, `corredo_presenza: ['Sì','No','Parziale']`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `git add pyarchinit_mini/models/thesaurus.py tests/tomba/test_tomba_thesaurus_seed.py && git commit -m "feat(tomba): thesaurus vocab seed for tomba fields"`

---

### Task 5: Web routes + service wiring + templates

**Files:** Modify `pyarchinit_mini/web_interface/app.py`; Create `templates/tomba/list.html`, `templates/tomba/form.html`; Modify `templates/base.html`; Test `tests/tomba/test_tomba_routes.py`

**Context:** Copy the TMA route block (`app.py:4831-4987`) and the TMA templates, renaming to tomba. Instantiate the service near `app.py:679` (`tomba_service = TombaService(db_manager)`) — closure like TMA. Routes: `/tomba` (list), `/tomba/new`, `/tomba/<int:tomba_id>` (edit), `/tomba/<int:tomba_id>/delete`, `/tomba/<int:tomba_id>/media/upload` (calls `media_service.add_media(tmp, 'tomba', tomba_id)`), `/api/tomba/thesaurus/<field>`. Edit view builds `media_items = _media_gallery('tomba', tomba_id)`. Templates copied from `templates/tma/{list,form}.html` with tomba fields; the form's `<datalist>` thesaurus JS `THES_FIELDS = ['rito','tipo_sepoltura','tipo_deposizione','copertura_tipo','tipo_contenitore_resti','stato_di_conservazione','corredo_presenza']` and fetch URL `/api/tomba/thesaurus/`. Add a nav link in `base.html` near the other entity links.

- [ ] **Step 1: Failing test** — write `tests/tomba/test_tomba_routes.py` using the repo's existing web test harness (grep `tests/` for the app/client/login fixtures used by other route tests). Assert: authenticated GET `/tomba` → 200; POST `/tomba/new` with `{sito, rito}` → redirect and the record is retrievable via `tomba_service`; GET `/tomba/<id>` → 200 shows the rito; `/api/tomba/thesaurus/rito` → 200 JSON list; POST `/tomba/<id>/delete` → record gone. (If the harness makes some assertion impractical, cover what you can and document.)
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the routes + templates + nav + service instantiation per Context.
- [ ] **Step 4: Run** → PASS; verify app imports `.venv/bin/python -c "import pyarchinit_mini.web_interface.app"`; regression `.venv/bin/pytest tests/tomba/ tests/media/ -q` green.
- [ ] **Step 5: Commit** `git add pyarchinit_mini/web_interface/app.py pyarchinit_mini/web_interface/templates/tomba/ pyarchinit_mini/web_interface/templates/base.html tests/tomba/test_tomba_routes.py && git commit -m "feat(tomba): web routes, form/list templates, media upload + thesaurus API"`

---

### Task 6: Dashboard tile + AI + MCP integration

**Files:** Modify `app.py` (index stats), `templates/dashboard.html`, `services/ai_assistant_service.py`, `mcp_server/tools/data_import_parser_tool.py`, `mcp_server/tools/pyarchinit_sync_tool.py`; Test `tests/tomba/test_tomba_integration.py`

- [ ] **Step 1: Failing test**
```python
# tests/tomba/test_tomba_integration.py
def test_mcp_maps_tomba_table_to_service():
    from pyarchinit_mini.mcp_server.tools.data_import_parser_tool import DataImportParserTool
    tool = DataImportParserTool(db_manager=None)  # adapt to real ctor; may need a stub
    svc = tool._get_service_for_table("tomba_table")
    assert type(svc).__name__ == "TombaService"

def test_ai_prompt_mentions_tomba():
    from pyarchinit_mini.services.ai_assistant_service import AIAssistantService
    p = AIAssistantService._get_system_prompt.__doc__ or ""  # adapt: read the IT/EN prompt constants
    from pyarchinit_mini.services import ai_assistant_service as m
    assert "/tomba" in (m.SYSTEM_PROMPT_IT + m.SYSTEM_PROMPT_EN)

def test_sync_tool_enum_has_tomba():
    from pyarchinit_mini.mcp_server.tools.pyarchinit_sync_tool import PyArchInitSyncTool  # adapt
    import json
    # assert the tool's input schema data_types enum contains "tomba" — read the real schema accessor
```
(Adapt each assertion to the real constructors/accessors — read the files first. The BEHAVIORS to assert: `_get_service_for_table('tomba_table')` returns a `TombaService`; the AI system prompts contain a `/tomba` link; the sync tool's `data_types` enum contains `"tomba"`.)
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement:**
  - Dashboard: in `app.py:index`, add `total_tomba = tomba_service.count_tomba()` (guarded like pottery) and `'total_tomba': total_tomba` to `stats`; add a tile in `dashboard.html` (copy the pottery `stats-card` block → `stats.get('total_tomba',0)`, label "Tombe", a FontAwesome icon).
  - AI: add a tomba link line to `SYSTEM_PROMPT_IT` and `SYSTEM_PROMPT_EN` in `ai_assistant_service.py` (e.g. `Link alle tombe: <a href="/tomba/ID">Tomba ID</a>`).
  - MCP `data_import_parser_tool.py`: add a `"tomba_table"` block to `FIELD_MAPPINGS`; add a `tomba_table` branch to `_get_service_for_table` (`from ...services.tomba_service import TombaService; return TombaService(self.db_manager)`); add `tomba_table` to the input-schema `enum` (~:118) and the `_import_records`/validation `if target_table == ...` chains.
  - MCP `pyarchinit_sync_tool.py`: add `"tomba"` to the `data_types` enum (:40) and `if 'tomba' in data_types:` branches at the import/export sites (:112/:155).
- [ ] **Step 4: Run** → PASS; regression `.venv/bin/pytest tests/tomba/ -q` + app import.
- [ ] **Step 5: Commit** `git add -A && git commit -m "feat(tomba): dashboard tile + AI prompt + MCP tool integration"`

---

### Task 7: Documentation + tutorial

**Files:** Create `docs/tomba.rst`, `docs/tomba_service.rst`; Modify `docs/index.rst`, `docs/tutorials/web_interface_tutorial.rst`, `README.md`, `CHANGELOG.md`

- [ ] **Step 1:** Create `docs/tomba.rst` + `docs/tomba_service.rst` (autodoc stubs mirroring `docs/inventario.rst`/`docs/inventario_service.rst` — automodule `pyarchinit_mini.models.tomba` / `pyarchinit_mini.services.tomba_service`). Add both to the `docs/index.rst` toctree next to the inventario entries.
- [ ] **Step 2:** Add a "Schede Tomba" subsection to `docs/tutorials/web_interface_tutorial.rst` (how to list/create/edit a tomba, media upload, thesaurus dropdowns). Add a "Tomba records" bullet to the features list in `README.md` and a `CHANGELOG.md` entry under an unreleased/3.0.0 heading.
- [ ] **Step 3:** Verify the Sphinx toctree references resolve (no missing-file warning): `grep -n tomba docs/index.rst`. If sphinx is available, `.venv/bin/python -m sphinx -b html -q docs /tmp/docs_build 2>&1 | grep -i tomba` shows no error (optional if sphinx not installed — then just confirm the .rst files exist and are referenced).
- [ ] **Step 4: Commit** `git add docs/ README.md CHANGELOG.md && git commit -m "docs(tomba): record-type docs + web tutorial + changelog"`

---

### Task 8: Full suite + template sign-off

- [ ] **Step 1:** `.venv/bin/pytest tests/tomba/ -v` → green; `.venv/bin/pytest tests/ -q` → no NEW failures (pre-existing `test_delete_site` unrelated).
- [ ] **Step 2:** Manual smoke (or documented): create a tomba via `/tomba/new`, edit it, upload media, see the dashboard count. Confirm `/api/tomba/thesaurus/rito` returns the seeded values.
- [ ] **Step 3: Commit** any fixups. This completes the TEMPLATE. struttura/fauna/UT replicate Tasks 1-8 with their own columns/thesaurus (fauna: drop media, add US-parent lookup).

---

## Self-Review
**Spec coverage:** SP2 spec §3 interop → Tasks 1-2; §4 checklist points 1-10 → Tasks 1-7; §5 tomba concrete → all; §7 testing → each task; §10 docs → Task 7.
**Placeholder scan:** Tasks 5/6 tests say "adapt to the real harness/accessors" — pointers to real fixtures with the exact behaviors to assert enumerated; the copy-from-TMA steps name the exact source lines + the specific renames. Novel units (model, service, thesaurus, migration) are code-complete.
**Type consistency:** `TombaService.{list,count,get,create,update,delete}_tomba`, `get_thesaurus_values(field)`, `get_distinct_sites()`; media key `'tomba'`; `_get_service_for_table('tomba_table')->TombaService` — consistent across tasks.
