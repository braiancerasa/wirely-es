#!/bin/bash
# Builds dist/Wirely-<rev>-x86_64.AppImage on Linux.
#   bash packaging/linux/build_appimage.sh
# Needs Python 3.10-3.13 with Wirely's requirements and PyInstaller (python3 -m pip install -r requirements.txt
# pyinstaller), and internet once to fetch appimagetool. An AppImage runs on Linux systems at least as new as
# the one it was built on, so build on the oldest distro you want to support.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
REV="$("$PY" -c 'import wirely; print(wirely.__revision__)')"
OUT="dist/Wirely-$REV-x86_64.AppImage"

echo "[Wirely] Packing Wirely with PyInstaller (a few minutes)..."
"$PY" -m PyInstaller packaging/wirely.spec --noconfirm --clean --distpath build/linux-dist --workpath build/linux-work

echo "[Wirely] Checking the packed app..."
rm -f build/selftest.txt
QT_QPA_PLATFORM=offscreen build/linux-dist/Wirely/Wirely --self-test "$ROOT/build/selftest.txt" || true
if ! grep -q '^OK' build/selftest.txt 2>/dev/null; then
  cat build/selftest.txt 2>/dev/null || true
  echo "[Wirely] The packed app failed its self-test." >&2
  exit 1
fi

echo "[Wirely] Making the AppDir..."
APPDIR=build/Wirely.AppDir
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps" \
         "$APPDIR/usr/share/icons/hicolor/256x256/mimetypes" "$APPDIR/usr/share/mime/packages"
cp -a build/linux-dist/Wirely "$APPDIR/usr/lib/wirely"
# never ship the graphics / C++ runtime libraries: the user's own must be used
find "$APPDIR/usr/lib/wirely" \( -name 'libGL.so*' -o -name 'libGLX*.so*' -o -name 'libEGL.so*' \
     -o -name 'libGLdispatch.so*' -o -name 'libdrm.so*' -o -name 'libgbm.so*' -o -name 'libxcb.so*' \
     -o -name 'libX11.so*' -o -name 'libwayland-client.so*' -o -name 'libstdc++.so*' -o -name 'libgcc_s.so*' \) -delete
cp packaging/linux/AppRun "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"
cp packaging/linux/wirely.desktop "$APPDIR/wirely.desktop"
cp packaging/linux/wirely.desktop "$APPDIR/usr/share/applications/"
cp packaging/linux/wirely-mime.xml "$APPDIR/usr/share/mime/packages/wirely.xml"
cp wirely/assets/logo_256.png "$APPDIR/wirely.png"
cp wirely/assets/logo_256.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/wirely.png"
cp wirely/assets/doc_256.png "$APPDIR/usr/share/icons/hicolor/256x256/mimetypes/application-x-wirely.png"
ln -sf wirely.png "$APPDIR/.DirIcon"

TOOL=build/appimagetool-x86_64.AppImage
if [ ! -x "$TOOL" ]; then
  echo "[Wirely] Downloading appimagetool..."
  curl -fL -o "$TOOL" https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$TOOL"
fi
echo "[Wirely] Building $OUT..."
mkdir -p dist
rm -f "$OUT"
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" --comp zstd "$APPDIR" "$OUT"
chmod +x "$OUT"
echo "[Wirely] Done: $OUT"
