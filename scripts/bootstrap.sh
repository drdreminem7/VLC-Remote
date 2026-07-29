#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.11 or newer is required." >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js 22 or newer is required." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm 10 or newer is required." >&2
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --editable '.[dev]'
npm install

echo
echo "Bootstrap complete."
echo "Run 'make dev' for development or 'make run' for the same-origin remote."
echo "For live VLC control, quit VLC, run 'make vlc-http', then run 'make run'."
echo "The VLC helper uses a loopback-only command-line override and never changes VLC preferences."
