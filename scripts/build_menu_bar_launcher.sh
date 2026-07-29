#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
app_root="$project_root/dist/Mac VLC Remote.app"
contents="$app_root/Contents"
iconset="$project_root/dist/AppIcon.iconset"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "The menu-bar launcher can only be built on macOS." >&2
  exit 1
fi

if ! command -v swiftc >/dev/null 2>&1; then
  echo "Swift is required to build the menu-bar launcher." >&2
  exit 1
fi

rm -rf "$app_root"
rm -rf "$iconset"
mkdir -p "$contents/MacOS" "$contents/Resources"
swiftc -parse-as-library "$project_root/macos/MenuBarLauncher.swift" \
  -o "$contents/MacOS/Mac VLC Remote"
install -m 644 "$project_root/macos/Info.plist" "$contents/Info.plist"
mkdir -p "$iconset"
for icon_size in 16 32 128 256 512; do
  sips -z "$icon_size" "$icon_size" "$project_root/macos/AppIcon.png" \
    --out "$iconset/icon_${icon_size}x${icon_size}.png" >/dev/null
  retina_size=$((icon_size * 2))
  sips -z "$retina_size" "$retina_size" "$project_root/macos/AppIcon.png" \
    --out "$iconset/icon_${icon_size}x${icon_size}@2x.png" >/dev/null
done
iconutil -c icns "$iconset" -o "$contents/Resources/AppIcon.icns"
rm -rf "$iconset"

echo "Built: $app_root"
echo "Open it with 'make menu-bar'. On first launch, choose this project folder."
