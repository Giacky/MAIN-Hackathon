#!/usr/bin/env bash
# Start the API and Vite client together. Ctrl-C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

cleanup() {
  kill "$api_pid" "$front_pid" 2>/dev/null || true
  wait 2>/dev/null || true
}

uvicorn api.main:app --host 127.0.0.1 --port 8000 &
api_pid=$!
(
  cd frontend
  npm run dev -- --host
) &
front_pid=$!

trap cleanup EXIT INT TERM
wait
