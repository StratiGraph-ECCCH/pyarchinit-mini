# Media layer di pyarchinit-mini → schema plugin classico (swap globale)

**Data:** 2026-07-02
**Stato:** design approvato, in attesa di review dello spec
**Schema di riferimento:** plugin QGIS `pyarchinit`, branch `Stratigraph_00001`
(`~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/pyarchinit`)

---

## 1. Contesto e problema

pyarchinit-mini e il plugin QGIS `pyarchinit` girano (nel caso festos / server univ. Bologna)
sullo **stesso database PostgreSQL**. Le tabelle media hanno però schemi divergenti:

- **Plugin (festos):** `media_table` (`filepath`, `filename`, `mediatype`, …) + tabella di
  collegamento M:N `media_to_entity_table` + `media_thumb_table` con path su disco.
- **pyarchinit-mini oggi:** `media_table` con collegamento **inline** (`entity_type` + `entity_id`,
  `media_path`, `media_filename`), nessuna `media_to_entity_table`, `media_thumb_table` con **blob**
  nel DB.

Poiché `create_all` non altera tabelle esistenti, quando mini apre/carica un media su un DB con lo
schema del plugin va in errore (`UndefinedColumn`).

**Obiettivo:** allineare il layer media di mini allo schema del plugin, così che i due strumenti
scrivano/leggano **le stesse righe** su un DB condiviso. Cancellare un media da QGIS lo fa sparire
dalla web app e viceversa — è letteralmente lo stesso record. **Nessun meccanismo di sync da mantenere.**

## 2. Decisioni già prese (brainstorming)

- **Swap globale:** lo schema del plugin diventa l'**unico** schema media di mini, ovunque
  (non dual-mode). Su Adarte/Railway le tabelle media sono vuote → si ricreano.
- **Thumbnail allineate al plugin:** file su disco (`filepath` 200×200 + `path_resize` 600×600),
  **niente blob** nel DB.
- **`is_primary` (immagine principale): fuori dall'MVP** (il plugin non ha il concetto; con l'M:N
  andrebbe sul link). Reintroducibile in seguito sul link se serve.
- **Nessun DDL sul DB di festos** (è di un'altra università): mini si adatta alle colonne esistenti,
  non le aggiunge.

## 3. Schema autorevole (target) — plugin `Stratigraph_00001`

DDL equivalente PostgreSQL (DB condiviso). PK **BIGINT** con sequence per-tabella (l'ORM del plugin
dichiara `Integer`, ma il DB reale usa BIGINT).

```sql
media_table(
  id_media           BIGINT PK DEFAULT nextval('media_table_id_media_seq'),
  mediatype   text,        -- "image" | "document" | "video" | ...
  filename    text,        -- nome file originale
  filetype    varchar(10), -- estensione
  filepath    text,        -- path assoluto locale OPPURE URI remoto (vedi §7)
  descrizione text,
  tags        text,
  entity_uuid text,        -- UUID4, unica colonna "sync"
  UNIQUE(filepath)         -- "ID_media_unico" — filepath è chiave naturale
)

media_thumb_table(
  id_media_thumb       BIGINT PK DEFAULT nextval('media_thumb_table_id_media_thumb_seq'),
  id_media  BIGINT REFERENCES media_table(id_media) ON DELETE CASCADE,  -- fk_media_thumb_to_media
  mediatype            text,
  media_filename       text,
  media_thumb_filename text,        -- UNIQUE
  filetype             varchar(10),
  filepath             text,        -- thumbnail 200×200
  path_resize          text,        -- resize 600×600
  entity_uuid          text,
  UNIQUE(media_thumb_filename)      -- "ID_media_thumb_unico"
)

media_to_entity_table(
  "id_mediaToEntity"   BIGINT PK DEFAULT nextval('media_to_entity_table_id_mediaToEntity_seq'),
  id_entity   BIGINT,   -- PK dell'entità collegata (id_us, id_rep, …)
  entity_type text,     -- vedi mappa §5 (MAIUSCOLO)
  table_name  text,     -- vedi mappa §5
  id_media    BIGINT REFERENCES media_table(id_media) ON DELETE CASCADE,  -- fk_mte_to_media
  filepath    text,     -- copia denormalizzata di media_table.filepath
  media_name  text,     -- copia denormalizzata di filename
  entity_uuid text,
  UNIQUE(id_entity, entity_type, id_media)  -- "ID_mediaToEntity_unico" (chiave dedupe)
)
```

**Watch-out irrinunciabili:**
1. `"id_mediaToEntity"` è un identificatore **CamelCase quotato** in PG → ogni SQL raw lo deve quotare.
2. PK **BIGINT + sequence** nel DB reale (non `Integer`); su insert lasciare che sia la sequence a
   generare l'id (non passare `id_media`).
3. `media_table.filepath` è **UNIQUE** e assoluto (o URI remoto) → prima di inserire un media, se il
   filepath esiste già, **riusa** la riga esistente invece di duplicarla.
4. Le due FK sono **ON DELETE CASCADE** (`fk_media_thumb_to_media`, `fk_mte_to_media`): cancellare la
   riga `media_table` cancella a cascata thumb e link.
5. L'**unica** colonna di sync è `entity_uuid` (text/UUID4). Non esistono `version_number`,
   `created_at`, `updated_at`, `sync_status`, `node_uuid`.

## 4. Modello dati in mini (`pyarchinit_mini/models/media.py`)

I tre modelli media **NON ereditano più `BaseModel`** (che imporrebbe colonne inesistenti nel plugin).
Diventano modelli autonomi che mappano **esattamente** le colonne del §3 + `entity_uuid`:

- `Media` → `media_table` (colonne del §3). Rimossi: `entity_type`/`entity_id` inline, `media_name`,
  `mime_type`, `file_size`, `is_primary`, `is_public`, `width`, `height`, `duration`, `resolution`,
  `copyright_info`, `author`, e le colonne `BaseModel` diverse da `entity_uuid`.
- `MediaThumb` → `media_thumb_table` (PK rinominata `id_thumb` → **`id_media_thumb`**; rimosso
  `thumb_data` blob; aggiunte `mediatype`, `media_filename`, `media_thumb_filename`, `filetype`,
  `path_resize`).
- **Nuovo** `MediaToEntity` → `media_to_entity_table` (PK `id_mediaToEntity`, FK `id_media`
  ON DELETE CASCADE, `id_entity`, `entity_type`, `table_name`, `filepath`, `media_name`, `entity_uuid`).
- PK come `BigInteger`, autoincrement dalla sequence esistente.
- Aggiornare `database/concurrency_manager.py` (già mappa `media_thumb_table → id_media_thumb`) e
  `models/__init__.py` per registrare `MediaToEntity`.
- `Documentation`/`documentation_table` resta invariata (non fa parte dello schema media del plugin).

## 5. Mappa entità mini → (entity_type, table_name) del plugin

Valori **reali** scritti dal plugin (verificati nei tab modules):

| entità mini | entity_type | table_name | id_entity |
|---|---|---|---|
| US | `US` | `us_table` | `id_us` |
| Reperto / inventario | `REPERTO` | `inventario_materiali_table` | `id_rep` / `id_invmat` |
| Ceramica (pottery) | `CERAMICA` | `pottery_table` | `id_rep` |
| Struttura | `STRUTTURA` | `struttura_table` | `id_struttura` |
| Tomba | `TOMBA` | `tomba_table` | `id_tomba` |
| TMA | `TMA` | `tma_table` | `id_tma` |
| UT | `UT` | `ut_table` | `id_ut` |

**Sito:** il plugin **non** collega media ai siti via `media_to_entity_table`. Mini oggi supporta media
a livello di sito. Decisione: mini può continuare a scriverli con `entity_type='SITE'`,
`table_name='site_table'` — righe valide ma **visibili solo in mini** (il plugin non le interroga).
Feature mini-only, innocua. Documentare che i media di sito non compaiono in QGIS.

## 6. Collegamento M:N — semantica di query/create/delete

- **Query per entità:** `get_media_by_entity(table_name, id_entity)` → JOIN
  `media_to_entity_table` (`table_name`, `id_entity`) → `media_table`. Sostituisce il filtro inline
  `entity_type`+`entity_id`.
- **Create:** (1) risolvi/inserisci la riga `media_table` (riusa per `filepath` esistente, vedi §3.3);
  (2) inserisci la riga `media_to_entity_table` solo se non viola
  `UNIQUE(id_entity, entity_type, id_media)` (check esistenza prima, come fa il plugin).
- **Delete = due operazioni distinte:**
  - *Scollega da questa entità* → elimina **solo** la riga `media_to_entity_table`.
  - *Elimina il file* → elimina la riga `media_table` (cascade su thumb + link) **e** il file fisico,
    **solo** quando non restano altri link a quel media.

## 7. File fisici e risoluzione dei path (il vero nodo di interop)

Convenzione del plugin:
- **Media originali** copiati in `$PYARCHINIT_HOME/pyarchinit_Media_folder/<filename>`; `filepath` =
  path **assoluto** (o URI remoto). Cartella media effettivamente hardcoded (non configurabile).
- **Storage remoto:** se configurato, `filepath` può essere un URI con schema `unibo://`,
  `cloudinary://`, `s3://`, `dropbox://`, `webdav://`, `gdrive://`. La risoluzione lato lettura è in
  `modules/utility/remote_image_loader.py` (`get_image_path`): se è già un URL/URI remoto lo restituisce
  as-is, altrimenti `os.path.join(base_dir, filename)`.
- **Thumbnail:** in due cartelle **configurabili** `THUMB_PATH` (200×200 → `filepath`) e `THUMB_RESIZE`
  (600×600 → `path_resize`), filename `thumb_<id_media>_<filename>`. Config in
  `config.cfg` / QSettings del plugin.

Requisiti per mini:
1. **Lettura/serving:** mini deve **portare la logica di risoluzione** dei path del plugin (almeno:
   path assoluto locale + lo schema remoto usato da festos, verosimilmente `unibo://`). Senza questo,
   mini avrebbe le righe DB ma non saprebbe mostrare i file. → *passo 0: leggere `remote_image_loader.py`
   e capire come risolve lo schema effettivo di festos.*
2. **Upload da mini:** scrivere il file con la **stessa convenzione** del target (copiare in
   `pyarchinit_Media_folder` per storage locale, **oppure** caricare sullo stesso storage remoto),
   così il plugin lo vede al suo `filepath`. Config via env/impostazione: media root + thumb dirs +
   eventuale endpoint remoto.
3. **Path locali della macchina QGIS**: se un utente QGIS usa path locali, mini (sul server web) non li
   vede — accettato e atteso. La condivisione reale funziona quando i media stanno su storage server
   (locale condiviso o remoto `unibo://`).

## 8. Thumbnail

- Mini genera `thumb_<id_media>_<filename>` in `THUMB_PATH` (200×200) e `THUMB_RESIZE` (600×600) e
  salva i path in `media_thumb_table.filepath` / `path_resize` (niente blob).
- `media_thumb_filename` è **UNIQUE**: usare un nome deterministico che non collida.
- Il web serve la thumbnail dal path risolto (stessa logica §7).

## 9. Service / handler

- `services/media_service.py` e `media_manager/media_handler.py`: riscrivere create/get/delete sulla
  nuova struttura + `MediaToEntity`. Rimuovere il codice che scriveva `media_path`/`entity_type` inline
  e il blob thumbnail. Popolare `entity_uuid` (UUID4) come fa il plugin.
- `mcp_server/tools/media_management_tool.py`: adattare al nuovo modello; enum `entity_type` →
  valori del §5.

## 10. Web (`pyarchinit_mini/web_interface/app.py`)

- Rotte `/media/upload`, `/media/list`, `/media/delete`, serving `/media/<path>`, e le API
  `/api/media/*`: adattare alla nuova struttura. La risoluzione entità dell'upload mappa gli input
  utente su `(entity_type, table_name, id_entity)` del §5. Il serving usa la risoluzione path del §7.

## 11. Fuori scope MVP

- Desktop GUI (`desktop_gui/media_manager_advanced.py`, `us_dialog_extended.py`): oggi non persiste su
  DB. Allineamento rimandato a follow-up.
- `is_primary` / immagine principale.
- Migrazione dei media legacy con path QGIS locali (pulsante "Convert to media_table entries" della
  pottery sheet resta separato).

## 12. Migrazione dei DB mini esistenti (Adarte v2, Railway)

Le tabelle media lì sono **vuote** → ricreazione pulita:
1. Guardia: procedere **solo se** `count(*)==0` su `media_table`, `media_thumb_table` (e nessuna
   `media_to_entity_table` con dati). Altrimenti **abortire** con warning.
2. `DROP TABLE media_thumb_table, media_table` (+ eventuale link inline) e ricreare con i nuovi modelli
   (`create_all` / migrazione dedicata) incluse sequence, FK CASCADE, UNIQUE.
3. Meccanismo esatto (create_all vs migrazione in `database/migrations/`) deciso in fase di piano.

## 13. Rollout

1. **Passo 0 — verifica live su festos** (checkpoint obbligatorio prima del codice DDL/query):
   confermare colonna-per-colonna lo schema del §3 sul DB reale, i valori `entity_type`/`table_name`
   effettivamente presenti, e **la convenzione dei filepath** (locale vs `unibo://`) leggendo qualche
   riga reale + `remote_image_loader.py`.
2. Implementazione (modelli → service/handler → web → mcp), TDD.
3. Test (vedi §14).
4. Release su PyPI.
5. Deploy Adarte + Railway (ricreano le tabelle vuote con lo schema nuovo).
6. Deploy/verifica su festos: la web app legge/scrive le stesse righe del plugin; smoke test
   bidirezionale (crea in QGIS → vedi nel web; crea nel web → vedi in QGIS; delete → cascade).

## 14. Testing

- Unit: modelli mappano le colonne esatte del §3; `MediaToEntity` dedupe su
  `UNIQUE(id_entity, entity_type, id_media)`; create riusa media per `filepath` esistente.
- Integrazione su Postgres (fixture con lo schema del plugin): create media + link, query per entità,
  delete-unlink vs delete-file con cascade, generazione thumbnail e path.
- Risoluzione path: locale assoluto e URI remoto (`unibo://`) → URL servibile corretto.
- Regressione: su un DB mini vuoto ricreato, il flusso media completo funziona.

## 15. Rischi e domande aperte

- **Convenzione filepath di festos** (locale vs `unibo://`): determina quanto lavoro serve sul serving
  remoto. Da chiarire al passo 0. Se `unibo://`, va portata la risoluzione (e l'upload) verso quel
  server.
- **Utenti PyPI esterni** con dati media nello schema inline: lo swap globale li romperebbe. Mitigazione:
  nota di release + eventuale script di migrazione one-shot (inline → plugin). Impatto atteso basso.
- **Sequenze PK condivise:** insert concorrenti plugin+mini devono usare `nextval` della stessa
  sequence (già problematiche di sequence in passato) — verificare che il modello mini non forzi l'id.
- **`entity_uuid`**: mini lo popola come il plugin (UUID4) su tutte e tre le tabelle.