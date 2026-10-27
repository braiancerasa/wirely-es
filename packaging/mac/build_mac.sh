#!/bin/bash
# Builds dist/Wirely.app and dist/Wirely-<rev>-mac-<arch>.dmg on a Mac.
#   bash packaging/mac/build_mac.sh
# Needs Python 3.10-3.13 with Wirely's requirements and PyInstaller (python3 -m pip install -r requirements.txt
# pyinstaller). GitHub Actions runs this automatically (.github/workflows/build.yml), so you don't need a Mac.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
REV="$("$PY" -c 'import wirely; print(wirely.__revision__)')"
ARCH="$(uname -m)"; [ "$ARCH" = "arm64" ] || ARCH="intel"
mkdir -p build dist

make_icns() {   # make_icns <prefix of PNGs in wirely/assets> <output .icns>
  local set="build/$(basename "$2" .icns).iconset"
  rm -rf "$set"; mkdir -p "$set"
  for s in 16 32 128 256 512; do
    cp "wirely/assets/$1_$s.png" "$set/icon_${s}x${s}.png"
    d=$((s * 2))
    cp "wirely/assets/$1_$d.png" "$set/icon_${s}x${s}@2x.png"
  done
  iconutil -c icns "$set" -o "$2"
}
echo "[Wirely] Creando los iconos de la app y de los documentos..."
make_icns logo build/Wirely.icns
make_icns doc build/WirelyDoc.icns

echo "[Wirely] Empaquetando Wirely con PyInstaller (unos minutos)..."
"$PY" -m PyInstaller packaging/wirely.spec --noconfirm --clean --distpath dist --workpath build/mac-work

echo "[Wirely] Verificando la app empaquetada..."
rm -f build/selftest.txt
dist/Wirely.app/Contents/MacOS/Wirely --self-test "$ROOT/build/selftest.txt" || true
if ! grep -q '^OK' build/selftest.txt 2>/dev/null; then
  cat build/selftest.txt 2>/dev/null || true
  echo "[Wirely] La app empaquetada no pasó su autoprueba." >&2
  exit 1
fi

# not signed with an Apple Developer ID: sign it "ad hoc" so Apple Silicon Macs will run it at all
codesign --force --deep --sign - dist/Wirely.app

echo "[Wirely] Creando el .dmg..."
DMG="dist/Wirely-$REV-mac-$ARCH.dmg"
STAGE=build/dmg
rm -rf "$STAGE" "$DMG"; mkdir -p "$STAGE"
cp -R dist/Wirely.app "$STAGE/"
ln -s /Applications "$STAGE/Applications"
hdiutil create -volname "Wirely" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
echo "[Wirely] Listo: $DMG"
