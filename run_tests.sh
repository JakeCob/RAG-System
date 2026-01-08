#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "Running pytest (with coverage)..."
pytest tests/ -v --cov=src/app --cov-report=term-missing

echo "Running mypy..."
mypy src/

echo "Running ruff check..."
ruff check src/ tests/

echo "Running ruff format check..."
ruff format --check src/ tests/

echo "All checks passed."
