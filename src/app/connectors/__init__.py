"""Data source connectors for the RAG system.

Contains:
- Local File Connector
- Google Drive Connector
- Web Scraper Connector
"""

from app.connectors.gdrive import GDriveConnector


__all__ = ["GDriveConnector"]
