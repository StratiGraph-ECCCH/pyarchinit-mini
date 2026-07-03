## 3.0.2 — 2026-07-03

### Fixed
- CSV-import routes (`import_sites_csv`/`import_us_csv`/`import_inventario_csv`) now remove their temp file in a `finally` block — no leak if the import raises.
- New-record thesaurus lookups (`get_thesaurus_values`) now `rollback()` between the `pyarchinit_thesaurus_sigle` and `thesaurus_field` fallback queries, so on PostgreSQL a missing sigle table no longer aborts the transaction and silently skips the `thesaurus_field` layer.

## 3.0.1 — 2026-07-03

Post-3.0.0 cleanup + plugin-thesaurus interop alignment for the new record types.

### Changed — thesaurus vocabularies shared with the classic plugin
- The tomba/struttura/fauna/ut web forms now read their controlled vocabularies from the classic plugin's `pyarchinit_thesaurus_sigle` table (by `nome_tabella` + `tipologia_sigla`, returning the extended label `sigla_estesa`), falling back to mini's `thesaurus_field` and then the in-memory seed. On a shared DB the dropdown values now match the plugin exactly. Combobox coverage expanded to the plugin's full set (fauna 6→15 fields, tomba 7→9, ut 5→7), and struttura's `orientamento_ingresso`/`articolazione`/`potenzialita_archeologica` are now fixed selects (the plugin uses hardcoded lists there, not the thesaurus).
- Note: the 4 new record tables are already covered by the generic nightly classic→v2 sync engine (`pyarchinit_mini/sync/`) with no code change — they mirror automatically once present in both databases.

### Fixed
- Media upload: all upload routes now go through a shared helper with a `finally`-guaranteed temp-file cleanup (no leak on error) and unique temp names (no collision on duplicate filenames).
- i18n: unfuzzed the shared list/pagination chrome msgids (`records`/`Page`/`Previous`/`Next`/`New`/`Create the first one`) — they had wrong machine translations and were dropped at compile, leaking English into the Italian UI.
- UT `potential_score`/`risk_score` now read back as `float` (`Numeric(asdecimal=False)`) instead of `Decimal`; the shared coercion helper's boolean branch also accepts raw `int` `0`/`1`.

## 3.0.0 — 2026-07-03

Major release: **four new archaeological record types** — Tomba, Struttura, Fauna, and UT (Unità Topografica) — added to the web interface, each mapping the classic PyArchInit plugin schema for shared-DB interop, with full CRUD, thesaurus-backed dropdowns, media (all except Fauna), dashboard tiles, AI + MCP integration, Sphinx docs + tutorial sections, and full IT/EN i18n. Internals: a shared `services/coercion.py` (int/float/bool/date/numeric) helper, a `BaseModel.writable_columns()` mass-assignment allowlist, and Postgres-safe search (ILIKE restricted to text columns) applied across the new entities.

### Added — Tomba (burial) record type
- New **Tomba** entity mirroring the classic PyArchInit `tomba_table`: ritual, structure, grave-goods (corredo), and chronology fields, with `TombaService` (list/count/get/create/update/delete, site filtering, free-text search).
- Web UI: `/tomba` list + create/edit form, media upload panel (same media pipeline as Sites/US/Inventario), and a "Tombe" dashboard tile/nav entry.
- Thesaurus-backed dropdowns for 7 fields (Rito, Tipo Sepoltura, Tipo Deposizione, Copertura Tipo, Tipo Contenitore Resti, Stato di Conservazione, Corredo Presenza) via `GET /api/tomba/thesaurus/<field>`.
- Docs: Sphinx autodoc stubs (`docs/tomba.rst`, `docs/tomba_service.rst`) and a new "Schede Tomba" section in the Web Interface Tutorial.
- i18n: added the missing `"Tombe"` catalog entry (IT: "Tombe", EN: "Graves") so the dashboard tile/nav label translates correctly instead of leaking Italian into the English UI.

### Added — Struttura (architectural structure) record type
- New **Struttura** entity mirroring the classic PyArchInit `struttura_table`: identification, description, room articolazione, and chronology fields, with `StrutturaService` (list/count/get/create/update/delete, site filtering, free-text search).
- Web UI: `/struttura` list + create/edit form (4 tabs: Identification, Description, Articolazione, Chronology), media upload panel (same media pipeline as Sites/US/Inventario/Tomba), and a "Strutture" dashboard tile/nav entry.
- Thesaurus-backed dropdowns for 4 fields (Categoria Struttura, Tipologia Struttura, Orientamento Ingresso, Articolazione) via `GET /api/struttura/thesaurus/<field>`.
- Docs: Sphinx autodoc stubs (`docs/struttura.rst`, `docs/struttura_service.rst`) and a new "Schede Struttura" section in the Web Interface Tutorial.
- i18n: full template extraction — 32 new catalog entries (tab names, field labels, "New/Edit Struttura", list/search/delete strings) added to both the Italian and English catalogs, so the Struttura pages are fully translated instead of leaking raw Italian into the English UI.

### Added — Fauna (faunal remains) record type
- New **Fauna** entity mirroring the classic PyArchInit `fauna_table`: US-linked identification, recovery context, species/skeletal data, and combustion/taphonomy fields, with `FaunaService` (list/count/get/create/update/delete, site filtering, free-text search).
- Web UI: `/fauna` list + create/edit form (5 tabs: Identification, Context, Fauna Data, Combustion & Conservation, Notes; no media panel — Fauna is a US-linked record), and a "Fauna" dashboard tile/nav entry.
- Thesaurus-backed dropdowns for 6 fields (Specie, Parti Scheletriche, Contesto, Stato di Conservazione, Metodologia Recupero, Deposizione) via `GET /api/fauna/thesaurus/<field>`.
- Docs: Sphinx autodoc stubs (`docs/fauna.rst`, `docs/fauna_service.rst`) and a new "Schede Fauna" section in the Web Interface Tutorial.
- i18n: full template extraction — 40 new catalog entries (tab names, field labels, "New/Edit Fauna", list/search/delete strings) added to both the Italian and English catalogs, so the Fauna pages are fully translated instead of leaking raw Italian into the English UI.

### Added — UT (topographic/survey unit) record type
- New **UT** entity mirroring the classic PyArchInit `ut_table`: project-scoped (via `progetto`, no `sito` column) identification, location, field-survey observations, and potential/risk analysis fields, with `UtService` (list/count/get/create/update/delete, project filtering, free-text search).
- Web UI: `/ut` list + create/edit form (4 tabs: Anagrafica, Ubicazione, Survey, Analisi), media upload panel (same media pipeline as Sites/US/Inventario/Tomba/Struttura), and a "UT" dashboard tile/nav entry.
- Thesaurus-backed dropdowns for 5 fields (Definizione UT, Survey Type, GPS Method, Surface Condition, Accessibility) via `GET /api/ut/thesaurus/<field>`.
- Docs: Sphinx autodoc stubs (`docs/ut.rst`, `docs/ut_service.rst`) and a new "Schede UT" section in the Web Interface Tutorial.
- i18n: full template extraction — 68 new catalog entries (tab names, field labels, "New/Edit UT", list/search/delete strings) added to both the Italian and English catalogs, so the UT pages are fully translated instead of leaking raw Italian into the English UI.

## 2.9.1 — 2026-05-19

### Fixed — Harris Matrix proper rendering (post-2.9.0 feedback)
- **Edge direction normalized to forward**: was reading "Coperto da" / "Tagliato da" etc. on the swimlane. Harris convention is recent→ancient with forward labels. Now every inverse canonical (`is_after`, `is_cut_by`, `is_filled_by`, `is_abutted_by`) is auto-swapped to its forward (`overlies`/`cuts`/`fills`/`abuts`) with source/target reversed. User reads "Copre" / "Taglia" / "Riempie" / "Si appoggia a".
- **Arrows now visible**: was missing because cytoscape's `data(style.targetArrowShape)` dot-notation accessor didn't resolve nested objects. All palette/edge fields flattened into top-level data keys (`shape`, `bgcolor`, `bordercolor`, `linecolor`, `arrowtarget`, …). Selectors `node[shape]`, `edge[linecolor]` etc. now match reliably.
- **Palette node styling visible**: USM/USD/USV/SF/VSF/TSU now appear with their palette shape + colors (was plain gray rectangles). Same flattening fix.
- **Period rows as compound swimlanes**: every US node is a child of its `period_row_N` compound parent (visible as a horizontal lane on the canvas with label "Periodo X — Fase Y — Datazione"). Sub-groupings (area/settore/quadrato/attivita/strutture) nest INSIDE period rows as sub-clusters.
- **Symmetric edges without arrows**: `has_same_time` / `is_bonded_to` now render as solid lines, no arrow heads, thicker stroke for visibility.
- **Vertical layout**: dagre `rankDir: "TB"` (top-to-bottom) — newer US on top, older on bottom.
- **Cuts dashed**: `cuts` edges get `line-style: dashed` (Harris convention).

### Fixed — Vocabulary corrections
- `vocab_it.json` had `"tagliato da"` mapping to `is_after` (wrong) — corrected to `is_cut_by`.
- `_IT_EXTRAS` had `"riempito da"` → `"is_after"` (wrong) — corrected to `is_filled_by`.
- `_IT_EXTRAS` had `"gli si appoggia"` → `"is_before"` (wrong) — corrected to `is_abutted_by`.

### Internals
- New constant `rapporti_codec.REVERSE_TO_FORWARD: Dict[str, str]` lookup.
- `s3d_projector._load_edges` normalizes inverse direction before dedup.
- `s3d_to_cytoscape.to_cytoscape` emits flat data fields + ALWAYS-on period row compounds (even with `group_by=none`).
- `harris_creator_editor.js` rebuilt cytoscape style selectors against flat data; layout switched to `rankDir: "TB"`.

## 2.9.0 — 2026-05-19

### Fixed — Swimlane UI/UX cleanup (post-2.8.0 feedback)
- **Toolbar consolidated**: removed duplicate `swimlane-toolbar` block. Single `Esporta` dropdown now contains yEd GraphML (.graphml), Heriverse/ATON JSON (.json), Graphviz DOT, PNG. `Importa` button accepts both .graphml and .json. The existing `group-by-selector` now uses the new vocabulary: Nessun raggruppamento / Area / Settore / Quadrato / Attività / Strutture (was: Period+Phase / Struttura / Attivita / Settore / Area / Ambient / Saggio / Quad-Par / No grouping).
- **Edge labels italianized**: swimlane web + GraphML export now show `Copre`/`Coperto da`/`Taglia`/`Tagliato da`/`Riempie`/`Riempito da`/`Si appoggia a`/`Gli si appoggia`/`Uguale a`/`Si lega a`/`Anteriore a` (locale `it`) or `Covers`/`Covered by`/etc (locale `en`) instead of canonical `overlies`/`is_after`/`cuts`/etc. Canonical kept in `data.canonical` for JS class hooks.
- **Inverse-edge dedup**: when both `A overlies B` and `B is_after A` exist (data redundancy), draw only the forward direction — no more overlapping labels at the same midpoint.
- **Transitive reduction**: if A→B→C exists, A→C is no longer drawn (per-canonical, only for DAGs). Applied via `networkx.transitive_reduction`. Adarte fixture: 516 → 343 edges (clean Harris Matrix layout).
- **Palette-driven frontend rendering**: cytoscape selectors `node[style]` and `edge[style]` now read `data.style.{shape,backgroundColor,borderColor,borderWidth,lineColor,…}` from the `/api/load` payload and apply them. US nodes finally appear with their palette colors/shapes (USM red border, USV octagonal, …) instead of default gray.
- **GraphML export rewritten**: now produces the proper Harris Matrix Creator format via `pyarchinit_mini.graphml_io.yed_writer.write_extended_matrix_graphml` — TableNode wrapper with `<y:Rows>` per period/fase (colored backgrounds, rotated labels like "Periodo 1 - Fase 1"), nodes positioned inside their period row, palette styles, italianized edge labels. Previously the writer just appended nodes to the palette template without TableNode rows.

### Internals
- New `rapporti_codec.CANONICAL_TO_ITALIAN`/`CANONICAL_TO_ENGLISH`/`display_label(canonical, locale)` (moved from `graph_to_db.py`).
- `s3d_projector._load_edges` post-process: inverse dedup + per-canonical `nx.transitive_reduction` (skipped for SYMMETRIC and cyclic graphs).
- `s3d_to_cytoscape` edges now carry `data.label` (italian display) AND `data.canonical` (English canonical for JS hooks).
- `graphml_writer.write_graphml` now bridges to the existing `yed_writer.write_extended_matrix_graphml` via a temp file.
- `harris_creator_editor.js`: 2 new cytoscape selectors (`node[style]`, `edge[style]`) read palette properties from element data.
- `editor.html`: removed `swimlane-toolbar` div + duplicate `group-by-select` + standalone `export-graphml-btn`/`export-dot-btn`/`export-png-btn` + `exportYedGraphml()` button; replaced with one unified `Esporta` dropdown + `Importa` button.

## 2.8.0 — 2026-05-19

### Added — EM Palette + Multi-Format Swimlane Round-Trip
- **EM palette is now the canonical style source** for swimlane rendering, GraphML export, and Heriverse/ATON JSON export. Palette loaded from `pyarchinit_mini/graphml_converter/templates/EM_palette.graphml` (3246-line canonical version) with `PaletteLoader` cache + SIGHUP hot-reload + fallback to minimal hardcoded defaults if missing.
- **`SWIMLANE_PIPELINE=s3dgraphy|legacy` feature flag** (default `s3dgraphy`) with automatic legacy fallback on exception. Set to `legacy` to roll back instantly.
- **New endpoints**:
  - `GET /harris-creator/api/export/<site>/heriverse-json` — Heriverse/ATON JSON (single format).
  - `POST /harris-creator/api/import/<site>/graphml` — yEd GraphML import that writes 4-tuple rapporti and inverses on BOTH involved US.
  - `POST /harris-creator/api/import/<site>/json` — Heriverse JSON import (same write path).
- **Standalone `/matrix-tools` page** for import/export operations (site picker + format radio + file uploader).
- **Per-site export buttons** (GraphML, Heriverse) in sites list.
- **Swimlane toolbar**: grouping dropdown (none/area/settore/quadrato/attività/strutture), export menu, import file picker.
- **Bilingual rapporti parser**: reads both legacy 2-tuple `[rel, us]` and new 4-tuple `[rel, us, area, sito]`; always writes 4-tuple. Italian aliases include extras (`riempito da`, `si lega a`, `gli si appoggia`) absent from `vocab_it.json`.
- **Automatic stub US creation** when import edges reference missing rows; counted in result.

### Changed
- Swimlane rows are now always periods (with "Periodo 1" fallback when `period_table` is empty or a US has no period match); the old `group_by=period_phase|struttura|...` registry collapses to a sub-grouping selector within rows. Legacy `group_by` values still work via the `legacy` pipeline.
- `/api/load/<site>` response includes a `style` dict per node and edge, derived from the EM palette (shape, fill color, border color, line style, arrow heads).

### Internals
- New modules: `pyarchinit_mini/em_palette/` (loader, styles), `pyarchinit_mini/graphproj/` (rapporti_codec, s3d_projector, s3d_to_cytoscape, graph_to_db, heriverse_parser, graphml_reader, graphml_writer).
- New tests: 13 test files across `tests/unit/` and `tests/integration/`, plus a regression fixture (`tests/fixtures/adarte_regression_dump.sql`) anonymized from `Rimini_RN_2020_21_Museo_Fellini` (100 US, 516 edges, 8 distinct canonical labels validated end-to-end).

### Migration notes
- The `patch_pyarchinit_post_upgrade.py` post-upgrade script's Section 27 (`swimlane.row_provider_schema`) and Section 28 (`swimlane.build_edges_literal`) still apply, but their fixes are now native to the s3dgraphy pipeline. After this upgrade, Sections 27/28 are no-ops if the legacy file no longer has the markers.

## [2.7.1] - 2026-05-19

### Fixed (IT)
- **AI Matrix Import** post-merge hotfix: la 2.7.0 era inservibile in produzione per 4 bug scoperti al primo uso reale.
  - `g.db_session` non viene mai popolato in produzione: ora si usa `_get_session()` context manager (stesso pattern di `yed_import_routes`).
  - Le chiavi API AI vivono nella tabella `app_settings` (gestita dalla UI Admin), non solo in env: bootstrap automatico in `os.environ` prima di chiamare l'extractor.
  - Schema `us_table` corretto: `descrizione` (Text) invece di `d_stratigrafica` (String); `fase_finale` invece del campo inventato `fase_recente`; cast int→str per le fasi (colonne TEXT).
  - Schema `us_relationships_table` corretto: colonna `sito` singola (non `sito_from`/`sito_to`), `relationship_type` (non `tipo_relazione`), `id_relationship` (non `id_rel`).
  - Endpoint redirect: `us_list` (bare route) invece di `us.list_us` (blueprint inesistente).
  - Template (upload/preview/rejected) ora estendono `base.html` con styling Bootstrap, navbar e icone Font Awesome.

### Fixed (EN)
- **AI Matrix Import** post-merge hotfix: 2.7.0 was unusable in production due to 4 bugs caught on first real use.
  - `g.db_session` was never populated in production: now uses `_get_session()` context manager (same pattern as `yed_import_routes`).
  - AI API keys live in the `app_settings` table (managed via UI Admin), not only in env: automatic bootstrap into `os.environ` before extractor call.
  - Corrected `us_table` schema: `descrizione` (Text) instead of `d_stratigrafica` (String); `fase_finale` instead of made-up `fase_recente`; int→str cast for phases (TEXT columns).
  - Corrected `us_relationships_table` schema: single `sito` column (not `sito_from`/`sito_to`), `relationship_type` (not `tipo_relazione`), `id_relationship` (not `id_rel`).
  - Redirect endpoint: `us_list` (bare route) instead of `us.list_us` (non-existent blueprint).
  - Templates (upload/preview/rejected) now extend `base.html` with Bootstrap styling, navbar, and Font Awesome icons.

## [2.7.0] - 2026-05-18

### Added (IT)
- **AI Matrix Import** (`/matrix-import/`): nuova feature che usa Vision API
  (Anthropic Claude Sonnet 4.7 o OpenAI GPT-5.5) per estrarre US e relazioni
  stratigrafiche da un'immagine di un Harris matrix. Include validation gate
  (l'AI rifiuta immagini che non sono matrici), preview editabile prima del
  commit, e auto-creazione del sito se nuovo.
- L'immagine sorgente viene salvata come media legato al sito.
- Toggle Anthropic / OpenAI nel form di upload.
- Required env vars: `ANTHROPIC_API_KEY` e/o `OPENAI_API_KEY`, `AI_PROVIDER` opzionale.

### Added (EN)
- **AI Matrix Import** (`/matrix-import/`): new feature that uses Vision API
  (Anthropic Claude Sonnet 4.7 or OpenAI GPT-5.5) to extract stratigraphic
  units and relationships from an image of a Harris matrix. Includes a
  validation gate (the AI rejects non-matrix images), editable preview
  before commit, and auto-creation of the site if new.
- Source image saved as media linked to the site.
- Anthropic / OpenAI toggle in the upload form.
- Required env vars: `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY`, optional `AI_PROVIDER`.

## [2.6.0] - 2026-05-18

### Changed (IT)
- Editor Harris Matrix Creator: gli archi stratigrafici sono ora resi con
  routing ortogonale (90°, `curve-style: 'taxi'`) invece che con curve
  bezier diagonali. Allineato al `y:PolyLineEdge` di yEd usato da
  pyarchinit QGIS plugin.
- `harris_swimlane/harris_layout.py`: defaults aumentati a `v_gap=40`
  (era 20) e `h_gap=50` (era 30) per dare respiro agli archi ortogonali.
  Chiamanti che passano i parametri esplicitamente non sono toccati.

### Changed (EN)
- Harris Matrix Creator editor: stratigraphic edges now render with
  right-angle routing (`curve-style: 'taxi'`) instead of bezier curves,
  matching the `y:PolyLineEdge` style used by pyarchinit QGIS.
- `harris_swimlane/harris_layout.py`: defaults bumped to `v_gap=40`
  (was 20) and `h_gap=50` (was 30) to give orthogonal edges breathing
  room. Explicit callers are unaffected.

## [2.5.1] - 2026-05-18

### Added (IT)
- Pottery list: anteprima media in linea con mini-carousel CSS scroll-snap
  (thumb 48x48 + GLightbox). N+1 evitato con pre-load batch via
  `MediaService.get_media_for_entity_ids`.
- Pottery filtri: nuovi input `id_number` e `anno` (esatti, integer cast
  con guard `try/except`).
- Pottery detail: galleria thumbnail inline (120x120, GLightbox) sopra i
  campi della scheda.
- Nuovo blueprint `pyarchinit_mini/i18n/lang_routes.py` con
  `POST /set-language/<lang>` che salva session e fa redirect al referrer.
  Lo switcher di lingua diventa `<form>` POST: preserva la query string
  corrente (filtri/ricerca non si perdono più al cambio lingua).

### Changed (IT)
- `templates/components/language_switcher.html`: `<a>` sostituiti con form POST.
- `PotteryService._FILTERABLE_INT` aggiunto con `id_number`, `anno`.
- `pottery_routes.FILTER_KEYS` esteso con `id_number`, `anno`.

### Added (EN)
- Pottery list: inline media preview with CSS scroll-snap mini-carousel
  (48x48 thumbs + GLightbox). Batch pre-load avoids N+1.
- Pottery filters: new `id_number` + `anno` exact-match inputs with
  integer cast guard.
- Pottery detail: inline thumbnail gallery (120x120, GLightbox).
- New `pyarchinit_mini/i18n/lang_routes.py` blueprint: `POST /set-language/<lang>`
  saves session + redirects to referrer, preserving the URL query string
  (filters/search no longer lost on language switch).

### Changed (EN)
- Language switcher templates: anchors replaced with POST forms.
- `PotteryService._FILTERABLE_INT` introduces `id_number`, `anno`.
- `pottery_routes.FILTER_KEYS` extended.

## [2.5.0] - 2026-05-18

### Added (IT)
- Editor swimlane: dropdown "Group by" con 9 valori (period_phase | struttura
  | attivita | settore | area | ambient | saggio | quad_par | none).
  Cambiando valore le lane si ricostruiscono e i nodi US si ridistribuiscono
  con un layout Harris-classico server-side.
- Nuovo modulo `harris_swimlane/harris_layout.py` — ordinamento topologico
  per dipendenze stratigrafiche (`overlies` / `is_after`), recent in alto.
- Nuovo `graphml_io/yed_importer.py` — parse + build_import_plan +
  apply_import_plan per round-trip da Extended Matrix → DB. Idempotente,
  preview 2-fasi, upsert by `node_uuid`.
- Nuova pagina `/import-graphml/` (upload + preview + apply). Sidebar entry
  sia in navbar che laterale (sezione Tools).

### Changed (IT)
- `graphml_io/yed_writer.py` riscritto: emette file Extended Matrix
  byte-compat con pyarchinit QGIS (38 keys d0..d37, `y:TableNode
  YED_TABLE_NODE`, `pyarchinit.epochs_meta`, `pyarchinit.*` per ogni nodo
  US). Vecchio `write_yed_graphml` mantenuto come wrapper deprecato.
- API `/harris-creator/api/load/<site>` accetta `?group_by=...` query
  param (default `period_phase`, retro-compat).
- API `/harris-creator/api/export/<site>/yed-graphml` accetta `?group_by=...`
  e popola `epochs_meta` da `periodizzazione_table`.
- Path output cambia in `data/exports/harris_yed/<slug>-extmatrix.graphml`
  (era `<slug>-harris-yed.graphml`).

### Added (EN)
- Editor "Group by" dropdown with 9 values; lanes rebuild + Harris-classic
  re-layout on change.
- New `harris_swimlane/harris_layout.py` — server-side topological
  positioning.
- New `graphml_io/yed_importer.py` — round-trip yEd → DB.
- New `/import-graphml/` page (upload + preview + apply).

### Changed (EN)
- `graphml_io/yed_writer.py` rewritten — emits 38-key Extended Matrix
  byte-compat with pyarchinit.
- `/api/load` and `/api/export` accept `?group_by=...`.
- Export output path renamed `*-extmatrix.graphml`.

## [2.4.8] - 2026-05-18

### Fixed (IT)
- `loadExistingData` (legacy loader) ora deduplica le relationship triple
  `(from_us, to_us, relationship)` e suffissa gli ID Cytoscape che
  collidono quando la stessa coppia compare con tipi diversi. Risolve
  l'errore "Can not create second element with ID `edge_131_136`" che
  abortiva l'intero forEach e lasciava il canvas senza archi.

### Fixed (EN)
- Legacy `loadExistingData` now deduplicates relationship triples and
  suffixes colliding edge IDs. Fixes "second element with ID
  edge_X_Y" errors that previously aborted edge loading.

## [2.4.7] - 2026-05-18

### Fixed (IT)
- Editor swimlane carica anche gli edge da `us_relationships_table` (Spec 3-bis
  ora unisce `us_table.rapporti` + tabella dedicata via EdgeRegistry). Risolve
  "0 edges" su siti come Ravenna dove tutte le 1085+ relazioni stanno nella
  tabella relationships e `rapporti` è vuoto.
- Auto-fix sequence PostgreSQL al startup esteso a `periodizzazione_table`,
  `period_table`, `us_relationships_table`, `harris_matrix_table`. Risolve
  l'HTTP 500 "UniqueViolation periodizzazione_table_pkey" che bloccava il
  Save Swimlane e di conseguenza l'export GraphML (il file scaricato era
  vuoto perché la transazione era rollbacked).

### Fixed (EN)
- Swimlane editor now reads edges from `us_relationships_table` too, not
  just `us_table.rapporti`. Fixes "0 edges" on sites where everything is
  in the dedicated relationships table.
- PostgreSQL sequence auto-sync extended to periodizzazione_table,
  period_table, us_relationships_table, harris_matrix_table. Fixes the
  HTTP 500 UniqueViolation that blocked Save Swimlane / GraphML export
  on Adarte.

## [2.4.6] - 2026-05-18

### Fixed (IT)
- Editor swimlane su DB SQLite locali tornava HTTP 500 "no such column:
  periodo" perché `period_table` era stata creata dal modello SQLAlchemy
  con lo schema legacy `period_name/phase_name/start_date/end_date`.
  Nuova migration `_2026_05_period_table_schema` aggiunge le colonne
  reali pyarchinit (`periodo`, `fase`, `datazione`, `descrizione`,
  `sito`) e backfilla `periodo ← period_name`, `fase ← phase_name`.
  Auto-applicata dal `migrate_all_tables()`.
- Modello SQLAlchemy `Period` aggiornato per dichiarare entrambi i set
  di colonne (legacy + reale), così `Base.metadata.create_all()` su DB
  nuovi parte già con lo schema corretto.

### Fixed (EN)
- Swimlane editor on local SQLite DBs returned HTTP 500 "no such column:
  periodo" because `period_table` was created with the legacy schema
  (`period_name/phase_name/...`). New `_2026_05_period_table_schema`
  migration adds the real pyarchinit columns (`periodo`, `fase`,
  `datazione`, `descrizione`, `sito`) and backfills them from legacy
  ones. Auto-applied by `migrate_all_tables()`.
- SQLAlchemy `Period` model now declares both legacy and real column
  sets, so freshly-created DBs start with the right shape.

## [2.4.5] - 2026-05-18

### Changed (IT)
- `/api/node-types` ora alimenta la sidebar del Harris Creator **direttamente
  da VocabProvider** (s3dgraphy JSON catalogues), abbandonando il vecchio
  YAML legacy. Conseguenza: i tipi USVs / USVn / USN / RSF / serSU /
  serUSD / serUSVn / serUSVs / TSU / UL / BR / SE / USD compaiono
  finalmente in sidebar. Aggiornare s3dgraphy aggiungerà automaticamente
  nuovi tipi all'editor.
- Colore e forma di ogni voce vengono presi da `visual_style.fill_color`
  e `visual_style.shape` di s3dgraphy (es. SF / VSF / RSF = octagon,
  USVs = parallelogram, USVn = hexagon, USD = roundrectangle, BR = diamond).

### Fixed (IT)
- Pannello Properties ora si popola correttamente al click di un nodo US:
  `SwimlaneState.load` aggiunge `us_number`, `description` (da
  `d_stratigrafica`), `area`, `datazione`, `file_path` ai `data` Cytoscape
  che il pannello legge.
- Ai US viene allegato anche `shape` / `border_color` / `border_style` da
  VocabProvider — i nodi rendono con la simbologia EM appropriata, non più
  rettangoli grigi.

### Added (IT)
- Toggle Hide/Show del pannello Properties (icona angle-double in alto a
  destra del pannello): collassa a 36px e la scelta viene persistita in
  `localStorage`. Cytoscape viene `fit()` dopo l'animazione per riempire
  lo spazio guadagnato.

### Changed (EN)
- `/api/node-types` is now sourced from VocabProvider (s3dgraphy JSON
  catalogues). Bumping s3dgraphy is enough to surface new types in the
  sidebar.
- US nodes pick `shape`/`fill_color`/`border_color`/`border_style` from
  the s3dgraphy `visual_style` block so EM symbology renders correctly.

### Fixed (EN)
- Properties panel populates again on node click — `SwimlaneState.load`
  now attaches `us_number` / `description` / `area` / `datazione` /
  `file_path` to the Cytoscape `data` payload.

### Added (EN)
- Properties panel Hide/Show toggle (collapses to a thin strip on the
  right). Choice persisted in `localStorage`; Cytoscape re-fits the
  viewport after the transition.

## [2.4.4] - 2026-05-18

### Fixed (IT)
- Nodi US dell'editor swimlane ora hanno `data.color` (risolto via
  `VocabProvider.get_visual_style().fill_color`). Stop ai warning Cytoscape
  "no mapping for property background-color with data field color".
- Edge stratigrafici deduplicati: `_build_edges` ora ignora le coppie
  doppie `(source, target, edge_name)` e tratta gli inversi `overlies` /
  `is_after` come la stessa relazione (un solo arco invece di due).
- Editor lancia un layout `dagre` dopo `cy.add()` + `cy.fit()`, così gli US
  si distribuiscono dentro le row e gli archi diventano visibili.

### Added (IT)
- Modelli SQLAlchemy `US`, `InventarioMateriali`, `Periodizzazione` ora
  definiscono la colonna `node_uuid = Column(String(36))`. Un DB nuovo
  creato via `Base.metadata.create_all()` nasce con la colonna corretta.
- `DatabaseMigrations.migrate_all_tables()` chiama automaticamente le 3
  migration di Spec 1 (`_2026_05_node_uuid_schema`, `_node_uuid_backfill`,
  `_vocab_alignment`) idempotentemente. Conseguenza: i DB esistenti
  (SQLite o PostgreSQL) vengono aggiornati al primo avvio del web —
  nessun bisogno di lanciare manualmente `pyarchinit-mini-migrate-vocab`.

### Fixed (EN)
- US nodes in the swimlane editor now carry `data.color`, resolved through
  `VocabProvider.get_visual_style().fill_color`. Eliminates Cytoscape
  warnings about missing color mapping.
- Stratigraphic edges deduplicated: `_build_edges` ignores duplicate
  `(source, target, edge_name)` triples and treats `overlies` / `is_after`
  inverse pairs as the same edge (one arrow, not two).
- Editor runs a `dagre` layout after `cy.add()` plus a `cy.fit()` so US
  children spread inside their swimlane row and edges become visible.

### Added (EN)
- SQLAlchemy models `US`, `InventarioMateriali`, `Periodizzazione` now
  declare `node_uuid = Column(String(36))`. New DBs created via
  `Base.metadata.create_all()` have the column from the start.
- `DatabaseMigrations.migrate_all_tables()` now invokes the 3 Spec 1
  migrations (`node_uuid_schema`, `node_uuid_backfill`, `vocab_alignment`)
  idempotently. Existing SQLite or PostgreSQL DBs get auto-upgraded on
  the first web startup — no need to run `pyarchinit-mini-migrate-vocab`
  by hand.

## [2.4.3] - 2026-05-18

### Fixed (IT)
- `RowProvider` e `PeriodSyncService` ora usano lo schema reale di pyarchinit
  per `period_table` (`periodo` / `fase` / `datazione` / `sito`) invece dello
  schema ipotetico Spec 3-bis (`period_name` / `phase_name` / `start_date` /
  `end_date`). Risolve l'HTTP 500 "la colonna 'period_name' non esiste"
  visto in produzione su PostgreSQL `pyarchinit_v2`.
- `period_table` viene ora filtrato per `sito` (con fallback a righe
  cross-site se `sito` IS NULL/''). `start_date` / `end_date` numerici non
  esistono in produzione: nella Row dataclass restano `None` e il sort è
  alfabetico per `(periodo, fase)`. Le date numeriche passate da `+ New
  Row` vengono serializzate nella colonna `datazione` come `start..end`.
- Fixture sintetica `sqlite_volterra_30us_with_periods.db` e i test
  associati (row_provider, period_sync, state_load, integration routes)
  rigenerati con lo schema reale.

### Fixed (EN)
- `RowProvider` and `PeriodSyncService` now use pyarchinit's real
  `period_table` schema (`periodo` / `fase` / `datazione` / `sito`).
  Fixes the HTTP 500 "column 'period_name' does not exist" against the
  production PostgreSQL DB.
- Numeric `start_date` / `end_date` are no longer expected as columns; the
  Row dataclass leaves them `None`, rows are sorted alphabetically by
  `(periodo, fase)`, and date inputs from the editor are serialized into
  the existing `datazione` text column as `start..end`.

## [2.4.2] - 2026-05-18

### Fixed (IT)
- `_get_session()` (Spec 3-bis endpoints) ora acquisisce la sessione DB in modo
  lazy via `get_db_session()` se nessun before_request hook ha pre-impostato
  `g.db_session`. Risolve l'errore HTTP 500 "g.db_session not set" che
  bloccava load / save / + Row / Export yEd su Adarte in 2.4.0-2.4.1.
- Aggiunto `teardown_request` sul blueprint che rilascia la sessione lazy
  alla fine della request.

### Fixed (EN)
- `_get_session()` now lazily opens a DB session via `get_db_session()` when no
  before_request hook has bound one to `g.db_session`. Fixes the HTTP 500
  "g.db_session not set" that broke load / save / + Row / Export on production
  in 2.4.0-2.4.1.
- Added `teardown_request` hook releasing the lazy session at request end.

## [2.4.1] - 2026-05-18

### Fixed (IT)
- Editor Harris Matrix: `window._currentSite` ora inizializzato server-side
  dall'hidden input `#site-name`, quindi i pulsanti Save / + New Row /
  Export yEd GraphML funzionano anche se `/api/load/<site>` fallisce (caso
  tipico: migration `node_uuid` non ancora applicata sul DB di produzione).
- Editor Harris Matrix: se `/api/load/<site>` ritorna errore, il corpo
  della risposta viene mostrato in un alert con suggerimento di lanciare
  `pyarchinit-mini-migrate-vocab --apply` (prima era silenzioso).
- Editor Harris Matrix: messaggio "No site loaded" sostituito con
  istruzione esplicita di tornare all'indice del Creator.

### Added (IT)
- Nuova pagina `/paradata/` (sezione Tools): picker sito + bottoni rapidi
  ai 5 tipi di paradata (authors, licenses, embargoes, documents, epochs).
  Link aggiunto sia al dropdown navbar che alla sidebar laterale.
- Modal di aiuto nell'editor Harris (icona "?") che spiega la differenza
  tra GraphML (s3dgraphy clean, auto-regen, per Datacenter/3D), Export
  yEd GraphML (TableNode swimlane, on-demand, per yEd Desktop), DOT
  (Graphviz), PNG (snapshot raster).
- Tooltip migliorati su tutti i pulsanti di export.

### Fixed (EN)
- Harris Matrix Editor: `window._currentSite` is now initialised server-side
  from hidden input `#site-name`, so Save / + New Row / Export buttons work
  even when `/api/load/<site>` fails (typical when the `node_uuid` migration
  is still pending on production).
- Harris Matrix Editor: failed swimlane loads now surface the backend error
  body in an alert with a hint to run `pyarchinit-mini-migrate-vocab`.

### Added (EN)
- New `/paradata/` landing page (Tools section): site picker + quick links
  to the 5 paradata kinds. Sidebar entries added.
- Help modal explaining the four export formats (GraphML, yEd GraphML,
  DOT, PNG) accessible via a question-mark icon on the editor toolbar.

## [2.4.0] - 2026-05-18

### Added (IT)
- Modulo `pyarchinit_mini/harris_swimlane/` (5 moduli: row_provider,
  swimlane_state, period_sync_service, compound_layout, exceptions) per
  l'editor swimlane di Harris Matrix.
- `pyarchinit_mini/graphml_io/yed_writer.py` — nuovo emitter
  yEd-flavored con `y:TableNode + y:Rows + y:ShapeNode`, separato
  dall'export s3dgraphy clean di Spec 2.
- 5 nuove route REST per il Harris Creator:
  `GET/POST /api/swimlanes/<site>`, `GET /api/load/<site>`,
  `POST /api/save/<site>`, `GET /api/export/<site>/yed-graphml`.
- Editor `/harris-creator/editor` ora carica swimlane automaticamente
  (row da `period_table` priorità → fallback distinct values), supporta
  drag-drop tra row, creazione interattiva di nuove row, save esplicito
  con auto-regen (Spec 2) post-commit.
- Export yEd GraphML on-demand → `data/exports/harris_yed/<slug>-harris-yed.graphml`.

### Added (EN)
- New `pyarchinit_mini/harris_swimlane/` package — backend for Harris
  Matrix swimlane editing.
- New `pyarchinit_mini/graphml_io/yed_writer.py` — yEd-flavored GraphML
  emitter (TableNode + Rows + ShapeNode), separate from Spec 2's
  s3dgraphy delegate.
- 5 new REST endpoints under `/harris-creator/api/`.
- Editor loads swimlanes auto from `period_table` (fallback distinct);
  drag-drop between rows; interactive row creation; explicit Save with
  Spec 2 auto-regen. On-demand yEd export.

### Changed
- `harris_creator_routes.py` extended additively — existing routes
  unchanged.
- `editor.html` extended additively — Cytoscape compound nodes,
  swimlane parents, new toolbar buttons.

### Architecture note
Two GraphML outputs now coexist:
- `data/paradata/<slug>/stratigraphy.graphml` (Spec 2 auto-regen,
  s3dgraphy clean, EM-canonical)
- `data/exports/harris_yed/<slug>-harris-yed.graphml` (Spec 3-bis,
  on-demand, yEd-flavored with TableNode)

Legacy `pure_networkx_exporter` stays deprecated (was deprecated in
Spec 2 PR8). NOT resurrected.

### Dependencies
- No new dependencies.

### Spec / Plan
- Spec: `docs/superpowers/specs/2026-05-18-harris-swimlane-template-design.md`
- Plan: `docs/superpowers/plans/2026-05-18-harris-swimlane-template.md`
- Spec 3-bis (auxiliary): independent of Spec 3 (SyncEngine + EM
  Datacenter, on hold pending Datacenter readiness).

## [2.3.0-alpha] - 2026-05-18

### Added (IT)
- Modulo `pyarchinit_mini/graphproj/` con `GraphProjector` (DB → s3dgraphy.Graph),
  `ParadataStore` (storage per-sito su filesystem), `GraphIngestor` (preview/apply
  bidirezionale con staleness check), `auto_regen` (hook post-commit), edge_registry,
  filesystem helpers.
- Modulo `pyarchinit_mini/graphml_io/` con writer/reader delegati a
  `s3dgraphy.exporter.graphml.GraphMLExporter` / `s3dgraphy.importer.import_graphml.GraphMLImporter`.
- Auto-regen di `data/paradata/<site_slug>/stratigraphy.graphml` su ogni save US/USM
  (best-effort, errori isolati). Disabilitabile con `PYARCHINIT_DISABLE_AUTO_REGEN=1`
  o col context manager `auto_regen.disable_regen()`.
- 5 pagine HTML CRUD per paradata (authors, licenses, embargoes, documents, epochs)
  con form Bootstrap.
- REST API completa `/api/v1/paradata/<site>/{authors,licenses,embargoes,documents,epochs}`.
- Route web `/sites/<site>/graph/{view,download,import-preview,import-apply}` con
  preview 2-fasi obbligatorio per l'import GraphML + snapshot staleness check.

### Changed
- `pyarchinit_mini/graphml_converter/{graphml_builder, graphml_exporter,
  pure_networkx_exporter, converter}.py` marcati deprecati (emettono
  `DeprecationWarning` all'import). Verranno rimossi in Spec 3.
- `harris_creator_routes.py` refactored: il branch `graphml` ora usa
  `GraphProjector.populate_graph()` + `graphml_io.writer.write_graphml()`
  invece di passare attraverso `HarrisMatrixGenerator.export_to_graphml()` /
  `GraphMLBuilder`.
- Edge canonical names allineati a s3dgraphy 0.1.42: `covers` → `overlies`,
  `leans_against` → `abuts`. Fix del bug latente Spec 1 in
  `vocab_{en,it}.json` e `s3d_converter._LEGACY_CODE_MAP`.

### Architecture note (paradata storage)
s3dgraphy 0.1.42's GraphML exporter does not round-trip standalone paradata
nodes (AuthorNode, etc.) — they're only serialised when wrapped in
ParadataNodeGroup. Spec 2 therefore adopted a **JSON sidecar pattern**:
paradata entities live in `data/paradata/<site_slug>/paradata.json`
(committed to git), while the auto-regenerated `stratigraphy.graphml` is
purely the stratigraphic projection. Paradata are exposed via REST/UI but
not embedded in the GraphML output.

### Added (EN)
- New `pyarchinit_mini/graphproj/` package: GraphProjector, ParadataStore,
  GraphIngestor (2-phase preview/apply), auto_regen post-commit hook,
  edge_registry, filesystem helpers.
- New `pyarchinit_mini/graphml_io/` package delegating to s3dgraphy.
- Auto-regen of stratigraphy.graphml on US/USM save, error-isolated.
- 5 paradata CRUD HTML pages + REST API.
- Graph routes: view, download, import-preview, import-apply with snapshot
  staleness check (409 on stale).
- Deprecation warnings on 4 legacy writers.

### Dependencies
- No new dependencies. Uses s3dgraphy 0.1.42 (bumped in 2.2.0-alpha).

### Spec / Plan
- Spec: `docs/superpowers/specs/2026-05-17-spec-2-local-graph-paradata-design.md`
- Plan: `docs/superpowers/plans/2026-05-17-spec-2-local-graph-paradata.md`
- Spec 2 of 4 for the s3dgraphy bidirectional bridge work.

## [2.2.0-alpha] - 2026-05-17

### Added (IT)
- Modulo `pyarchinit_mini/vocab/` con `VocabProvider` singleton: legge i tre pillar JSON di s3dgraphy
  (`s3Dgraphy_node_datamodel.json`, `s3Dgraphy_connections_datamodel.json`, `em_visual_rules.json`)
  come fonte canonica per tipi di unità, tipi di relazione, e stili visivi.
- Endpoint REST `/api/v1/vocab/{unit-types, edge-types, visual-style, diagnostics}` per popolare
  select e form lato web.
- CLI `pyarchinit-mini-migrate-vocab` per allineare il vocabolario legacy
  (`USVA`/`USVB` → `USVs`, `USVC` → `USVn`) e fare il backfill della colonna `node_uuid` (UUID v7)
  su `us_table`, `inventario_materiali_table`, `periodizzazione_table`.
- Colonna `node_uuid` (prerequisito per il sync futuro col Datacenter EM).
- Catalogo i18n custom (`pyarchinit_mini/vocab/translations/vocab_{en,it}.json`) con
  `edge_type_aliases` per il parsing dei `rapporti` italiani.

### Added (EN)
- New `pyarchinit_mini/vocab/` package with `VocabProvider` singleton reading three s3dgraphy
  JSON pillars as canonical source of unit types, edge types, and visual styles.
- REST endpoints `/api/v1/vocab/{unit-types, edge-types, visual-style, diagnostics}` to populate
  forms in the web UI.
- CLI `pyarchinit-mini-migrate-vocab` to align legacy vocabulary (`USVA`/`USVB` → `USVs`,
  `USVC` → `USVn`) and backfill `node_uuid` (UUID v7) across `us_table`,
  `inventario_materiali_table`, `periodizzazione_table`.
- `node_uuid` column (prerequisite for future EM Datacenter sync).
- Custom i18n catalogue with `edge_type_aliases` for parsing Italian `rapporti` strings.

### Changed
- `graphml_converter/em_palette.py` reads visual styles from `VocabProvider` instead of the
  hardcoded `PALETTE` dict (kept as deprecated shim emitting `DeprecationWarning` on access).
- `s3d_integration/s3d_converter.py` parses `rapporti` text and categorizes node families via
  `VocabProvider` (`italian_aliases`, `family`, `class_name`) instead of hardcoded if/elif chains.
- Harris Matrix Creator now consumes `VocabProvider` visual styles end-to-end.

### Migration required
- After upgrading, run `pyarchinit-mini-migrate-vocab --dry-run` to preview, then
  `--apply` to migrate (auto-backup under `data/backups/`).
- See `docs/CLI_MIGRATE_VOCAB.md` for full reference.

### Dependencies
- `s3dgraphy>=0.1.42` (was 0.1.15).
- New: `uuid7>=0.1.0` (importable as `uuid_extensions`).
- Dev: `freezegun>=1.5.0`.

### Spec / Plan
- Spec: `docs/superpowers/specs/2026-05-16-s3dgraphy-web-foundation-design.md`
- Plan: `docs/superpowers/plans/2026-05-16-s3dgraphy-web-foundation.md`
- This is Spec 1 of 4 for porting the s3dgraphy bidirectional bridge from the QGIS plugin.

## [2.1.6] - 2026-02-25

### Fixed
- USValidator: us field validated as positive integer instead of string
  Root cause: validators.py still had old check 
  even though us_table.us is VARCHAR(100) since v2.0.2
  Fix: accept str or int, convert to str, validate max length 100
  Error shown: "US number must be a positive integer" on New SU form

## [2.1.5] - 2026-02-24

### Added
- Comprehensive in-app documentation/tutorial page at `/docs`
  - Full Italian documentation covering all 15 sections of the app
  - Sticky TOC sidebar with search, scrollable content area
  - Troubleshooting accordions with version badges
  - Fully consistent with dark/light theme system

## [2.1.4] - 2026-02-24

### Fixed
- Harris Matrix: removed broken cytoscape-elk CDN (was unused, dagre is used instead)
- Harris Matrix: /api/periods returned 500 because period_table lacked BaseModel columns
  Fixed: raw SQL query avoids ORM touching unmigrated columns; returns [] on any error
- Harris Matrix: loadPeriods() no longer blocks/alerts on failure (periods are optional)
- Migration: added ALL missing tables to concurrency columns migration
  (harris_matrix_table, period_table, datazioni_table, extended_matrix_table,
   pyarchinit_thesaurus_sigle, thesaurus_field, thesaurus_category)
  Migration auto-runs on startup — fixes OperationalError on any of these tables

## [2.1.3] - 2026-02-24

### Fixed
- Harris Matrix editor: canvas click not adding nodes/arcs on new matrices
  Root cause: #cy height was 0 in flexbox (height:100% without min-height:0 on parent)
  Fix: #cy now uses position:absolute to fill #cy-canvas + cy.resize() on requestAnimationFrame
- Added window resize handler so canvas auto-adjusts when sidebar toggles

## [2.1.2] - 2026-02-24

### Fixed
- `us_relationships_table` missing from concurrency columns migration: caused
  `OperationalError: no such column: entity_uuid` when opening Harris Matrix editor
  on existing databases. Migration now auto-runs on startup.

## [2.1.1] - 2026-02-24

### Fixed
- Added missing MCP server tool files: `create_harris_matrix_tool.py` and `create_database_tool.py`
  that caused `ModuleNotFoundError` on startup (pre-existing bug, never committed to repo)
- `pyarchinit-mini-web` now starts correctly without ImportError from mcp_server

## [2.1.0] - 2026-02-24

### Added
- **Modern UI Design System**: Comprehensive CSS design system with CSS custom properties for consistent theming across all pages
- **Dark/Light Theme Toggle**: One-click theme switching with localStorage persistence, earth-tone palettes (terracotta/sand/olive for light; deep navy/charcoal/warm amber for dark)
- **Collapsible Sidebar Navigation**: Slide-out sidebar with section grouping, active link highlighting, and mobile overlay mode
- **Redesigned Top Navbar**: Clean icon-based navigation with theme toggle, quick-nav dropdown, and user menu
- **Harris Matrix: Edge Style Differentiation**: Dashed red lines for negative relations (cuts, abuts), thick blue lines for contemporary relations (same as, bonds with), solid lines for normal stratigraphic relations
- **Harris Matrix: Export PNG**: One-click PNG export of the Harris Matrix canvas at 2x resolution
- **Harris Matrix: Node Tooltips**: Hover tooltips showing US number, type, description, area, and period
- **Harris Matrix: Dark Theme Canvas**: Graph canvas automatically adapts colors to match the selected UI theme

### Changed
- Redesigned dashboard with earth-tone gradient stat cards (terracotta, olive, clay, earth)
- All templates (dashboard, sites list/detail, US list) updated for design system consistency
- Harris Matrix editor panels and controls now theme-aware with CSS custom properties
- Improved mobile responsiveness with card-based layouts and touch-friendly targets
- Sites detail page labels internationalized (previously hardcoded Italian)

## [2.0.2] - 2026-02-24

### Fixed
- **PostgreSQL type mismatch on US creation**: `us_table.us` column was migrated from INTEGER to VARCHAR(100) but code was still passing integer values, causing `psycopg2.errors.UndefinedFunction: operator does not exist: character varying = integer` on PostgreSQL databases
- Fixed `us_service._get_us_by_site_area_number`: always cast `us_number` to `str` in SQL params
- Fixed `us_service.create_us_dto`: cast `US.us == str(us_data['us'])` in ORM filter
- Fixed `web_interface/app.py`: `us` field kept as `str` instead of `int` in `us_data` dict (create and update flows)
- Fixed `web_interface/three_d_builder_routes.py`: `US.us == str(data['us'])` in all 3D builder filters
- Fixed `desktop_gui/dialogs.py`: validate US number as int but pass as str to DB layer
- Fixed `inventario_service.py`: cast `us_number` to str in all US existence checks
- Fixed `api/schemas.py`: `us` field changed from `int` to `str` (with backward-compatible validator accepting both)
- Fixed `mcp_server/graphml_parser.py`: safe int cast for Periodizzazione.us comparison (still INTEGER column)


# Changelog

All notable changes to PyArchInit-Mini will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.9.11] - 2025-11-02

### Added - CRUD + Validation Tools
- **Complete Data Management System**
  - Unified `manage_data` MCP tool with 6 operations
  - `get_schema`: Database schema inspector with constraints and sample values
  - `insert`: Create new archaeological records with full validation
  - `update`: Modify existing records by ID or filters
  - `delete`: Safe deletion with dry-run and cascade warnings
  - `upsert`: Intelligent conflict resolution (insert or update)
  - `validate_stratigraphy`: Stratigraphic relationship validator with auto-fix

- **Database Operations**
  - Field validation (required fields, data types, constraints)
  - Foreign key validation and referential integrity checks
  - Auto-increment field detection (SQLite and PostgreSQL)
  - Transaction safety with automatic rollback on errors
  - Partial updates (only modify specified fields)
  - Dry-run modes for all destructive operations

- **Stratigraphic Validation**
  - Paradox detection (contradictory relationships)
  - Cycle detection in Harris Matrix (temporal paradoxes)
  - Missing reciprocal relationship detection
  - Chronological consistency validation with periodization data
  - Auto-fix for missing reciprocals
  - Error categorization (paradoxes, cycles, chronology, other)
  - Re-validation after auto-fixes with improvement metrics
  - Support for Italian and English relationship types

- **Conflict Resolution (UPSERT)**
  - Detect duplicates by composite keys
  - 4 resolution strategies: detect, skip, update, upsert
  - 3 merge strategies: prefer_new, prefer_existing, replace_all
  - Atomic operations (no race conditions)
  - Intelligent data merging

- **Documentation**
  - `CRUD_TOOLS.md`: Comprehensive guide (500+ lines)
  - Complete API reference for all 6 operations
  - Best practices and error handling
  - Usage examples and common patterns
  - Architecture documentation
  - `MCP_TOOLS_REFERENCE.md`: Complete MCP tools reference (1465 lines, 41KB)
  - Documentation for all 14 MCP tools
  - Parameter specifications and return values
  - Usage examples for each tool
  - Best practices and troubleshooting
  - Tool categorization and quick reference table
  - Updated `docs/MCP_INTEGRATION.md` with links to tool reference

- **Testing**
  - `test_crud_tools.py`: Full test suite (330 lines)
  - 11 test operations covering all functionality
  - All tests passing (59 US validated, 0 errors)
  - Dry-run and actual execution tests
  - Foreign key and constraint validation tests

### Fixed
- **Database Connection**
  - Fixed DatabaseManager initialization in all CRUD tools
  - Proper DatabaseConnection object creation
  - Correct engine reference pattern

### Changed
- **MCP Server**
  - Updated from 13 to 14 MCP tools
  - Added `manage_data` to tool registry
  - Updated server documentation

## [1.9.10] - 2025-11-02

### Added - AI Integration & 3D Visualization
- **Model Context Protocol (MCP) Integration**
  - Complete MCP server implementation for AI assistants (Claude Desktop, ChatGPT)
  - 5 MCP tools: `build_3d`, `filter`, `export`, `position`, `material`
  - 5 MCP resources: GraphML, US data, periods, relationships, sites
  - 3 MCP prompts: Stratigraphic Model, Period Visualization, US Description
  - HTTP/SSE transport for ChatGPT integration
  - stdio transport for Claude Desktop integration
  - Zero-config setup with `uvx` package runner
  - Natural language interface to archaeological data

- **3D Viewer (Browser-Based)**
  - Interactive Three.js r150 WebGL viewer in browser
  - Real-time 3D visualization of stratigraphic units
  - Chat interface for natural language commands (Italian/English)
  - Auto-populate US from site selection
  - GraphML-based positioning with Harris Matrix relationships
  - Color-coding by period, type, or custom colors
  - OrbitControls for camera navigation (rotate, zoom, pan)
  - View presets: Top, Front, Side, Isometric
  - Object selection with metadata display
  - Support for 3 positioning modes: GraphML, Simple, Grid
  - Adjustable layer spacing for vertical positioning

- **Blender Integration**
  - Real-time streaming addon for Blender 3.0+ (Socket.IO WebSocket)
  - Automatic 3D geometry generation based on US type
  - Professional material application (earth, stone, brick textures)
  - Color assignment by archaeological period
  - Different geometry for each US type: layers, walls, cuts, fills
  - Real-time sync between Blender and web viewer
  - Export to multiple formats: .blend, .glb, .fbx, .obj
  - AI-powered reconstruction with specialized agents
  - 4 AI agents: Architect, Validator, Texturizer, Reconstructor
  - Prompt generator for Claude AI site reconstruction

- **Comprehensive Documentation**
  - `docs/MCP_INTEGRATION.md` - Complete MCP setup guide (644 lines)
  - `docs/3D_VIEWER_GUIDE.md` - Browser 3D viewer guide (646 lines)
  - `docs/BLENDER_INTEGRATION.md` - Blender addon guide (645 lines)
  - Step-by-step setup instructions for all platforms
  - Multiple usage examples with screenshots
  - Troubleshooting sections for common issues
  - Complete API reference for developers

### Changed
- **MCP Configuration**: Switched from direct Python path to `uvx` package runner
  - Simplified Claude Desktop setup (no need to find Python path)
  - Auto-install PyArchInit-Mini on first run
  - Cross-platform compatibility (macOS, Linux, Windows)
  - Added `uvx` installation instructions for all platforms

- **Documentation Structure**
  - Updated `docs/index.rst` with new AI Integration & 3D Visualization section
  - Added quick links to MCP, 3D Viewer, and Blender guides
  - Integrated new documentation into ReadTheDocs
  - Updated README.md with AI Integration and 3D Visualization sections

- **Web Interface Enhancements**
  - New `/3d-builder/` route for browser-based 3D viewer
  - Socket.IO integration for real-time Blender streaming
  - Auto-populate US endpoint: `GET /api/sites/<site_name>/us`
  - Chat command parser for natural language queries
  - MCP executor for tool invocation from web interface

### Technical Details

**Backend:**
- New MCP server: `pyarchinit_mini/mcp_server/`
  - `server.py` - stdio MCP server (Claude Desktop)
  - `http_server.py` - HTTP/SSE MCP server (ChatGPT)
  - `tools/` - 5 MCP tool implementations
  - `proxy_generator.py` - 3D proxy object generation
  - `graphml_parser.py` - GraphML positioning parser
- New services:
  - `command_parser.py` - Natural language command parsing
  - `mcp_executor.py` - MCP tool execution from web interface

**Frontend:**
- New templates:
  - `templates/3d_builder/index.html` - 3D viewer interface
  - `templates/blender_viewer.html` - Blender real-time viewer
- New JavaScript:
  - `static/js/three-d-viewer.js` - Three.js viewer logic
  - `static/js/three.min.js` - Three.js r150 library
  - `static/js/OrbitControls.js` - Camera controls
- Socket.IO client integration for WebSocket communication

**Blender Addon:**
- `blender_addons/pyarchinit_realtime_streamer.py` - Real-time streaming addon
  - TCP socket listener (port 9876)
  - WebSocket client (Socket.IO)
  - Geometry generation based on US data
  - Material and color management
  - Real-time sync with web viewer

**Entry Points:**
- `pyarchinit-mini-mcp` - MCP server entry point (for uvx)
- MCP server accessible via uvx without installation

### Files Modified
- `docs/index.rst` - Added new documentation sections
- `docs/conf.py` - Verified Markdown support
- `README.md` - Updated with new features and roadmap
- `pyarchinit_mini/web_interface/app.py` - 3D builder routes, Socket.IO
- `pyarchinit_mini/web_interface/socketio_events.py` - WebSocket handlers
- `pyarchinit_mini/web_interface/three_d_builder_routes.py` - 3D viewer routes

### Files Added
- `docs/MCP_INTEGRATION.md` - MCP setup guide
- `docs/3D_VIEWER_GUIDE.md` - 3D viewer user guide
- `docs/BLENDER_INTEGRATION.md` - Blender integration guide
- `pyarchinit_mini/mcp_server/__main__.py` - MCP server entry point
- `pyarchinit_mini/services/command_parser.py` - Command parser
- `pyarchinit_mini/services/mcp_executor.py` - MCP executor
- `blender_addons/pyarchinit_realtime_streamer.py` - Blender addon
- `scripts/generate_3d_with_claude.py` - AI prompt generator

### Impact
- **AI Integration**: Natural language interface to archaeological data via Claude Desktop and ChatGPT
- **3D Visualization**: Interactive browser-based 3D viewer for stratigraphic units
- **Professional 3D Modeling**: Real-time Blender integration with AI-powered reconstruction
- **Zero-Config Setup**: uvx eliminates manual Python configuration
- **Cross-Platform**: Works on macOS, Linux, Windows with consistent experience
- **Real-Time Collaboration**: WebSocket streaming enables team collaboration
- **Enhanced Documentation**: 1,900+ lines of new user guides and technical documentation

### Upgrading from 1.8.6
- Update to version 1.9.10: `pip install --upgrade pyarchinit-mini`
- Install uvx: `brew install uv` (macOS) or see MCP_INTEGRATION.md
- Configure Claude Desktop with uvx (see docs/MCP_INTEGRATION.md)
- Install Blender addon (optional, see docs/BLENDER_INTEGRATION.md)

## [1.8.6] - 2025-10-31

### Added
- **Comprehensive Database Migration Conflict Resolution System**
  - **Automatic Backup System**: Creates timestamped backups before migration
    - SQLite: File copy with timestamp
    - PostgreSQL: Uses `pg_dump` for SQL backup
    - Configurable via `auto_backup` parameter (default: True)

  - **Conflict Detection**: Analyzes source and target databases for ID conflicts
    - Automatic primary key detection per table (handles id_sito, id_us, id_invmat, etc.)
    - Identifies conflicting IDs (exist in both databases)
    - Identifies new records (only in source)
    - Returns detailed statistics per table

  - **Three Merge Strategies**:
    - **Skip** (default): Skips records with conflicting IDs, preserves target data
    - **Overwrite**: Updates existing records with source data
    - **Renumber**: Generates new sequential IDs for conflicts, preserves all data

  - **New API Endpoints**:
    - `POST /api/pyarchinit/preview-migration-conflicts` - Preview conflicts before migration
    - Updated `/api/pyarchinit/migrate-database` - Now supports `merge_strategy` and `auto_backup` parameters

  - **Comprehensive Documentation**: Added `docs/DATABASE_MIGRATION_CONFLICTS.md`
    - API usage examples
    - Python code examples
    - Best practices and troubleshooting
    - Complete test coverage documentation

  - **Complete UI Integration**:
    - Visual merge strategy selector with 3 card-based options (Skip, Overwrite, Renumber)
    - "Preview Conflicts" button with detailed analysis modal
    - Auto-backup checkbox (enabled by default)
    - Bootstrap modal showing:
      - Conflict summary statistics
      - Intelligent recommendations based on conflict count
      - Table-by-table analysis with conflicting IDs
      - Responsive table design
    - Backup information display in success messages
    - Enhanced migration form with all new parameters

### Changed
- `ImportExportService.migrate_database()` signature updated with new parameters:
  - `merge_strategy`: `'skip'`, `'overwrite'`, or `'renumber'` (default: `'skip'`)
  - `auto_backup`: Boolean to enable/disable automatic backups (default: `True`)
- `ImportExportService._migrate_table()` completely rewritten to support conflict resolution strategies
- Migration response now includes backup information (path, size, status)

### Improved
- Database migration now provides detailed conflict analysis before proceeding
- Migration success rate improved with automatic conflict handling
- Data safety enhanced with automatic pre-migration backups
- Better error handling and logging for migration operations
- User experience significantly enhanced with visual feedback and preview capabilities
- JavaScript code quality improved with DRY principle (eliminated duplication)

### Technical Details
**Backend:**
- Added `_create_backup()` static method (lines 1820-1953 in import_export_service.py)
- Added `_detect_conflicts()` static method (lines 1955-2082 in import_export_service.py)
- Updated `_migrate_table()` with conflict resolution logic (lines 2197-2381)
- New test files with 100% pass rate:
  - `test_backup_system.py` (3/3 tests passing)
  - `test_conflict_detection.py` (comprehensive scenarios)
  - `test_conflict_detection_simple.py` (real database testing, 3/3 passing)
  - `test_merge_strategies.py` (3/3 tests passing)

**Frontend:**
- Updated `admin/database.html` template (+315 lines, -20 lines)
- Added JavaScript helper functions:
  - `buildMigrationRequestData()` - builds request with all parameters
  - `addSourceDatabaseFields()` - validates and adds source DB configuration
  - `addTargetDatabaseFields()` - validates and adds target DB configuration
- Added conflict preview modal with Bootstrap 5
- Integrated conflict preview API endpoint
- Enhanced migration form with new merge strategy and backup options
- All UI features tested with integration tests

## [1.8.5] - 2025-10-31

### Added
- **Default Database in Saved Connections**: Default SQLite database now automatically appears in "Saved Connections" section
  - Added initialization code in `app.py` to save active default database to ConnectionManager during startup
  - Default database persists across server restarts and is visible in Admin → Database Management
  - Resolves issue where only uploaded databases appeared in saved connections

### Improved
- **Complete English Translation for Database Management**: Fully translated the Database Management page to English
  - Translated all Italian strings in `admin/database.html` template
  - Added 30+ new translations to `messages.po` for both Italian and English
  - Sections now translated:
    - Database statistics (Sites, Stratigraphic Units, Inventory)
    - Database operations (Upload, Connect, Info)
    - Data migration section (SQLite ↔ PostgreSQL)
    - Saved connections table headers and actions
    - Help section
  - English interface now fully functional for database administration

### Changed
- Database Management UI now uses Flask-Babel translation functions throughout
- Compiled translation files (.mo) updated with new strings

## [1.8.4] - 2025-10-31

### Fixed
- **Windows bcrypt Compatibility**: Fixed bcrypt version incompatibility on Windows
  - Changed from `passlib[bcrypt]>=1.7.4` to `passlib>=1.7.4` + `bcrypt>=4.0.0,<4.1.0`
  - Resolves: `AttributeError: module 'bcrypt' has no attribute 'about'`
  - Resolves: `ValueError: password cannot be longer than 72 bytes`
  - Ensures bcrypt 4.0.x is installed (compatible with passlib 1.7.4)
  - Updated in both `web` and `all` dependency groups

### Technical Details
- passlib 1.7.4 is not compatible with bcrypt 4.1.0+
- On Windows, `passlib[bcrypt]` was installing bcrypt 4.1.x or 4.2.x
- Explicit version constraint ensures compatible bcrypt version
- Improves Windows installation reliability

## [1.8.3] - 2025-10-31

### Fixed
- **Web Interface Dependencies**: Added authentication dependencies to `web` optional dependency group
  - Added `passlib[bcrypt]>=1.7.4` to web dependencies
  - Added `python-jose[cryptography]>=3.3.0` to web dependencies
  - Added `flask-login>=0.6.3` to web dependencies
  - Resolves: `ImportError: passlib is required for password hashing` when installing with `pip install pyarchinit-mini[web]`
  - Web interface now works correctly on Windows without requiring separate `pip install pyarchinit-mini[web,auth]`

### Changed
- Web interface installation is now self-contained with all required dependencies
- Users can install with just `pip install pyarchinit-mini[web]` and have full authentication support

### Technical Details
- Authentication libraries were previously only in `auth` and `all` dependency groups
- Web interface requires authentication for login, so these dependencies are now included in `web` group
- Improves user experience by reducing installation steps

## [1.8.2] - 2025-10-31

### Fixed
- **Italian Translation**: Corrected "Media Files" translation in dashboard from "ha modificato US" to "File Multimediali"
  - Fixed in `pyarchinit_mini/translations/it/LC_MESSAGES/messages.po` line 934
  - Compiled updated translation files (.mo)

- **Windows Installation**: Fixed passlib dependency error on Windows
  - Changed from separate `passlib>=1.7.4` + `bcrypt>=4.0.0,<4.1.0` to unified `passlib[bcrypt]>=1.7.4`
  - Updated in both `auth` and `all` dependency groups in `pyproject.toml`
  - Resolves: "Error creating admin user: passlib is required for password hashing. Install with: pip install 'passlib[bcrypt]'"
  - Ensures bcrypt backend is properly installed on all platforms, especially Windows

### Technical Details
- Translation files properly compiled with pybabel
- Dependencies now correctly specify bcrypt as a passlib extra
- Improves cross-platform compatibility (macOS, Linux, Windows)

## [1.8.1] - 2025-10-30

### Fixed - Database Migration Hotfix
- **Critical Bug**: Fixed missing `tipo_documento` and `file_path` columns in existing databases
  - Root cause: `DatabaseMigrations.migrate_all_tables()` was not calling the tipo_documento migration
  - Added `migrate_tipo_documento()` method to `pyarchinit_mini/database/migrations.py`
  - Updated `migrate_all_tables()` to include tipo_documento migration
  - Ensures compatibility with databases created before version 1.8.0
  - Users upgrading from versions prior to 1.8.0 will now have columns added automatically
  - Resolves `sqlite3.OperationalError: no such column: us_table.tipo_documento` error

### Technical Details
- Migration script `add_tipo_documento.py` existed but was not being executed
- Adds two columns to `us_table`:
  - `tipo_documento` VARCHAR(100) - Document type classification
  - `file_path` TEXT - Path to associated document files
- Migration uses safe `add_column_if_not_exists()` method to prevent duplicate column errors

## [1.8.0] - 2025-10-30

### Added - Enhanced Media Management System
- **Image Viewer**: GLightbox 3.2.0 integration with gallery support
  - Separate galleries per entity type (sites, US, inventario)
  - Lightbox navigation with touch support
  - Thumbnail generation and preview
- **PDF Viewer**: In-browser PDF viewing with GLightbox iframe support
- **Video Viewer**: Native HTML5 video playback with GLightbox
  - Support for 10 video formats: MP4, AVI, MOV, WMV, FLV, WebM, MKV, M4V, MPEG, MPG
  - Fullscreen playback and controls
- **Excel/CSV Viewer**: pandas-powered spreadsheet viewer
  - Bootstrap-styled HTML tables
  - Supports up to 1000 rows
  - Preserves formatting and data types
- **DOCX Viewer**: python-docx HTML converter
  - Table support with Bootstrap styling
  - Heading detection and conversion
  - Opens in new window for better screen space
- **3D Model Viewer**: Interactive Three.js r147 viewer
  - OrbitControls for navigation (rotate, pan, zoom)
  - Support for 6 formats: OBJ, STL, PLY, GLTF, GLB, DAE
  - Wireframe toggle and reset view features
  - Opens in new window for immersive experience
- **Media Deletion**: Delete functionality across all interfaces
  - Available in media list view
  - Available in all entity forms (sites, US, inventario)
  - JavaScript confirmation before deletion
  - Smart redirect logic (returns to form if deleted from edit page)
  - CSRF protection on all delete operations

### Changed
- **Video Detection**: Enhanced file type recognition by extension
  - Improved detection for 10 video formats in `MediaHandler._determine_media_type()`
  - More reliable than MIME-type based detection
- **Media Organization**: Automatic file organization by entity type and ID
  - Separate galleries prevent cross-entity media mixing
  - Consistent viewer interface across all entity forms
- **Dependencies**: Added media viewing libraries
  - `python-docx>=1.0.0` for DOCX viewing
  - `pandas>=2.0.0` for Excel/CSV parsing (already in export dependencies)
  - `openpyxl>=3.1.0` for Excel file support
  - GLightbox 3.2.0 loaded from CDN for image/PDF/video lightbox
  - Three.js r147 loaded from CDN for 3D model rendering

### Technical Details
- Complex viewers (DOCX, Excel, 3D) open in new window (`target="_blank"`)
- Simple viewers (images, PDF, video) use lightbox for quick preview
- Three.js r147 used for stable 3D loader compatibility (last version with legacy `/examples/js/` structure)
- Removed unsupported formats: FBX and 3DS (loaders not available in Three.js r147)

## [1.7.13] - 2025-10-29

### Changed
- **Version Management**: Unified version display across all interfaces
  - Web Interface: Dashboard and login now show dynamic version from `__version__`
  - CLI: `--version` flag now shows dynamic version from `__version__`
  - Desktop GUI: Now imports version from main package instead of hardcoded
  - API: Already using dynamic version (no changes needed)
  - All interfaces now consistently display version 1.7.13

### Fixed
- Removed hardcoded version strings from templates and interface files
- Web dashboard was showing v1.5.5 (now shows v1.7.13)
- Web login was showing v1.0.7 (now shows v1.7.13)
- CLI was showing v0.1.0 (now shows v1.7.13)
- Desktop GUI was using v0.1.0 (now shows v1.7.13)

## [1.7.12] - 2025-10-29

### Fixed - CRITICAL
- **Desktop GUI**: Synchronized all files with actively developed version
  - Added missing `assets/` folder with GUI assets
  - Updated `__init__.py`, `graphml_export_dialog.py`, `i18n.py`
  - Updated `media_manager_advanced.py`, `us_dialog_extended.py`
  - All Desktop GUI features now match latest development version

### Impact
- Desktop GUI was missing critical files (assets folder and 5+ Python files)
- Systematic comparison revealed archive_local contained most complete versions
- All interface directories (Web, CLI, Desktop GUI) now fully synchronized
- Package now contains complete, up-to-date code for all interfaces

## [1.7.10] - 2025-10-29

### Fixed - CRITICAL
- **All Interfaces**: Synchronized all interface code with actively developed versions
  - **Web Interface**: Fixed import statements in all route files
    - Fixed `em_node_config_routes.py` imports to use package-qualified paths
    - Fixed `excel_import_routes.py`, `harris_creator_routes.py`, `pyarchinit_import_export_routes.py`
    - Removed all `sys.path.append('..')` statements
    - All imports now use full package paths: `from pyarchinit_mini.web_interface.* import`
  - **Desktop GUI**: Updated to latest version from external development
    - Copied `main_window.py`, `gui_app.py`, `excel_import_dialog.py`, `pyarchinit_import_export_dialog.py`
    - Fixed import statements for package compatibility
    - Added missing PyArchInit import/export dialog and Excel import dialog features
  - **CLI Interface**: Synchronized with external development version
    - Ensured all features are up to date
  - **Web Interface app.py**: Copied and updated from external development version
    - Added `__version__` import and injection in context processor
    - All template contexts now have access to current version number

### Impact - CRITICAL FIX
- Version 1.7.9 had import errors preventing web server from starting
- This release fixes all import issues and ensures all interfaces work correctly
- All interfaces now use the actively developed code from external directories
- Package structure is now correctly configured for pip installation

### Technical Details
- The external development directories (`archive_local/web_interface`, `archive_local/desktop_gui`, `archive_local/cli_interface`) contained the most up-to-date code
- Previous versions were mistakenly using older code from the package directory
- This release properly synchronizes all package code with external development versions
- Import statements have been corrected to work within the installed package context

## [1.7.9] - 2025-10-29

### Fixed - CRITICAL
- **Web Interface**: Restored missing features from external development version
  - **RESTORED 4 Missing Route Files**:
    - `pyarchinit_import_export_routes.py` - PyArchInit legacy format import/export
    - `harris_creator_routes.py` - Interactive Harris Matrix creator interface
    - `excel_import_routes.py` - Excel batch import functionality
    - `em_node_config_routes.py` - Extended Matrix node configuration
  - **Enhanced US Form** with additional fields:
    - `tipo_documento` field with file type selection
    - `documento_file` field for file upload
    - Extended `unita_tipo` choices (VSF, SF, CON, USD, USVA, USVB, USVC, DOC, TU, property, Combiner, Extractor)
    - Changed `us` field from IntegerField to StringField for alphanumeric support
  - **Additional Service Imports**:
    - `RelationshipSyncService` for stratigraphic relationship management
    - `DatazioneService` for chronological data handling

### Impact - CRITICAL FIX
- Version 1.7.8 was published with incomplete web_interface code
- This release restores all missing functionality that was in active development
- Users upgrading from 1.7.7 or earlier now get the complete feature set
- Fixes missing routes that would cause 404 errors for PyArchInit import, Harris Creator, Excel Import

### Note
- The external `/web_interface` directory contained the actively developed code
- Version 1.7.8 mistakenly used the older package version
- This release properly integrates the external development code into the package

## [1.7.8] - 2025-10-29

### Fixed
- **Version Consistency Across All Interfaces**: Unified version display across all interfaces
  - **API**: Now uses `__version__` from main package instead of hardcoded "0.1.0"
  - **CLI**: Updated version display from hardcoded "v1.2.12" to dynamic `v{__version__}`
  - **Desktop GUI**: Now imports and uses `__version__` from main package
  - **Web Interface**: Already using dynamic version (from 1.7.7)
  - All interfaces now display correct synchronized version number

### Changed
- **Repository Cleanup**: Removed duplicate development directories
  - Moved old package versions (1.2.14, 1.4.0, 1.6.1) to `archive_local/`
  - Removed duplicate `web_interface/`, `cli_interface/`, `desktop_gui/` directories
  - Removed test directories: `test_data/`, `test_graphml/`, `examples/`
  - Updated `.gitignore` to exclude archived and development files

### Added
- **Documentation**: Added comprehensive tutorial documentation
  - Installation tutorial with step-by-step setup guide
  - Web interface tutorial with screenshots
  - Desktop GUI tutorial
  - Tutorial index page in ReadTheDocs

### Impact
- All interfaces (API, CLI, Desktop GUI, Web) now display version 1.7.8
- Cleaner repository structure with only necessary files
- Better documentation for new users
- Reduced package confusion from duplicate directories

## [1.7.7] - 2025-10-29

### Fixed
- **Database Schema i18n**: Added missing internationalization columns to sample databases
  - **Site table**: Added `definizione_sito_en`, `descrizione_en` (2 columns)
  - **US table**: Added 15 i18n/document columns (`d_stratigrafica_en`, `d_interpretativa_en`, `descrizione_en`, `interpretazione_en`, `formazione_en`, `stato_di_conservazione_en`, `colore_en`, `consistenza_en`, `struttura_en`, `inclusi_en`, `campioni_en`, `documentazione_en`, `osservazioni_en`, `tipo_documento`, `file_path`)
  - **Inventario table**: Added 9 i18n columns (`tipo_reperto_en`, `criterio_schedatura_en`, `definizione_en`, `descrizione_en`, `stato_conservazione_en`, `elementi_reperto_en`, `corpo_ceramico_en`, `rivestimento_en`, `tipo_contenitore_en`)
  - Fixed all `OperationalError: no such column` errors on dashboard load
  - All sample databases now have complete schema with full i18n support

### Impact
- Dashboard loads correctly without SQL errors
- All main tables (Sites, US, Inventory) support bilingual content
- Full bilingual (IT/EN) support now functional in web interface
- Resolves issues for users in multilingual archaeological projects
- Total: 26 new columns added across all sample databases

## [1.7.6] - 2025-10-29

### Fixed
- **Sample Databases Authentication**: Added admin user to all sample databases
  - Created `users` table in `pyarchinit_mini.db`
  - Created `users` table in `pyarchinit_mini_sample.db`
  - All databases now include admin user (username: `admin`, password: `admin`)
  - Users can now log in to web interface without manual database setup

### Impact
- Fresh installs can immediately access web interface with admin credentials
- No need to manually create admin user after installation

## [1.7.5] - 2025-10-29

### Fixed
- **Critical Code Restoration**: Restored complete 1.7.0 code base with all features
  - Version 1.7.4 published with incomplete code (missing database_creator, harris features)
  - Restored from git commit 5a3fbf0 which contains all 1.7.0 features
  - All features now present: database creation, harris matrix, networks, extended matrix
- **Version String Alignment**: Corrected `__version__` in `__init__.py` to match package version
  - All version identifiers now consistently report correct version
  - Login template now dynamically displays version from `__version__`

### Added
- **Dynamic Version Display**: Login template now uses `{{ version }}` variable
  - Added `__version__` import in web interface app.py
  - Modified context_processor to inject version into all templates
  - No more hardcoded version strings in templates

### Documentation
- Interactive Tutorials with Screenshots remain from 1.7.4
- Tutorial database and screenshot automation tools available

## [1.7.4] - 2025-10-29

⚠️ **This version was published with incomplete code. Use 1.7.5 instead.**

### Issues
- Published with code from version 1.7.2 instead of 1.7.0
- Missing: database_creator, enhanced harris matrix features, network exporters

## [1.7.3] - 2025-10-29

### Added
- **ReadTheDocs Multiple Formats**: Enabled PDF, EPUB, and HTMLZip generation on ReadTheDocs
  - PDF output with optimized LaTeX configuration
  - EPUB output with metadata and cover image
  - HTMLZip for offline documentation access
  - Updated `.readthedocs.yaml` to enable all formats
  - Added EPUB configuration in `docs/conf.py`

### Documentation
- Documentation now available in 4 formats on ReadTheDocs:
  - HTML (online reading)
  - PDF (printable/offline)
  - EPUB (e-readers)
  - HTMLZip (offline archive)

## [1.7.2] - 2025-10-29

### Changed
- **Documentation: GraphML Export Clarification** - Complete rewrite of technical documentation
  - Clarified that **Pure NetworkX is the DEFAULT export method** (no Graphviz required)
  - Graphviz is now correctly documented as **OPTIONAL** (only for DOT file generation)
  - Added clear comparison table between Pure NetworkX vs Graphviz export methods
  - Updated all code examples to show both export approaches
  - Removed misleading statements that suggested Graphviz was required
  - Added troubleshooting section for both export methods
  - Updated README.md to reflect that Graphviz is optional
  - Technical guide now at: `docs/features/graphml-export-technical.rst`

### Documentation Improvements
- Restructured GraphML export documentation for clarity
- Added "When to Use" sections for each export method
- Improved CLI and API usage examples
- Added comprehensive comparison table
- Enhanced troubleshooting guide with clear solutions

## [1.7.1] - 2025-10-29

### Changed
- **Documentation Links**: Updated all README documentation links to point to ReadTheDocs
  - Excel Import Guide → https://pyarchinit-mini.readthedocs.io/en/latest/features/harris_matrix_import.html
  - Extended Matrix Export → https://pyarchinit-mini.readthedocs.io/en/latest/features/graphml-export-technical.html
  - DOC File Upload → https://pyarchinit-mini.readthedocs.io/en/latest/features/media_management.html
  - EM Node Type Management → https://pyarchinit-mini.readthedocs.io/en/latest/features/extended-matrix-framework.html
  - CHANGELOG → https://pyarchinit-mini.readthedocs.io/en/latest/development/changelog.html
  - Quick Start → https://pyarchinit-mini.readthedocs.io/en/latest/installation/quickstart.html
  - Contributing Guide → https://pyarchinit-mini.readthedocs.io/en/latest/development/contributing.html
- Removed broken links to non-existent documentation files
- Improved documentation accessibility for PyPI users

### Fixed
- Removed invalid documentation file references
- Updated documentation section with centralized ReadTheDocs links

## [1.6.1] - 2025-10-28

### Added
- **Excel Import Web GUI**: Complete integration with dual format support
  - Harris Matrix Template format (sheet-based: NODES + RELATIONSHIPS)
  - Extended Matrix Parser format (inline with relationship columns)
  - Radio button format selection
  - Site name validation
  - Optional GraphML generation
  - Success/error messages with statistics
- **Documentation**: Comprehensive Excel import guide (500+ lines)
  - `docs/EXCEL_IMPORT_GUIDE.md` - User guide
  - `docs/EXCEL_IMPORT_BUG_FIXES.md` - Technical bug fixes
  - `docs/EXCEL_IMPORT_INTEGRATION_SUMMARY.md` - Session summary
- **Italian Relationships**: Full support for lowercase Italian relationship names
- **Database Consistency**: Unified database path across Web GUI, Desktop GUI, and CLI

### Fixed
- **CRITICAL: Database Schema**: Fixed `id_us` field type from `VARCHAR(100)` to `INTEGER AUTOINCREMENT`
  - Old databases created with v1.6.0 or earlier may have incorrect schema
  - Migration instructions provided in documentation
- **Date Type Handling**: Fixed SQLite date field type errors (None instead of .isoformat())
- **Desktop GUI**: Updated to use consistent database connection via `db_manager.connection`
- **Italian Relationships**: Added lowercase variants ("anteriore a", "copre", "coperto da", etc.)

### Changed
- **Web GUI Routes**: Registered `excel_import_bp` blueprint with CSRF exemption
- **Desktop GUI**: Modified `excel_import_dialog.py` to pass `db_connection` parameter

### Testing
- ✅ Harris Template: 20 US + 24 relationships imported successfully
- ✅ Extended Matrix: 5 US + 6 relationships imported successfully
- ✅ Metro C Real Data: 65 US + 658 relationships imported successfully
- ✅ All data visible immediately in all interfaces

### Migration Note
**IMPORTANT**: Users upgrading from v1.6.0 or earlier must recreate or migrate their database due to schema changes. See `docs/EXCEL_IMPORT_BUG_FIXES.md` for detailed migration instructions.

### Files Modified
- `web_interface/excel_import_routes.py` - New file
- `web_interface/templates/excel_import/index.html` - New file
- `web_interface/app.py` - Blueprint registration
- `web_interface/templates/base.html` - Menu link
- `desktop_gui/excel_import_dialog.py` - Database consistency fix
- `pyarchinit_mini/services/extended_matrix_excel_parser.py` - Bug fixes
- `pyarchinit_mini/cli/harris_import.py` - Bug fixes
- `README.md` - Feature documentation
- `docs/index.rst` - What's New section
- `pyproject.toml` - Version 1.6.1
- `docs/conf.py` - Version 1.6.1

---

## [1.5.8] - 2025-10-27
## [1.5.9] - 2025-10-27

### Fixed
- **Italian Translation**: Corrected "Errore export PDF" → "Esporta PDF" for Export PDF button
- **English Translations**: Added missing translations for Configuration menu and Thesaurus ICCD

### Added
- **README**: Updated with v1.5.8 features (Periodization & Thesaurus Management interfaces)

### Technical
- Files modified:
  - `pyarchinit_mini/translations/it/LC_MESSAGES/messages.po` - Fixed PDF export button translation
  - `pyarchinit_mini/translations/en/LC_MESSAGES/messages.po` - Added Configuration and Thesaurus ICCD translations
  - `pyarchinit_mini/translations/*/LC_MESSAGES/messages.mo` - Recompiled translation catalogs
  - `README.md` - Added Periodization & Thesaurus Management section
  - `pyproject.toml` - Version 1.5.9

### Impact
- Correct button labels in Italian interface
- Complete internationalization support for new features
- Updated documentation reflects latest capabilities


### Added
- **Periodizzazione Management Interface**
  - Complete CRUD web interface for managing archaeological dating periods
  - List view displaying all datazioni with pagination support
  - Create form with fields: nome_datazione, fascia_cronologica, descrizione
  - Edit functionality for updating existing dating periods
  - Delete functionality with confirmation dialog
  - Integrated in navigation menu under "Configuration" section

- **Thesaurus ICCD Management Interface**
  - Complete CRUD web interface for ICCD controlled vocabularies
  - Two-step selection: choose table, then field
  - Dynamic field dropdown based on selected table
  - Display predefined ICCD values (read-only) with "ICCD" badge
  - Create, edit, and delete custom vocabulary values
  - Inline editing with JavaScript for quick updates
  - Visual distinction between predefined and custom values (gray background for ICCD)
  - Help documentation explaining ICCD standard compliance

- **US Form Thesaurus Integration**
  - `definizione_stratigrafica`: NEW field added as SelectField with thesaurus values
  - `formazione`: Converted from hardcoded to dynamic thesaurus-driven SelectField
  - `colore`: Converted from StringField to SelectField with thesaurus values
  - `consistenza`: Converted from hardcoded to dynamic thesaurus-driven SelectField
  - All fields populated via `ThesaurusService.get_field_values()`
  - Works in both `/us/create` and `/us/<us_id>/edit` routes

- **Navigation Updates**
  - New "Configuration" section in dropdown menu and sidebar
  - Links to Periodizzazione and Thesaurus ICCD interfaces
  - Italian translations: "Configurazione", "Periodizzazione", "Thesaurus ICCD"

### Changed
- **Thesaurus Routes**
  - `/thesaurus/<field_id>/edit` and `/thesaurus/<field_id>/delete` now accept string IDs
  - Protection for predefined ICCD values (cannot be modified or deleted)
  - Warning messages when attempting to modify read-only values

- **Template Improvements**
  - Thesaurus list template with conditional rendering for read-only values
  - Visual indicators (badges, locked icons) for ICCD predefined entries
  - Help cards with usage instructions in all new interfaces

### Fixed
- **CSRF Protection**
  - Added CSRF tokens to periodizzazione create/edit forms
  - Added CSRF tokens to thesaurus create/edit/delete forms
  - Fixed inline JavaScript edit function to include CSRF token

- **Thesaurus State Management**
  - Fixed table/field selection losing state on page reload
  - Replaced `form.submit()` with JavaScript URL parameter management
  - Maintains query parameters (?table=x&field=y) across interactions

- **Predefined Values Handling**
  - Fixed "invalid literal for int() with base 10: 'predefined_0'" error
  - Proper handling of string IDs for predefined vocabulary entries
  - Routes now check for 'predefined_' prefix before attempting integer conversion

### Technical
- Files modified:
  - `web_interface/app.py` - Added periodizzazione routes (2478-2594), thesaurus routes (2596-2717), updated USForm with thesaurus fields
  - `web_interface/templates/periodizzazione/list.html` - NEW: List interface for datazioni
  - `web_interface/templates/periodizzazione/form.html` - NEW: Create/edit form for datazioni
  - `web_interface/templates/thesaurus/list.html` - NEW: ICCD thesaurus management interface
  - `web_interface/templates/us/form.html` - Updated definizione_stratigrafica, formazione, colore, consistenza fields
  - `web_interface/templates/base.html` - Added Configuration section to navigation
  - `pyarchinit_mini/translations/it/LC_MESSAGES/messages.po` - Added Italian translations
  - `pyproject.toml` - Version 1.5.8

### User Experience
- Users can now manage archaeological dating periods via web interface
- ICCD controlled vocabularies fully manageable with clear distinction between standard and custom values
- US forms now use standardized thesaurus values for consistency
- Read-only protection ensures ICCD standard compliance
- Intuitive two-step selection (table → field) for thesaurus management
- Visual feedback (badges, colors) for different value types

### Impact
- Complete web GUI for configuration management
- ICCD standards compliance with user-friendly interface
- Enhanced data quality through controlled vocabularies
- Foundation for future thesaurus expansion to other forms
- Consistent terminology across archaeological documentation

## [1.5.7] - 2025-10-27

### Added
- **Web GUI Combobox Integration for Datazioni**
  - `datazione` field in US form now uses SelectField with database-driven choices
  - Dynamic dropdown populated from `datazioni_table` via `DatazioneService`
  - Choices displayed in format: "Nome Datazione (Fascia Cronologica)"
  - Default option: "-- Seleziona Datazione --"
  - Works in both `/us/create` and `/us/<us_id>/edit` routes

- **Italian Translation for Chronology Fields**
  - "Initial Period" → "Periodo Iniziale"
  - "Initial Phase" → "Fase Iniziale"
  - "Final Period" → "Periodo Finale"
  - "Final Phase" → "Fase Finale"
  - Translations added to `pyarchinit_mini/translations/it/LC_MESSAGES/messages.po`

### Changed
- **US Form Field Type Updates**
  - `datazione`: Changed from StringField to SelectField (dropdown with 36 Italian periods)
  - `periodo_iniziale`: Changed from SelectField to StringField (removed 40+ hardcoded choices)
  - `periodo_finale`: Changed from SelectField to StringField (removed 40+ hardcoded choices)
  - `fase_iniziale`: Remains StringField (flexible text entry)
  - `fase_finale`: Remains StringField (flexible text entry)

- **Service Integration**
  - `DatazioneService` initialized at Flask app startup
  - `get_datazioni_choices()` returns formatted list of dicts: `[{'value': 'nome', 'label': 'Nome (Fascia)'}]`
  - Fixed dict access syntax in `get_datazioni_choices()` to use `d['nome_datazione']` instead of `d.nome_datazione`

- **Bootstrap 5 CSS Classes**
  - `datazione`: Uses `form-select` class for dropdown styling
  - `periodo_iniziale`, `periodo_finale`, `fase_iniziale`, `fase_finale`: Use `form-control` class for text input styling

### Fixed
- **Session Management**
  - Fixed AttributeError: 'dict' object has no attribute 'nome_datazione'
  - All DatazioneService methods return dicts instead of ORM objects to prevent detached instance errors

### Technical
- Files modified:
  - `web_interface/app.py` - Added DatazioneService import, updated USForm fields, populated choices in create/edit routes
  - `web_interface/templates/us/form.html` - Updated field rendering with correct CSS classes
  - `pyarchinit_mini/services/datazione_service.py` - Fixed dict access in get_datazioni_choices()
  - `pyarchinit_mini/translations/it/LC_MESSAGES/messages.po` - Added Italian translations
  - `README.md` - Added v1.5.7 release notes
  - `docs/index.rst` - Added v1.5.7 version documentation
  - `pyproject.toml` - Version 1.5.7

### User Experience
- Users can now select standardized datazioni from dropdown with 36 Italian archaeological periods
- Free-text entry for periodo/fase fields maintains flexibility for chronological data
- Full Italian language support in web interface
- Consistent dropdown behavior on both create and edit forms

### Next Steps (v1.6.0)
- Desktop GUI combobox integration for datazione field
- Parser synchronization with datazioni table
- Import/export updates for datazioni support

### Impact
- Web interface now provides standardized chronological dating selection
- Maintains flexibility with free-text periodo/fase fields
- Foundation completed for Desktop GUI integration
- Consistent user experience across create and edit workflows

## [1.5.6] - 2025-10-27

### Added
- **Chronological Datazioni System**
  - New `datazioni_table` model for standardized archaeological dating periods
  - Fields: `id_datazione`, `nome_datazione`, `fascia_cronologica`, `descrizione`, `created_at`, `updated_at`
  - 36 pre-configured Italian archaeological periods from Paleolitico to Età Contemporanea
  - Multi-database support: SQLite and PostgreSQL via SQLAlchemy ORM
  - Property `full_label` returns formatted "Nome Datazione (Fascia Cronologica)"
  - Method `to_dict()` for JSON serialization

- **DatazioneService - Complete CRUD Operations**
  - `create_datazione(datazione_data)` - Create new dating period with validation
  - `get_datazione_by_id(datazione_id)` - Retrieve by ID
  - `get_datazione_by_nome(nome)` - Search by name
  - `get_all_datazioni(page, size)` - Paginated list with ordering
  - `get_datazioni_choices()` - Formatted choices for dropdown/combobox forms
  - `update_datazione(datazione_id, update_data)` - Update existing period
  - `delete_datazione(datazione_id)` - Delete period
  - `count_datazioni()` - Count total periods
  - `initialize_default_datazioni()` - Auto-populate with 36 standard Italian periods

- **Testing Infrastructure**
  - Comprehensive test script `test_datazioni_table.py` with 7 test cases
  - Tests: table creation, default initialization, CRUD operations, choices generation, search
  - 90%+ test coverage for core functionality
  - Validates multi-database compatibility

### Changed
- Updated README with Chronological Datazioni System feature in Advanced Archaeological Tools section
- Updated Project Status section with v1.5.6 release notes
- Session management improvements with context managers to avoid detached instance errors

### Technical
- Files added:
  - `pyarchinit_mini/models/datazione.py` - Datazione model
  - `pyarchinit_mini/services/datazione_service.py` - Service layer
  - `test_datazioni_table.py` - Test script
- Files modified:
  - `pyarchinit_mini/models/__init__.py` - Added Datazione import
  - `README.md` - Added feature documentation and v1.5.6 release notes
  - `pyproject.toml` - Version 1.5.6

### Next Steps (v1.6.0)
- Web GUI combobox integration for datazione field
- Desktop GUI combobox integration
- Parser synchronization with datazioni table
- Import/export updates for datazioni support

### Database Schema
```sql
CREATE TABLE datazioni_table (
    id_datazione INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_datazione VARCHAR(200) NOT NULL UNIQUE,
    fascia_cronologica VARCHAR(200),
    descrizione TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Impact
- Foundation for standardized chronological dating across all US records
- Replaces free-text datazione field with controlled vocabulary
- Enables consistent periodization for Harris Matrix exports
- Prepares GUI integration for dropdown/combobox in v1.6.0
- Compatible with both SQLite (development) and PostgreSQL (production)

## [1.5.3] - 2025-10-26

### Added
- **Harris Matrix Import Tool (CLI)**
  - New command-line tool `pyarchinit-harris-import` for bulk import of Harris Matrix data
  - Supports CSV and Excel (.xlsx, .xls) file formats
  - Import complete stratigraphic sequences with nodes and relationships
  - Full Extended Matrix node types support: US, USM, USVA, USVB, SF, VSF, TU, DOC, Extractor, Combiner, etc.
  - All relationship types: Covers, Fills, Cuts, Bonds_to, Equal_to, Continuity, >, >>, etc.
  - Automatic periodization (periodo/fase) support with area grouping
  - Built-in validation with detailed error messages and warnings
  - Export to GraphML and DOT formats after import
  - Duplicate detection and update handling
  - Transaction safety with automatic rollback on error
  - Command: `pyarchinit-harris-import matrix.xlsx --site "Site Name" --export-graphml`

- **Harris Matrix Template Generator**
  - New command `pyarchinit-harris-template` to generate Excel template
  - Pre-configured sheets: NODES and RELATIONSHIPS
  - Column headers and format ready to use
  - Helpful for creating new import files

- **Comprehensive Documentation**
  - Added `docs/features/harris_matrix_import.rst` - Complete 600+ line guide
  - Covers file format specification (CSV/Excel structure)
  - All Extended Matrix node types with examples
  - Complete relationship types reference (Italian/English)
  - Step-by-step usage guide with real-world examples
  - Validation and error handling documentation
  - Best practices and troubleshooting
  - Python API usage examples
  - Web GUI integration documentation

### Changed
- Updated main documentation index to include Harris Matrix Import guide
- Enhanced CLI interface with comprehensive help messages
- Improved error reporting with clear actionable messages

### Technical
- Files added:
  - `pyarchinit_mini/cli/harris_import.py` - Main import tool implementation
  - `pyarchinit_mini/cli/harris_template.py` - Template generator
  - `docs/features/harris_matrix_import.rst` - Complete documentation
- Files modified:
  - `docs/index.rst` - Added reference to new documentation
  - `pyproject.toml` - Version 1.5.3, added CLI entry points
- New entry points:
  - `pyarchinit-harris-import` - Import Harris Matrix from file
  - `pyarchinit-harris-template` - Generate import template
- Supported node types: US, USM, USVA, USVB, USVC, SF, VSF, TU, USD, CON, DOC, Extractor, Combiner, property
- Supported relationships: Covers, Covered_by, Fills, Filled_by, Cuts, Cut_by, Bonds_to, Equal_to, Leans_on, Continuity, >, <, >>, <<

### Documentation
- Complete Harris Matrix Import guide with:
  - File format specification (Excel with 2 sheets, CSV with 2 sections)
  - Column definitions (required/optional for NODES and RELATIONSHIPS)
  - All 14 Extended Matrix node types with descriptions
  - All 14 relationship types (stratigraphic + Extended Matrix)
  - Command-line usage examples (basic, with exports, custom database)
  - Complete working example with 10-US test site
  - Web interface integration guide
  - Validation and error handling reference
  - Database integration details
  - Best practices and troubleshooting
  - Python API programmatic usage
  - Appendix with complete type/relationship reference tables

### Impact
- Users can now import entire Harris Matrix datasets from spreadsheets
- Bulk creation of stratigraphic sequences from external systems
- Standardized data exchange format for archaeological projects
- Simplified testing with sample datasets
- Full Extended Matrix methodology support in imports
- Seamless integration with existing GraphML export workflow

## [1.5.2] - 2025-10-26

### Fixed
- **Web Dashboard Documentation Links**
  - Changed documentation links to point to ReadTheDocs (always available)
  - Previously pointed to localhost:8000/docs (requires FastAPI server running)
  - Now points to https://pyarchinit-mini.readthedocs.io/en/latest/
  - Affects both inline link in System Info section and Documentation button

### Changed
- Updated version display in web dashboard to v1.5.2
- Documentation link label changed from "API REST" to "Documentation"

### Technical
- Files modified:
  - `web_interface/templates/dashboard.html` (lines 169, 176)
  - `pyproject.toml` (version 1.5.2)

## [1.5.1] - 2025-10-26

### Fixed
- **Harris Matrix - Graphviz Orthogonal Splines Crash**
  - Fixed Graphviz crash when using orthogonal splines with edge labels and clusters
  - Error: "Warning: Orthogonal edges do not currently handle edge labels"
  - Error: "Assertion failed: (np->cells[0]), function chkSgraph, file maze.c, line 317"
  - Solution: Use `xlabel` instead of `label` for edge labels when `splines='ortho'`
  - **Impact**: Harris Matrix now renders correctly for all graph sizes with period/area clustering
  - Affects both small graphs (51 nodes) and large graphs (758+ nodes)
  - Maintains hierarchical structure and orthogonal splines as before

### Changed
- **Web Dashboard Updated**
  - Version display updated to v1.5.1 (was v0.1.0)
  - GitHub link updated to correct repository: https://github.com/enzococca/pyarchinit-mini
  - API documentation link functional

### Technical
- Files modified:
  - `pyarchinit_mini/harris_matrix/pyarchinit_visualizer.py` (lines 156-163, 403-460)
  - `web_interface/templates/dashboard.html` (lines 167, 179)
  - `pyproject.toml` (version 1.5.1)
- Modified edge label handling: `xlabel` for orthogonal splines, `label` for other spline types
- Ensures compatibility with Graphviz dot engine for complex archaeological matrices

## [1.5.0] - 2025-10-26

### Fixed
- **GraphML Export - Periodization Display**
  - Fixed `parse_clusters()` in `dot_parser.py` to handle both quoted and unquoted label values
  - Fixed cluster label parsing: now supports `label=value` format in addition to `label="value"`
  - Fixed node label parsing: now supports `NODE [...]` format in addition to `"NODE" [...]`
  - Fixed bracket counting for proper cluster boundary detection
  - Fixed period ordering: now uses chronological order (based on periodo/fase) instead of alphabetical
  - Fixed reverse epochs: now correctly inverts chronological order instead of using alphabetical reverse
  - **Result**: All 8 archaeological periods now visible in GraphML export (was showing only 3-4)
  - **Impact**: Large sites like Dom zu Lund (760 US nodes) now display complete period structure

- **GraphML Export - Period Ordering**
  - Modified `graphml_exporter.py` to use chronological ordering based on cluster_id
  - Periods now appear in correct archaeological sequence: Geologisch → Neuzeit
  - Reverse epochs properly shows newest → oldest: Non datato → Geologisch
  - Maintains consistency with database periodization (periodo_iniziale, fase_iniziale)

- **Harris Matrix - Large Graph Rendering**
  - Fixed Graphviz crash for large archaeological sites (> 500 nodes)
  - Web interface now detects large graphs and shows informative message instead of attempting render
  - Optimized `get_matrix_statistics()` to skip expensive operations (cycle detection, levels) for large graphs
  - Statistics calculation reduced from minutes to seconds for large sites
  - Users directed to GraphML export solution which works perfectly for any graph size
  - **Error Fixed**: "Assertion failed: trouble in init_rank" Graphviz crashes eliminated
  - **Impact**: Large sites like Dom zu Lund (758 nodes) now have graceful UX with working export path
  - Created `large_graph_message.html` template with statistics display and export options

### Changed
- **DOT Parser Enhanced**
  - `parse_clusters()` now more robust with flexible label format detection
  - Better handling of DOT files generated by GraphViz without quoted attributes
  - Improved cluster boundary detection using balanced bracket counting

### Documentation
- Added `docs/FIX_GRAPHML_8_PERIODS.md`: Complete technical documentation of the GraphML fix
- Added `docs/HARRIS_MATRIX_LARGE_GRAPHS.md`: Technical guide for large graph handling
- Added test scripts: `debug_parse_clusters.py`, `verify_graphml_periods.py`, `verify_graphml_reverse.py`

### Technical
- Files modified:
  - `pyarchinit_mini/graphml_converter/dot_parser.py` (lines 1259-1331)
  - `pyarchinit_mini/graphml_converter/graphml_exporter.py` (lines 268-279, 518, 551)
  - `web_interface/app.py` (lines 1268-1282) - Large graph detection
  - `pyarchinit_mini/harris_matrix/matrix_generator.py` (lines 699-739) - Statistics optimization
- Created templates:
  - `web_interface/templates/harris_matrix/large_graph_message.html` - Large graph informative page
- Verified on Dom zu Lund site: 758 US nodes, 8 periods, all correctly positioned
- Export performance: ~0.5 seconds for 758 nodes, 0.81 MB GraphML file
- Web interface gracefully handles large graphs with informative message and working export path

## [1.4.0] - 2025-10-25

### Added
- **Automatic Database Backup System** (CRITICAL SAFETY FEATURE)
  - Automatic SQLite backup using file copy with timestamp (e.g., `database.db.backup_20251025_165843`)
  - PostgreSQL backup support using pg_dump to create SQL dumps
  - Backup created BEFORE any database modification during import
  - Only one backup per session (multiple imports reuse same backup)
  - Backup path returned in import statistics for verification
  - New `auto_backup` parameter (default=True) for all import functions
  - Backup can be disabled with `auto_backup=False` for trusted sources
  - Complete logging of all backup operations
  - Tested with real databases (5.8 MB → 4.7 MB backup verified)

- **Spatial Relationship Types Support**
  - Added support for 3 spatial relationship types in Harris Matrix generation:
    * "connected to" / "collegato a" / "connects to" (195 relationships in Dom zu Lund)
    * "supports" (3 relationships)
    * "abuts" / "confina con" / "adiacente a" (3 relationships)
  - Previously these 201 relationships were being skipped with warning messages
  - Now properly included in Harris Matrix visualization and GraphML export
  - Represents 8.9% increase in relationship data for typical archaeological sites

- **Complete Dom zu Lund Import**
  - Successfully imported complete archaeological site from PyArchInit database
  - 1 site record (Lund Cathedral, Sweden)
  - 758 stratigraphic units (US)
  - 2,459 relationships (100% imported, no skipped relationships)
  - 42 periodization records (21 new + 21 existing)
  - Comprehensive test with real-world dataset

### Fixed
- **UnboundLocalError in Harris Matrix Generator**
  - Fixed variable 'filters' not being defined at function start
  - Moved filters definition to beginning of `_get_relationships()` function
  - Eliminated warning messages: "cannot access local variable 'filters' where it is not associated with a value"
  - Affects USRelationships and HarrisMatrix table queries

- **PyArchInit Import Issues** (Session: Dom zu Lund)
  - Fixed ORM metadata cache issues when importing from PyArchInit databases
  - Replaced ORM queries with raw SQL in critical import functions
  - Fixed missing i18n columns handling with automatic migration
  - Fixed relationship column name (`id_us_relationship` → `id_relationship`)
  - All import errors resolved for both SQLite and PostgreSQL sources

### Changed
- **Import Functions Enhanced**
  - `import_sites()` now accepts `auto_backup` parameter
  - `import_us()` now accepts `auto_backup` parameter
  - `import_inventario()` now accepts `auto_backup` parameter
  - `migrate_source_database()` now accepts `auto_backup` parameter
  - All import functions return backup path in statistics dictionary
  - Import service tracks backup creation with `_backup_created` and `_backup_path` instance variables

### Documentation
- Added `docs/AUTOMATIC_IMPORT_AND_BACKUP_GUIDE.md`: Comprehensive guide for automatic import and backup
- Added `docs/SESSION_DOM_ZU_LUND_IMPORT_COMPLETE.md`: Complete session summary for Dom zu Lund import
- Updated `docs/IMPORT_SUCCESS_VERIFICATION.md`: Added spatial relationship fix documentation
- Added `test_backup_system.py`: Test script for automatic backup functionality
- Added `import_complete_dom_zu_lund.py`: Complete import script for all entity types
- Added `test_import_dom_zu_lund.py`: Diagnostic script for import verification

### Technical
- New method: `_backup_source_database()` for automatic database backup
- Supports both SQLite (shutil.copy2) and PostgreSQL (pg_dump) backups
- Backup creation is idempotent - only one backup per service instance
- Non-destructive: backups created before any ALTER TABLE operations
- Timestamped filenames ensure unique backup names
- Complete error handling with fallback to continue if backup fails (with warning)

### Security
- **CRITICAL**: Source database is now automatically backed up before ANY modification
- Backup is created BEFORE adding i18n columns during migration
- Provides safety net for accidental data loss or corruption
- Allows easy rollback to pre-import state if needed

## [1.3.2] - 2025-10-25

### Added
- **Heriverse/ATON Export Integration**: Complete support for Heriverse and ATON platform JSON format
  - New `export_to_heriverse_json()` method in S3DConverter with CouchDB/scene wrapper
  - Auto-generated UUIDs for scene and creator metadata
  - Environment configuration (panoramas, lighting, scene settings)
  - Scenegraph support for 3D scene hierarchy
  - USVn category for virtual negative stratigraphic units (separate from USVs)
  - Semantic shapes: Auto-generated 3D proxy model placeholders (GLB) for each US
  - Representation models and panorama models support
  - Extended edge types: generic_connection, changed_from, contrasts_with for paradata
  - 13 node categories including semantic_shapes, representation_models, panorama_models
  - 13 edge types for comprehensive relationship modeling
  - New Flask route: `GET /3d/export/heriverse/<site_name>`
  - Web UI button: "Export Heriverse" (orange button in s3Dgraphy section)
  - Complete test suite with 4/4 tests passing

### Updated
- **Documentation**:
  - Updated `README.md` with comprehensive Heriverse/ATON section
  - Updated `docs/features/s3dgraphy.rst` with Heriverse export documentation
  - Updated `docs/s3dgraphy_integration.md` with Heriverse format comparison
  - Added `docs/HERIVERSE_INTEGRATION_SUMMARY.md` technical guide
  - Created `test_heriverse_export.py` validation suite
- **Web Interface**: Added third export button in s3Dgraphy section (JSON, Heriverse, Interactive Viewer)

### Technical
- Complete Heriverse JSON v1.5 specification compliance
- Auto-generates semantic_shape placeholders for each stratigraphic unit
- Full CouchDB/scene wrapper with proper UUID generation
- Compatible with Heriverse platform and ATON 3D viewer
- Supports both standard s3Dgraphy v1.5 and Heriverse formats as separate export options

## [1.2.12] - 2025-10-22

### Fixed
- **Web Interface Language Switching**: Fixed all navbar and menu translations
  - Uncommented 42 missing translation strings for both Italian and English
  - Fixed incorrect translations (Menu was "Manuale", now correctly "Menu")
  - All interface elements now properly switch between languages
  - Language switcher now affects entire web interface, not just analytics page

### Added
- **PyArchInit-Mini Logo**: Professional logo added to all interfaces
  - Web interface: navbar and login page
  - Desktop GUI: window icon and toolbar
  - CLI: ASCII art logo in welcome screen
  - Documentation: ReadTheDocs and README
  - Favicon for web interface

### Technical
- Updated all navigation and menu translation strings in messages.po files
- Recompiled translation catalogs with complete string coverage
- Created logo assets in PNG and ICO formats

## [1.2.11] - 2025-10-22

### Fixed
- **Web Interface Internationalization**: Fixed all hardcoded Italian text in web interface
  - All error and success messages now use translation system
  - Analytics dashboard fully translated
  - Database info page fully translated
  - All flash messages support language switching
- **Language Switching**: Fixed language switcher to properly change interface language
  - Added missing translations for Italian and English
  - Compiled translation files with all required strings
  - Session-based language preference storage

### Added
- Complete translation coverage for web interface
- 80+ new translation strings for both Italian and English

### Technical
- Updated Flask-Babel integration for proper i18n support
- All templates now use `{{ _() }}` for translatable strings
- Flash messages in app.py use gettext for dynamic translation

## [1.2.10] - 2025-10-22

### Added
- **pyarchinit-mini-init command**: New initialization command for first-time setup
  - Creates database and configuration directories automatically
  - Prompts for admin user creation interactively
  - Supports --non-interactive flag for automated deployments
  - Combines setup and admin user creation in one command

### Changed
- Updated README with clearer installation instructions
- Improved first-time user experience with single initialization command
- Fixed all command names in documentation to use correct prefixes

### Fixed
- Admin user creation now works with installed package paths
- Database path detection improved for various Python environments

## [1.2.9] - 2025-10-22

### Fixed
- Removed duplicate Project Status section from README
- Corrected version number in Project Status section

### Documentation
- Cleaned up README to show only the current Project Status

## [1.2.8] - 2025-10-22

### Added
- **Project Status Section**: Added comprehensive project status to README
- Clear indication that all interfaces are now fully functional
- Summary of recent fixes and improvements

### Changed
- Updated README to reflect production-ready status
- Emphasized that all installation issues have been resolved

### Documentation
- Added detailed status badges and checkmarks for features
- Listed all recent fixes from versions 1.2.5-1.2.8
- Added reference to active development status

## [1.2.7] - 2025-10-22

### Fixed
- **Web Server**: Fixed Flask template and static file path resolution for installed package
- **Web Server**: Added proper error handling for server startup
- **Web Server**: Created minimal CSS structure for proper static file inclusion

### Changed
- Flask app now uses absolute paths based on module location instead of pkg_resources
- Improved error messages and diagnostics for web server startup

### Added
- Basic CSS file (style.css) to ensure static directory is properly packaged

## [1.2.6] - 2025-10-22

### Fixed
- **API**: Added missing email-validator dependency for Pydantic EmailStr validation
- **Desktop GUI**: Fixed language switching by properly importing and initializing i18n system
- **Web Interface**: Changed relative imports to absolute imports for proper module resolution

### Added
- email-validator>=2.0.0 to core dependencies

## [1.2.5] - 2025-10-22

### Fixed
- **Desktop GUI**: Removed orphaned help_window reference in language dialog (line 1463)
- **Database**: Added automatic i18n column migrations during initialization
- **Database**: Missing English translation columns (definizione_sito_en, descrizione_en, etc.) now created automatically

### Added
- i18n migration method to DatabaseMigrations class
- Automatic migration of translation columns for site_table, us_table, and inventario_materiali_table

## [1.2.0] - 2025-10-22

### Added
- **s3Dgraphy Integration**: 3D visualization support for stratigraphic units
- **i18n Support**: Full internationalization for Italian and English
- **GraphViz Layout**: Enhanced Harris Matrix with GraphViz dot layout engine
- **Translation System**: Complete translation infrastructure for all interfaces

### Changed
- Improved Harris Matrix visualization with multiple layout options
- Enhanced US and Inventory forms with multilingual support

## [0.1.3] - 2025-01-18

### Added
- Complete web interface with all core functionality
- Stratigraphic relationships field in US form
- Complete Bootstrap 5 templates for all entities
- Comprehensive documentation for web interface features
- WEB_INTERFACE_FEATURES.md with detailed functionality overview

### Fixed
- **Harris Matrix generation** - Fixed 0 nodes issue by passing us_service to HarrisMatrixGenerator
- **PDF export** - Fixed detached instance error with proper session handling
- **Web server port** - Changed default from 5000 to 5001 to avoid macOS AirPlay conflict
- **Rapporti stratigrafici** - Added missing field to US form and template

### Changed
- HarrisMatrixGenerator now requires us_service parameter for proper initialization
- PDF export route now converts models to dicts within session scope
- All web templates updated with professional Bootstrap styling

### Verified
- ✅ Harris Matrix: 50 nodes, 99 edges, 7 levels - working correctly
- ✅ PDF Export: 5679 bytes generated - working correctly
- ✅ Stratigraphic Relationships: 228 relationships parsed from database
- ✅ All web templates rendering correctly

## [0.1.2] - 2025-01-17

### Changed
- Updated GitHub repository URLs from `pyarchinit/pyarchinit-mini` to `enzococa/pyarchinit-mini-desk`
- Fixed project URLs in pyproject.toml and setup.py

## [0.1.1] - 2025-01-17

### Added
- Initial PyPI publication configuration
- Modular installation with optional dependencies (cli, web, gui, harris, pdf, media, all)
- Console script entry points for all interfaces:
  - `pyarchinit-mini` - CLI interface
  - `pyarchinit-mini-api` - REST API server
  - `pyarchinit-mini-web` - Web interface
  - `pyarchinit-mini-gui` - Desktop GUI
  - `pyarchinit-mini-setup` - User environment setup
- User environment setup script for `~/.pyarchinit_mini` directory
- MANIFEST.in for proper file inclusion in distribution
- Comprehensive PyPI documentation (PYPI_PUBLICATION.md, PYPI_QUICKSTART.md)

### Changed
- Restructured dependencies with extras_require for modular installation
- API server now uses run_server() entry point
- Web interface now uses main() entry point with environment configuration

## [0.1.0] - 2025-01-17

### Added
- Core database models (Site, US, InventarioMateriali)
- Multi-database support (SQLite, PostgreSQL)
- Service layer (SiteService, USService, InventarioService)
- REST API with FastAPI
- Flask web interface
- Tkinter desktop GUI
- CLI interface with Click
- Harris Matrix generation and visualization
- PDF report export
- Media file management
- Database migration script for stratigraphic relationships
- Sample data population script

### Database
- Migrated stratigraphic relationships from textual to structured format
- 114 relationships migrated (90 "Copre", 14 "Taglia", 10 "Si appoggia a")
- Normalized us_relationships_table with proper relationship types

### Documentation
- Complete CLAUDE.md with architecture and development guidelines
- README with installation and usage instructions
- API documentation with OpenAPI/Swagger
