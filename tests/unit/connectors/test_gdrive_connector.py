"""Unit tests for Google Drive connector with mocked Google API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from googleapiclient.errors import HttpError

from app.connectors.gdrive import GDriveConnector
from app.schemas import AgentFailure, ErrorCodes


class TestGDriveConnector:
    """Test suite for GDriveConnector class."""

    @pytest.fixture
    def mock_credentials(self) -> Mock:
        """Mock service account credentials."""
        return Mock()

    @pytest.fixture
    def mock_service(self) -> MagicMock:
        """Mock Google Drive API service."""
        service = MagicMock()
        return service

    @pytest.mark.unit
    @patch("app.connectors.gdrive.service_account.Credentials")
    @patch("app.connectors.gdrive.build")
    async def test_fetch_file_success(
        self,
        mock_build: MagicMock,
        mock_creds: MagicMock,
    ) -> None:
        """Test successful file download."""
        # Setup mocks
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock file metadata (not a Google native file)
        mock_service.files().get().execute.return_value = {
            "id": "file_123",
            "name": "test.pdf",
            "mimeType": "application/pdf",
        }

        # Mock file download
        mock_downloader = MagicMock()
        mock_downloader.next_chunk.side_effect = [
            (None, False),
            (None, True),  # Done
        ]

        with patch(
            "app.connectors.gdrive.MediaIoBaseDownload",
            return_value=mock_downloader,
        ):
            connector = GDriveConnector(credentials_path="fake.json")
            result = await connector.fetch_file("file_123")

        assert isinstance(result, bytes)

    @pytest.mark.unit
    @patch("app.connectors.gdrive.service_account.Credentials")
    @patch("app.connectors.gdrive.build")
    async def test_fetch_file_not_found(
        self,
        mock_build: MagicMock,
        mock_creds: MagicMock,
    ) -> None:
        """Test 404 error handling."""
        # Setup mocks
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock 404 error
        http_error = HttpError(
            resp=MagicMock(status=404),
            content=b"Not found",
        )
        mock_service.files().get().execute.side_effect = http_error

        connector = GDriveConnector(credentials_path="fake.json")
        result = await connector.fetch_file("missing_file")

        assert isinstance(result, AgentFailure)
        assert result.error_code == ErrorCodes.CONNECTOR_NOT_FOUND
        assert "not found" in result.message.lower()

    @pytest.mark.unit
    @patch("app.connectors.gdrive.service_account.Credentials")
    @patch("app.connectors.gdrive.build")
    async def test_fetch_file_permission_denied(
        self,
        mock_build: MagicMock,
        mock_creds: MagicMock,
    ) -> None:
        """Test 403 permission denied error."""
        # Setup mocks
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock 403 error
        http_error = HttpError(
            resp=MagicMock(status=403),
            content=b"Permission denied",
        )
        mock_service.files().get().execute.side_effect = http_error

        connector = GDriveConnector(credentials_path="fake.json")
        result = await connector.fetch_file("restricted_file")

        assert isinstance(result, AgentFailure)
        assert result.error_code == ErrorCodes.CONNECTOR_AUTH
        assert "permission denied" in result.message.lower()

    @pytest.mark.unit
    @patch("app.connectors.gdrive.service_account.Credentials")
    @patch("app.connectors.gdrive.build")
    @patch("app.connectors.gdrive.asyncio.sleep", new_callable=AsyncMock)
    async def test_rate_limit_retry(
        self,
        mock_sleep: AsyncMock,
        mock_build: MagicMock,
        mock_creds: MagicMock,
    ) -> None:
        """Test exponential backoff on 429 errors."""
        # Setup mocks
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock 429 error then success
        http_error = HttpError(
            resp=MagicMock(status=429),
            content=b"Rate limit exceeded",
        )

        call_count = 0

        def get_side_effect() -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise http_error
            return {
                "id": "file_123",
                "name": "test.pdf",
                "mimeType": "application/pdf",
            }

        mock_service.files().get().execute.side_effect = get_side_effect

        # Mock successful download after retry
        mock_downloader = MagicMock()
        mock_downloader.next_chunk.return_value = (None, True)

        with patch(
            "app.connectors.gdrive.MediaIoBaseDownload",
            return_value=mock_downloader,
        ):
            connector = GDriveConnector(credentials_path="fake.json")
            result = await connector.fetch_file("file_123")

        # Verify it retried and succeeded
        assert isinstance(result, bytes)
        # Verify exponential backoff was called
        mock_sleep.assert_called()

    @pytest.mark.unit
    @patch("app.connectors.gdrive.service_account.Credentials")
    @patch("app.connectors.gdrive.build")
    @patch("app.connectors.gdrive.asyncio.sleep", new_callable=AsyncMock)
    async def test_rate_limit_max_retries(
        self,
        mock_sleep: AsyncMock,
        mock_build: MagicMock,
        mock_creds: MagicMock,
    ) -> None:
        """Test max retries on persistent rate limit."""
        # Setup mocks
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock 429 error every time
        http_error = HttpError(
            resp=MagicMock(status=429),
            content=b"Rate limit exceeded",
        )
        mock_service.files().get().execute.side_effect = http_error

        connector = GDriveConnector(credentials_path="fake.json")
        result = await connector.fetch_file("file_123")

        assert isinstance(result, AgentFailure)
        assert result.error_code == ErrorCodes.CONNECTOR_RATE_LIMIT
        assert result.recoverable is True
        # Should have called sleep MAX_RETRIES - 1 times
        assert mock_sleep.call_count == connector.MAX_RETRIES - 1

    @pytest.mark.unit
    @patch("app.connectors.gdrive.service_account.Credentials")
    @patch("app.connectors.gdrive.build")
    async def test_export_google_doc_to_markdown(
        self,
        mock_build: MagicMock,
        mock_creds: MagicMock,
    ) -> None:
        """Test native Google Docs export to Markdown."""
        # Setup mocks
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock Google Docs metadata
        mock_service.files().get().execute.return_value = {
            "id": "doc_123",
            "name": "test.gdoc",
            "mimeType": "application/vnd.google-apps.document",
        }

        # Mock export
        mock_downloader = MagicMock()
        mock_downloader.next_chunk.return_value = (None, True)

        with patch(
            "app.connectors.gdrive.MediaIoBaseDownload",
            return_value=mock_downloader,
        ):
            connector = GDriveConnector(credentials_path="fake.json")
            result = await connector.fetch_file("doc_123")

        assert isinstance(result, bytes)
        # Verify export_media was called with Markdown MIME type
        mock_service.files().export_media.assert_called_once_with(
            fileId="doc_123",
            mimeType="text/markdown",
        )

    @pytest.mark.unit
    @patch("app.connectors.gdrive.service_account.Credentials")
    @patch("app.connectors.gdrive.build")
    async def test_list_files_success(
        self,
        mock_build: MagicMock,
        mock_creds: MagicMock,
    ) -> None:
        """Test listing files in a folder."""
        # Setup mocks
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock file list response
        mock_service.files().list().execute.return_value = {
            "files": [
                {
                    "id": "file_1",
                    "name": "test1.pdf",
                    "mimeType": "application/pdf",
                    "size": "1024",
                },
                {
                    "id": "file_2",
                    "name": "test2.docx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "size": "2048",
                },
            ],
            "nextPageToken": None,
        }

        connector = GDriveConnector(credentials_path="fake.json")
        result = await connector.list_files(folder_id="folder_123")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "test1.pdf"
        assert result[1]["name"] == "test2.docx"

    @pytest.mark.unit
    @patch("app.connectors.gdrive.service_account.Credentials")
    @patch("app.connectors.gdrive.build")
    async def test_list_files_with_pagination(
        self,
        mock_build: MagicMock,
        mock_creds: MagicMock,
    ) -> None:
        """Test listing files with pagination."""
        # Setup mocks
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock paginated responses
        call_count = 0

        def list_side_effect(**kwargs: dict[str, str]) -> dict[str, list | str | None]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "files": [{"id": "file_1", "name": "test1.pdf"}],
                    "nextPageToken": "token_page2",
                }
            else:
                return {
                    "files": [{"id": "file_2", "name": "test2.pdf"}],
                    "nextPageToken": None,
                }

        mock_service.files().list().execute.side_effect = list_side_effect

        connector = GDriveConnector(credentials_path="fake.json")
        result = await connector.list_files()

        assert isinstance(result, list)
        assert len(result) == 2
        assert call_count == 2

    @pytest.mark.unit
    @patch("app.connectors.gdrive.service_account.Credentials")
    @patch("app.connectors.gdrive.build")
    async def test_list_files_folder_not_found(
        self,
        mock_build: MagicMock,
        mock_creds: MagicMock,
    ) -> None:
        """Test listing files in non-existent folder."""
        # Setup mocks
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock 404 error
        http_error = HttpError(
            resp=MagicMock(status=404),
            content=b"Folder not found",
        )
        mock_service.files().list().execute.side_effect = http_error

        connector = GDriveConnector(credentials_path="fake.json")
        result = await connector.list_files(folder_id="missing_folder")

        assert isinstance(result, AgentFailure)
        assert result.error_code == ErrorCodes.CONNECTOR_NOT_FOUND

    @pytest.mark.unit
    @patch("app.connectors.gdrive.service_account.Credentials")
    @patch("app.connectors.gdrive.build")
    @patch("app.connectors.gdrive.asyncio.sleep", new_callable=AsyncMock)
    async def test_network_error_retry(
        self,
        mock_sleep: AsyncMock,
        mock_build: MagicMock,
        mock_creds: MagicMock,
    ) -> None:
        """Test retry on 503 network errors."""
        # Setup mocks
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock 503 error
        http_error = HttpError(
            resp=MagicMock(status=503),
            content=b"Service unavailable",
        )
        mock_service.files().get().execute.side_effect = http_error

        connector = GDriveConnector(credentials_path="fake.json")
        result = await connector.fetch_file("file_123")

        assert isinstance(result, AgentFailure)
        assert result.error_code == ErrorCodes.CONNECTOR_NETWORK
        assert result.recoverable is True
        # Should have retried MAX_RETRIES - 1 times
        assert mock_sleep.call_count == connector.MAX_RETRIES - 1
