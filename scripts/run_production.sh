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
echo "Phase 2 enforces bearer authentication on status and control endpoints."
echo "If VLC_REMOTE_ACCESS_TOKEN is empty, protected requests are safely rejected."
echo "Live VLC control remains disabled until a safe VLC configuration is verified."

exec .venv/bin/python -m uvicorn backend.app.main:app \
  --host "$remote_host" \
  --port "$remote_port"
