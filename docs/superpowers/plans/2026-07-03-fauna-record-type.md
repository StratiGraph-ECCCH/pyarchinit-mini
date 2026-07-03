# Fauna Record Type (SP2 slice 3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add the `fauna` (archaeozoology) record type to pyarchinit-mini web — full CRUD, plugin-schema-compatible, thesaurus + dashboard + AI + MCP + docs — by REPLICATING the merged tomba/struttura template, with fauna's structural differences.

**Architecture:** Mirror the merged `struttura`/`tomba` artifacts. Fauna is the MOST different slice: PK `id_fauna` is **BigInteger**; it is **US-parented** (`id_us` BigInteger + `sito/area/us` text), has **NO media** (not in `entity_map` — no media tab/route), and adds **Date** (`data_compilazione`) and **Boolean** (`combustione_altri_materiali_us`) columns. This slice also **extracts the numeric coercion into a shared helper** (int/float/**bool/date**) and retrofits tomba/struttura to use it (addresses the struttura final-review duplication finding).

**Tech Stack:** Python 3.12, SQLAlchemy, Flask, pytest.

## Global Constraints

- Plugin `fauna_table`, PK `id_fauna` (**BigInteger**). Map these columns EXACTLY (types from plugin `Fauna_table.py`); `entity_uuid` + sync cols come from `BaseModel` — do NOT redeclare `entity_uuid`:
  `id_us`(BigInteger), `sito`(Text), `area`(Text), `saggio`(Text), `us`(Text), `datazione_us`(Text), `responsabile_scheda`(Text), `data_compilazione`(Date), `documentazione_fotografica`(Text), `metodologia_recupero`(Text), `contesto`(Text), `descrizione_contesto`(Text), `resti_connessione_anatomica`(Text), `tipologia_accumulo`(Text), `deposizione`(Text), `numero_stimato_resti`(Text), `numero_minimo_individui`(Integer), `specie`(Text), `parti_scheletriche`(Text), `specie_psi`(Text), `misure_ossa`(Text), `stato_frammentazione`(Text), `tracce_combustione`(Text), `combustione_altri_materiali_us`(Boolean), `tipo_combustione`(Text), `segni_tafonomici_evidenti`(Text), `caratterizzazione_segni_tafonomici`(Text), `stato_conservazione`(Text), `alterazioni_morfologiche`(Text), `note_terreno_giacitura`(Text), `campionature_effettuate`(Text), `affidabilita_stratigrafica`(Text), `classi_reperti_associazione`(Text), `osservazioni`(Text), `interpretazione`(Text).
- **NO MEDIA:** fauna is NOT in `entity_map.py` (leave it out). NO media upload route, NO media tab in the form, no `_media_gallery` call.
- **Coercion (shared helper):** Integer `numero_minimo_individui` → int; **Boolean** `combustione_altri_materiali_us` → bool (truthy: `true/1/si/sì/on/yes` → True; `false/0/no/off` → False; empty/other → None); **Date** `data_compilazione` → a `datetime.date` parsed from `YYYY-MM-DD` (empty/unparseable → None). `numero_stimato_resti` stays Text. Non-parseable numeric/date → None (never crash on Postgres).
- **JSON-in-Text fields** (textarea, store as-is): `specie_psi, misure_ossa`.
- **Thesaurus datalist fields:** `specie, parti_scheletriche, contesto, stato_conservazione, metodologia_recupero, deposizione`.
- **Search (Postgres-safe):** ilike ONLY on Text cols — `sito, area, us, saggio, specie, contesto`. NEVER on Integer/Boolean/Date.
- **US linkage (MVP):** expose `sito, area, us` as text inputs + `id_us` as a `type="number"` input (matches the plugin's flat fields). A US-lookup dropdown is a documented future enhancement, NOT this slice.
- **Write routes** (`/fauna/new`, `/fauna/<id>` edit, `/fauna/<id>/delete`) carry `@login_required` + `@write_permission_required` (whole-view). There is NO media-upload route.
- Run tests with `.venv/bin/pytest`. TDD, DRY, YAGNI, frequent commits. No `Co-Authored-By`/AI-attribution trailer. Do NOT change US/inventario/pottery/TMA behavior. Harris stays US-only.

## File Structure
Mirror struttura minus media: create `models/fauna.py`, `services/fauna_service.py`, `services/coercion.py` (NEW shared helper), `templates/fauna/{list,form}.html`, `tests/fauna/*`; modify `models/__init__.py`, `database/database_creator.py`, `database/migrations/__init__.py`, `services/__init__.py`, `services/tomba_service.py` + `services/struttura_service.py` (retrofit to shared helper), `web_interface/app.py`, `templates/base.html`, `templates/dashboard.html`, `models/thesaurus.py`, `services/ai_assistant_service.py`, `mcp_server/tools/{data_import_parser_tool,pyarchinit_sync_tool}.py`, docs, i18n.

---

### Task 1: Fauna model
**Files:** Create `pyarchinit_mini/models/fauna.py`; Modify `models/__init__.py`, `database/database_creator.py`; Test `tests/fauna/test_fauna_model.py` (+ `__init__.py`).
- [ ] Mirror `models/struttura.py`: `class Fauna(BaseModel)`, `__tablename__='fauna_table'`, `id_fauna = Column(BigInteger, primary_key=True, autoincrement=True)`, then the 35 mapped columns from Global Constraints with EXACT types. Import `BigInteger, Date, Boolean, Integer, Float, String, Text, Column` from sqlalchemy. `to_dict()` as in struttura. Register in `models/__init__.py` (import + `__all__`) and `database/database_creator.py::_import_all_models`.
- [ ] Test (mirror struttura's): assert `fauna_table` columns include the full expected set + BaseModel sync cols; assert `id_fauna` is a BigInteger-family type (`inspect(...).get_columns` type is BIGINT on sqlite it shows INTEGER — instead assert `Fauna.__table__.c.id_fauna.type.__class__.__name__ == 'BigInteger'`); assert `to_dict()` round-trips.
- [ ] Run `.venv/bin/pytest tests/fauna/test_fauna_model.py -v` → pass; imports clean.
- [ ] Commit `feat(fauna): model mapping classic fauna_table (BigInteger PK, Date/Boolean cols)`.

### Task 2: Concurrency migration covers fauna_table
**Files:** Modify `database/migrations/__init__.py`; Test `tests/fauna/test_fauna_migration.py`.
- [ ] Add `'fauna_table'` to the `tables` list in `migrate_concurrency_columns()`.
- [ ] Test (mirror struttura's): bare plugin-shaped `fauna_table` (id_fauna INTEGER PRIMARY KEY, sito TEXT, specie TEXT, entity_uuid TEXT) → run migration → assert `{version_number, sync_status, editing_by} <= columns`.
- [ ] Run → pass; `.venv/bin/pytest tests/fauna/ -q` green.
- [ ] Commit `feat(fauna): concurrency migration adds sync columns to fauna_table`.

### Task 3: Shared coercion helper (int/float/bool/date) + retrofit + FaunaService
**Files:** Create `pyarchinit_mini/services/coercion.py`; Modify `services/tomba_service.py`, `services/struttura_service.py` (retrofit); Create `services/fauna_service.py`; Modify `services/__init__.py`; Test `tests/fauna/test_fauna_service.py`, `tests/services/test_coercion.py`.
- [ ] **Shared helper** `services/coercion.py`: `coerce_types(model, data: dict) -> dict` — for each key in data that maps to a model column, coerce by the column's SQLAlchemy type: `Integer`→`int(v)`; `Float`→`float(v)`; `Boolean`→truthy parse (`true/1/si/sì/on/yes`→True, `false/0/no/off/''`→False-or-None per spec: empty→None, recognized false-words→False, else None); `Date`→`datetime.date.fromisoformat(v)` (empty/ValueError→None); leave other types untouched. Non-parseable numeric/date → None, never raise. Skip `bool` already-correct values. (Read the existing `_coerce_types` in `struttura_service.py` for the int/float logic to preserve.)
- [ ] **Test the helper** `tests/services/test_coercion.py` against a throwaway model or the Fauna model: int "7"→7; float "1.5"→1.5 (use a model with a Float col, e.g. Struttura); bool "sì"→True, "no"→False, ""→None, "xyz"→None; date "2024-05-01"→`date(2024,5,1)`, "bad"→None, ""→None; a Text field passes through untouched.
- [ ] **Retrofit** `tomba_service.py` and `struttura_service.py`: replace their local `_coerce_types` with a call to `from .coercion import coerce_types; ... = coerce_types(Tomba, data)` (resp. Struttura). Delete the now-dead local helpers. Run `.venv/bin/pytest tests/tomba/ tests/struttura/ -q` → still green (regression).
- [ ] **FaunaService** `services/fauna_service.py` mirroring struttura's, Struttura→Fauna, `id_struttura`→`id_fauna`: methods `list_fauna/count_fauna/get_fauna/create_fauna/update_fauna/delete_fauna/get_thesaurus_values(field)` (table_name='fauna_table')/`get_distinct_sites`. Use `Fauna.writable_columns()` + `coerce_types(Fauna, data)` in create/update. Search ilike ONLY on `sito, area, us, saggio, specie, contesto`. Order by `Fauna.id_fauna.desc()`. NO media methods. Register in `services/__init__.py`.
- [ ] **Test** `tests/fauna/test_fauna_service.py` (mirror struttura's + fauna specifics): CRUD (sito, specie); distinct sites; unknown thesaurus→[]; search on text fields; allowlist bypass (`id_fauna`/`version_number` injection ignored); coercion (`numero_minimo_individui:"3"`→3; `combustione_altri_materiali_us:"sì"`→True, `"no"`→False; `data_compilazione:"2024-05-01"`→date; bad date→None).
- [ ] Run `.venv/bin/pytest tests/fauna/ tests/services/test_coercion.py tests/tomba/ tests/struttura/ -q` → all green.
- [ ] Commit `feat(fauna): FaunaService + shared coercion helper (int/float/bool/date) + retrofit tomba/struttura`.

### Task 4: Thesaurus seed for fauna
**Files:** Modify `models/thesaurus.py`; Test `tests/fauna/test_fauna_thesaurus_seed.py`.
- [ ] Add `'fauna_table'` block to `THESAURUS_MAPPINGS` for `specie, parti_scheletriche, contesto, stato_conservazione, metodologia_recupero, deposizione` with sensible Italian vocab, e.g. `specie: ['Bos taurus','Ovis aries','Capra hircus','Sus domesticus','Equus caballus','Canis familiaris','Cervus elaphus','Gallus gallus']`, `parti_scheletriche: ['Cranio','Mandibola','Costola','Vertebra','Omero','Femore','Tibia','Metapodio','Falange']`, `contesto: ['Strato','Fossa','Focolare','Butto','Sepoltura','Riempimento']`, `stato_conservazione: ['Ottimo','Buono','Discreto','Cattivo','Frammentario']`, `metodologia_recupero: ['Raccolta manuale','Setacciatura a secco','Flottazione','Vagliatura']`, `deposizione: ['Primaria','Secondaria','In connessione','Sparsa']`.
- [ ] Test (mirror struttura): assert the block + 6 fields non-empty. Run → pass. Commit `feat(fauna): thesaurus vocab seed`.

### Task 5: Web routes + templates (NO media)
**Files:** Modify `web_interface/app.py`, `templates/base.html`; Create `templates/fauna/{list,form}.html`; Test `tests/fauna/test_fauna_routes.py`.
- [ ] Mirror the `/struttura` routes for fauna BUT WITHOUT media: instantiate `fauna_service`; routes `GET /fauna` (list), `GET/POST /fauna/new`, `GET/POST /fauna/<int:fauna_id>` (edit — NO `_media_gallery`), `POST /fauna/<int:fauna_id>/delete`, `GET /api/fauna/thesaurus/<field>`. NO `/fauna/<id>/media/upload` route. `@write_permission_required` on new/edit/delete.
- [ ] Templates copied from `templates/struttura/`, adapted to `id_fauna` PK + fauna fields, and **remove the media tab entirely**. `sito/area/us/saggio` text inputs; `id_us` `type="number"`; `numero_minimo_individui` `type="number"`; `data_compilazione` `type="date"`; `combustione_altri_materiali_us` a `<select>` (Sì/No/—) or checkbox; the 2 JSON fields (`specie_psi, misure_ossa`) as `<textarea>`; thesaurus datalist JS `THES_FIELDS = ['specie','parti_scheletriche','contesto','stato_conservazione','metodologia_recupero','deposizione']` fetching `/api/fauna/thesaurus/`. List columns: id_fauna, sito, us, specie, numero_minimo_individui. Nav link "Fauna" in base.html.
- [ ] Test `tests/fauna/test_fauna_routes.py` (mirror struttura's, minus media, incl. viewer write-denial): authed GET `/fauna`→200; POST `/fauna/new` {sito, specie}→302 + retrievable; GET `/fauna/<id>`→200 shows specie; `/api/fauna/thesaurus/specie`→200 JSON; delete→gone; viewer POST to `/fauna/<id>` blocked.
- [ ] Run → pass; app import clean; `.venv/bin/pytest tests/fauna/ -q` green.
- [ ] Commit `feat(fauna): web routes, list/form templates (no media) + thesaurus API`.

### Task 6: Dashboard tile + AI + MCP
**Files:** Modify `app.py`, `templates/dashboard.html`, `services/ai_assistant_service.py`, `mcp_server/tools/{data_import_parser_tool,pyarchinit_sync_tool}.py`; Test `tests/fauna/test_fauna_integration.py`.
- [ ] Mirror struttura's Task 6 for fauna: guarded `total_fauna = fauna_service.count_fauna()` in index stats + `dashboard.html` tile (`stats.get('total_fauna',0)`, label `{{ _('Fauna') }}`, icon e.g. `fa-bone` / `fa-paw`); `/fauna/ID` link in both AI prompts; `data_import_parser_tool` (`FIELD_MAPPINGS['fauna_table']` with sito/area/us/specie/contesto/numero_minimo_individui, `_get_service_for_table` → FaunaService, enum + target_table branches); `pyarchinit_sync_tool` (`"fauna"` enum + hasattr-guarded branches). i18n: add `"Fauna"` to both catalogs (it "Fauna", en "Fauna") if not present; recompile .mo.
- [ ] Test (mirror struttura integration): `_get_service_for_table('fauna_table')` → FaunaService; `/fauna` in both AI prompts; sync enum has `"fauna"`.
- [ ] Run → pass; imports clean. Commit `feat(fauna): dashboard tile + AI prompt + MCP integration`.

### Task 7: Docs + tutorial + i18n
**Files:** Create `docs/fauna.rst`, `docs/fauna_service.rst`; Modify `docs/index.rst`, `docs/tutorials/web_interface_tutorial.rst`, `README.md`, `CHANGELOG.md`, i18n catalogs.
- [ ] Mirror struttura's Task 7: `.rst` autodoc stubs (fully-qualified) + toctree; "Schede Fauna" tutorial section (note: US-linked, no media, Date/Boolean fields, 6 thesaurus dropdowns); README bullet; CHANGELOG entry under Unreleased.
- [ ] **i18n:** extract+translate ALL new fauna template strings into both it/en catalogs (`pybabel update` merge, hand-insert only fauna msgids, `pybabel compile`). Not just nav.
- [ ] Verify toctree refs; `.venv/bin/pytest tests/fauna/ -q` green. Commit `docs(fauna): record-type docs + tutorial + changelog + i18n`.

### Task 8: Full suite + sign-off
- [ ] `.venv/bin/pytest tests/fauna/ -v` green; `.venv/bin/pytest tests/ -q` → no NEW failures (pre-existing `test_delete_site` only). Confirm tomba/struttura still green after the coercion retrofit.
- [ ] Commit any fixups. Fauna complete.

## Self-Review
Covers fauna deltas: BigInteger PK, US linkage (text+id_us MVP), NO media (no entity_map/tab/route), Date+Boolean coercion via the NEW shared helper, JSON textareas, Postgres-safe search, write-guards. Addresses the struttura review's duplication finding by extracting `services/coercion.py` and retrofitting tomba/struttura. No placeholders — struttura is the concrete template to copy (minus media).
