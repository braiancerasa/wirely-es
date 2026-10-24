#!/bin/bash
# Adds Wirely to your Linux desktop's app menu and makes .wirely files open in it, with their own icon.
#   bash packaging/linux/install-desktop.sh /path/to/Wirely-1.0.0-x86_64.AppImage
# (for your user only — nothing needs sudo). Run it again after moving the AppImage.
set -euo pipefail
APPIMAGE="$(readlink -f "${1:?give the path to the Wirely AppImage}")"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
mkdir -p "$DATA/applications" "$DATA/mime/packages" "$DATA/icons/hicolor/256x256/apps" \
         "$DATA/icons/hicolor/256x256/mimetypes"
sed "s|^Exec=.*|Exec=\"$APPIMAGE\" %F|" "$ROOT/packaging/linux/wirely.desktop" > "$DATA/applications/wirely.desktop"
cp "$ROOT/packaging/linux/wirely-mime.xml" "$DATA/mime/packages/wirely.xml"
cp "$ROOT/wirely/assets/logo_256.png" "$DATA/icons/hicolor/256x256/apps/wirely.png"
cp "$ROOT/wirely/assets/doc_256.png" "$DATA/icons/hicolor/256x256/mimetypes/application-x-wirely.png"
update-mime-database "$DATA/mime" >/dev/null 2>&1 || true
update-desktop-database "$DATA/applications" >/dev/null 2>&1 || true
xdg-mime default wirely.desktop application/x-wirely 2>/dev/null || true
gtk-update-icon-cache "$DATA/icons/hicolor" >/dev/null 2>&1 || true
echo "Wirely is now in your app menu, and .wirely files open with it."
