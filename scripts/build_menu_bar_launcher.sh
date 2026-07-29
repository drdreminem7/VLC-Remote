#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
app_root="$project_root/dist/Mac VLC Remote.app"
contents="$app_root/Contents"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "The menu-bar launcher can only be built on macOS." >&2
  exit 1
fi

if ! command -v swiftc >/dev/null 2>&1; then
  echo "Swift is required to build the menu-bar launcher." >&2
  exit 1
fi

rm -rf "$app_root"
mkdir -p "$contents/MacOS" "$contents/Resources"
swiftc -parse-as-library "$project_root/macos/MenuBarLauncher.swift" \
  -o "$contents/MacOS/Mac VLC Remote"
install -m 644 "$project_root/macos/Info.plist" "$contents/Info.plist"

echo "Built: $app_root"
echo "Open it with 'make menu-bar'. On first launch, choose this project folder."
