#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
source_app="$project_root/dist/VLC Remote.app"
if [ -d "/Applications/VLC Remote.app" ]; then
  destination_root="/Applications"
else
  destination_root="$HOME/Applications"
fi
destination_app="$destination_root/VLC Remote.app"
shortcut_launcher_source="$project_root/scripts/start_remote_from_shortcut.sh"
shortcut_launcher_root="$HOME/.local/bin"
shortcut_launcher_destination="$shortcut_launcher_root/vlc-remote-shortcut"

if [ ! -d "$source_app" ]; then
  echo "Build the app first with 'make menu-bar-build'." >&2
  exit 1
fi

mkdir -p "$destination_root"
rm -rf "$destination_app"
ditto "$source_app" "$destination_app"
install -d -m 700 "$shortcut_launcher_root"
install -m 700 "$shortcut_launcher_source" "$shortcut_launcher_destination"
open "$destination_app"

echo "Installed and opened: $destination_app"
echo "Installed iPhone Shortcut launcher: $shortcut_launcher_destination"
