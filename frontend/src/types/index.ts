/**
 * Shared TypeScript types for the RAG System frontend.
 * These should mirror the Pydantic schemas from the backend.
 */

/** Response from the /health endpoint */
export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  services: {
    vectordb: boolean;
    llm: boolean;
  };
}

/** Input for the /query endpoint */
export interface QueryInput {
  query: string;
  persona?: "technical" | "executive" | "general";
  maxResults?: number;
}

/** Citation attached to a response */
export interface SourceCitation {
  documentId: string;
  chunkId: string;
  text: string;
  relevanceScore: number;
  metadata: Record<string, unknown>;
}

/** Response from the /query endpoint */
export interface QueryResponse {
  answer: string;
  citations: SourceCitation[];
  processingTimeMs: number;
}

/** Input for the /ingest endpoint */
export interface IngestInput {
  file: File;
  sourceType: "local" | "gdrive" | "web";
  metadata?: Record<string, unknown>;
}

/** Response from the /ingest endpoint */
export interface IngestResponse {
  documentId: string;
  chunksCreated: number;
  status: "success" | "partial" | "failed";
  errors?: string[];
}

/** Error response structure */
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}
