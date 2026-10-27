"""First-run setup: create a private virtual environment next to the project and install the
requirements into it, then launch Wirely from there. Standard library only, so it can run
before anything is installed.

Used by start.py (and the .bat/.sh launchers), and as a fallback by `python -m wirely`.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import venv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV = os.path.join(ROOT, ".venv")
REQS = os.path.join(ROOT, "requirements.txt")
MARKER = os.path.join(VENV, ".wirely-installed")
REQUIRED_MODULES = ("PySide6", "numpy")
MIN_PY, MAX_PY = (3, 10), (3, 13)


def _say(msg):
    print(f"[Wirely] {msg}", flush=True)


def _venv_python():
    if os.name == "nt":
        return os.path.join(VENV, "Scripts", "python.exe")
    return os.path.join(VENV, "bin", "python")


def _running_in_venv():
    try:
        return os.path.samefile(sys.prefix, VENV)
    except OSError:
        return False


def _reqs_hash():
    with open(REQS, "rb") as fh:
        return hashlib.sha1(fh.read()).hexdigest()


def missing_modules(python=None):
    """Modules Wirely needs that the given interpreter can't import."""
    python = python or sys.executable
    code = ("import importlib.util,sys;"
            f"print(','.join(m for m in {REQUIRED_MODULES!r} if importlib.util.find_spec(m) is None))")
    try:
        out = subprocess.run([python, "-c", code], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return list(REQUIRED_MODULES)
    if out.returncode != 0:
        return list(REQUIRED_MODULES)
    return [m for m in out.stdout.strip().split(",") if m]


def _check_python():
    v = sys.version_info[:2]
    if v < MIN_PY:
        _say(f"Python {v[0]}.{v[1]} es demasiado antiguo. Instale Python 3.10 – 3.13 desde https://www.python.org")
        sys.exit(1)
    if v > MAX_PY:
        _say(f"Aviso: Python {v[0]}.{v[1]} es más reciente que la versión con la que se ha probado Wirely; "
             "si la instalación falla, instale Python 3.12 o 3.13.")


def _create_venv():
    _say("Primer inicio: creando un entorno privado de Python en .venv …")
    try:
        venv.EnvBuilder(with_pip=True, clear=False, upgrade_deps=False).create(VENV)
        return
    except Exception as e:  # e.g. a half-made .venv left by an earlier attempt, or no python3-venv
        first = e
    # a half-made or locked .venv from an earlier attempt: start it again from scratch, once
    _say("Eso no funcionó: se elimina el .venv a medio crear y se intenta de nuevo …")
    try:
        import shutil
        import stat

        def _unlock(func, path, _exc):
            os.chmod(path, stat.S_IWRITE)
            func(path)
        shutil.rmtree(VENV, onerror=_unlock)
        venv.EnvBuilder(with_pip=True, clear=False, upgrade_deps=False).create(VENV)
        return
    except Exception as e:
        _say(f"No se pudo crear el entorno: {e}  (primer intento: {first})")
        if sys.platform.startswith("win"):
            _say("Cierre cualquier ventana de Wirely o Python, elimine la carpeta .venv dentro de la carpeta de "
                 "Wirely y vuelva a ejecutar esto. Si la carpeta está en el Escritorio o en OneDrive, pruebe una "
                 "carpeta como C:\\Wirely.")
        if sys.platform.startswith("linux"):
            _say("En Debian/Ubuntu instálelo con:  sudo apt install python3-venv   y vuelva a ejecutar.")
        sys.exit(1)


def _install():
    py = _venv_python()
    _say("Instalando los requisitos (Qt y numpy). Esto descarga unos 150 MB "
         "y tarda un minuto o dos la primera vez …")
    r = subprocess.run([py, "-m", "pip", "install", "-r", REQS])
    if r.returncode != 0:
        _say("La instalación de los requisitos falló — vea los mensajes de arriba. "
             "Compruebe su conexión a internet y que esté usando Python de 64 bits 3.10 – 3.13.")
        sys.exit(1)
    missing = missing_modules(py)
    if missing:
        _say(f"Instalado, pero estos módulos aún no se pueden importar: {', '.join(missing)}")
        sys.exit(1)
    with open(MARKER, "w") as fh:
        fh.write(_reqs_hash())
    _say("Configuración completada.")


def ensure_environment():
    """Make sure .venv exists and has the requirements. Returns the python to run Wirely with."""
    _check_python()
    py = _venv_python()
    if not os.path.exists(py):
        _create_venv()
    missing = missing_modules(py)
    if not missing:
        # everything imports (e.g. a .venv copied over from another Wirely folder): nothing to download
        if not os.path.exists(MARKER):
            try:
                with open(MARKER, "w") as fh:
                    fh.write(_reqs_hash())
            except OSError:
                pass
        return py
    _say("Faltan: " + ", ".join(missing))
    _install()
    return py


def launch(args=None):
    """Set up if needed, then run Wirely inside the private environment."""
    args = list(sys.argv[1:] if args is None else args)
    py = ensure_environment()
    _say("Iniciando Wirely … (el primer inicio tras la instalación puede tardar hasta un minuto)")
    if _running_in_venv():
        from wirely.__main__ import main
        sys.argv = [sys.argv[0]] + args
        main()
        return
    cmd = [py, "-m", "wirely"] + args
    env = dict(os.environ, FREESHAPE_BOOTSTRAPPED="1")
    sys.exit(subprocess.call(cmd, cwd=ROOT, env=env))
