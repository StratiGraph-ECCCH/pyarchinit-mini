# Struttura Record Type (SP2 slice 2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add the `struttura` (structure) record type to pyarchinit-mini web — full CRUD, plugin-schema-compatible, integrated with thesaurus, media, dashboard, AI, MCP, docs — by REPLICATING the completed, hardened **tomba** template.

**Architecture:** The `tomba` record type is already merged on `main` and is the clean reference. Every task MIRRORS the corresponding tomba artifact (`models/tomba.py`, `services/tomba_service.py`, the `/tomba` routes in `app.py`, `templates/tomba/{list,form}.html`, the tomba dashboard/AI/MCP/docs hooks) and adapts it to struttura's schema. Reuse the shared helpers already added for tomba: `BaseModel.writable_columns()` (mass-assignment allowlist) and the numeric-coercion helper.

**Tech Stack:** Python 3.12, SQLAlchemy, Flask, pytest.

## Global Constraints

- Plugin `struttura_table`, PK `id_struttura` (Integer). Map these columns EXACTLY (types from plugin `Struttura_table.py`); `entity_uuid` + sync columns come from `BaseModel` — do NOT redeclare `entity_uuid`:
  `sito`(Text), `sigla_struttura`(Text), `numero_struttura`(Integer), `categoria_struttura`(Text), `tipologia_struttura`(Text), `definizione_struttura`(Text), `descrizione`(Text), `interpretazione`(Text), `periodo_iniziale`(Integer), `fase_iniziale`(Integer), `periodo_finale`(Integer), `fase_finale`(Integer), `datazione_estesa`(String(300)), `materiali_impiegati`(Text), `elementi_strutturali`(Text), `rapporti_struttura`(Text), `misure_struttura`(Text), `data_compilazione`(Text), `nome_compilatore`(Text), `stato_conservazione`(Text), `quota`(Float), `relazione_topografica`(Text), `prospetto_ingresso`(Text), `orientamento_ingresso`(Text), `articolazione`(Text), `n_ambienti`(Integer), `orientamento_ambienti`(Text), `sviluppo_planimetrico`(Text), `elementi_costitutivi`(Text), `motivo_decorativo`(Text), `potenzialita_archeologica`(Text), `manufatti`(Text), `elementi_datanti`(Text), `fasi_funzionali`(Text).
- **Numeric columns** (coerce via the shared helper): Integer — `numero_struttura, periodo_iniziale, fase_iniziale, periodo_finale, fase_finale, n_ambienti`; Float — `quota`. The tomba coercion helper handled Integer only; EXTEND it (or the shared version) to also coerce Float columns. Non-parseable → `None` (no crash on Postgres).
- **JSON-in-Text fields** (the plugin stores JSON arrays here): `stato_conservazione, prospetto_ingresso, orientamento_ambienti, elementi_costitutivi, manufatti, fasi_funzionali`. For THIS MVP render them as `<textarea>` (store the string as-is); a repeatable-list widget is a future enhancement. These are NOT numeric and NOT datalist.
- **Thesaurus datalist fields:** `categoria_struttura, tipologia_struttura, orientamento_ingresso, articolazione` (NOT `stato_conservazione` — it's a JSON multi-value here, so keep it a textarea, don't wire a single datalist to it).
- **Media key** is `struttura` (already in `pyarchinit_mini/media_manager/entity_map.py` → `STRUTTURA`/`struttura_table`/`id_struttura`).
- **Search (Postgres-safe):** ilike ONLY on Text columns — `sito, sigla_struttura, categoria_struttura, tipologia_struttura, definizione_struttura`. NEVER ilike on Integer/Float columns.
- **Every write route** (`/struttura/new`, `/struttura/<id>` edit, `/struttura/<id>/delete`, `/struttura/<id>/media/upload`) carries `@login_required` + `@write_permission_required` (whole-view, matching tomba/us/inventario).
- Run tests with `.venv/bin/pytest`. TDD, DRY, YAGNI, frequent commits. No `Co-Authored-By`/AI-attribution trailer. Do NOT modify tomba/US/inventario/pottery/TMA. Harris stays US-only.

## File Structure
Mirror tomba: create `models/struttura.py`, `services/struttura_service.py`, `templates/struttura/{list,form}.html`, `tests/struttura/*`; modify `models/__init__.py`, `database/database_creator.py`, `database/migrations/__init__.py`, `services/__init__.py`, `web_interface/app.py`, `templates/base.html`, `templates/dashboard.html`, `models/thesaurus.py`, `services/ai_assistant_service.py`, `mcp_server/tools/{data_import_parser_tool,pyarchinit_sync_tool}.py`, docs, i18n catalogs.

---

### Task 1: Struttura model
**Files:** Create `pyarchinit_mini/models/struttura.py`; Modify `models/__init__.py`, `database/database_creator.py`; Test `tests/struttura/test_struttura_model.py` (+ `tests/struttura/__init__.py`).
- [ ] Mirror `pyarchinit_mini/models/tomba.py`: `class Struttura(BaseModel)`, `__tablename__='struttura_table'`, `id_struttura = Column(Integer, primary_key=True, autoincrement=True)`, then the 34 mapped columns from Global Constraints with exact types, and `to_dict()`. Register in `models/__init__.py` (import + `__all__`) and `database/database_creator.py::_import_all_models`.
- [ ] Test (mirror tomba's): assert `struttura_table` columns include the full expected set + BaseModel sync cols (`version_number`,`sync_status`,`created_at`); assert `to_dict()`.
- [ ] Run `.venv/bin/pytest tests/struttura/test_struttura_model.py -v` → pass; `.venv/bin/python -c "import pyarchinit_mini.models; import pyarchinit_mini.database.database_creator"` clean.
- [ ] Commit `feat(struttura): model mapping classic struttura_table`.

### Task 2: Concurrency migration covers struttura_table
**Files:** Modify `database/migrations/__init__.py`; Test `tests/struttura/test_struttura_migration.py`.
- [ ] Add `'struttura_table'` to the `tables` list in `migrate_concurrency_columns()` (same one-line change as tomba — read how tomba was added).
- [ ] Test (mirror tomba's migration test): create a bare plugin-shaped `struttura_table` (id_struttura, sito, categoria_struttura, entity_uuid) WITHOUT sync columns → run `migrate_concurrency_columns()` → assert `{version_number, sync_status, editing_by} <= columns`.
- [ ] Run → pass; `.venv/bin/pytest tests/struttura/ -q` green.
- [ ] Commit `feat(struttura): concurrency migration adds sync columns to struttura_table`.

### Task 3: StrutturaService (CRUD + thesaurus + sites + numeric coercion)
**Files:** Create `pyarchinit_mini/services/struttura_service.py`; Modify `services/__init__.py`; Test `tests/struttura/test_struttura_service.py`.
- [ ] Mirror `pyarchinit_mini/services/tomba_service.py`: methods `list_struttura(page,size,search,sito)`, `count_struttura(search,sito)`, `get_struttura(id)`, `create_struttura(data)`, `update_struttura(id,data)`, `delete_struttura(id)`, `get_thesaurus_values(field)` (thesaurus_field lookup, table_name=`'struttura_table'`, [] for unknown), `get_distinct_sites()`. Use `Struttura.writable_columns()` for the allowlist. Search ilike ONLY on the Text columns listed in Global Constraints. Order by `Struttura.id_struttura.desc()`.
- [ ] **Numeric coercion:** reuse tomba's coercion helper but ensure it coerces BOTH Integer AND Float columns (extend the helper so `quota` (Float) → `float()`; Integer cols → `int()`; non-parseable → None). If tomba's helper was local, promote a shared version or replicate the extended one.
- [ ] Register in `services/__init__.py`.
- [ ] Test (mirror tomba's, incl. the hardening tests): CRUD; `get_distinct_sites`; `get_thesaurus_values("nope")==[]`; search matches text fields; **allowlist bypass**: `create_struttura({"sito":"S","id_struttura":999,"version_number":42})` → id auto-assigned (not 999), version_number not 42; **coercion**: `create_struttura({"sito":"S","numero_struttura":"7","quota":"1.5"})` → `numero_struttura==7` (int), `quota==1.5` (float); `create_struttura({"sito":"S","quota":"abc"})` → `quota is None`.
- [ ] Run → pass; `.venv/bin/pytest tests/struttura/ -q` green.
- [ ] Commit `feat(struttura): StrutturaService CRUD + thesaurus + numeric coercion`.

### Task 4: Thesaurus seed for struttura
**Files:** Modify `models/thesaurus.py`; Test `tests/struttura/test_struttura_thesaurus_seed.py`.
- [ ] Add a `'struttura_table'` block to `THESAURUS_MAPPINGS` (mirror tomba's block) for fields `categoria_struttura, tipologia_struttura, orientamento_ingresso, articolazione` with sensible Italian vocab, e.g. `categoria_struttura: ['Muro','Fondazione','Pavimentazione','Focolare','Pozzo','Canaletta','Buca','Struttura muraria']`, `tipologia_struttura: ['In pietra','In laterizio','Mista','In terra','Lignea']`, `orientamento_ingresso: ['N','NE','E','SE','S','SO','O','NO']`, `articolazione: ['Semplice','Complessa','A vani multipli']`.
- [ ] Test (mirror tomba): assert the `'struttura_table'` block present with those 4 fields, each a non-empty list.
- [ ] Run → pass. Commit `feat(struttura): thesaurus vocab seed`.

### Task 5: Web routes + templates + service wiring
**Files:** Modify `web_interface/app.py`, `templates/base.html`; Create `templates/struttura/{list,form}.html`; Test `tests/struttura/test_struttura_routes.py`.
- [ ] Mirror the `/tomba` routes block in `app.py` for struttura: instantiate `struttura_service = StrutturaService(db_manager)` near the tomba service; routes `GET /struttura` (list), `GET/POST /struttura/new`, `GET/POST /struttura/<int:struttura_id>` (edit; `_media_gallery('struttura', struttura_id)`), `POST /struttura/<int:struttura_id>/delete`, `POST /struttura/<int:struttura_id>/media/upload` (`media_service.add_media(tmp, 'struttura', struttura_id)`), `GET /api/struttura/thesaurus/<field>`. SAME decorators as tomba (`@write_permission_required` on all 4 writes, INCLUDING edit).
- [ ] Templates: copy `templates/tomba/{list,form}.html`, adapt to `id_struttura` PK + struttura fields. The 6 JSON fields render as `<textarea>`; the 4 thesaurus fields use `list="thes-<field>"` + `<datalist>` and the JS `THES_FIELDS = ['categoria_struttura','tipologia_struttura','orientamento_ingresso','articolazione']` fetching `/api/struttura/thesaurus/`. Integer/Float fields use `type="number"` (`step="any"` for `quota`). Keep the media tab. List table shows id_struttura/sito/sigla_struttura/categoria_struttura/tipologia_struttura. Nav link "Strutture" in `base.html` → `url_for('struttura_list')`.
- [ ] Test (mirror tomba's routes test, incl. the viewer write-denial test): authed GET `/struttura`→200; POST `/struttura/new` {sito, categoria_struttura}→302 + retrievable; GET `/struttura/<id>`→200; `/api/struttura/thesaurus/categoria_struttura`→200 JSON; delete→gone; a no-write (viewer) session POST to `/struttura/<id>` is blocked.
- [ ] Run → pass; app import clean; `.venv/bin/pytest tests/struttura/ tests/media/ -q` green.
- [ ] Commit `feat(struttura): web routes, templates, media upload + thesaurus API`.

### Task 6: Dashboard tile + AI + MCP
**Files:** Modify `app.py` (index stats), `templates/dashboard.html`, `services/ai_assistant_service.py`, `mcp_server/tools/{data_import_parser_tool,pyarchinit_sync_tool}.py`; Test `tests/struttura/test_struttura_integration.py`.
- [ ] Mirror tomba's Task 6: guarded `total_struttura = struttura_service.count_struttura()` in `index()` stats + a `dashboard.html` tile (`stats.get('total_struttura',0)`, label "Strutture", a FontAwesome icon); `/struttura/ID` link line in both AI system prompts; `data_import_parser_tool` (`FIELD_MAPPINGS['struttura_table']`, `_get_service_for_table` branch → `StrutturaService`, enum + target_table branches); `pyarchinit_sync_tool` (`"struttura"` enum + hasattr-guarded branches).
- [ ] Test (mirror tomba integration): `_get_service_for_table('struttura_table')` → StrutturaService; `/struttura` in both AI prompts; sync enum contains `"struttura"`.
- [ ] Run → pass; imports clean. Commit `feat(struttura): dashboard tile + AI prompt + MCP integration`.

### Task 7: Docs + tutorial + i18n
**Files:** Create `docs/struttura.rst`, `docs/struttura_service.rst`; Modify `docs/index.rst`, `docs/tutorials/web_interface_tutorial.rst`, `README.md`, `CHANGELOG.md`, i18n catalogs.
- [ ] Mirror tomba's Task 7: `.rst` autodoc stubs (fully-qualified module names, as tomba did) + toctree entries; a "Schede Struttura" tutorial section; README bullet; CHANGELOG entry under Unreleased.
- [ ] **i18n:** extract+translate ALL new struttura template strings (labels, tab names, "New/Edit Struttura", field labels) into both it/en catalogs (`pybabel update` merge, hand-insert only struttura msgids to avoid churn, `pybabel compile`). Not just the nav label — the whole template.
- [ ] Verify toctree refs; `.venv/bin/pytest tests/struttura/ -q` green. Commit `docs(struttura): record-type docs + tutorial + changelog + i18n`.

### Task 8: Full suite + sign-off
- [ ] `.venv/bin/pytest tests/struttura/ -v` green; `.venv/bin/pytest tests/ -q` → no NEW failures (pre-existing `test_delete_site` only).
- [ ] Commit any fixups. Struttura complete.

## Self-Review
Covers Global Constraints (schema, numeric coercion incl. Float, JSON-as-textarea, thesaurus datalist minus stato_conservazione, media key, Postgres-safe search, write-guards). Each task mirrors the merged tomba artifact + names the struttura-specific deltas. Reuses `writable_columns()` + coercion helper. No placeholders — the tomba files are the concrete template to copy.
