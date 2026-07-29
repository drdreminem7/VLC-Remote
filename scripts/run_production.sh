#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"

if [ ! -x .venv/bin/python ] || [ ! -d node_modules ]; then
  echo "Dependencies are missing. Run 'make bootstrap' first." >&2
  exit 1
fi

npm run build

remote_host=${VLC_REMOTE_HOST:-0.0.0.0}
remote_port=${VLC_REMOTE_PORT:-8000}

if [ -z "${VLC_REMOTE_ALLOWED_HOSTS:-}" ]; then
  VLC_REMOTE_ALLOWED_HOSTS="$(.venv/bin/python scripts/show_pairing_qr.py --print-allowed-hosts)"
  export VLC_REMOTE_ALLOWED_HOSTS
fi

echo "Serving the UI and API together on port ${remote_port}."
echo "Use 'make vlc-http' first if VLC has not been launched with its local HTTP override."
.venv/bin/python scripts/show_pairing_qr.py --port "$remote_port"

exec .venv/bin/python -m uvicorn backend.app.main:app \
  --host "$remote_host" \
  --port "$remote_port"
