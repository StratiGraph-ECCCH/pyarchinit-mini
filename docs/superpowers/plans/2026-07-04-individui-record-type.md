# Individui (scheda individuo) Record Type — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add the `individui` (anthropological individual / SCHEDAIND) record type to pyarchinit-mini web — full CRUD, plugin-schema-compatible, NO media, thesaurus-backed dropdowns, **auto-populated tomba↔individui link** (tomba's `nr_individuo` picks from existing individui), export, dashboard/AI/MCP, docs+i18n — replicating the proven fauna template (the closest: no media).

**Architecture:** Mirror the merged fauna slice (`models/fauna.py`, `services/fauna_service.py` — the LATEST version with lingua-aware `get_thesaurus_values`, `writable_columns()`, `coerce_types` — `/fauna` routes, `templates/fauna/`), adapted to individui. Plus one NEW piece: the tomba form's `nr_individuo` becomes a multi-select populated from individui filtered by sito+sigla_struttura+nr_struttura (stored comma-joined, exactly like the plugin).

**Tech Stack:** Python 3.12, SQLAlchemy, Flask, pytest.

## Global Constraints

- Plugin table **`individui_table`**, PK **`id_scheda_ind`** (Integer, native autoincrement), **UniqueConstraint('sito','nr_individuo', name='ID_individuo_unico')**. PRODUCTION NOTE: the table already EXISTS on the shared v2 DB with ~394 rows — the concurrency migration must only ALTER-add sync columns (like the other 4 entities); never recreate/drop.
- Map these columns EXACTLY (`entity_uuid`+sync from `BaseModel` — do NOT redeclare entity_uuid):
  `sito`(Text), `area`(Text), `us`(Text), `nr_individuo`(Integer), `data_schedatura`(String(100)), `schedatore`(String(100)), `sesso`(String(100)), `eta_min`(Text), `eta_max`(Text), `classi_eta`(String(100)), `osservazioni`(Text), `sigla_struttura`(Text), `nr_struttura`(Integer), `completo_si_no`(String(5)), `disturbato_si_no`(String(5)), `in_connessione_si_no`(String(5)), `lunghezza_scheletro`(Numeric(6, 2, asdecimal=False)), `posizione_scheletro`(String(50)), `posizione_cranio`(String(50)), `posizione_arti_superiori`(String(50)), `posizione_arti_inferiori`(String(50)), `orientamento_asse`(Text), `orientamento_azimut`(Text).
- **NO MEDIA** (like fauna): not in `entity_map`, no media route/tab; the form shows no media anything.
- **No JSON/repr columns** — all scalar. No flattening needed for export.
- **Thesaurus** (nome_tabella `'individui_table'`, lingua-aware like the other services):
  `THESAURUS_MAP = {'area':'8.6','posizione_cranio':'8.1','posizione_scheletro':'8.2','orientamento_asse':'8.3','posizione_arti_superiori':'8.4','posizione_arti_inferiori':'8.5','completo_si_no':'801.801','disturbato_si_no':'801.801','in_connessione_si_no':'801.801'}`.
  **SIGLA-vs-ESTESA nuance:** the plugin stores the **`sigla`** (short code) for the three `801.801` yes/no fields, and the **`sigla_estesa`** for the `8.x` fields. So `get_thesaurus_values` needs a per-field flag: `USE_SIGLA_FIELDS = {'completo_si_no','disturbato_si_no','in_connessione_si_no'}` → for those, `value = sigla` (code), else `value = sigla_estesa or sigla` as today.
  PRODUCTION NOTE: the shared v2 DB currently has ZERO `individui_table` sigle rows → the in-memory seed (tier-3 fallback) is the effective vocabulary source; make it complete (see Task 4).
- **Fixed hardcoded selects** (NOT thesaurus — exact plugin lists):
  `sesso`: `["", "Non identificabile", "Maschio", "Femmina", "Indeterminato"]`;
  `classi_eta`: `["", "Adulto giovane (20-29)", "Adulto maturo (30-50)", "Adulto di eta' avanzata (>50)"]`;
  `eta_min` and `eta_max`: `["", "0","1","2","3","4","5","6","7","8","9","10","20","30","40","50"]`.
- Number inputs: `nr_individuo`, `nr_struttura` (`type="number"`); `lunghezza_scheletro` (`type="number" step="any"`).
- **Search (Postgres-safe):** ilike ONLY on Text/String cols — `sito, area, us, sigla_struttura, sesso, classi_eta, schedatore`. NEVER on Integer/Numeric.
- **Tomba link (the plugin behavior to replicate):** tomba's `nr_individuo` column is **Text holding a comma-joined list** of `individui_table.nr_individuo` values. The plugin fills a multi-select from individui filtered by `sito + sigla_struttura + nr_struttura`. Mini: add `IndividuiService.get_nr_individui(sito, sigla_struttura=None, nr_struttura=None) -> list[int]` + API `GET /api/tomba/individui?sito=..&sigla_struttura=..&nr_struttura=..` + in `templates/tomba/form.html` replace the `nr_individuo` plain input with a `<select multiple>` populated by JS from that API (refetch when sito/sigla_struttura/nr_struttura change), serialized comma-joined into a hidden `<input name="nr_individuo">` on change/submit; current stored value pre-selected (split on comma). If the API returns nothing, keep an editable fallback (the hidden input keeps the existing value; show a small "no individui found" note).
- **Write routes** (`/individui/new`, `/individui/<id>` edit, `/individui/<id>/delete`) carry `@login_required` + `@write_permission_required` (whole-view). Reuse `Individui.writable_columns()` + `coerce_types(Individui, data)`.
- Run tests with `.venv/bin/pytest`. TDD, DRY, YAGNI, frequent commits. No `Co-Authored-By`/AI-attribution trailer. Do NOT change the existing entities' behavior beyond the tomba `nr_individuo` widget described above. Harris stays US-only.

## File Structure
Create `models/individui.py`, `services/individui_service.py`, `templates/individui/{list,form}.html`, `tests/individui/*`; modify `models/__init__.py`, `database/database_creator.py`, `database/migrations/__init__.py`, `services/__init__.py`, `web_interface/app.py`, `templates/base.html`, `templates/dashboard.html`, `templates/tomba/form.html` (nr_individuo widget), `models/thesaurus.py`, `services/ai_assistant_service.py`, `mcp_server/tools/{data_import_parser_tool,pyarchinit_sync_tool}.py`, docs, i18n catalogs.

---

### Task 1: Individui model
**Files:** Create `pyarchinit_mini/models/individui.py`; Modify `models/__init__.py`, `database/database_creator.py`; Test `tests/individui/test_individui_model.py` (+ `__init__.py`).
- [ ] Mirror `models/fauna.py`: `class Individui(BaseModel)`, `__tablename__='individui_table'`, `id_scheda_ind = Column(Integer, primary_key=True, autoincrement=True)`, the 23 columns from Global Constraints with EXACT types (import `Numeric`; use `Numeric(6, 2, asdecimal=False)` for lunghezza_scheletro), plus `__table_args__ = (UniqueConstraint('sito', 'nr_individuo', name='ID_individuo_unico'),)` and `to_dict()`. Register in `models/__init__.py` (import + `__all__`) and `database_creator.py::_import_all_models`.
- [ ] Test (mirror fauna's): full column set + BaseModel sync cols present; `lunghezza_scheletro` type name `Numeric`; `to_dict()` round-trips; the unique constraint exists (`any(c.name == 'ID_individuo_unico' for c in Individui.__table__.constraints if hasattr(c,'name'))`).
- [ ] Run → pass; imports clean. Commit `feat(individui): model mapping classic individui_table (SCHEDAIND)`.

### Task 2: Concurrency migration covers individui_table
**Files:** Modify `database/migrations/__init__.py`; Test `tests/individui/test_individui_migration.py`.
- [ ] Add `'individui_table'` to the `tables` list in `migrate_concurrency_columns()`.
- [ ] Test (mirror fauna's): bare plugin-shaped `individui_table` (id_scheda_ind INTEGER PRIMARY KEY, sito TEXT, nr_individuo INTEGER, entity_uuid TEXT — NO sync cols) → run migration → assert `{version_number, sync_status, editing_by} <= columns`. (Data-preserving by construction: ALTER ADD only.)
- [ ] Run → pass; `.venv/bin/pytest tests/individui/ -q` green. Commit `feat(individui): concurrency migration adds sync columns to individui_table`.

### Task 3: IndividuiService (CRUD + lingua-aware thesaurus with sigla fields + tomba helper)
**Files:** Create `pyarchinit_mini/services/individui_service.py`; Modify `services/__init__.py`; Test `tests/individui/test_individui_service.py`.
- [ ] Mirror the LATEST `services/fauna_service.py` (Fauna→Individui, `id_fauna`→`id_scheda_ind`; NO media/JSON helpers, NO max+1 allocator — plain Integer PK): `list_individui(page,size,search,sito)`, `count_individui(search,sito)`, `get_individui(id)`, `create_individui(data)`, `update_individui(id,data)`, `delete_individui(id)`, `get_thesaurus_values(field, lang='it')` (copy fauna's lingua-aware 3-tier version: sigle→thesaurus_field→seed, lang map it→IT/en→en_US, dedupe, PG-safe rollbacks), `get_distinct_sites()`. Use `Individui.writable_columns()` + `coerce_types(Individui, data)`. Search ilike ONLY on `sito, area, us, sigla_struttura, sesso, classi_eta, schedatore`. Order by `Individui.id_scheda_ind.desc()`.
- [ ] **Sigla-vs-estesa:** add `THESAURUS_MAP` (from Global Constraints) + `USE_SIGLA_FIELDS = {'completo_si_no','disturbato_si_no','in_connessione_si_no'}`; in the sigle query result loop, `value = r.sigla if field in self.USE_SIGLA_FIELDS else (r.sigla_estesa or r.sigla)`.
- [ ] **Tomba helper:** `get_nr_individui(self, sito, sigla_struttura=None, nr_struttura=None) -> list` — query `Individui.nr_individuo` filtered by `sito ==` (required) and, when given, `sigla_struttura ==` / `nr_struttura ==` (coerce nr_struttura to int, ignore if unparseable); distinct, non-null, sorted ascending as ints.
- [ ] Register in `services/__init__.py`.
- [ ] Test (mirror fauna's + specifics): CRUD (sito, sesso); distinct sites; unknown thesaurus→[]; the lingua-filter/dedupe test (mirror fauna's, field `posizione_cranio` sigla `8.1`); **USE_SIGLA test:** seed sigle rows for `801.801` with sigla='SI'/sigla_estesa='Sì presente' etc. → `get_thesaurus_values('completo_si_no')` returns value 'SI' (the sigla); allowlist bypass (`id_scheda_ind`:999/`version_number`:42 ignored); coercion (`nr_individuo`:"7"→7, `lunghezza_scheletro`:"165.5"→165.5 float, bad→None); `get_nr_individui`: create 3 individui (two for sito S+struttura TB/1, one other) → `get_nr_individui('S','TB',1)` returns exactly the two nr, sorted.
- [ ] Run `.venv/bin/pytest tests/individui/ -q` green. Commit `feat(individui): IndividuiService CRUD + lingua-aware thesaurus (sigla yes/no fields) + get_nr_individui`.

### Task 4: Thesaurus seed for individui
**Files:** Modify `models/thesaurus.py`; Test `tests/individui/test_individui_thesaurus_seed.py`.
- [ ] Add `'individui_table'` block to `THESAURUS_MAPPINGS`. IMPORTANT: production v2 has ZERO individui sigle rows, so this seed IS the effective dropdown vocabulary — make it complete and sensible:
  - `posizione_cranio`: ['Nord','Nord-Est','Est','Sud-Est','Sud','Sud-Ovest','Ovest','Nord-Ovest','Frontale','Laterale destro','Laterale sinistro']
  - `posizione_scheletro`: ['Supino','Prono','Fianco destro','Fianco sinistro','Rannicchiato','Seduto']
  - `orientamento_asse`: ['N-S','S-N','E-O','O-E','NE-SO','SO-NE','NO-SE','SE-NO']
  - `posizione_arti_superiori`: ['Distesi lungo i fianchi','Incrociati sul bacino','Incrociati sul petto','Piegati sul bacino','Piegati sul petto']
  - `posizione_arti_inferiori`: ['Distesi','Flessi','Incrociati','Rannicchiati']
  - `area`: ['1','2','3']
  - `completo_si_no`: ['Sì','No','Parziale']
  - `disturbato_si_no`: ['Sì','No']
  - `in_connessione_si_no`: ['Sì','No','Parziale']
- [ ] Test: block present with those 9 fields, each non-empty. Run → pass. Commit `feat(individui): thesaurus vocab seed`.

### Task 5: Web routes + templates (NO media) + fixed selects
**Files:** Modify `web_interface/app.py`, `templates/base.html`; Create `templates/individui/{list,form}.html`; Test `tests/individui/test_individui_routes.py`.
- [ ] Mirror the `/fauna` routes (fauna has no media — closest template): instantiate `individui_service`; add `app.individui_service`; routes `GET /individui` (list; filter by sito), `GET/POST /individui/new`, `GET/POST /individui/<int:individui_id>` (edit — NO media), `POST /individui/<int:individui_id>/delete`, `GET /api/individui/thesaurus/<field>` (pass `lang=get_locale()` guarded, like the others). `@write_permission_required` on the 3 writes incl. edit.
- [ ] Templates copied from `templates/fauna/` adapted to `id_scheda_ind` PK + individui fields, organized in tabs/fieldsets (Identificazione: sito/area/us/nr_individuo/data_schedatura/schedatore + sigla_struttura/nr_struttura; Antropologia: sesso/eta_min/eta_max/classi_eta/lunghezza_scheletro; Giacitura: completo/disturbato/in_connessione/posizione_scheletro/posizione_cranio/arti sup/arti inf/orientamento_asse/orientamento_azimut; Osservazioni textarea). Thesaurus fields as visible `<select id="sel-<field>">` (the CURRENT pattern — copy fauna's select+JS with `data-current`, fetch `/api/individui/thesaurus/<field>`) for the 9 mapped fields; **fixed selects** for sesso/classi_eta/eta_min/eta_max with the exact plugin lists (Jinja `selected` on current value); number inputs per Global Constraints. NO media tab. List table: id_scheda_ind, sito, us, nr_individuo, sesso, classi_eta. Nav link "Individui" in base.html.
- [ ] Test (mirror fauna's routes test incl. viewer write-denial + no-media check): authed GET `/individui`→200; POST `/individui/new` {sito, nr_individuo, sesso}→302 + retrievable; GET `/individui/<id>`→200 shows sesso; `/api/individui/thesaurus/posizione_cranio`→200 JSON; delete→gone; viewer POST blocked; NO `/individui/<id>/media/upload` rule in the URL map.
- [ ] Run → pass; app import clean; `.venv/bin/pytest tests/individui/ -q` green. Commit `feat(individui): web routes, list/form templates (no media) + thesaurus API`.

### Task 6: Tomba nr_individuo auto-populate + dashboard + AI + MCP
**Files:** Modify `web_interface/app.py`, `templates/tomba/form.html`, `templates/dashboard.html`, `services/ai_assistant_service.py`, `mcp_server/tools/{data_import_parser_tool,pyarchinit_sync_tool}.py`; Test `tests/individui/test_individui_integration.py` (+ extend `tests/tomba/test_tomba_routes.py` only if trivially).
- [ ] **Tomba link:** add `GET /api/tomba/individui` (login_required) reading `sito` (required), `sigla_struttura`, `nr_struttura` query args → `jsonify(individui_service.get_nr_individui(...))`. In `templates/tomba/form.html`, replace the `nr_individuo` plain input with: a `<select multiple id="sel-nr-individuo" class="form-select" size="4">` + hidden `<input name="nr_individuo" value="{{ tomba.nr_individuo or '' }}">` + JS that (a) fetches the API using the form's current sito/sigla_struttura/nr_struttura values (re-fetch on change of any of the three), (b) renders options, pre-selecting those in the hidden input's comma-split value, (c) keeps any stored values not in the fetched list as extra selected options (never lose data), (d) on selection change writes the comma-joined (`', '`) selection to the hidden input. A short helper text `{{ _('Individuals are loaded from the Individui records of this site/structure.') }}`.
- [ ] **Dashboard/AI/MCP** (mirror fauna's Task 6): guarded `total_individui` + tile (`{{ _('Individui') }}`, icon `fa-user` / `fa-skull`); `/individui/ID` link line in BOTH AI prompts + `individui_summary` context block in `/api/ai/ask` (total, by_sesso, by_classi_eta, sample[:200] with id/sito/us/nr_individuo/sesso/classi_eta) + inject in `_build_context_block`; MCP `data_import_parser_tool` (`FIELD_MAPPINGS['individui_table']` sito/area/us/nr_individuo/sesso/classi_eta, `_get_service_for_table` → IndividuiService, enum + branches); `pyarchinit_sync_tool` (`"individui"` enum + hasattr-guarded branches reading `imported`/`errors`). i18n msgid "Individui" if new.
- [ ] Test: `_get_service_for_table('individui_table')` → IndividuiService; `/individui` in both AI prompts; sync enum has `"individui"`; `_build_context_block({'individui_summary': {...}})` contains "INDIVIDUI"; the `/api/tomba/individui` route returns the filtered list (harness: mirror how the thesaurus API route is tested).
- [ ] Run → pass; imports clean. Commit `feat(individui): tomba nr_individuo auto-populate + dashboard + AI + MCP`.

### Task 7: Export + docs + tutorial + i18n
**Files:** Modify `web_interface/app.py`, `templates/individui/list.html`; Create `docs/individui.rst`, `docs/individui_service.rst`; Modify `docs/index.rst`, `docs/tutorials/web_interface_tutorial.rst`, `README.md`, `CHANGELOG.md`, i18n catalogs.
- [ ] **Export:** 3 routes `/export/individui/{excel,csv,pdf}` mirroring fauna's (filter by `sito`, `finally`-guarded temp, `send_file`; NO flattening needed — all scalar; use the existing `_export_tmp_send`/pattern + `pdf_generator.generate_records_pdf('Individui', data, tmp)`). Export buttons on `templates/individui/list.html` (mirror fauna's).
- [ ] **Docs:** `docs/individui.rst` + `docs/individui_service.rst` (fully-qualified autodoc) + toctree; "Schede Individuo" tutorial section (no media, tomba link, fixed selects); README bullet; CHANGELOG under a new Unreleased heading.
- [ ] **i18n:** extract+translate ALL new template strings (hand-insert only individui msgids, `pybabel compile` WITHOUT --use-fuzzy).
- [ ] Verify toctree refs; export smoke test (CSV 200, content has a created record). Run `.venv/bin/pytest tests/individui/ -q` green. Commit `feat(individui): export + docs + tutorial + i18n`.

### Task 8: Full suite + sign-off
- [ ] `.venv/bin/pytest tests/individui/ -v` green; `.venv/bin/pytest tests/ -q` → no NEW failures. Confirm tomba tests still green (the nr_individuo widget change).
- [ ] Commit any fixups. Individui complete.

## Self-Review
Covers: plugin schema (23 cols + UNIQUE), existing-table-with-data migration safety (ALTER only), sigla-vs-estesa thesaurus nuance (801.801), lingua-aware vocab, complete seed (production sigle are empty), fixed plugin selects, NO media, tomba↔individui auto-populate with comma-joined storage (plugin-identical), export without flattening, AI/MCP/dashboard/docs/i18n. Reuses writable_columns/coerce_types/select pattern. fauna is the concrete template (no media); tomba form gets the only cross-entity edit.
