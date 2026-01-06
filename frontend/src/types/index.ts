/**
 * Shared TypeScript types that mirror the backend Pydantic schemas.
 * Reference: docs/02_AGENT_SPECS.md & src/app/schemas/*
 */

/** Backend persona literal */
export type Persona = "Technical" | "Executive" | "General";

/** Standardized agent failure payload */
export interface AgentFailure {
  agent_id: string;
  error_code: string;
  message: string;
  recoverable: boolean;
  details?: Record<string, unknown> | undefined;
  timestamp: string;
}

/** Response from GET /health */
export interface HealthStatus {
  db: "connected" | "degraded" | "offline";
  agents: "ready" | "initializing" | "degraded";
}

/** Request body for POST /query */
export interface QueryRequest {
  text: string;
  persona?: Persona;
  stream?: boolean;
}

/** Citation returned by the Tailor agent */
export interface SourceCitation {
  source_id: string;
  chunk_id: string;
  text_snippet: string;
  url?: string | null;
}

/** Tailor agent response mirrored for the frontend */
export interface TailorOutput {
  content: string;
  citations: SourceCitation[];
  tone_used: string;
  follow_up_suggestions: string[];
  confidence_score: number;
}

/** Alias for clarity when working with /query responses */
export type QueryResponse = TailorOutput;

/** A single Server-Sent Event emitted by the /query stream */
export type QueryStreamEvent =
  | { event: "token"; data: { index: number; token: string } }
  | { event: "complete"; data: TailorOutput }
  | { event: "error"; data: AgentFailure };

/** Response body from POST /ingest */
export interface IngestResponse {
  task_id: string;
  filename: string;
  status: "queued" | "processing" | "completed";
}

/** Minimal shape for ingestion requests */
export interface IngestRequest {
  file: File | null;
  token: string;
}
