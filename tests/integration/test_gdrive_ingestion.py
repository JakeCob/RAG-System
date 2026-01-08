"""Integration tests for Google Drive ingestion with real API.

These tests require:
1. A Google Cloud project with Drive API enabled
2. Service account credentials in a JSON file
3. A test file uploaded to Google Drive
4. The test file shared with the service account email

Environment Variables:
    RAG_GDRIVE_CREDENTIALS_PATH: Path to service account JSON
    GDRIVE_TEST_FILE_ID: Google Drive file ID for testing
    GDRIVE_TEST_FOLDER_ID: Google Drive folder ID for listing tests (optional)

Setup Instructions:
    See docs/08_GDRIVE_SETUP.md for complete setup guide.
"""

from __future__ import annotations

import os

import pytest

from app.connectors.gdrive import GDriveConnector
from app.schemas import AgentFailure


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("RAG_GDRIVE_CREDENTIALS_PATH"),
    reason="GDrive credentials not configured (set RAG_GDRIVE_CREDENTIALS_PATH)",
)
class TestGDriveIntegration:
    """Integration tests with real Google Drive API."""

    @pytest.fixture
    def credentials_path(self) -> str:
        """Get credentials path from environment."""
        path = os.getenv("RAG_GDRIVE_CREDENTIALS_PATH", "")
        assert path, "RAG_GDRIVE_CREDENTIALS_PATH not set"
        return path

    @pytest.fixture
    def test_file_id(self) -> str:
        """Get test file ID from environment."""
        file_id = os.getenv("GDRIVE_TEST_FILE_ID", "")
        if not file_id:
            pytest.skip("GDRIVE_TEST_FILE_ID not set - skipping test")
        return file_id

    @pytest.fixture
    def test_folder_id(self) -> str | None:
        """Get test folder ID from environment (optional)."""
        return os.getenv("GDRIVE_TEST_FOLDER_ID")

    @pytest.fixture
    def connector(self, credentials_path: str) -> GDriveConnector:
        """Create GDrive connector instance."""
        return GDriveConnector(credentials_path=credentials_path)

    async def test_fetch_real_file(
        self,
        connector: GDriveConnector,
        test_file_id: str,
    ) -> None:
        """Test fetching a real file from Google Drive.

        This test verifies:
        - Authentication works correctly
        - File can be downloaded
        - Content is returned as bytes
        """
        result = await connector.fetch_file(test_file_id)

        assert isinstance(result, bytes)
        assert len(result) > 0
        print(f"✓ Successfully fetched {len(result)} bytes from GDrive")

    async def test_fetch_nonexistent_file(
        self,
        connector: GDriveConnector,
    ) -> None:
        """Test fetching a file that doesn't exist."""
        # Use an obviously invalid file ID
        result = await connector.fetch_file("INVALID_FILE_ID_123456789")

        assert isinstance(result, AgentFailure)
        assert (
            "not found" in result.message.lower() or "invalid" in result.message.lower()
        )
        print(f"✓ Correctly handled nonexistent file: {result.error_code}")

    async def test_list_files_in_folder(
        self,
        connector: GDriveConnector,
        test_folder_id: str | None,
    ) -> None:
        """Test listing files in a folder.

        If no test folder ID is provided, this test lists files in root.
        """
        if test_folder_id is None:
            pytest.skip("GDRIVE_TEST_FOLDER_ID not set - skipping folder listing test")

        result = await connector.list_files(folder_id=test_folder_id)

        assert isinstance(result, list)
        print(f"✓ Listed {len(result)} files in folder")

        # If there are files, verify structure
        if result:
            first_file = result[0]
            assert "id" in first_file
            assert "name" in first_file
            assert "mimeType" in first_file
            print(f"  Example file: {first_file['name']} ({first_file['mimeType']})")

    async def test_export_google_doc(
        self,
        connector: GDriveConnector,
    ) -> None:
        """Test exporting a Google Doc to Markdown.

        This test is skipped if GDRIVE_TEST_DOC_ID is not set.
        To enable this test:
        1. Create a Google Doc in your test Drive
        2. Share it with the service account
        3. Set GDRIVE_TEST_DOC_ID to the document ID
        """
        doc_id = os.getenv("GDRIVE_TEST_DOC_ID")
        if not doc_id:
            pytest.skip("GDRIVE_TEST_DOC_ID not set - skipping Google Docs export test")

        result = await connector.fetch_file(doc_id)

        assert isinstance(result, bytes)
        assert len(result) > 0
        # Verify it's markdown-like content (should contain text)
        content = result.decode("utf-8", errors="ignore")
        assert len(content) > 0
        print(f"✓ Successfully exported Google Doc to Markdown ({len(content)} chars)")


@pytest.mark.integration
def test_integration_setup_instructions() -> None:
    """Display setup instructions if integration tests are not configured.

    This test always passes but provides helpful setup information.
    """
    if not os.getenv("RAG_GDRIVE_CREDENTIALS_PATH"):
        print("\n" + "=" * 70)
        print("Google Drive Integration Tests - Setup Required")
        print("=" * 70)
        print("\nTo enable Google Drive integration tests:")
        print("\n1. Create a Google Cloud project:")
        print("   https://console.cloud.google.com")
        print("\n2. Enable Google Drive API")
        print("\n3. Create a Service Account and download JSON credentials")
        print("\n4. Upload a test file to Google Drive")
        print("\n5. Share the file with the service account email")
        print("\n6. Set environment variables:")
        print("   export RAG_GDRIVE_CREDENTIALS_PATH=/path/to/credentials.json")
        print("   export GDRIVE_TEST_FILE_ID=your-file-id-from-url")
        print("   export GDRIVE_TEST_FOLDER_ID=your-folder-id  # Optional")
        print("   export GDRIVE_TEST_DOC_ID=your-gdoc-id  # Optional")
        print("\n7. Run integration tests:")
        print("   pytest tests/integration/test_gdrive_ingestion.py -v")
        print("\nFor detailed setup instructions, see:")
        print("   docs/08_GDRIVE_SETUP.md")
        print("=" * 70 + "\n")
