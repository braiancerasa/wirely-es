@echo off
rem ===========================================================================
rem  Builds Wirely as a normal Windows program:
rem    dist\Wirely\Wirely.exe        the app (with its support files)
rem    dist\Wirely-Setup-rN.exe      an installer (only if Inno Setup is installed)
rem  Double-click this file. The first build takes a few minutes.
rem  (GitHub builds the Windows, Mac and Linux downloads automatically - see BUILDING.md.)
rem ===========================================================================
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto :have_venv
echo [Wirely] Setting up Python first...
set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY where python >nul 2>nul && set PY=python
if not defined PY goto :no_python
%PY% -c "import sys; sys.path.insert(0, '.'); from wirely.bootstrap import ensure_environment; ensure_environment()"
if errorlevel 1 goto :failed
:have_venv
set VPY=%~dp0.venv\Scripts\python.exe

echo [Wirely] Installing the packaging tool...
"%VPY%" -m pip install --quiet --upgrade "pyinstaller>=6.16"
if errorlevel 1 ( echo Could not install PyInstaller - check your internet connection. & pause & exit /b 1 )

echo [Wirely] Packing Wirely into an .exe (this takes a few minutes)...
"%VPY%" -m PyInstaller packaging\wirely.spec --noconfirm --clean --distpath dist --workpath build
if errorlevel 1 goto :failed

if exist "%TEMP%\wirely_selftest.txt" del "%TEMP%\wirely_selftest.txt"
start "" /wait "dist\Wirely\Wirely.exe" --self-test "%TEMP%\wirely_selftest.txt"
findstr /b "OK" "%TEMP%\wirely_selftest.txt" >nul 2>nul
if errorlevel 1 (
  if exist "%TEMP%\wirely_selftest.txt" type "%TEMP%\wirely_selftest.txt"
  goto :failed
)
echo [Wirely] dist\Wirely\Wirely.exe works.

for /f %%v in ('"%VPY%" -c "import wirely; print(wirely.__version__)"') do set VER=%%v
for /f %%r in ('"%VPY%" -c "import wirely; print(wirely.__revision__)"') do set REV=%%r

set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe
if defined ISCC (
  echo [Wirely] Building the installer...
  "%ISCC%" /Q /DAppVersion=%VER% /DAppRevision=%REV% "packaging\Wirely.iss"
  if errorlevel 1 ( echo The installer build failed - the app itself is still in dist\Wirely. ) else ( echo [Wirely] Installer: dist\Wirely-Setup-%REV%.exe )
) else (
  echo [Wirely] Skipped the installer: Inno Setup isn't installed. Get it free from https://jrsoftware.org/isdl.php
)
echo.
echo Done! Wirely is in the dist folder.
explorer dist
pause
exit /b 0

:no_python
echo Python was not found - install it from https://www.python.org (tick "Add python.exe to PATH").
pause
exit /b 1

:failed
echo.
echo The build failed - scroll up for the error, or send a screenshot of this window.
pause
exit /b 1
