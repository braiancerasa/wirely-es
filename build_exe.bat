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
echo [Wirely] Configurando Python primero...
set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY where python >nul 2>nul && set PY=python
if not defined PY goto :no_python
%PY% -c "import sys; sys.path.insert(0, '.'); from wirely.bootstrap import ensure_environment; ensure_environment()"
if errorlevel 1 goto :failed
:have_venv
set VPY=%~dp0.venv\Scripts\python.exe

echo [Wirely] Instalando la herramienta de empaquetado...
"%VPY%" -m pip install --quiet --upgrade "pyinstaller>=6.16"
if errorlevel 1 ( echo No se pudo instalar PyInstaller - revise su conexión a internet. & pause & exit /b 1 )

echo [Wirely] Empaquetando Wirely en un .exe (tarda unos minutos)...
"%VPY%" -m PyInstaller packaging\wirely.spec --noconfirm --clean --distpath dist --workpath build
if errorlevel 1 goto :failed

if exist "%TEMP%\wirely_selftest.txt" del "%TEMP%\wirely_selftest.txt"
start "" /wait "dist\Wirely\Wirely.exe" --self-test "%TEMP%\wirely_selftest.txt"
findstr /b "OK" "%TEMP%\wirely_selftest.txt" >nul 2>nul
if errorlevel 1 (
  if exist "%TEMP%\wirely_selftest.txt" type "%TEMP%\wirely_selftest.txt"
  goto :failed
)
echo [Wirely] dist\Wirely\Wirely.exe funciona.

for /f %%v in ('"%VPY%" -c "import wirely; print(wirely.__version__)"') do set VER=%%v
for /f %%r in ('"%VPY%" -c "import wirely; print(wirely.__revision__)"') do set REV=%%r

set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe
if defined ISCC (
  echo [Wirely] Creando el instalador...
  "%ISCC%" /Q /DAppVersion=%VER% /DAppRevision=%REV% "packaging\Wirely.iss"
  if errorlevel 1 ( echo Falló la creación del instalador - la app sigue en dist\Wirely. ) else ( echo [Wirely] Instalador: dist\Wirely-Setup-%REV%.exe )
) else (
  echo [Wirely] Se omitió el instalador: Inno Setup no está instalado. Descárguelo gratis desde https://jrsoftware.org/isdl.php
)
echo.
echo ¡Listo! Wirely está en la carpeta dist.
explorer dist
pause
exit /b 0

:no_python
echo No se encontró Python - instálelo desde https://www.python.org (marque "Add python.exe to PATH").
pause
exit /b 1

:failed
echo.
echo Falló la compilación - desplácese hacia arriba para ver el error o envíe una captura de esta ventana.
pause
exit /b 1
