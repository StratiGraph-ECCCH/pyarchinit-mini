# Nuove schede archeologiche in pyarchinit-mini (SP2): tomba, struttura, UT, fauna

**Data:** 2026-07-02
**Stato:** design approvato (brainstorming), in attesa di review dello spec
**Riferimento schemi:** plugin QGIS `pyarchinit`, branch `Stratigraph_00001`
(`~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/pyarchinit/modules/db/structures/`)

Segue [[media-plugin-schema-alignment]] e [[media-storage-backends]]. Prerequisito di SP3 (media UI per struttura/tomba/UT).

## 1. Contesto e obiettivo

mini web non ha ancora le schede **struttura, tomba, UT (unità topografica), fauna**. Il plugin classico sì. Obiettivo: aggiungerle a mini web con **CRUD completo**, **schema-compatibili col plugin** (per interop su DB condiviso festos), e integrate in **tutti i sistemi collegati**: thesaurus, media (tranne fauna), AI (chat/MCP), dashboard/stats, export PDF/Excel, e **documentazione + tutorial**.

## 2. Approccio (deciso)

**Costruire TOMBA end-to-end come template comprovato**, revisionarla, poi **replicare lo stesso pattern** su struttura, fauna, UT. Ogni scheda = il suo piano d'implementazione (che riusa il checklist §4). La release **3.0.0** arriva quando tutte e 4 (+ docs) sono complete.

## 3. Modello di interop (come le schede esistenti US/inventario)

Le schede-record di mini (US, inventario, pottery) **ereditano `BaseModel`** (colonne di sync: `version_number`, `sync_status`, `editing_by`, `entity_uuid`, `created_at`, …) e sul DB condiviso col plugin quelle colonne vengono **aggiunte alle tabelle del plugin dalla migrazione concurrency** di mini (i log Railway mostrano "Column version_number already exists in table us_table"). Le nuove schede seguono lo **stesso pattern**:
- Modello = `BaseModel` + **tutte le colonne del plugin** (nomi/tipi esatti del §5/§6).
- La migrazione concurrency di mini (`database/migrations/__init__.py`) va estesa per aggiungere le colonne di sync a `tomba_table`/`struttura_table`/`ut_table`/`fauna_table`. Il plugin ignora le colonne extra (come già per us/inventario).
- Su DB nuovo, `create_all` crea la tabella (registrare il modello in `models/__init__.py` **e** `database/database_creator.py::_import_all_models`). Su DB esistente senza la tabella, una migrazione `CREATE TABLE`.
- Allocazione id: mirror del pattern `inventario_service`/`tma_service` (coesiste col plugin come già fanno US/inventario).

## 4. Checklist di integrazione per OGNI scheda (il template da replicare)

Verificato nel codice mini (path/riga citati inline):
1. **Modello** `pyarchinit_mini/models/<entity>.py` (BaseModel + colonne plugin) + registrazione in `models/__init__.py` e `database/database_creator.py:_import_all_models`.
2. **Migrazione**: `CREATE TABLE` per DB esistenti + estendere la concurrency-migration per le colonne sync.
3. **Service** `pyarchinit_mini/services/<entity>_service.py` (mirror `services/tma_service.py`: CRUD, `get_thesaurus_values`, `get_distinct_sites`) + registrazione in `services/__init__.py` + attach in `app.py` (~riga 698-711).
4. **Route + form**: blocco in `web_interface/app.py` sul modello del blocco **TMA** (`app.py:4831-4987`): list/new/edit/delete (+ media upload + thesaurus API), WTForms sul modello `InventarioForm` (`app.py:239-304`) con `SelectField(choices=[])` popolati a runtime via `get_thesaurus_choices`.
5. **Template** `web_interface/templates/<entity>/{list,form,detail}.html` + nav in `templates/base.html` + tile in `templates/dashboard.html`.
6. **Thesaurus**: seed in `models/thesaurus.py::THESAURUS_MAPPINGS` (blocco per `<table>`), route `/api/<entity>/thesaurus/<field>`.
7. **Media** (tranne fauna): `entity_map.py` **ha già** struttura/tomba/ut → serve upload route (copia `tma_media_upload` `app.py:4917`) + gallery via `_media_gallery('<key>', id)` (`app.py:685`) + opzionale `/api/media/<entity>`.
8. **AI/MCP**: aggiungere l'entità ai **system prompt** `services/ai_assistant_service.py:39-78` (link + summary), e alle **liste hardcoded** nei tool MCP (`data_import_parser_tool.py` FIELD_MAPPINGS/`_get_service_for_table`, `pyarchinit_sync_tool.py:40`, `batch_insert_tool.py`).
9. **Dashboard/stats + export**: conteggio in `services/analytics_service.py:31-61` + tile dashboard; template PDF in `pdf_export/` + route export (mirror inventario `app.py:2801/2840`, pottery excel `pottery_routes.py:242`).
10. **Docs/tutorial**: `.rst` Sphinx (`docs/<entity>.rst` + `<entity>_service.rst` in `docs/index.rst` toctree), sezione in `docs/tutorials/web_interface_tutorial.rst`, voci in `README.md`/`CHANGELOG.md`, pagina in-app `templates/docs/index.html`.

*(Harris matrix resta solo-US → nessuna modifica.)*

## 5. TOMBA — design concreto (prima slice)

**Tabella `tomba_table`, PK `id_tomba` (Integer), 27 colonne** (dal plugin `Tomba_table.py`), legata al sito via `sito`:
`id_tomba, sito, area, nr_scheda_taf, sigla_struttura, nr_struttura, nr_individuo, rito, descrizione_taf, interpretazione_taf, segnacoli, canale_libatorio_si_no, oggetti_rinvenuti_esterno, stato_di_conservazione, copertura_tipo, tipo_contenitore_resti, tipo_deposizione, tipo_sepoltura, corredo_presenza, corredo_tipo, corredo_descrizione, periodo_iniziale, fase_iniziale, periodo_finale, fase_finale, datazione_estesa, entity_uuid` (+ colonne sync da BaseModel).

- **Modello** `models/tomba.py` (`class Tomba(BaseModel)`), registrato in `models/__init__.py` + `database_creator`.
- **Campi thesaurus-controllati** (SelectField + seed `THESAURUS_MAPPINGS['tomba_table']`): `rito`, `tipo_sepoltura`, `tipo_deposizione`, `copertura_tipo`, `tipo_contenitore_resti`, `stato_di_conservazione`, `corredo_presenza`. Gli altri sono testo/numero.
- **Service** `services/tomba_service.py` (CRUD + thesaurus + distinct sites), sul modello `tma_service`.
- **Route** `/tomba` (list), `/tomba/new`, `/tomba/<id>` (edit), `/tomba/<id>/delete`, `/tomba/<id>/media/upload`, `/api/tomba/thesaurus/<field>`. Form `TombaForm` (WTForms).
- **Template** `templates/tomba/{list,form}.html` (+ detail opz.), nav + dashboard tile.
- **Media**: key `tomba` (già in `entity_map` → `TOMBA`/`tomba_table`/`id_tomba`); upload + gallery.
- **AI/MCP**: prompt + mapping `tomba_table`→`tomba_service`.
- **Dashboard**: conteggio tombe; **export** PDF scheda tomba + Excel.
- **Docs**: `docs/tomba.rst` + tutorial + README/CHANGELOG.

## 6. Delta per le altre 3 (stesso checklist, differenze)

- **struttura** (`struttura_table`, PK `id_struttura`, 36 col, sito, media STRUTTURA): 6 campi Text-JSON (`stato_conservazione`, `prospetto_ingresso`, `orientamento_ambienti`, `elementi_costitutivi`, `manufatti`, `fasi_funzionali`) → UI a lista ripetibile (o textarea JSON validata). Thesaurus: `categoria_struttura, tipologia_struttura, stato_conservazione, orientamento_ingresso, articolazione`.
- **fauna** (`fauna_table`, PK `id_fauna` BigInt, 37 col): **NO media** (per design); legata a **US** (`id_us`/`us`) → il form ha un selettore US (lookup) invece del sito. Thesaurus: `specie, parti_scheletriche, contesto, stato_conservazione, metodologia_recupero, deposizione`. Campi JSON: `specie_psi, misure_ossa`.
- **UT** (`ut_table`, PK `id_ut`, 60 col, `progetto`, media UT): la più grossa; sezioni survey/GIS (`geometria, coord_*, gps_method, survey_type, visibility_percent`, …) e analisi (`potential_score, risk_score, potential_factors/risk_factors` JSON). Form suddiviso in fieldset (anagrafica / ubicazione / survey / analisi). Thesaurus: `def_ut, survey_type, gps_method, surface_condition, accessibility`.

## 7. Testing (per scheda)
- Unit: modello mappa le colonne esatte del plugin; service CRUD (create/get/list/update/delete) su sqlite; thesaurus values; distinct sites.
- Integrazione: route list/new/edit/delete (harness web esistente); media upload+gallery (tranne fauna); thesaurus API dropdown.
- Regressione: suite intera verde; le schede esistenti (US/inventario/pottery/TMA) invariate.
- Migrazione: su DB con la tabella vecchia (schema plugin) le colonne sync vengono aggiunte; su DB nuovo `create_all` crea la tabella.

## 8. Rollout
Un **piano d'implementazione per scheda** (writing-plans), eseguito subagent-driven con review. Ordine: **tomba** (template) → struttura → fauna → UT. Docs/tutorial aggiornati con ogni scheda + una passata finale. **Bump 3.0.0** (major: nuove entità) quando tutte e 4 + docs sono complete; poi PyPI + push (Railway) + Adarte.

## 9. Rischi / aperti
- **Campi Text-JSON** (struttura/UT/fauna): decidere UI — lista ripetibile vs textarea JSON validata (proposta: textarea JSON con validazione lato server per l'MVP, lista ripetibile come miglioramento).
- **Allocazione id su DB condiviso**: seguire il pattern esistente di US/inventario (nessuna regressione nota).
- **fauna→US**: il form fauna deve risolvere/legare un `id_us` reale (selettore US per sito/area/us).
- **Seed thesaurus**: valori iniziali dei vocabolari — prendere dal plugin dove disponibili, altrimenti liste minime estendibili da UI.
- **AI/MCP liste hardcoded**: assicurarsi di aggiornarle tutte (grep-verificato) per non lasciare l'entità "invisibile" all'AI.
- **Docs Sphinx**: aggiungere gli `.rst` al toctree o il build fallisce.
