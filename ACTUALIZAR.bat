@echo off
rem ===========================================================================
rem  Atajo para las herramientas de actualización.
rem  Doble clic: muestra el estado.  Con argumento: ACTUALIZAR.bat buscar
rem ===========================================================================
setlocal
cd /d "%~dp0"

set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

if "%~1"=="" (
    "%PY%" tools\actualizar\actualizar.py estado
) else (
    "%PY%" tools\actualizar\actualizar.py %*
)
echo.
pause
