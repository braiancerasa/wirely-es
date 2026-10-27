"""Comprueba que la traducción no rompió nada.

Corre, en orden:
    1. sintaxis de todos los .py
    2. sintaxis de web/app.js (node --check)
    3. autoprueba de la app (--self-test)
    4. carga de todos los ejemplos
    5. que el generador de ejemplos reproduzca los ejemplos guardados
    6. una prueba rápida de la versión web
    7. el glosario (que no queden términos viejos)

Uso:
    python tools/actualizar/verificar.py            # todo
    python tools/actualizar/verificar.py --rapido   # sin la prueba web ni el generador

Código de salida: 0 si todo está bien, 1 si algo falló.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
VPY = ROOT / ".venv" / "Scripts" / "python.exe"
EXCLUIR = {".git", ".venv", "build", "dist", "_site", "__pycache__", "node_modules",
           "actualizacion", "web-smoke", "pyodide-dl"}

PRUEBA_WEB = r'''
import json, pathlib, sys
raiz = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(raiz / "web" / "py"))
sys.path.insert(0, str(raiz))
import wirely_web
app = wirely_web.App()
ejemplos = sorted((raiz / "examples").glob("*.wirely"))
texto = ejemplos[0].read_text(encoding="utf-8")
error = app.load(texto, ejemplos[0].stem)
assert not error, error
app.frame(-1000, -1000, 3000, 3000)
assert not app.run(), "no arrancó la simulación"
for _ in range(5):
    app.tick()
estado = json.loads(app.state())
assert estado.get("sim") == "running", estado.get("sim")
assert json.loads(app.bom()), "lista de materiales vacía"
print("OK", len(ejemplos), "ejemplos")
'''


def _reubicar_en_venv():
    """Si existe el entorno del proyecto, volver a ejecutarse con él."""
    if not VPY.exists():
        return
    if Path(sys.prefix).resolve() == (ROOT / ".venv").resolve():
        return
    resultado = subprocess.run([str(VPY), str(Path(__file__).resolve()), *sys.argv[1:]], cwd=ROOT)
    sys.exit(resultado.returncode)


def _archivos(sufijo):
    for ruta in sorted(ROOT.rglob(f"*{sufijo}")):
        if not ruta.is_file() or any(parte in EXCLUIR for parte in ruta.relative_to(ROOT).parts):
            continue
        yield ruta


# ------------------------------------------------------------------ pasos

def sintaxis_python():
    malos = []
    total = 0
    for ruta in _archivos(".py"):
        total += 1
        try:
            compile(ruta.read_text(encoding="utf-8"), str(ruta), "exec")
        except (SyntaxError, UnicodeDecodeError) as e:
            malos.append(f"{ruta.relative_to(ROOT)}: {e}")
    return (not malos), f"{total} archivos" + ("".join("\n    " + m for m in malos))


def sintaxis_js():
    if not shutil.which("node"):
        return True, "omitido: Node.js no está instalado"
    resultado = subprocess.run(["node", "--check", str(ROOT / "web" / "app.js")],
                               cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if resultado.returncode:
        return False, (resultado.stdout + resultado.stderr).strip()
    return True, "web/app.js"


def autoprueba():
    with tempfile.TemporaryDirectory() as tmp:
        salida = Path(tmp) / "selftest.txt"
        entorno = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        resultado = subprocess.run([sys.executable, "-m", "wirely", "--self-test", str(salida)],
                                   cwd=ROOT, env=entorno, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace")
        texto = salida.read_text(encoding="utf-8", errors="replace") if salida.exists() else ""
        if resultado.returncode or not texto.startswith("OK"):
            detalle = (texto or resultado.stdout + resultado.stderr).strip()
            return False, detalle[:800]
        return True, "OK"


def ejemplos():
    sys.path.insert(0, str(ROOT))
    from wirely.model.circuit import Circuit
    malos = []
    total = 0
    for ruta in sorted((ROOT / "examples").glob("*.wirely")):
        total += 1
        try:
            circuito = Circuit.load(str(ruta))
        except Exception as e:                       # noqa: BLE001
            malos.append(f"{ruta.name}: {e}")
            continue
        if not circuito.title:
            malos.append(f"{ruta.name}: sin título")
    return (not malos), f"{total} ejemplos" + ("".join("\n    " + m for m in malos))


def _normalizar(datos):
    return {
        "title": datos.get("title"),
        "notes": sorted(c["props"].get("text", "") for c in datos.get("components", [])
                        if c.get("kind") == "note"),
        "props": sorted((c.get("kind"), clave, valor)
                        for c in datos.get("components", [])
                        for clave, valor in (c.get("props") or {}).items()
                        if isinstance(valor, str)),
    }


def generador():
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("make_examples", ROOT / "tools" / "make_examples.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    with tempfile.TemporaryDirectory() as tmp:
        modulo.OUT = tmp
        with contextlib.redirect_stdout(io.StringIO()):
            modulo.main()
        generados = {p.stem: _normalizar(json.loads(p.read_text(encoding="utf-8")))
                     for p in Path(tmp).glob("*.wirely")}
    guardados = {p.stem: _normalizar(json.loads(p.read_text(encoding="utf-8")))
                 for p in (ROOT / "examples").glob("*.wirely")}
    problemas = []
    for nombre in sorted(set(generados) - set(guardados)):
        problemas.append(f"el generador crea «{nombre}» y no está en examples/")
    for nombre in sorted(set(guardados) - set(generados)):
        problemas.append(f"«{nombre}» está en examples/ y el generador no lo crea")
    for nombre in sorted(set(generados) & set(guardados)):
        if generados[nombre] != guardados[nombre]:
            problemas.append(f"«{nombre}» no coincide con el generador")
    detalle = f"{len(guardados)} ejemplos" + ("".join("\n    " + p for p in problemas))
    return (not problemas), detalle


def web():
    with tempfile.TemporaryDirectory() as tmp:
        entorno = dict(os.environ)
        entorno.pop("QT_QPA_PLATFORM", None)
        entorno["PYTHONPATH"] = os.pathsep.join([str(ROOT / "web" / "py"), str(ROOT)])
        resultado = subprocess.run([sys.executable, "-c", PRUEBA_WEB, str(ROOT)],
                                   cwd=ROOT, env=entorno, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=300)
    if resultado.returncode:
        return False, (resultado.stdout + resultado.stderr).strip()[-800:]
    return True, resultado.stdout.strip()


def glosario():
    spec = importlib.util.spec_from_file_location("glosario", HERE / "glosario.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        codigo = modulo.main(["--check"])
    texto = buffer.getvalue().strip()
    if codigo:
        return False, texto
    return True, "sin términos viejos"


PASOS = [
    ("Sintaxis de Python", sintaxis_python),
    ("Sintaxis de JavaScript", sintaxis_js),
    ("Autoprueba de la app", autoprueba),
    ("Carga de ejemplos", ejemplos),
    ("Generador de ejemplos", generador),
    ("Versión web", web),
    ("Glosario", glosario),
]


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    _reubicar_en_venv()
    argumentos = sys.argv[1:] if argv is None else argv
    rapido = "--rapido" in argumentos
    pasos = [p for p in PASOS if not (rapido and p[0] in ("Generador de ejemplos", "Versión web"))]

    fallos = 0
    for indice, (nombre, funcion) in enumerate(pasos, 1):
        try:
            bien, detalle = funcion()
        except Exception as e:                       # noqa: BLE001
            bien, detalle = False, f"{type(e).__name__}: {e}"
        etiqueta = f"[{indice}/{len(pasos)}] {nombre}"
        estado = "OK" if bien else "FALLA"
        corto = detalle and "\n" not in str(detalle)
        print(f"{etiqueta:.<44} {estado}" + (f"  ({detalle})" if bien and corto else ""))
        if not bien:
            fallos += 1
            for linea in str(detalle).splitlines():
                print(f"    {linea}")
        elif detalle and not corto:
            for linea in str(detalle).splitlines():
                print(f"    {linea}")

    print()
    if fallos:
        print(f"Resultado: {fallos} de {len(pasos)} comprobaciones fallaron.")
        return 1
    print("Resultado: todo bien.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
