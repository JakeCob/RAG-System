# Google Drive Connector Setup Guide

**Phase 4 - Task P4-2**

This guide walks you through setting up the Google Drive connector for document ingestion in the RAG system.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Option 1: Service Account (Recommended)](#option-1-service-account-recommended)
4. [Configuration](#configuration)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)
7. [Security Best Practices](#security-best-practices)

---

## Overview

The Google Drive connector allows the RAG system to ingest documents directly from Google Drive. It supports:

- **Regular files**: PDF, DOCX, PPTX, TXT, etc.
- **Google native files**: Google Docs → Markdown, Sheets → CSV, Slides → Plain text
- **Automatic retry logic**: Handles rate limits and transient errors
- **Streaming downloads**: Efficient handling of large files

## Prerequisites

- Google Cloud account (free tier is sufficient)
- Python 3.11+ with the RAG system installed
- Access to Google Drive files you want to ingest

## Option 1: Service Account (Recommended)

Service accounts are ideal for:
- Automated ingestion workflows
- Server-side applications
- Testing and development
- No browser interaction required

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **"Select a project"** → **"New Project"**
3. Enter project name (e.g., `rag-gdrive-connector`)
4. Click **"Create"**

### Step 2: Enable Google Drive API

1. In the Google Cloud Console, go to **"APIs & Services"** → **"Library"**
2. Search for **"Google Drive API"**
3. Click **"Enable"**

### Step 3: Create Service Account

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"Create Credentials"** → **"Service Account"**
3. Enter service account details:
   - **Name**: `rag-drive-reader`
   - **Description**: `Service account for RAG document ingestion`
4. Click **"Create and Continue"**
5. Skip **"Grant this service account access to project"** (optional)
6. Click **"Done"**

### Step 4: Create and Download Service Account Key

1. In the **Credentials** page, find your service account
2. Click on the service account name
3. Go to the **"Keys"** tab
4. Click **"Add Key"** → **"Create new key"**
5. Select **JSON** format
6. Click **"Create"**
7. Save the downloaded JSON file securely

**IMPORTANT**: This JSON file contains sensitive credentials. Never commit it to version control!

### Step 5: Share Google Drive Files/Folders

1. Open Google Drive in your browser
2. Right-click the file or folder you want to ingest
3. Click **"Share"**
4. In the **"Add people and groups"** field, paste the service account email:
   - Found in the JSON file as `client_email`
   - Format: `rag-drive-reader@project-id.iam.gserviceaccount.com`
5. Set permission to **"Viewer"** (read-only)
6. Uncheck **"Notify people"** (no need to email the service account)
7. Click **"Share"**

### Step 6: Get File/Folder IDs

**For a single file:**
1. Open the file in Google Drive
2. Copy the URL: `https://drive.google.com/file/d/FILE_ID_HERE/view`
3. Extract the file ID from the URL

**For a folder:**
1. Open the folder in Google Drive
2. Copy the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
3. Extract the folder ID from the URL

**Example:**
```
URL: https://drive.google.com/file/d/1a2b3c4d5e6f7g8h9i0j/view
File ID: 1a2b3c4d5e6f7g8h9i0j
```

---

## Configuration

### 1. Place Credentials File

Create a `credentials/` directory in your project root:

```bash
mkdir -p credentials
mv ~/Downloads/service-account-key.json credentials/service-account.json
chmod 600 credentials/service-account.json  # Restrict permissions
```

### 2. Update Environment Variables

Create or edit your `.env` file:

```bash
cp .env.example .env
```

Add the following configuration:

```bash
# Google Drive Connector
RAG_GDRIVE_CREDENTIALS_PATH="credentials/service-account.json"

# Optional: Customize OAuth scopes (comma-separated)
# RAG_GDRIVE_SCOPES="https://www.googleapis.com/auth/drive.readonly"
```

### 3. Verify Configuration

Test that the connector can authenticate:

```bash
python -c "
from app.connectors.gdrive import GDriveConnector
from app.config.settings import get_settings

settings = get_settings()
connector = GDriveConnector(credentials_path=settings.gdrive_credentials_path)
print('✓ GDrive connector initialized successfully')
"
```

---

## Testing

### Unit Tests (Mocked API)

Run unit tests with mocked Google API:

```bash
pytest tests/unit/connectors/test_gdrive_connector.py -v
```

Expected output:
```
tests/unit/connectors/test_gdrive_connector.py::TestGDriveConnector::test_fetch_file_success PASSED
tests/unit/connectors/test_gdrive_connector.py::TestGDriveConnector::test_fetch_file_not_found PASSED
tests/unit/connectors/test_gdrive_connector.py::TestGDriveConnector::test_rate_limit_retry PASSED
...
```

### Integration Tests (Real API)

**Setup test environment:**

1. Upload a small test file (e.g., `test.txt`) to Google Drive
2. Share it with your service account email
3. Copy the file ID from the URL
4. Set environment variables:

```bash
export RAG_GDRIVE_CREDENTIALS_PATH="credentials/service-account.json"
export GDRIVE_TEST_FILE_ID="your-test-file-id-here"
export GDRIVE_TEST_FOLDER_ID="your-folder-id-here"  # Optional
export GDRIVE_TEST_DOC_ID="your-google-doc-id-here"  # Optional
```

**Run integration tests:**

```bash
pytest tests/integration/test_gdrive_ingestion.py -v
```

Expected output:
```
tests/integration/test_gdrive_ingestion.py::TestGDriveIntegration::test_fetch_real_file PASSED
  ✓ Successfully fetched 1024 bytes from GDrive
tests/integration/test_gdrive_ingestion.py::TestGDriveIntegration::test_fetch_nonexistent_file PASSED
  ✓ Correctly handled nonexistent file: ERR_CONNECTOR_NOT_FOUND
...
```

### Manual Testing

**Test file download:**

```python
import asyncio
from app.connectors.gdrive import GDriveConnector

async def test_download():
    connector = GDriveConnector(credentials_path="credentials/service-account.json")

    # Replace with your test file ID
    result = await connector.fetch_file("YOUR_FILE_ID_HERE")

    if isinstance(result, bytes):
        print(f"✓ Downloaded {len(result)} bytes")
    else:
        print(f"✗ Error: {result.error_code} - {result.message}")

asyncio.run(test_download())
```

**Test file listing:**

```python
import asyncio
from app.connectors.gdrive import GDriveConnector

async def test_list():
    connector = GDriveConnector(credentials_path="credentials/service-account.json")

    # List files in root or specific folder
    result = await connector.list_files(folder_id="YOUR_FOLDER_ID")  # or None for root

    if isinstance(result, list):
        print(f"✓ Found {len(result)} files:")
        for file in result[:5]:  # Show first 5
            print(f"  - {file['name']} ({file['mimeType']})")
    else:
        print(f"✗ Error: {result.error_code} - {result.message}")

asyncio.run(test_list())
```

---

## Troubleshooting

### Error: "Permission denied for file"

**Cause**: The service account doesn't have access to the file.

**Solution**:
1. Share the file with the service account email
2. Verify the email in your JSON credentials file (`client_email`)
3. Make sure you shared with **Viewer** or **Editor** permissions

### Error: "File not found"

**Cause**: Invalid file ID or file was deleted.

**Solution**:
1. Verify the file ID is correct (check the Drive URL)
2. Make sure the file still exists in Google Drive
3. Try accessing the file directly in your browser while logged out

### Error: "Invalid service account credentials"

**Cause**: Credentials file is missing, corrupted, or in wrong format.

**Solution**:
1. Verify the JSON file exists at the path specified in `.env`
2. Check the JSON file is valid (not truncated)
3. Re-download the credentials from Google Cloud Console if needed

### Error: "Rate limit exceeded"

**Cause**: Too many API requests in a short time.

**Solution**:
- The connector automatically retries with exponential backoff
- If persistent, reduce the frequency of requests
- Consider using batch operations for multiple files

### Error: "ModuleNotFoundError: No module named 'googleapiclient'"

**Cause**: Google API client libraries not installed.

**Solution**:
```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

---

## Security Best Practices

### 1. Protect Credentials

- **Never commit** `service-account.json` to version control
- Store credentials in a secure location with restricted permissions:
  ```bash
  chmod 600 credentials/service-account.json
  ```
- Use environment variables for paths, not hardcoded values

### 2. Use Readonly Scopes

The default scope is `https://www.googleapis.com/auth/drive.readonly`:
- Provides read-only access to Drive files
- Prevents accidental modifications or deletions
- Follows principle of least privilege

### 3. Rotate Credentials Regularly

- Delete old service account keys from Google Cloud Console
- Generate new keys periodically (every 90 days recommended)
- Update your `.env` file with the new credentials path

### 4. Monitor API Usage

- Check Google Cloud Console → **"APIs & Services"** → **"Dashboard"**
- Set up alerts for unusual API usage patterns
- Review access logs regularly

### 5. Limit File Sharing

- Only share necessary files/folders with the service account
- Review shared items periodically
- Remove access when no longer needed

---

## Option 2: User OAuth (Future Enhancement)

**Note**: User OAuth flow is planned for Phase 6. This will allow:
- User-specific Drive access
- Browser-based authorization flow
- Refresh token management
- Per-user file permissions

For now, use Service Account authentication as documented above.

---

## Next Steps

Once you've completed the setup:

1. **Ingest your first document**:
   ```python
   from app.ingestion.service import IngestionService
   from app.connectors.gdrive import GDriveConnector
   from app.memory import MemoryAgent

   # Initialize services
   memory = MemoryAgent()
   gdrive = GDriveConnector(credentials_path="credentials/service-account.json")
   ingestion = IngestionService(memory_agent=memory, gdrive_connector=gdrive)

   # Ingest from Google Drive
   result = await ingestion.ingest_from_gdrive(
       file_id="YOUR_FILE_ID",
       filename="my-document.pdf",
   )
   ```

2. **Integrate with API endpoints**: See `docs/06_FRONTEND_PLAYBOOK.md` for API integration

3. **Monitor ingestion**: Check logs for errors and performance metrics

4. **Explore advanced features**: Folder ingestion, batch processing, scheduled syncs

---

## Support

For issues or questions:
- Check existing tests: `tests/unit/connectors/test_gdrive_connector.py`
- Review error codes: `src/app/schemas/base.py` → `ErrorCodes`
- Consult API reference: [Google Drive API Docs](https://developers.google.com/drive/api/guides/about-sdk)

---

**Document Version**: 1.0
**Last Updated**: 2026-01-07
**Phase**: Phase 4 - Task P4-2
