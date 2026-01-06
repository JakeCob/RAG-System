from typing import Any

from langchain_community.document_loaders import GoogleDriveLoader, SeleniumURLLoader


def load_from_urls(urls: list[str], browser: str = "chrome") -> list[dict[str, Any]]:
    """Load content from URLs using Selenium.

    Args:
        urls: List of URLs to fetch.
        browser: Browser to use for Selenium.

    Returns:
        List of dicts with `text` and `metadata`.
    """
    try:
        loader = SeleniumURLLoader(urls=urls, browser=browser)
        docs = loader.load()
        return [{"text": d.page_content, "metadata": d.metadata} for d in docs]
    except Exception as e:
        print(f"Error loading URLs: {e}")
        return []


def load_from_gdrive(
    folder_id: str | None = None,
    document_ids: list[str] | None = None,
    credentials_path: str = "credentials.json",
    token_path: str = "token.json",
) -> list[dict[str, Any]]:
    """Load content from Google Drive.

    Args:
        folder_id: Folder ID to ingest.
        document_ids: Explicit document IDs to ingest.
        credentials_path: Path to OAuth credentials JSON.
        token_path: Path to OAuth token JSON.

    Returns:
        List of dicts with `text` and `metadata`.
    """
    try:
        # Note: credentials_file and token_path usually need to be set up in the
        # environment
        # or passed explicitly. This assumes standard locations or mapped volumes.
        loader = GoogleDriveLoader(
            folder_id=folder_id,
            document_ids=document_ids,
            credentials_path=credentials_path,
            token_path=token_path,
            recursive=False,
        )
        docs = loader.load()
        return [{"text": d.page_content, "metadata": d.metadata} for d in docs]
    except Exception as e:
        print(f"Error loading from Google Drive: {e}")
        return []
