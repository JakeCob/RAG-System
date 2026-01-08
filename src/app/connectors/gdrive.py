"""Google Drive connector for document ingestion.

Reference: docs/03_INGESTION_STRATEGY.md
"""

from __future__ import annotations

import asyncio
import io
from typing import Any, ClassVar

from google.auth.exceptions import GoogleAuthError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from app.schemas import AgentFailure, ErrorCodes


class GDriveConnector:
    """Fetch files from Google Drive with OAuth2 authentication."""

    EXPORT_FORMATS: ClassVar[dict[str, str]] = {
        "application/vnd.google-apps.document": "text/markdown",
        "application/vnd.google-apps.spreadsheet": "text/csv",
        "application/vnd.google-apps.presentation": "text/plain",
    }

    DEFAULT_SCOPES: ClassVar[list[str]] = [
        "https://www.googleapis.com/auth/drive.readonly"
    ]

    MAX_RETRIES: ClassVar[int] = 5
    INITIAL_BACKOFF_SECONDS: ClassVar[int] = 2

    def __init__(
        self,
        credentials_path: str,
        scopes: list[str] | None = None,
    ) -> None:
        """Initialize GDrive connector with service account credentials.

        Args:
            credentials_path: Path to service account JSON file.
            scopes: OAuth scopes (defaults to Drive readonly).
        """
        self._credentials_path = credentials_path
        self._scopes = scopes or self.DEFAULT_SCOPES
        self._service: Any = None
        self._credentials: Any = None

    def _get_service(self) -> Any:
        """Get or create Google Drive API service instance."""
        if self._service is None:
            try:
                creds = service_account.Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
                    self._credentials_path,
                    scopes=self._scopes,
                )
                self._credentials = creds
                self._service = build("drive", "v3", credentials=creds)
            except FileNotFoundError as e:
                msg = f"Service account credentials not found: {
                    self._credentials_path
                }"
                raise ValueError(msg) from e
            except GoogleAuthError as e:
                msg = f"Invalid service account credentials: {e}"
                raise ValueError(msg) from e

        return self._service

    def _handle_http_error(
        self,
        error: HttpError,
        file_id: str,
        attempt: int,
    ) -> AgentFailure | None:
        """Handle HTTP errors and return AgentFailure or None for retry.

        Returns:
            AgentFailure if error is not retryable, None if should retry.
        """
        status = error.resp.status

        if status == 404:
            return AgentFailure(
                agent_id="gdrive_connector",
                error_code=ErrorCodes.CONNECTOR_NOT_FOUND,
                message=f"File not found: {file_id}",
                recoverable=False,
            )

        if status == 403:
            return AgentFailure(
                agent_id="gdrive_connector",
                error_code=ErrorCodes.CONNECTOR_AUTH,
                message=f"Permission denied for file: {file_id}",
                recoverable=False,
                details={"file_id": file_id, "error": str(error)},
            )

        if status == 429:
            # Rate limit - check if can retry
            if attempt < self.MAX_RETRIES - 1:
                return None  # Signal retry
            return AgentFailure(
                agent_id="gdrive_connector",
                error_code=ErrorCodes.CONNECTOR_RATE_LIMIT,
                message=f"Rate limit exceeded after {self.MAX_RETRIES} retries",
                recoverable=True,
                details={"file_id": file_id, "retries": self.MAX_RETRIES},
            )

        if status >= 500:
            # Server error - check if can retry
            if attempt < self.MAX_RETRIES - 1:
                return None  # Signal retry
            return AgentFailure(
                agent_id="gdrive_connector",
                error_code=ErrorCodes.CONNECTOR_NETWORK,
                message=f"Network error after {self.MAX_RETRIES} retries",
                recoverable=True,
                details={"file_id": file_id, "status": status},
            )

        # Other HTTP error
        return AgentFailure(
            agent_id="gdrive_connector",
            error_code=ErrorCodes.CONNECTOR_NETWORK,
            message=f"HTTP error {status}: {error}",
            recoverable=False,
            details={"file_id": file_id, "status": status},
        )

    async def fetch_file(
        self,
        file_id: str,
        export_format: str | None = None,
    ) -> bytes | AgentFailure:
        """Download a file from Google Drive.

        Args:
            file_id: The Google Drive file ID.
            export_format: Export format for Google native files.

        Returns:
            File content as bytes or AgentFailure.

        Error Codes:
            - ERR_CONNECTOR_NOT_FOUND: File doesn't exist (404)
            - ERR_CONNECTOR_AUTH: Permission denied (403)
            - ERR_CONNECTOR_RATE_LIMIT: Too many requests (429)
            - ERR_CONNECTOR_NETWORK: Network error (503)
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                service = self._get_service()

                # Get file metadata to determine if it's a Google native file
                file_metadata = service.files().get(fileId=file_id).execute()
                mime_type = file_metadata.get("mimeType", "")

                # Check if this is a Google native file that needs export
                if mime_type in self.EXPORT_FORMATS:
                    export_mime = export_format or self.EXPORT_FORMATS[mime_type]
                    request = service.files().export_media(
                        fileId=file_id,
                        mimeType=export_mime,
                    )
                else:
                    # Regular file download
                    request = service.files().get_media(fileId=file_id)

                # Download the file in chunks
                file_buffer = io.BytesIO()
                downloader = MediaIoBaseDownload(file_buffer, request)
                done = False

                while not done:
                    _, done = downloader.next_chunk()

                return file_buffer.getvalue()

            except HttpError as e:
                failure = self._handle_http_error(e, file_id, attempt)
                if failure is None:
                    # Should retry
                    backoff = self.INITIAL_BACKOFF_SECONDS * (2**attempt)
                    await asyncio.sleep(backoff)
                    continue
                return failure

            except GoogleAuthError as e:
                return AgentFailure(
                    agent_id="gdrive_connector",
                    error_code=ErrorCodes.CONNECTOR_AUTH,
                    message=f"Authentication error: {e}",
                    recoverable=False,
                )

            except Exception as e:
                return AgentFailure(
                    agent_id="gdrive_connector",
                    error_code=ErrorCodes.CONNECTOR_NETWORK,
                    message=f"Unexpected error: {e}",
                    recoverable=False,
                    details={"file_id": file_id, "error": str(e)},
                )

        # Should never reach here, but just in case
        return AgentFailure(
            agent_id="gdrive_connector",
            error_code=ErrorCodes.CONNECTOR_NETWORK,
            message="Max retries exceeded",
            recoverable=True,
        )

    async def list_files(
        self,
        folder_id: str | None = None,
        mime_types: list[str] | None = None,
        page_size: int = 100,
    ) -> list[dict[str, Any]] | AgentFailure:
        """List files in a Drive folder.

        Args:
            folder_id: Folder ID (None = root).
            mime_types: Filter by MIME types.
            page_size: Number of results per page (max 1000).

        Returns:
            List of file metadata dicts or AgentFailure.
        """
        try:
            service = self._get_service()

            # Build query
            query_parts = []
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            if mime_types:
                mime_query = " or ".join([f"mimeType='{mt}'" for mt in mime_types])
                query_parts.append(f"({mime_query})")

            query = " and ".join(query_parts) if query_parts else None

            # Paginate through results
            all_files: list[dict[str, Any]] = []
            page_token = None

            while True:
                file_fields = (
                    "nextPageToken, files(id, name, mimeType, size, modifiedTime)"
                )
                results = (
                    service.files()
                    .list(
                        q=query,
                        pageSize=min(page_size, 1000),
                        fields=file_fields,
                        pageToken=page_token,
                    )
                    .execute()
                )

                files = results.get("files", [])
                all_files.extend(files)

                page_token = results.get("nextPageToken")
                if not page_token:
                    break

            return all_files

        except HttpError as e:
            status = e.resp.status
            if status == 404:
                return AgentFailure(
                    agent_id="gdrive_connector",
                    error_code=ErrorCodes.CONNECTOR_NOT_FOUND,
                    message=f"Folder not found: {folder_id}",
                    recoverable=False,
                )
            if status == 403:
                return AgentFailure(
                    agent_id="gdrive_connector",
                    error_code=ErrorCodes.CONNECTOR_AUTH,
                    message=f"Permission denied for folder: {folder_id}",
                    recoverable=False,
                )
            return AgentFailure(
                agent_id="gdrive_connector",
                error_code=ErrorCodes.CONNECTOR_NETWORK,
                message=f"Error listing files: {e}",
                recoverable=False,
                details={"status": status},
            )

        except GoogleAuthError as e:
            return AgentFailure(
                agent_id="gdrive_connector",
                error_code=ErrorCodes.CONNECTOR_AUTH,
                message=f"Authentication error: {e}",
                recoverable=False,
            )

        except Exception as e:
            return AgentFailure(
                agent_id="gdrive_connector",
                error_code=ErrorCodes.CONNECTOR_NETWORK,
                message=f"Unexpected error: {e}",
                recoverable=False,
            )


__all__ = ["GDriveConnector"]
