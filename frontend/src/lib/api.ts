import type {
  AgentFailure,
  HealthStatus,
  IngestRequest,
  IngestResponse,
  MemoryStatus,
  QueryRequest,
  QueryResponse,
  QueryStreamEvent,
  TailorOutput,
} from "@/types";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  public readonly status: number;
  public readonly failure: AgentFailure | undefined;

  constructor(message: string, status: number, failure?: AgentFailure) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.failure = failure;
  }
}

export async function getHealth(): Promise<HealthStatus> {
  const response = await makeRequest("/health", { method: "GET" });
  return (await response.json()) as HealthStatus;
}

export async function getMemoryStatus(): Promise<MemoryStatus> {
  const response = await makeRequest("/memory/status", { method: "GET" });
  return (await response.json()) as MemoryStatus;
}

export async function submitQuery(payload: QueryRequest): Promise<QueryResponse> {
  const response = await makeRequest("/query", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ...payload, stream: false }),
  });
  return (await response.json()) as QueryResponse;
}

export async function* streamQuery(
  payload: QueryRequest,
): AsyncGenerator<QueryStreamEvent, void, void> {
  const response = await makeRequest("/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ...payload, stream: true }),
  });

  const reader = response.body?.getReader();
  if (!reader) {
    throw new ApiError("Streaming is not supported in this environment.", 500);
  }

  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  let isReading = true;
  while (isReading) {
    const chunkResult = await reader.read();
    if (chunkResult.done) {
      buffer += decoder.decode();
    } else {
      buffer += decoder.decode(chunkResult.value, { stream: true });
    }

    let separatorIndex = buffer.indexOf("\n\n");
    while (separatorIndex !== -1) {
      const rawEvent = buffer.slice(0, separatorIndex).trim();
      buffer = buffer.slice(separatorIndex + 2);
      if (rawEvent) {
        const event = parseSseEvent(rawEvent);
        if (event) {
          yield event;
        }
      }
      separatorIndex = buffer.indexOf("\n\n");
    }

    if (chunkResult.done) {
      isReading = false;
    }
  }
}

export async function ingestDocument(input: IngestRequest): Promise<IngestResponse> {
  if (input.file === null) {
    throw new ApiError("Please select a file to ingest.", 400);
  }
  const trimmedToken = input.token.trim();
  if (trimmedToken.length === 0) {
    throw new ApiError("Bearer token is required for ingestion.", 401);
  }

  const formData = new FormData();
  formData.append("file", input.file);

  const response = await makeRequest("/ingest", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${trimmedToken}`,
    },
    body: formData,
  });
  return (await response.json()) as IngestResponse;
}

async function makeRequest(path: string, init: RequestInit): Promise<Response> {
  const url = `${API_BASE_URL}${path}`;
  const headers = mergeHeaders(init.headers);
  const response = await fetch(url, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    throw await buildApiError(response);
  }

  return response;
}

function mergeHeaders(headers?: HeadersInit): Headers {
  const merged = new Headers({ Accept: "application/json" });
  if (headers) {
    const custom = new Headers(headers);
    custom.forEach((value, key) => {
      merged.set(key, value);
    });
  }
  return merged;
}

async function buildApiError(response: Response): Promise<ApiError> {
  let failure: AgentFailure | undefined;

  try {
    const payload: unknown = await response.clone().json();
    failure = extractAgentFailure(payload);
  } catch {
    failure = undefined;
  }

  const message =
    failure?.message ??
    `Request to ${response.url} failed with status ${String(response.status)}`;
  return new ApiError(message, response.status, failure);
}

function extractAgentFailure(payload: unknown): AgentFailure | undefined {
  if (payload === null || typeof payload !== "object") {
    return undefined;
  }

  if ("detail" in payload) {
    const nested = (payload as Record<string, unknown>).detail;
    return extractAgentFailure(nested);
  }

  const candidate = payload as Partial<AgentFailure>;
  if (
    typeof candidate.agent_id === "string" &&
    typeof candidate.error_code === "string" &&
    typeof candidate.message === "string" &&
    typeof candidate.timestamp === "string"
  ) {
    return {
      agent_id: candidate.agent_id,
      error_code: candidate.error_code,
      message: candidate.message,
      recoverable: Boolean(candidate.recoverable),
      details: candidate.details ?? undefined,
      timestamp: candidate.timestamp,
    };
  }

  return undefined;
}

function parseSseEvent(chunk: string): QueryStreamEvent | undefined {
  const lines = chunk.split(/\r?\n/);
  let eventName: QueryStreamEvent["event"] | undefined;
  let dataPayload = "";

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim() as QueryStreamEvent["event"];
    } else if (line.startsWith("data:")) {
      dataPayload += `${line.slice(5).trim()}\n`;
    }
  }

  if (!eventName) {
    return undefined;
  }

  const parsedData = parseSseData(dataPayload.trim());

  if (eventName === "thinking" && typeof parsedData === "string") {
    return { event: "thinking", data: parsedData };
  }
  if (eventName === "token") {
    if (typeof parsedData === "string") {
      return { event: "token", data: parsedData };
    }
    if (isTokenEventData(parsedData)) {
      return { event: "token", data: parsedData.token };
    }
  }
  if (eventName === "complete" && isTailorOutput(parsedData)) {
    return { event: "complete", data: parsedData };
  }
  if (eventName === "error") {
    const failure = extractAgentFailure(parsedData);
    if (failure) {
      return { event: "error", data: failure };
    }
  }

  return undefined;
}

function parseSseData(payload: string): unknown {
  if (!payload) {
    return "";
  }

  const trimmed = payload.trim();
  if (
    (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
    (trimmed.startsWith("[") && trimmed.endsWith("]"))
  ) {
    try {
      return JSON.parse(trimmed);
    } catch {
      return trimmed;
    }
  }
  return trimmed;
}

function isTokenEventData(value: unknown): value is { token: string } {
  if (value === null || typeof value !== "object") {
    return false;
  }
  const record = value as Record<string, unknown>;
  return typeof record.token === "string";
}

function isTailorOutput(value: unknown): value is TailorOutput {
  if (value === null || typeof value !== "object") {
    return false;
  }

  const data = value as Record<string, unknown>;
  return (
    typeof data.content === "string" &&
    Array.isArray(data.citations) &&
    typeof data.tone_used === "string" &&
    Array.isArray(data.follow_up_suggestions) &&
    typeof data.confidence_score === "number"
  );
}
