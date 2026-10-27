"""Guía las actualizaciones de la traducción al español de Wirely.

Uso:
    python tools/actualizar/actualizar.py estado             # dónde estamos parados
    python tools/actualizar/actualizar.py buscar             # ver si hay versiones nuevas
    python tools/actualizar/actualizar.py actualizar v1.5.3  # fusionar la versión nueva
    python tools/actualizar/actualizar.py pendientes         # cadenas nuevas por traducir
    python tools/actualizar/actualizar.py glosario           # aplicar la terminología fija
    python tools/actualizar/actualizar.py verificar          # probar todo
    python tools/actualizar/actualizar.py cerrar             # guardar y etiquetar
    python tools/actualizar/actualizar.py compilar           # armar el instalador de Windows

El repositorio local tiene dos ramas:
    base   la versión original, tal como la publica el autor
    es     la traducción, colgada de la versión original

Así, cada versión nueva se fusiona con git y solo hay que traducir lo que llegó en inglés.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DATOS = HERE / "datos"
VERSION = DATOS / "version.json"
EN_CURSO = DATOS / "en-curso.json"
CADENAS = HERE / "cadenas.py"
VERIFICAR = HERE / "verificar.py"
GLOSARIO = HERE / "glosario.py"

REQUIERE_LIMPIO = "El árbol de trabajo tiene cambios sin guardar. Ejecute «cerrar» o guárdelos antes de seguir."


# ------------------------------------------------------------------ utilidades

def flujos_utf8():
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        except Exception:
            pass


def git(*args, check=False):
    resultado = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
    if check and resultado.returncode:
        salir(f"Falló «git {' '.join(args)}»:\n{resultado.stdout}{resultado.stderr}".strip())
    return resultado


def python(*args, **kwargs):
    return subprocess.run([sys.executable, *args], cwd=ROOT, **kwargs)


def salir(mensaje, codigo=1):
    print(mensaje)
    sys.exit(codigo)


def leer_version():
    return json.loads(VERSION.read_text(encoding="utf-8"))


def escribir_version(datos):
    VERSION.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tags_ordenados():
    salida = git("tag", "--list", "v*", "--sort=-v:refname").stdout
    return [t for t in salida.split() if t]


def tags_nuevas(todas, base):
    if base not in todas:
        return todas
    return todas[:todas.index(base)]


def arbol_limpio():
    return not git("status", "--porcelain").stdout.strip()


def en_merge():
    return (ROOT / ".git" / "MERGE_HEAD").exists()


def conflictos():
    salida = git("diff", "--name-only", "--diff-filter=U").stdout
    return [linea for linea in salida.splitlines() if linea.strip()]


def archivos_con_marcadores():
    """Archivos que todavía tienen marcas de conflicto (<<<<<<< / >>>>>>>)."""
    salida = git("grep", "-l", "-E", r"^(<<<<<<< |>>>>>>> )").stdout
    return [linea.strip() for linea in salida.splitlines() if linea.strip()]


def asunto(ref):
    return git("log", "-1", "--format=%s", ref).stdout.strip()


def modulo_cadenas():
    spec = importlib.util.spec_from_file_location("cadenas", CADENAS)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def resumen_cadenas():
    modulo = modulo_cadenas()
    encontradas, _total = modulo.extraer_todo()
    catalogo = modulo.cargar_catalogo()
    conocidas = set(catalogo["cadenas"]) if catalogo else set()
    pendientes = [t for t in encontradas if t not in conocidas]
    ingles = [t for t in encontradas if modulo.parece_ingles(t)]
    return len(encontradas), pendientes, ingles


# ------------------------------------------------------------------ comandos

def cmd_estado(_args):
    version = leer_version()
    base = version.get("base", "?")
    rama = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    todas = tags_ordenados()
    nuevas = tags_nuevas(todas, base)
    hash_base = git("rev-parse", "--short", f"{base}^{{commit}}").stdout.strip() if base in todas else "?"

    print(f"Rama: {rama}")
    print(f"Árbol de trabajo: {'limpio' if arbol_limpio() else 'con cambios sin guardar'}")
    print(f"Base traducida: {base} ({hash_base}), actualizada el {version.get('actualizado', '?')}")
    if en_merge():
        print("Merge en curso: sí (resolver los conflictos y ejecutar «cerrar»)")
    if todas:
        print(f"Última versión publicada: {todas[0]} — {asunto(todas[0])}")
    if nuevas:
        print(f"Actualizaciones disponibles: {', '.join(nuevas)}")
        print("  Para traerlas: python tools/actualizar/actualizar.py actualizar " + nuevas[-1])
    else:
        print("Actualizaciones disponibles: ninguna, está al día.")
    if en_merge() or not arbol_limpio():
        print("Cadenas: se revisan al terminar (ejecutar «pendientes»).")
        return 0
    total, pendientes, ingles = resumen_cadenas()
    print(f"Cadenas visibles: {total}; pendientes de traducir: {len(pendientes)}; en inglés: {len(ingles)}.")
    return 0


def cmd_buscar(_args):
    print("Buscando versiones nuevas en el repositorio original...")
    resultado = git("fetch", "upstream", "--tags", "--prune")
    if resultado.returncode:
        print("No se pudo conectar; se usan las versiones ya descargadas.")
        print((resultado.stdout + resultado.stderr).strip())
    version = leer_version()
    base = version.get("base", "?")
    todas = tags_ordenados()
    nuevas = tags_nuevas(todas, base)
    if not nuevas:
        print(f"No hay nada nuevo: la traducción está sobre {base}, la última versión.")
        return 0
    print(f"\nVersiones nuevas desde {base}:")
    for tag in reversed(nuevas):
        print(f"  {tag:10s} {asunto(tag)}")
    print(f"\nPara traer la más nueva:\n  python tools/actualizar/actualizar.py actualizar {nuevas[-1]}")
    return 0


def cmd_actualizar(args):
    if not args.tag:
        salir("Indique la versión: actualizar v1.5.3")
    tag = args.tag
    if not arbol_limpio():
        salir(REQUIERE_LIMPIO)
    if en_merge():
        salir("Ya hay un merge en curso. Termínelo con «cerrar» o cancélelo con: git merge --abort")

    if tag not in tags_ordenados():
        print(f"No tengo {tag}; lo busco en el repositorio original...")
        git("fetch", "upstream", "--tags")
        if tag not in tags_ordenados():
            salir(f"No existe la versión {tag}.")
    if git("merge-base", "--is-ancestor", tag, "HEAD").returncode == 0:
        salir(f"{tag} ya está incluida en la traducción.")

    version = leer_version()
    print(f"Fusionando {tag} sobre la traducción (base {version.get('base')})...")
    print(f"  {asunto(tag)}")
    resultado = git("merge", "--no-ff", "--no-commit", tag)
    salida = (resultado.stdout + resultado.stderr).strip()
    if salida:
        print(salida)

    pendientes = conflictos()
    if pendientes:
        DATOS.mkdir(parents=True, exist_ok=True)
        EN_CURSO.write_text(json.dumps({"tag": tag}, ensure_ascii=False), encoding="utf-8")
        print(f"\nHay {len(pendientes)} archivo(s) con conflictos:")
        for archivo in pendientes:
            print(f"  {archivo}")
        print("\nResuélvalos conservando la traducción (y traduciendo lo nuevo): borre las líneas de marca de")
        print("conflicto y deje el texto final. No hace falta ejecutar git add. Después:")
        print("  python tools/actualizar/actualizar.py pendientes")
        print("  python tools/actualizar/actualizar.py verificar")
        print("  python tools/actualizar/actualizar.py cerrar")
        return 3

    if resultado.returncode:
        git("merge", "--abort")
        salir(f"La fusión no se pudo hacer:\n{salida}")

    DATOS.mkdir(parents=True, exist_ok=True)
    EN_CURSO.write_text(json.dumps({"tag": tag}, ensure_ascii=False), encoding="utf-8")
    print("\nFusión limpia, sin conflictos. Aplico la terminología fija...")
    python(str(GLOSARIO), "--aplicar")
    print("\nCadenas nuevas:")
    python(str(CADENAS), "--pendientes", "--limite", "60")
    print("\nSiguiente paso: traducir lo que quedó en inglés y después ejecutar «cerrar».")
    return 0


def cmd_pendientes(_args):
    return python(str(CADENAS)).returncode


def cmd_glosario(_args):
    return python(str(GLOSARIO), "--aplicar").returncode


def cmd_verificar(args):
    extra = ["--rapido"] if args.rapido else []
    return python(str(VERIFICAR), *extra).returncode


def cmd_cerrar(args):
    marcados = archivos_con_marcadores()
    if marcados:
        salir("Todavía hay marcas de conflicto en:\n  " + "\n  ".join(marcados) +
              "\nBorre esas líneas (las que empiezan con los signos de menor y de mayor) y vuelva a intentar.")
    if conflictos():
        git("add", "-A")        # ya no quedan marcas: los conflictos están resueltos
    tag = args.tag
    if not tag and EN_CURSO.exists():
        tag = json.loads(EN_CURSO.read_text(encoding="utf-8")).get("tag")
    if not tag:
        salir("No sé qué versión se está cerrando. Use: cerrar v1.5.3")

    if not args.sin_verificar:
        print("Compruebo todo antes de guardar...\n")
        codigo = python(str(VERIFICAR), *(["--rapido"] if args.rapido else [])).returncode
        if codigo:
            salir("\nNo se guardó nada: hay comprobaciones que fallan.")

    version = leer_version()
    version.update({"base": tag, "actual": tag, "actualizado": date.today().isoformat()})
    version.pop("objetivo", None)
    escribir_version(version)

    print("\nActualizo el catálogo de cadenas...")
    python(str(CADENAS), "--guardar")

    git("add", "-A")
    if not git("status", "--porcelain").stdout.strip():
        print("No hay nada nuevo para guardar.")
    else:
        mensaje = f"Actualización a {tag}"
        resultado = git("commit", "-m", mensaje)
        print((resultado.stdout + resultado.stderr).strip())
        if resultado.returncode:
            salir("No se pudo guardar el commit.")

    git("tag", "-f", f"es-{tag}")
    if EN_CURSO.exists():
        EN_CURSO.unlink()
    print(f"\nListo: la traducción quedó sobre {tag} y etiquetada como es-{tag}.")
    print("Para el instalador: python tools/actualizar/actualizar.py compilar")
    return 0


def cmd_compilar(_args):
    iscc = None
    for candidato in (Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
                      Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Inno Setup 6" / "ISCC.exe",
                      Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe"):
        if candidato.exists():
            iscc = candidato
            break
    if not iscc:
        print("No encontré Inno Setup 6, que es el programa que arma el instalador.")
        print("Descárguelo de https://jrsoftware.org/isdl.php, instálelo con las opciones por defecto")
        print("y vuelva a ejecutar este comando. Mientras tanto puede usar build_exe.bat, que deja")
        print("la versión portable en dist\\Wirely\\Wirely.exe.")
        return 1
    print("Compilando la app y el instalador (tarda unos minutos)...\n")
    resultado = subprocess.run(["cmd", "/c", "build_exe.bat"], cwd=ROOT)
    if resultado.returncode:
        salir("La compilación falló; revise el mensaje de arriba.")
    instaladores = sorted((ROOT / "dist").glob("Wirely-Setup-*.exe"))
    print()
    if instaladores:
        print("Instalador listo:", instaladores[-1])
    print("Versión portable:", ROOT / "dist" / "Wirely" / "Wirely.exe")
    return 0


# ------------------------------------------------------------------ entrada

def main(argv=None):
    flujos_utf8()
    ap = argparse.ArgumentParser(description="Actualiza la traducción al español de Wirely.")
    sub = ap.add_subparsers(dest="comando")

    sub.add_parser("estado", help="dónde estamos parados").set_defaults(func=cmd_estado)
    sub.add_parser("buscar", help="ver si hay versiones nuevas").set_defaults(func=cmd_buscar)

    p = sub.add_parser("actualizar", help="fusionar una versión nueva")
    p.add_argument("tag", nargs="?", help="por ejemplo v1.5.3")
    p.set_defaults(func=cmd_actualizar)

    sub.add_parser("pendientes", help="cadenas nuevas por traducir").set_defaults(func=cmd_pendientes)
    sub.add_parser("glosario", help="aplicar la terminología fija").set_defaults(func=cmd_glosario)

    p = sub.add_parser("verificar", help="probar todo")
    p.add_argument("--rapido", action="store_true", help="sin la prueba web ni el generador")
    p.set_defaults(func=cmd_verificar)

    p = sub.add_parser("cerrar", help="guardar y etiquetar la actualización")
    p.add_argument("tag", nargs="?", help="versión que se cierra (por defecto, la que se fusionó)")
    p.add_argument("--rapido", action="store_true", help="verificación corta")
    p.add_argument("--sin-verificar", action="store_true", help="no comprobar antes de guardar")
    p.set_defaults(func=cmd_cerrar)

    sub.add_parser("compilar", help="armar el instalador de Windows").set_defaults(func=cmd_compilar)

    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
