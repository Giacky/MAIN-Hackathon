#!/usr/bin/env bash
# Start the API and Vite client together. Ctrl-C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Homebrew node@22 is keg-only, so GUI terminals often lack `npm` on PATH.
for extra in \
  /opt/homebrew/opt/node@22/bin \
  /usr/local/opt/node@22/bin \
  /opt/homebrew/opt/node/bin \
  /usr/local/opt/node/bin \
  /opt/homebrew/bin \
  /usr/local/bin; do
  if [[ -d "$extra" ]]; then
    PATH="$extra:$PATH"
  fi
done
export PATH

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found. Install Node 20+ and put it on PATH, e.g.:" >&2
  echo "  brew install node@22" >&2
  echo "  export PATH=/opt/homebrew/opt/node@22/bin:\$PATH" >&2
  exit 1
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
