# RAG System Architecture: ROMA & Dolphin Integration

## Overview

This system implements a high-performance Retrieval-Augmented Generation (RAG) pipeline leveraging **Dolphin** for intelligent layout-aware document parsing and **ROMA** (Recursive Open Meta-Agent) for orchestrating the ingestion and retrieval processes.

## Core Components

### 1. Data Ingestion & Parsing (Dolphin & Connectors)
*   **Role**: The "Eyes" of the system.
*   **Sources**:
    *   **Documents**: PDF, Images (processed via Dolphin Layout Analysis).
    *   **Web**: Dynamic websites (processed via **SeleniumURLLoader**).
    *   **Cloud**: Google Drive folders/docs (processed via **GoogleDriveLoader**).
*   **Process**:
    *   **Layout Analysis (Docs)**: Identifies tables, headers, paragraphs, and figures.
    *   **Web Scraping (URLs)**: Headless browser rendering to capture JS-heavy content.
    *   **Content Extraction**: Parses text within the identified layout blocks.
    *   **Output**: Structured JSON/Markdown preserving the document hierarchy and spatial relationships.

### 2. Orchestration & Processing (ROMA Agents)
*   **Role**: The "Brain" of the system.
*   **Concept**: Uses a recursive meta-agent architecture to handle complex tasks.
*   **Nodes**:
    *   **Ingestion Node**:
        *   Receives structured data from Dolphin.
        *   Recursively splits content based on semantic boundaries (sections, tables) rather than arbitrary character counts.
        *   Generates embeddings for each chunk.
        *   Routes metadata to PostgreSQL and vectors to LanceDB.
    *   **Retrieval Node**:
        *   Analyzes user queries.
        *   Formulates a search strategy (recursive search or flat retrieval).
        *   Queries LanceDB for semantic matches and PostgreSQL for metadata filtering (e.g., "papers from 2024").
        *   Synthesizes the answer using an LLM.

### 3. Storage Layer
*   **PostgreSQL**:
    *   **Usage**: Relational metadata store.
    *   **Data**: Document IDs, authors, upload dates, processing status, original file paths, and chunk-to-document mappings.
*   **LanceDB**:
    *   **Usage**: High-performance vector store (embedded).
    *   **Data**: 
        *   Vector embeddings of text chunks.
        *   Original text content (stored alongside vectors for fast retrieval).
        *   Structural tags (from Dolphin) to allow filtering by section type (e.g., "search only in tables").

## Data Flow

1.  **Upload**: User uploads a file via the API.
2.  **Parse**: `Dolphin` processes the file => `ParsedDocument`.
3.  **Ingest (ROMA)**: 
    *   `IngestionAgent` reads `ParsedDocument`.
    *   Splits into `Chunks`.
    *   Embeds `Chunks` => `Vectors`.
    *   Transactionally writes to `PostgreSQL` (Metadata) and `LanceDB` (Vectors).
4.  **Query**:
    *   User asks a question.
    *   `RetrievalAgent` converts question to vector.
    *   Searches `LanceDB`.
    *   Retrieves context, synthesizes response.

## Infrastructure (Docker)

*   **FastAPI Backend**: Hosts the ROMA agents and the API endpoints. Includes the embedded LanceDB instance (persisted to disk).
*   **PostgreSQL**: Standard relational database service.
