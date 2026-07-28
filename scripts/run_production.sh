#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"

if [ ! -x .venv/bin/python ] || [ ! -d node_modules ]; then
  echo "Dependencies are missing. Run 'make bootstrap' first." >&2
  exit 1
fi

npm run build

remote_host=${VLC_REMOTE_HOST:-127.0.0.1}
remote_port=${VLC_REMOTE_PORT:-8000}

echo "Serving the UI and API together at http://${remote_host}:${remote_port}"
echo "Phase 1 has no access-token enforcement; keep this on a trusted machine."

exec .venv/bin/python -m uvicorn backend.app.main:app \
  --host "$remote_host" \
  --port "$remote_port"
