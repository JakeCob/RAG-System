#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"

cd "${ROOT_DIR}"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
}

trap cleanup INT TERM EXIT

echo "Starting FastAPI backend on http://localhost:8000 ..."
(
  cd "${ROOT_DIR}"
  uvicorn app.api:app --app-dir src --host 0.0.0.0 --port 8000 --reload
) &
BACKEND_PID=$!

echo "Starting Next.js frontend on http://localhost:3000 ..."
(
  cd "${FRONTEND_DIR}"
  npm run dev
) &
FRONTEND_PID=$!

if command -v wait &>/dev/null && wait -n 2>/dev/null; then
  while true; do
    if wait -n "${BACKEND_PID}" "${FRONTEND_PID}"; then
      :
    else
      break
    fi
  done
else
  wait "${BACKEND_PID}"
  wait "${FRONTEND_PID}"
fi
