# Media storage backends in pyarchinit-mini web (SP1)

**Data:** 2026-07-02
**Stato:** design approvato (brainstorming), in attesa di review dello spec
**Riferimento plugin:** `modules/storage/` del pyarchinit classico, branch `Stratigraph_00001`
(`~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/pyarchinit`)

Fa parte del filone media (vedi [[media-plugin-schema-alignment]]). È il follow-up "storage remoto / `unibo://`" generalizzato a **tutti** i backend del plugin.

---

## 1. Contesto e problema

Oggi pyarchinit-mini web sa scrivere/servire i media **solo sul filesystem locale** (env `PYARCHINIT_MEDIA_ROOT` / `PYARCHINIT_THUMB_PATH` / `PYARCHINIT_THUMB_RESIZE`). Il `path_resolver` riconosce gli schemi remoti (`unibo://`, `s3://`, `webdav://`, `gdrive://`, `dropbox://`, `cloudinary://`, `http(s)://`) ma **non scarica né carica** i byte su quei backend.

Il plugin QGIS invece supporta uno storage configurabile su molti backend, e memorizza in `media_table.filepath` una stringa **scheme-prefixed** (es. `unibo://project/folder/file`). Su un DB condiviso (festos), mini deve scrivere/leggere gli **stessi formati** per interoperare.

**Obiettivo:** dare a mini web parità piena col plugin sui backend storage, configurabili da una **UI web**, così i media possono risiedere sullo stesso server (volume locale) **oppure** su NAS/servizio esterno (WebDAV, S3, Unibo, GDrive, Dropbox, Cloudinary), interoperando col plugin sul DB condiviso.

## 2. Decisioni (dal brainstorming)

- **Parità piena** con i backend del plugin.
- **Approccio: PORT** del pacchetto `modules/storage/` del plugin in `pyarchinit_mini/storage/` (è headless-ready, nessun aggancio a QGIS tranne una lettura opzionale di `QgsSettings` da sostituire).
- **Config via UI web**, credenziali salvate in DB **cifrate**.
- **Granularità globale** (una config storage per istanza mini; vale per il DB in uso).
- **Serving remoto = proxy** (mini scarica i byte e li stream-a) per i backend privati; **redirect** per URL pubblici (http/https/cloudinary).
- **SFTP escluso** (dichiarato ma NON implementato nel plugin).

## 3. Backend in scope, formati di path, dipendenze

Contratto uniforme (`StorageBackend`): `__init__(base_path, credentials)`, `read(rel)->bytes|None`, `write(rel, data)->bool`, `exists`, `delete`, `list`, `get_url`.

| Backend | scheme / formato `filepath` | libreria (opzionale) | serving |
|---|---|---|---|
| Local | path assoluto (nessuno schema) | stdlib | file |
| Unibo | `unibo://{project}/{folder}/.../file` | **stdlib** (bespoke JWT REST) | proxy |
| WebDAV | `webdav://{server}/{path}` | `webdavclient3` (`webdav3`) | proxy |
| S3 | `s3://{bucket}/{key}` | `boto3` | proxy (o URL firmato) |
| R2 | `r2://{bucket}/{key}` (S3Backend + `account_id`) | `boto3` | proxy |
| Cloudinary | `cloudinary://{folder}/.../file` (public_id senza estensione) | `cloudinary` | **redirect** a `https://res.cloudinary.com/{cloud}/image/upload/…` (strip `_thumb`) |
| Google Drive | `gdrive://{folder}/.../file` | `google-api-python-client` + `google-auth*` | proxy |
| Dropbox | `dropbox://{folder}/.../file` | `dropbox` | proxy |
| HTTP(S) | `http(s)://{server}/{path}` | `requests` | **redirect** |

Le librerie sono importate **solo dentro il rispettivo backend**; se assente, quel backend è disabilitato con messaggio chiaro (il core di mini non le richiede tutte). Unibo/Local: stdlib.

## 4. Architettura / componenti

### 4.1 `pyarchinit_mini/storage/` (port del pacchetto plugin)
Port quasi 1:1 di `modules/storage/`: `base_backend.py` (ABC + `StorageType`, `StorageFile`, `StorageConfig`), `storage_manager.py` (dispatcher: `SCHEME_MAP`, `detect_storage_type`, `parse_path()->(type, base_path, relative)`, `get_backend`, `read/write/exists/delete`), e i backend `local/s3/webdav/cloudinary/gdrive/dropbox/http/unibo`. **`credentials.py` adattato**: rimuove la dipendenza da `QgsSettings`; le credenziali arrivano da un `MiniCredentialsProvider` che legge dalla config DB di mini (via `set_credentials(type, dict)`), oltre a env var/`.env`/JSON come fallback (già supportati).

### 4.2 Config DB + UI impostazioni
- **Modello** `StorageConfig` (singola riga globale): `active_media_root`, `active_thumb_path`, `active_thumb_resize` (stringhe, eventualmente scheme-prefixed → selezionano il backend di **upload**), + `credentials_encrypted` (JSON cifrato con le credenziali per-backend). Riusa il pattern `app_setting` se conveniente.
- **UI** `/settings/storage` (solo utenti con permesso admin): un form/tab per backend, con gli **stessi nomi campo del plugin** (§6 sotto) → read-compatibili col loader del plugin. Bottone **"Test connessione"** per backend (chiama `backend.connect()`/`exists`).
- L'"upload target" è dato dallo schema di `active_media_root`/`active_thumb_*` (come il plugin, dove `THUMB_PATH` può essere `unibo://…`). La **lettura** usa lo schema della `filepath` memorizzata.

### 4.3 Cifratura segreti
Credenziali cifrate a riposo con **Fernet**, chiave da env `PYARCHINIT_SECRET_KEY` (generata/derivata; se assente, la UI storage è read-only e avvisa). Mai loggare le credenziali in chiaro.

### 4.4 Upload (`MediaHandler`)
`store_original` / `make_thumbnails`: se `media_root`/`thumb_path` sono scheme-prefixed (backend remoto), scrivono i byte via `StorageManager.write(path, data)` e restituiscono la **stringa scheme-prefixed** come `filepath` (interop col plugin). Se locale, comportamento attuale (copia su FS). La generazione thumbnail resta locale (PIL), poi upload sul backend.

### 4.5 Serving (`/media/serve`)
Matrice per schema della `filepath`:
- **locale** (path assoluto) → `send_file` sotto le root consentite (guard anti-traversal già presente).
- **http/https** → `redirect(url)`.
- **cloudinary** → `redirect(cloudinary_to_url(path))` (strip `_thumb`, cloud name da config).
- **unibo/webdav/s3/r2/gdrive/dropbox** → **proxy**: `StorageManager.read(path)` → `send_file(BytesIO, mimetype)` (stream). Cache header opzionale.
Errori backend → 502/404 con log (non crash).

### 4.6 Path resolver
`public_url`/`thumb_url` restano; `serve_media` instrada secondo la matrice §4.5. Il `path_resolver` esistente (schemi) viene riusato; la logica di fetch passa dallo `StorageManager`.

## 5. Requisiti (requirements.txt)
Aggiungere come **extra opzionali** (o dipendenze soft con import lazy): `boto3`, `webdavclient3`, `dropbox`, `cloudinary`, `google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`, `requests` (già presente), `Pillow` (già presente). Documentare che senza una libreria il relativo backend è disattivato.

## 6. Campi credenziali per backend (specchio del plugin)
Persistere con gli **stessi nomi** (compat col loader del plugin, chiavi `pyarchinit/storage/{type}/{field}`):
- **Unibo**: `server_url`, `username`, `password`, `project_code`, `base_folder`, `verify_ssl`
- **Cloudinary**: `cloud_name`, `api_key`, `api_secret`, `folder`, `auto_tagging`
- **Google Drive**: `client_id`, `client_secret`, `refresh_token`
- **Dropbox**: `access_token`, `app_key`, `app_secret`
- **S3/R2**: `access_key`, `secret_key`, `region`, `endpoint`, `account_id` (R2)
- **WebDAV**: `username`, `password`, `verify_ssl`
- **HTTP**: `api_key`, `username`, `password`, `bearer_token`

## 7. Testing
- Unit: `StorageManager.parse_path` per ogni schema restituisce `(type, base_path, relative)` corretti; `LocalBackend` read/write/exists/delete su tmp; import lazy → backend assente se libreria mancante (senza crash).
- Backend con SDK: test con mock/localstack dove possibile (S3→moto/localstack; WebDAV→server fittizio; Unibo→mock del REST). Almeno il contratto `read/write` mockato.
- Cifratura: round-trip encrypt/decrypt; assenza chiave → UI read-only.
- Serving matrix: local→file, http/cloudinary→redirect (URL corretto, strip `_thumb`), backend→proxy (byte da `StorageManager.read` mockato).
- Interop: `filepath` scritto = esattamente il formato del plugin per ogni schema (§3).
- Regressione: flusso locale invariato quando nessun backend remoto è configurato.

## 8. Rollout
Release su PyPI → deploy Adarte + Railway. La UI storage compare in impostazioni; finché non si configura un backend, il comportamento locale resta identico (nessuna regressione). Aggiornare le dipendenze nel deploy (extra opzionali).

## 9. Rischi / aperti
- **Peso dipendenze**: 5+ SDK. Mitigazione: import lazy + extra opzionali; il core non li richiede.
- **Proxy serving**: media grandi passano attraverso mini (memoria/banda). Mitigazione: stream, e per S3/HTTP preferire URL firmati/redirect quando possibile (fase 2).
- **Unibo bespoke**: dipende dall'API `/api/v1/` di quel server (self-signed, `ssl.CERT_NONE`); portato as-is, ma da testare contro il server reale.
- **Cloudinary**: cloud name hardcoded nel plugin (`dkioeufik`) → in mini va in config.
- **SFTP**: fuori scope (non esiste nel plugin).
- **Sicurezza credenziali**: chiave Fernet in env; documentare la gestione. Mai in DB in chiaro né nei log.

## 10. Fuori scope
- SFTP; per-connessione/per-sito storage (deciso globale); SP2 (nuove schede) e SP3 (media per struttura/tomba/UT). L'AI/thesaurus/altri sistemi collegati riguardano SP2.
