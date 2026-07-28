#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"

if [ ! -x .venv/bin/python ] || [ ! -d node_modules ]; then
  echo "Dependencies are missing. Run 'make bootstrap' first." >&2
  exit 1
fi

cleanup() {
  kill "$backend_pid" "$frontend_pid" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

.venv/bin/python -m uvicorn backend.app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload &
backend_pid=$!

npm run dev &
frontend_pid=$!

echo "Frontend: http://127.0.0.1:5173"
echo "Backend health: http://127.0.0.1:8000/api/v1/health"

wait "$backend_pid" "$frontend_pid"
