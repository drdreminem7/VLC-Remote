#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
source_app="$project_root/dist/VLC Remote.app"
destination_root="$HOME/Applications"
destination_app="$destination_root/VLC Remote.app"

if [ ! -d "$source_app" ]; then
  echo "Build the app first with 'make menu-bar-build'." >&2
  exit 1
fi

mkdir -p "$destination_root"
rm -rf "$destination_app"
ditto "$source_app" "$destination_app"
open "$destination_app"

echo "Installed and opened: $destination_app"
