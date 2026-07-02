# Media Storage Backends Runbook

## Overview

PyArchInit supports multiple storage backends for media files and thumbnails. This runbook covers deployment setup and configuration.

## Prerequisites: PYARCHINIT_SECRET_KEY

Before enabling any storage backend, set the `PYARCHINIT_SECRET_KEY` environment variable in your deployment. This is a Fernet encryption key used for encrypting sensitive credentials (API keys, tokens, etc.) at rest.

### Generate a new Fernet key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Example output:
```
Z0FBQUFBQmQyN1pNTi1YYTBUdEhFcE...
```

Set this in your deployment environment:

**Development (`.env` file):**
```
PYARCHINIT_SECRET_KEY=Z0FBQUFBQmQyN1pNTi1YYTBUdEhFcE...
```

**Production (Railway, Adarte, etc.):**
Add as an environment variable in your deployment platform's settings.

**⚠️ Important:** The same key must be used across all instances of a deployment. If you rotate the key, all stored credentials become inaccessible.

## Configuration

Once `PYARCHINIT_SECRET_KEY` is set, go to **Admin Settings** → **Storage** (`/settings/storage`) to configure:

1. **Storage Backend**: Select from available backends (see [Available Backends](#available-backends) below)
2. **Media Root**: Where media files are stored (path format depends on backend)
3. **Thumbnail Path**: Where thumbnails are stored (path format depends on backend)
4. **Thumbnail Resize**: Resize dimensions (e.g., `150x150`, `300x300`) — leave empty to disable thumbnails
5. **Backend-Specific Credentials**: API keys, tokens, etc. (encrypted using `PYARCHINIT_SECRET_KEY`)

## Available Backends

### Local (`LOCAL`)
- **Dependencies**: None (always available)
- **Media Root format**: `/path/to/media` or `C:\path\to\media`
- **Example**:
  - Media Root: `/var/media/pyarchinit/media`
  - Thumbnail Path: `/var/media/pyarchinit/thumbnails`

### Unibo File Manager (`UNIBO`)
- **Dependencies**: None (always available)
- **Media Root format**: `unibo://project_code/folder/path`
- **Example**:
  - Media Root: `unibo://ProjX/photolog/original`
  - Thumbnail Path: `unibo://ProjX/photolog/thumbnails`
- **Credentials**: Unibo server URL (no auth required in current implementation)

### Amazon S3 (`S3`)
- **Dependencies**: `boto3`
- **Media Root format**: `s3://bucket-name/path`
- **Example**:
  - Media Root: `s3://my-archive/media`
  - Thumbnail Path: `s3://my-archive/thumbs`
- **Credentials**: AWS Access Key ID + Secret Access Key
- **Note**: Requires S3 bucket created beforehand; ensure CORS is enabled if serving directly

### Cloudflare R2 (`R2`)
- **Dependencies**: `boto3`
- **Media Root format**: `r2://bucket-name/path`
- **Example**:
  - Media Root: `r2://my-bucket/media`
  - Thumbnail Path: `r2://my-bucket/thumbs`
- **Credentials**: R2 Account ID, Access Key ID + Secret Access Key
- **Note**: R2 is S3-compatible; configure with your R2 endpoint URL

### WebDAV (`WEBDAV`)
- **Dependencies**: `webdavclient3`
- **Media Root format**: `webdav://server-hostname/path`
- **Example**:
  - Media Root: `webdav://cloud.example.com/dav/files/media`
  - Thumbnail Path: `webdav://cloud.example.com/dav/files/thumbs`
- **Credentials**: WebDAV username + password
- **Note**: HTTPS is recommended; HTTP will be converted to HTTPS internally

### Dropbox (`DROPBOX`)
- **Dependencies**: `dropbox`
- **Media Root format**: `dropbox://app-folder/path`
- **Example**:
  - Media Root: `dropbox://media`
  - Thumbnail Path: `dropbox://thumbs`
- **Credentials**: Dropbox App Key + Secret (or OAuth token)
- **Note**: Requires Dropbox App configured with appropriate permissions

### Google Drive (`GOOGLE_DRIVE`)
- **Dependencies**: `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`, `google-api-python-client`
- **Media Root format**: `gdrive://folder-id/path`
- **Example**:
  - Media Root: `gdrive://1a2b3c4d5e6f7g8h/media`
  - Thumbnail Path: `gdrive://1a2b3c4d5e6f7g8h/thumbs`
- **Credentials**: Google service account JSON or OAuth credentials
- **Note**: Requires Google Drive API enabled; folder must be accessible to authenticated account

### Cloudinary (`CLOUDINARY`)
- **Dependencies**: `cloudinary`
- **Media Root format**: `cloudinary://cloud-name/folder`
- **Example**:
  - Media Root: `cloudinary://my-cloud/media`
  - Thumbnail Path**: `cloudinary://my-cloud/thumbs`
- **Credentials**: Cloudinary Cloud Name + API Key + API Secret
- **Note**: Cloudinary handles thumbnails automatically; `thumbnail_resize` controls Cloudinary transformation params

## Optional Dependencies

Optional storage backends are disabled if their SDK is not installed. Enable a backend by installing its extra:

```bash
# S3 and R2
pip install pyarchinit-mini[storage-s3]

# WebDAV
pip install pyarchinit-mini[storage-webdav]

# Dropbox
pip install pyarchinit-mini[storage-dropbox]

# Google Drive
pip install pyarchinit-mini[storage-gdrive]

# Cloudinary
pip install pyarchinit-mini[storage-cloudinary]
```

Or install all storage backends at once:
```bash
pip install pyarchinit-mini[storage-all]
```

**Missing SDKs gracefully disable backends** — the application will continue to work with available backends.

## Testing Your Configuration

After setting up a backend:

1. Go to **Admin Settings** → **Storage** and configure the backend
2. Click **Test Connection** (if provided) to verify credentials
3. Upload a test file via the web UI
4. Verify the file appears in the configured storage location
5. Verify thumbnails are created if `thumbnail_resize` is set

## Troubleshooting

### "Backend not available" error
- Check that `PYARCHINIT_SECRET_KEY` is set
- Verify the required SDK for your backend is installed (see [Optional Dependencies](#optional-dependencies))
- Check credentials are correct and have appropriate permissions

### Files not appearing in storage
- Verify the path format matches the backend (see examples above)
- Check that the account/bucket/folder exists and is accessible
- Review application logs for detailed error messages

### Thumbnails not generating
- Ensure `thumbnail_resize` is not empty
- Check that the thumbnail path is accessible and has write permissions
- For remote backends, verify credentials have write access

## Monitoring

Storage operations are logged to the application log file. For production deployments:
- Monitor disk space (local backend)
- Monitor S3/R2 bucket size and costs
- Monitor API rate limits (Dropbox, Google Drive, Cloudinary)
- Periodically audit credentials for rotation needs
