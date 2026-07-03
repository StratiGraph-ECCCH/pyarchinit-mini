# UT (Unità Topografica) Record Type (SP2 slice 4) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add the `ut` (unità topografica / topographic unit) record type to pyarchinit-mini web — full CRUD, plugin-schema-compatible, thesaurus + **media** + dashboard + AI + MCP + docs — by REPLICATING the merged tomba/struttura template with UT's differences (60 columns, **project-scoped**, survey/analysis fields incl. `Numeric`, HAS media).

**Architecture:** Mirror the merged `struttura` artifacts (struttura HAS media, so it's the closest template). UT differences: PK `id_ut` **Integer** (native autoincrement — NOT the fauna max+1 allocator); it is **project-scoped** (`progetto`, not `sito`); it has **`Numeric(5,2)`** columns (`potential_score`/`risk_score`) → **extend the shared `coerce_types` helper to handle Numeric**; it HAS media (`ut` is in `entity_map`). The form is large — organize into fieldset sections.

**Tech Stack:** Python 3.12, SQLAlchemy, Flask, pytest.

## Global Constraints

- Plugin `ut_table`, PK `id_ut` (Integer, native autoincrement). Map these columns EXACTLY (types from plugin `UT_table.py`); `entity_uuid`+sync cols from `BaseModel` — do NOT redeclare `entity_uuid`:
  `progetto`(String(100)), `nr_ut`(Integer), `ut_letterale`(String(100)), `def_ut`(String(100)), `descrizione_ut`(Text), `interpretazione_ut`(String(100)), `nazione`(String(100)), `regione`(String(100)), `provincia`(String(100)), `comune`(String(100)), `frazione`(String(100)), `localita`(String(100)), `indirizzo`(String(100)), `nr_civico`(String(100)), `carta_topo_igm`(String(100)), `carta_ctr`(String(100)), `coord_geografiche`(String(100)), `coord_piane`(String(100)), `quota`(Float), `andamento_terreno_pendenza`(String(100)), `utilizzo_suolo_vegetazione`(String(100)), `descrizione_empirica_suolo`(Text), `descrizione_luogo`(Text), `metodo_rilievo_e_ricognizione`(String(100)), `geometria`(String(100)), `bibliografia`(Text), `data`(String(100)), `ora_meteo`(String(100)), `responsabile`(String(100)), `dimensioni_ut`(String(100)), `rep_per_mq`(String(100)), `rep_datanti`(String(100)), `periodo_I`(String(100)), `datazione_I`(String(100)), `interpretazione_I`(String(100)), `periodo_II`(String(100)), `datazione_II`(String(100)), `interpretazione_II`(String(100)), `documentazione`(Text), `enti_tutela_vincoli`(String(100)), `indagini_preliminari`(String(100)), `visibility_percent`(Integer), `vegetation_coverage`(String(255)), `gps_method`(String(100)), `coordinate_precision`(Float), `survey_type`(String(100)), `surface_condition`(String(255)), `accessibility`(String(255)), `photo_documentation`(Integer), `weather_conditions`(String(255)), `team_members`(Text), `foglio_catastale`(String(100)), `potential_score`(Numeric(5,2)), `risk_score`(Numeric(5,2)), `potential_factors`(Text), `risk_factors`(Text), `analysis_date`(String(100)), `analysis_method`(String(100)).
  (If the plugin `UT_table.py` differs from any type above, the plugin is authoritative — read it and match; note deviations in the report.)
- **PK id_ut is plain Integer → native autoincrement.** Do NOT use the fauna max+1 allocator.
- **Project-scoped:** UT has NO `sito`. The list/filter/distinct use **`progetto`**. Service: `list_ut(page,size,search,progetto)`, `count_ut(search,progetto)`, `get_distinct_projects()` (query `Ut.progetto`).
- **Coercion — extend the shared helper for Numeric:** `potential_score`/`risk_score` are `Numeric(5,2)`. `Float` IS-A `Numeric` but `Numeric` is NOT-A `Float`, so the current helper's `isinstance(col.type, Float)` MISSES Numeric columns. Extend `pyarchinit_mini/services/coercion.py` so numeric coercion uses `isinstance(col.type, Numeric)` (which catches BOTH Float and Numeric) → coerce to `float(v)` (non-parseable → None). Verify `Integer` is still handled by its own branch (Integer is NOT a Numeric subclass) and struttura's `quota` (Float) still coerces (regression). Numeric cols to coerce: `potential_score, risk_score` (+ `quota, coordinate_precision` are Float). Integer cols: `nr_ut, visibility_percent, photo_documentation`.
- **JSON-in-Text fields** (textarea): `potential_factors, risk_factors`.
- **Thesaurus datalist fields:** `def_ut, survey_type, gps_method, surface_condition, accessibility`.
- **Search (Postgres-safe):** ilike ONLY on Text/String cols — `progetto, ut_letterale, def_ut, localita, comune, descrizione_ut`. NEVER on Integer/Float/Numeric.
- **HAS media:** `ut` is already in `entity_map.py` (`UT`/`ut_table`/`id_ut`). Wire the media tab + `/ut/<id>/media/upload` route + `_media_gallery('ut', ut_id)` (like tomba/struttura). Do NOT leave the entity_map entry half-wired.
- **Write routes** (`/ut/new`, `/ut/<id>` edit, `/ut/<id>/delete`, `/ut/<id>/media/upload`) carry `@login_required` + `@write_permission_required` (whole-view).
- Reuse `Ut.writable_columns()` (mass-assignment allowlist) + `coerce_types(Ut, data)`.
- Run tests with `.venv/bin/pytest`. TDD, DRY, YAGNI, frequent commits. No `Co-Authored-By`/AI-attribution trailer. Do NOT change tomba/struttura/fauna/US/inventario/pottery/TMA. Harris stays US-only.

## File Structure
Mirror struttura (which has media): create `models/ut.py`, `services/ut_service.py`, `templates/ut/{list,form}.html`, `tests/ut/*`; modify `models/__init__.py`, `database/database_creator.py`, `database/migrations/__init__.py`, `services/coercion.py` (Numeric extension), `services/__init__.py`, `web_interface/app.py`, `templates/base.html`, `templates/dashboard.html`, `models/thesaurus.py`, `services/ai_assistant_service.py`, `mcp_server/tools/{data_import_parser_tool,pyarchinit_sync_tool}.py`, docs, i18n.

---

### Task 1: Ut model
**Files:** Create `pyarchinit_mini/models/ut.py`; Modify `models/__init__.py`, `database/database_creator.py`; Test `tests/ut/test_ut_model.py` (+ `__init__.py`).
- [ ] Mirror `models/struttura.py`: `class Ut(BaseModel)`, `__tablename__='ut_table'`, `id_ut = Column(Integer, primary_key=True, autoincrement=True)`, then the 57 mapped columns from Global Constraints with EXACT types. Import `Column, Integer, String, Text, Float, Numeric` from sqlalchemy. `to_dict()`. Register in `models/__init__.py` (import + `__all__`) and `database_creator.py::_import_all_models`.
- [ ] Test (mirror struttura): assert `ut_table` columns include the full expected set + BaseModel sync cols; assert `potential_score`/`risk_score` are `Numeric` (`Ut.__table__.c.potential_score.type.__class__.__name__ == 'Numeric'`); assert `to_dict()` round-trips.
- [ ] Run → pass; imports clean. Commit `feat(ut): model mapping classic ut_table (60 cols incl. Numeric survey/analysis)`.

### Task 2: Concurrency migration covers ut_table
**Files:** Modify `database/migrations/__init__.py`; Test `tests/ut/test_ut_migration.py`.
- [ ] Add `'ut_table'` to the `tables` list in `migrate_concurrency_columns()`.
- [ ] Test (mirror struttura): bare plugin-shaped `ut_table` (id_ut INTEGER PRIMARY KEY, progetto TEXT, def_ut TEXT, entity_uuid TEXT) → migration → assert `{version_number, sync_status, editing_by} <= columns`.
- [ ] Run → pass; `.venv/bin/pytest tests/ut/ -q` green. Commit `feat(ut): concurrency migration adds sync columns to ut_table`.

### Task 3: Extend coercion (Numeric) + UtService
**Files:** Modify `pyarchinit_mini/services/coercion.py`; Create `pyarchinit_mini/services/ut_service.py`; Modify `services/__init__.py`; Test `tests/services/test_coercion.py` (extend), `tests/ut/test_ut_service.py`.
- [ ] **Extend `coercion.py`:** change the float-coercion type test from `isinstance(col.type, Float)` to `isinstance(col.type, Numeric)` (catches Float AND Numeric) → `float(v)`, non-parseable → None. Ensure `Integer`/`Boolean`/`Date` branches are checked appropriately (Integer is NOT a Numeric subclass; Boolean/Date checked before). Add a test to `tests/services/test_coercion.py`: a model with a `Numeric` column coerces "1.50"→1.5 (float) and "bad"→None; confirm the existing Float (`Struttura.quota`) test still passes.
- [ ] **UtService** `services/ut_service.py` mirroring `struttura_service.py` (Struttura→Ut, `id_struttura`→`id_ut`) BUT project-scoped: `list_ut(page=1,size=50,search='',progetto='')`, `count_ut(search='',progetto='')`, `get_ut(id)`, `create_ut(data)`, `update_ut(id,data)`, `delete_ut(id)`, `get_thesaurus_values(field)` (table_name='ut_table'), **`get_distinct_projects()`** (query `Ut.progetto`). Filter by `progetto` (not sito). Use `Ut.writable_columns()` + `coerce_types(Ut, data)`. Search ilike ONLY on `progetto, ut_letterale, def_ut, localita, comune, descrizione_ut`. Order by `Ut.id_ut.desc()`. Register in `services/__init__.py`. (Integer PK → plain constructor, NO max+1 allocator.)
- [ ] **Test** `tests/ut/test_ut_service.py` (mirror struttura's + UT specifics): CRUD (progetto, def_ut); `get_distinct_projects()` returns the project; unknown thesaurus→[]; search matches text fields; allowlist bypass (`id_ut`:999/`version_number`:42 ignored); coercion (`nr_ut`:"5"→5; `quota`:"1.5"→1.5; `potential_score`:"3.25"→3.25 float; `potential_score`:"bad"→None).
- [ ] Run `.venv/bin/pytest tests/ut/ tests/services/test_coercion.py tests/struttura/ tests/fauna/ tests/tomba/ -q` → ALL green (Numeric extension must not regress struttura/fauna/tomba).
- [ ] Commit `feat(ut): UtService (project-scoped) + Numeric coercion extension`.

### Task 4: Thesaurus seed for ut
**Files:** Modify `models/thesaurus.py`; Test `tests/ut/test_ut_thesaurus_seed.py`.
- [ ] Add `'ut_table'` block to `THESAURUS_MAPPINGS` for `def_ut, survey_type, gps_method, surface_condition, accessibility` with sensible vocab, e.g. `def_ut: ['Area','Struttura','Affioramento','Dispersione di materiale','Traccia']`, `survey_type: ['Sistematica','Non sistematica','Intensiva','Estensiva','Campionaria']`, `gps_method: ['RTK','DGPS','Navigazione','Punto singolo']`, `surface_condition: ['Arato','Incolto','Boscato','Urbanizzato','Prato']`, `accessibility: ['Alta','Media','Bassa','Non accessibile']`.
- [ ] Test (mirror struttura): block + 5 fields non-empty. Run → pass. Commit `feat(ut): thesaurus vocab seed`.

### Task 5: Web routes + templates (WITH media) + wiring
**Files:** Modify `web_interface/app.py`, `templates/base.html`; Create `templates/ut/{list,form}.html`; Test `tests/ut/test_ut_routes.py`.
- [ ] Mirror the `/struttura` routes (WITH media) for ut: instantiate `ut_service`; routes `GET /ut` (list; `list_ut/count_ut/get_distinct_projects`, pass `projects` to template), `GET/POST /ut/new`, `GET/POST /ut/<int:ut_id>` (edit; `_media_gallery('ut', ut_id)`), `POST /ut/<int:ut_id>/delete`, `POST /ut/<int:ut_id>/media/upload` (`media_service.add_media(tmp, 'ut', ut_id)`), `GET /api/ut/thesaurus/<field>`. `@write_permission_required` on the 4 writes incl. edit.
- [ ] Templates `templates/ut/{list,form}.html` copied from struttura, adapted to `id_ut` PK + ut fields, **organized into fieldset/tab sections** (Anagrafica: progetto/nr_ut/ut_letterale/def_ut/descrizione_ut/interpretazione_ut; Ubicazione: nazione…coord_piane/quota/geometria; Survey: visibility_percent/vegetation_coverage/gps_method/coordinate_precision/survey_type/surface_condition/accessibility/photo_documentation/weather_conditions/team_members/foglio_catastale; Analisi: potential_score/risk_score/potential_factors/risk_factors/analysis_date/analysis_method; Media tab). Numeric/Float/Integer fields `type="number"` (`step="any"` for Float/Numeric: quota, coordinate_precision, potential_score, risk_score; integer step for nr_ut/visibility_percent/photo_documentation); `potential_factors`/`risk_factors` `<textarea>`; thesaurus datalist JS `THES_FIELDS = ['def_ut','survey_type','gps_method','surface_condition','accessibility']` fetching `/api/ut/thesaurus/`. Keep the media tab (upload → `url_for('ut_media_upload', ut_id=ut.id_ut)`). List table: id_ut, progetto, nr_ut, ut_letterale, def_ut, localita. **The list filter dropdown is by `progetto`** (not sito) — populate from `projects`. Nav link "UT" in base.html.
- [ ] Test `tests/ut/test_ut_routes.py` (mirror struttura's, incl. media + viewer write-denial): authed GET `/ut`→200; POST `/ut/new` {progetto, def_ut}→302 + retrievable; GET `/ut/<id>`→200 shows def_ut; `/api/ut/thesaurus/def_ut`→200 JSON; delete→gone; viewer POST to `/ut/<id>` blocked. (Media upload route exists — a smoke check that it's registered is enough.)
- [ ] Run → pass; app import clean; `.venv/bin/pytest tests/ut/ tests/media/ -q` green. Commit `feat(ut): web routes, fieldset templates, media upload + thesaurus API`.

### Task 6: Dashboard tile + AI + MCP
**Files:** Modify `app.py`, `templates/dashboard.html`, `services/ai_assistant_service.py`, `mcp_server/tools/{data_import_parser_tool,pyarchinit_sync_tool}.py`; Test `tests/ut/test_ut_integration.py`.
- [ ] Mirror struttura's Task 6 for ut: guarded `total_ut = ut_service.count_ut()` + `dashboard.html` tile (`stats.get('total_ut',0)`, label `{{ _('UT') }}`, icon e.g. `fa-map-marked-alt` / `fa-map-pin`); `/ut/ID` link in both AI prompts; `data_import_parser_tool` (`FIELD_MAPPINGS['ut_table']` with progetto/nr_ut/def_ut/localita/comune, `_get_service_for_table` → UtService, enum + branches); `pyarchinit_sync_tool` (`"ut"` enum + hasattr-guarded branches). i18n: add `"UT"` to both catalogs if new; recompile .mo.
- [ ] Test (mirror struttura integration): `_get_service_for_table('ut_table')` → UtService; `/ut` in both AI prompts; sync enum has `"ut"`.
- [ ] Run → pass; imports clean. Commit `feat(ut): dashboard tile + AI prompt + MCP integration`.

### Task 7: Docs + tutorial + i18n
**Files:** Create `docs/ut.rst`, `docs/ut_service.rst`; Modify `docs/index.rst`, `docs/tutorials/web_interface_tutorial.rst`, `README.md`, `CHANGELOG.md`, i18n catalogs.
- [ ] Mirror struttura's Task 7: `.rst` autodoc stubs (fully-qualified) + toctree; "Schede UT" tutorial section (project-scoped, survey/analysis fieldsets, media, 5 thesaurus dropdowns); README bullet; CHANGELOG entry under Unreleased.
- [ ] **i18n:** extract+translate ALL new ut template strings into both it/en catalogs (`pybabel update` merge, hand-insert only ut msgids, `pybabel compile`). Not just nav.
- [ ] Verify toctree refs; `.venv/bin/pytest tests/ut/ -q` green. Commit `docs(ut): record-type docs + tutorial + changelog + i18n`.

### Task 8: Full suite + sign-off
- [ ] `.venv/bin/pytest tests/ut/ -v` green; `.venv/bin/pytest tests/ -q` → no NEW failures (pre-existing `test_delete_site` only). Confirm struttura/fauna/tomba still green after the Numeric coercion extension.
- [ ] Commit any fixups. UT complete — SP2 (all 4 new record types) done.

## Self-Review
Covers UT deltas: 60 cols incl. Numeric (coercion extended, not duplicated), Integer PK native autoincrement (NOT max+1), project-scoped list/filter/distinct, HAS media (tab+route+gallery), fieldset form organization, JSON textareas, Postgres-safe search, write-guards. Reuses writable_columns + coerce_types. No placeholders — struttura is the concrete template (WITH media).
