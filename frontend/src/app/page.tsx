"use client";

import { useEffect, useRef, useState } from "react";

import {
  ApiError,
  getHealth,
  getMemoryStatus,
  ingestDocument,
  streamQuery,
} from "@/lib/api";
import type {
  AgentFailure,
  HealthStatus,
  IngestResponse,
  MemoryStatus,
  Persona,
  QueryResponse,
} from "@/types";

const PERSONAS: Persona[] = ["General", "Technical", "Executive"];
const RECOMMENDED_INGEST_SIZE_MB = 20;

type NoticeTone = "success" | "info" | "warning";

export default function Home(): JSX.Element {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthMessage, setHealthMessage] = useState<string | null>(null);
  const [memoryStatus, setMemoryStatus] = useState<MemoryStatus | null>(null);
  const [memoryMessage, setMemoryMessage] = useState<string | null>(null);
  const [queryText, setQueryText] = useState("");
  const [persona, setPersona] = useState<Persona>("General");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [streamingStatus, setStreamingStatus] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [failure, setFailure] = useState<AgentFailure | null>(null);
  const [formMessage, setFormMessage] = useState<string | null>(null);

  const [ingestFile, setIngestFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [ingestToken, setIngestToken] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const [ingestResult, setIngestResult] = useState<IngestResponse | null>(null);
  const [ingestFailure, setIngestFailure] = useState<AgentFailure | null>(null);
  const [ingestNotice, setIngestNotice] = useState<{ tone: NoticeTone; message: string } | null>(
    null,
  );
  const ingestFormRef = useRef<HTMLFormElement | null>(null);
  const ingestFileSizeMb = ingestFile ? ingestFile.size / (1024 * 1024) : null;
  const ingestFileTooLarge =
    ingestFileSizeMb !== null && ingestFileSizeMb > RECOMMENDED_INGEST_SIZE_MB;
  const ingestFileSizeLabel = ingestFileSizeMb === null ? "" : ingestFileSizeMb.toFixed(1);

  useEffect(() => {
    let mounted = true;
    getHealth()
      .then((snapshot) => {
        if (mounted) {
          setHealth(snapshot);
        }
      })
      .catch((error: unknown) => {
        if (!mounted) {
          return;
        }
        const fallback =
          error instanceof ApiError ? error.message : "Unable to load system status.";
        setHealthMessage(fallback);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const refreshMemoryStatus = async (): Promise<void> => {
    try {
      const snapshot = await getMemoryStatus();
      setMemoryStatus(snapshot);
      setMemoryMessage(null);
      if (snapshot.chunk_count > 0) {
        setFormMessage(null);
      }
    } catch (error: unknown) {
      const fallback =
        error instanceof ApiError ? error.message : "Unable to load document status.";
      setMemoryMessage(fallback);
    }
  };

  useEffect(() => {
    void refreshMemoryStatus();
  }, []);

  const handleQuerySubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    const trimmed = queryText.trim();
    if (trimmed.length === 0) {
      setFormMessage("Please enter a question for ROMA to process.");
      return;
    }
    if (memoryStatus === null) {
      setFormMessage("Checking indexed documents. Please try again in a moment.");
      return;
    }
    if (memoryStatus.chunk_count === 0) {
      setFormMessage("Ingest a document before submitting a query.");
      return;
    }
    setIsStreaming(true);
    setFormMessage(null);
    setFailure(null);
    setResult(null);
    setStreamingText("");
    setStreamingStatus("Starting...");

    try {
      for await (const event of streamQuery({ text: trimmed, persona })) {
        // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
        if (event.event === "thinking") {
          setStreamingStatus(event.data);
          continue;
        }
        // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
        if (event.event === "token") {
          setStreamingText((prev) => prev + event.data);
          continue;
        }
        // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
        if (event.event === "complete") {
          setResult(event.data);
          setStreamingText(event.data.content);
          setStreamingStatus("Complete");
          break;
        }
        // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
        if (event.event === "error") {
          setFailure(event.data);
          setStreamingStatus("Error");
          break;
        }
      }
    } catch (error: unknown) {
      if (error instanceof ApiError) {
        if (error.failure) {
          setFailure(error.failure);
        } else {
          setFormMessage(error.message);
        }
      } else {
        setFormMessage("Unexpected error while executing the query.");
      }
    } finally {
      setIsStreaming(false);
    }
  };

  const handleIngestSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    setIngestNotice(null);
    setIngestFailure(null);
    setIngestResult(null);

    if (ingestFile === null) {
      setIngestNotice({ tone: "warning", message: "Select a document to upload." });
      return;
    }
    if (ingestToken.trim().length === 0) {
      setIngestNotice({ tone: "warning", message: "Provide the ingestion Bearer token." });
      return;
    }

    setIngesting(true);
    try {
      const response = await ingestDocument({
        file: ingestFile,
        token: ingestToken,
      });
      setIngestResult(response);
      setIngestNotice({ tone: "success", message: "Document accepted for processing." });
      setIngestFile(null);
      setFileInputKey((value) => value + 1);
      await refreshMemoryStatus();
    } catch (error: unknown) {
      if (error instanceof ApiError && error.failure) {
        setIngestFailure(error.failure);
      } else if (error instanceof ApiError) {
        setIngestNotice({ tone: "warning", message: error.message });
      } else {
        setIngestNotice({
          tone: "warning",
          message: "Unable to upload the document. Please try again.",
        });
      }
    } finally {
      setIngesting(false);
    }
  };

  const memoryChecked = memoryStatus !== null;
  const memoryEmpty = memoryChecked && memoryStatus.chunk_count === 0;
  const queryLocked = !memoryChecked || memoryEmpty;

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
        <header className="rounded-2xl bg-white px-6 py-8 shadow-sm">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600">
                Multi-Source Agentic RAG
              </p>
              <h1 className="mt-2 text-3xl font-bold text-slate-900">ROMA Knowledge Console</h1>
              <p className="mt-2 text-base text-slate-600">
                Submit a query, inspect grounded citations, and optionally ingest fresh documents.
              </p>
            </div>
            <div className="space-y-3 rounded-xl border border-slate-100 bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-700">System Status</p>
              {health !== null ? (
                <div className="flex flex-wrap gap-2 text-sm">
                  <StatusBadge label="Database" status={health.db} />
                  <StatusBadge label="Agents" status={health.agents} />
                </div>
              ) : (
                <p className="text-sm text-slate-500">
                  {healthMessage ?? "Checking LanceDB and agents..."}
                </p>
              )}
              {memoryStatus !== null ? (
                <p className="text-xs text-slate-500">
                  Indexed chunks: {memoryStatus.chunk_count}
                </p>
              ) : null}
            </div>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[2fr,1fr]">
          <form
            onSubmit={(event) => {
              void handleQuerySubmit(event);
            }}
            className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">Ask ROMA</h2>
              <label className="text-sm text-slate-600">
                Persona
                <select
                  className="ml-3 rounded-md border border-slate-200 bg-white px-3 py-1 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
                  value={persona}
                  onChange={(event) => {
                    setPersona(event.target.value as Persona);
                  }}
                >
                  {PERSONAS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <textarea
              className="mt-4 h-40 w-full resize-none rounded-xl border border-slate-200 bg-slate-50 p-4 text-base text-slate-900 outline-none transition focus:border-indigo-500 focus:bg-white"
              placeholder="e.g., Compare Q3 cloud budget deltas vs. our pricing plan updates."
              value={queryText}
              disabled={isStreaming || queryLocked}
              onChange={(event) => {
                setQueryText(event.target.value);
              }}
            />

            {formMessage !== null ? (
              <p className="mt-2 text-sm text-rose-600" role="alert">
                {formMessage}
              </p>
            ) : null}

            {queryLocked ? (
              <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                <p className="font-semibold">
                  {memoryChecked ? "No indexed documents yet." : "Checking document index..."}
                </p>
                <p className="mt-1">
                  {memoryChecked
                    ? "Upload a document to activate ROMA queries."
                    : "Once indexing is ready, you can submit queries."}
                </p>
                <button
                  type="button"
                  className="mt-3 inline-flex items-center rounded-lg border border-amber-300 bg-white px-3 py-1 text-xs font-semibold text-amber-700 transition hover:bg-amber-100"
                  onClick={() => {
                    ingestFormRef.current?.scrollIntoView({ behavior: "smooth" });
                  }}
                >
                  Go to ingestion
                </button>
              </div>
            ) : null}

            {memoryMessage !== null ? (
              <p className="mt-2 text-xs text-slate-500">{memoryMessage}</p>
            ) : null}

            {streamingStatus !== null ? (
              <p className="mt-2 text-xs text-slate-500">
                Status: {streamingStatus}
                {isStreaming ? <span className="ml-2 animate-pulse">●</span> : null}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={isStreaming || queryLocked || queryText.trim().length === 0}
              className="mt-4 inline-flex items-center justify-center rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-300"
            >
              {isStreaming ? "Streaming..." : "Run Query"}
            </button>
          </form>

          <form
            onSubmit={(event) => {
              void handleIngestSubmit(event);
            }}
            ref={ingestFormRef}
            className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm"
          >
            <h2 className="text-lg font-semibold text-slate-900">Ingest a Document</h2>
            <p className="mt-1 text-sm text-slate-600">
              Upload PDFs, slides, or docs to update LanceDB (requires Bearer token).
            </p>

            <label className="mt-4 block text-sm font-medium text-slate-700">
              Document
              <input
                key={fileInputKey}
                type="file"
                accept=".pdf,.docx,.pptx,.txt,.md,.xlsx,.xls,.csv"
                className="mt-2 w-full rounded-xl border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-600 file:mr-4 file:rounded-lg file:border-0 file:bg-indigo-50 file:px-3 file:py-2 file:text-indigo-600"
                onChange={(event) => {
                  const files = event.target.files;
                  if (files && files.length > 0) {
                    const file = files.item(0);
                    setIngestFile(file ?? null);
                    return;
                  }
                  setIngestFile(null);
                }}
              />
              {ingestFile !== null ? (
                <p className="mt-1 text-xs text-slate-500">
                  Selected: <span className="font-medium">{ingestFile.name}</span>{" "}
                  <span className="text-slate-400">({ingestFileSizeLabel} MB)</span>
                </p>
              ) : null}
              {ingestFileTooLarge ? (
                <p className="mt-2 text-xs text-amber-700">
                  This file is {ingestFileSizeLabel} MB. Hosted ingestion can time out for large
                  files; consider splitting the document or using a smaller upload (recommended
                  under {RECOMMENDED_INGEST_SIZE_MB} MB).
                </p>
              ) : null}
            </label>

            <label className="mt-4 block text-sm font-medium text-slate-700">
              Bearer Token
              <input
                type="password"
                className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-500"
                value={ingestToken}
                onChange={(event) => {
                  setIngestToken(event.target.value);
                }}
                placeholder="•••••••••••"
              />
            </label>

            {ingestNotice !== null ? (
              <p
                className={`mt-3 text-sm ${
                  ingestNotice.tone === "success"
                    ? "text-emerald-600"
                    : ingestNotice.tone === "warning"
                      ? "text-amber-600"
                      : "text-slate-600"
                }`}
              >
                {ingestNotice.message}
              </p>
            ) : null}

            {ingestFailure !== null ? (
              <FailureAlert title="Ingestion Error" failure={ingestFailure} className="mt-3" />
            ) : null}

            {ingestResult !== null ? (
              <div className="mt-3 rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                <p>
                  Task <span className="font-semibold">{ingestResult.task_id}</span> queued for{" "}
                  <span className="font-semibold">{ingestResult.filename}</span> (
                  {ingestResult.status})
                </p>
              </div>
            ) : null}

            <button
              type="submit"
              disabled={ingesting}
              className="mt-4 w-full rounded-xl border border-indigo-600 bg-white px-4 py-2 text-sm font-semibold text-indigo-600 transition hover:bg-indigo-50 disabled:cursor-not-allowed disabled:border-indigo-200 disabled:text-indigo-300"
            >
              {ingesting ? "Uploading..." : "Send to Ingestion"}
            </button>
          </form>
        </section>

        <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Grounded Answer</h2>
              <p className="text-sm text-slate-600">
                ROMA responses must cite every assertion. Citations appear below.
              </p>
            </div>
            {result !== null ? (
              <div className="flex flex-wrap gap-2 text-sm">
                <span className="rounded-full bg-slate-100 px-3 py-1 font-medium text-slate-800">
                  Tone: {result.tone_used}
                </span>
                <span className="rounded-full bg-slate-100 px-3 py-1 font-medium text-slate-800">
                  Confidence: {(result.confidence_score * 100).toFixed(0)}%
                </span>
              </div>
            ) : null}
          </div>

          {failure !== null ? (
            <FailureAlert title="Agent Failure" failure={failure} className="mt-4" />
          ) : null}

          {streamingText.length > 0 && result === null && failure === null ? (
            <div className="mt-6 rounded-2xl border border-slate-100 bg-slate-50 px-4 py-5 text-slate-900">
              <p className="whitespace-pre-line text-base leading-relaxed">
                {streamingText}
                {isStreaming ? <span className="ml-1 animate-pulse">▊</span> : null}
              </p>
            </div>
          ) : null}

          {result !== null ? (
            <div className="mt-6 space-y-6">
              <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-5 text-slate-900">
                <p className="whitespace-pre-line text-base leading-relaxed">{result.content}</p>
              </div>

              {result.follow_up_suggestions.length > 0 ? (
                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                    Follow-up suggestions
                  </h3>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {result.follow_up_suggestions.map((suggestion) => (
                      <span
                        key={suggestion}
                        className="rounded-full bg-indigo-50 px-3 py-1 text-sm text-indigo-700"
                      >
                        {suggestion}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}

              {result.citations.length > 0 ? (
                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                    Source citations
                  </h3>
                  <ol className="mt-3 space-y-4 text-sm text-slate-700">
                    {result.citations.map((citation, index) => (
                      <li
                        key={`${citation.source_id}-${citation.chunk_id}`}
                        className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="font-semibold text-slate-900">
                            [{index + 1}] {citation.source_id}
                          </p>
                          {citation.url !== undefined && citation.url !== null && citation.url !== "" ? (
                            <a
                              href={citation.url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-sm font-medium text-indigo-600 hover:text-indigo-500"
                            >
                              Open source
                            </a>
                          ) : null}
                        </div>
                        <p className="mt-2 text-slate-600">{citation.text_snippet}</p>
                        <p className="mt-1 text-xs text-slate-500">Chunk {citation.chunk_id}</p>
                      </li>
                    ))}
                  </ol>
                </div>
              ) : null}
            </div>
          ) : failure === null && streamingText.length === 0 ? (
            <p className="mt-6 text-sm text-slate-500">
              Submit a question to see ROMA&apos;s grounded response with citations.
            </p>
          ) : null}
        </section>
      </div>
    </main>
  );
}

function StatusBadge({
  label,
  status,
}: {
  label: string;
  status: HealthStatus["db"] | HealthStatus["agents"];
}): JSX.Element {
  const palette =
    status === "connected" || status === "ready"
      ? "bg-emerald-100 text-emerald-700"
      : status === "degraded"
        ? "bg-amber-100 text-amber-700"
        : "bg-rose-100 text-rose-700";
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 ${palette}`}>
      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</span>
      <span className="text-sm font-semibold capitalize">{status}</span>
    </span>
  );
}

function FailureAlert({
  title,
  failure,
  className,
}: {
  title: string;
  failure: AgentFailure;
  className?: string;
}): JSX.Element {
  return (
    <div
      className={`rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 ${className ?? ""}`}
    >
      <p className="font-semibold">
        {title}: {failure.error_code}
      </p>
      <p className="mt-1">{failure.message}</p>
      <p className="mt-1 text-xs text-rose-700">Source: {failure.agent_id}</p>
    </div>
  );
}
