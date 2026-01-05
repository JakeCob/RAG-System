from langchain_community.document_loaders import SeleniumURLLoader, GoogleDriveLoader
from typing import List, Dict, Any

def load_from_urls(urls: List[str], browser: str = "chrome") -> List[Dict[str, Any]]:
    """
    Loads content from a list of URLs using Selenium.
    Returns a list of dictionaries with 'text' and 'metadata'.
    """
    try:
        loader = SeleniumURLLoader(urls=urls, browser=browser)
        docs = loader.load()
        return [{"text": d.page_content, "metadata": d.metadata} for d in docs]
    except Exception as e:
        print(f"Error loading URLs: {e}")
        return []

def load_from_gdrive(folder_id: str = None, document_ids: List[str] = None, credentials_path: str = "credentials.json", token_path: str = "token.json") -> List[Dict[str, Any]]:
    """
    Loads content from Google Drive (folder or list of doc IDs).
    Returns a list of dictionaries with 'text' and 'metadata'.
    """
    try:
        # Note: credentials_file and token_path usually need to be set up in the environment
        # or passed explicitly. This assumes standard locations or mapped volumes.
        loader = GoogleDriveLoader(
            folder_id=folder_id,
            document_ids=document_ids,
            credentials_path=credentials_path,
            token_path=token_path,
            recursive=False
        )
        docs = loader.load()
        return [{"text": d.page_content, "metadata": d.metadata} for d in docs]
    except Exception as e:
        print(f"Error loading from Google Drive: {e}")
        return []
