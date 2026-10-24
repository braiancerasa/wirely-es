# Building Wirely

This is for people who want to run Wirely from its source code, change it, or make the installers themselves.
To just **use** Wirely, download it from the [latest release](https://github.com/richiewillmott/Wirely/releases/latest)
instead — see the [README](README.md).

## Run from source

You need Python 3.10–3.13 (64-bit) from https://www.python.org. On Windows, tick "Add python.exe to PATH".
Then start it — **the first run installs everything automatically**:

- **Windows:** double-click `run_wirely.bat` (or `start.py` if Smart App Control blocks .bat files)
- **Mac / Linux:** run `./run_wirely.sh` (or `python3 start.py`)

The first start creates a private `.venv` folder and downloads Qt and numpy (about 170 MB). To reinstall from
scratch, delete the `.venv` folder. Or manage it yourself: `pip install -r requirements.txt` then `python -m wirely`.

## Automatic builds on GitHub (Windows, Mac and Linux)

`.github/workflows/build.yml` does it all on GitHub's own computers:

- **Every push** runs the automatic tests.
- **Publishing a release** builds the Windows installer, the Mac `.dmg` (Apple Silicon) and the Linux AppImage,
  checks each one starts (its self-test), and attaches all three to the release.
- **Actions → Build (Windows, Mac, Linux) → Run workflow** makes a test build instead: the files, a screenshot
  of Wirely running on the Mac and the logs go on a private *Test builds* draft release (only you can see it).

To release: bump `__version__` in `wirely/__init__.py` (and `pyproject.toml`), push, then on GitHub
**Releases → Draft a new release**, tag it (e.g. `v1.0.1`) and **Publish**. The downloads appear on the release
about 15 minutes later.

## Make a Windows program yourself

Double-click **`build_exe.bat`**. It packs Wirely into **`dist\Wirely\Wirely.exe`** (runs on any 64-bit Windows
PC without Python) and, if [Inno Setup](https://jrsoftware.org/isdl.php) (free) is installed, also builds
**`dist\Wirely-Setup-<version>.exe`** with Start-menu and desktop shortcuts and `.wirely` files opening in Wirely.

## Mac and Linux yourself

- Mac: `python3 -m pip install -r requirements.txt pyinstaller` then `bash packaging/mac/build_mac.sh`
- Linux: `python3 -m pip install -r requirements.txt pyinstaller` then `bash packaging/linux/build_appimage.sh`
  (an AppImage runs on Linux systems at least as new as the one it was built on).

## Icons

The logo and the `.wirely` file icon are drawn in code (`wirely/ui/icons.py`). After changing them, run
`python tools/make_icons.py` (needs Pillow) to rewrite the PNG, ICO and SVG files in `wirely/assets`.

## Where things are

```
wirely/
  model/       the circuit (parts library, wires, connections, files) — no Qt
  sim/         the circuit solver, part models, current flow, sound synthesis — no Qt
  ui/          the window: sheet, gallery, graph, dialogs, splash, sound output
packaging/     PyInstaller recipe, Windows installer, Mac and Linux build scripts
tests/         pytest: model, solver (vs hand-worked answers and ngspice), editor and live simulation
tools/         example circuits, icons and screenshots
```
