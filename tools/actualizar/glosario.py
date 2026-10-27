"""Aplica el glosario fijo de la traducción (términos técnicos y dialecto).

Uso:
    python tools/actualizar/glosario.py --check     # solo informa (código 1 si hay cambios)
    python tools/actualizar/glosario.py --aplicar   # reescribe los archivos

Las reglas viven en glosario.json, al lado de este archivo. Es idempotente:
aplicarlo dos veces no cambia nada la segunda vez.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).with_name("glosario.json")

SUFFIXES = {".py", ".js", ".html", ".wirely", ".md", ".iss", ".sh", ".bat", ".toml",
            ".webmanifest", ".desktop", ".xml"}
EXCLUDE_DIRS = {".git", ".opencode", ".venv", "build", "dist", "_site", "__pycache__", "node_modules",
                "actualizacion", "tests", "fallback", "docs", "assets"}
EXCLUDE_FILES = {"LICENSE", "THIRD-PARTY-NOTICES.txt", "requirements.txt", "glosario.json",
                 "ACTUALIZAR.md", "ACTUALIZAR.bat"}

LETRAS = "0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ"


def cargar_reglas():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    reglas = []
    for r in data["reglas"]:
        termino = r["buscar"]
        flags = re.IGNORECASE if r.get("ignorar_mayusculas", True) else 0
        patron = re.compile(
            rf"(?<![{LETRAS}]){re.escape(termino)}(?![{LETRAS}])", flags
        )
        reglas.append((termino, patron, r["reemplazar"]))
    return reglas


def archivos():
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(parte in EXCLUDE_DIRS for parte in rel.parts):
            continue
        if p.name in EXCLUDE_FILES or p.suffix.lower() not in SUFFIXES:
            continue
        if rel.parts[:2] == ("tools", "actualizar"):
            continue
        if rel.as_posix() == "web/sw.js":
            continue
        yield p


def _reemplazo(texto, reemplazo):
    if texto.isupper() and reemplazo.islower():
        return reemplazo.upper()
    if texto[:1].isupper() and reemplazo[:1].islower():
        return reemplazo[:1].upper() + reemplazo[1:]
    return reemplazo


def aplicar_texto(texto, reglas):
    cambios = []
    for termino, patron, reemplazo in reglas:
        texto, n = patron.subn(lambda m, r=reemplazo: _reemplazo(m.group(0), r), texto)
        if n:
            cambios.append((termino, reemplazo, n))
    return texto, cambios


def main(argv=None):
    ap = argparse.ArgumentParser(description="Aplica el glosario de la traducción al español.")
    grupo = ap.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--check", action="store_true", help="solo informar")
    grupo.add_argument("--aplicar", action="store_true", help="reescribir los archivos")
    args = ap.parse_args(argv)

    reglas = cargar_reglas()
    total_archivos = total_cambios = 0
    for p in archivos():
        texto = p.read_text(encoding="utf-8", errors="replace")
        nuevo, cambios = aplicar_texto(texto, reglas)
        if not cambios:
            continue
        total_archivos += 1
        total_cambios += sum(n for _t, _r, n in cambios)
        rel = p.relative_to(ROOT)
        detalle = ", ".join(f"«{t}» → «{r}» ×{n}" for t, r, n in cambios)
        print(f"{rel}: {detalle}")
        if args.aplicar:
            p.write_text(nuevo, encoding="utf-8")

    if total_cambios == 0:
        print("Glosario: todo en orden, no hay nada que normalizar.")
        return 0
    if args.check:
        print(f"\nGlosario: {total_cambios} cambios en {total_archivos} archivos (usar --aplicar).")
        return 1
    print(f"\nGlosario aplicado: {total_cambios} cambios en {total_archivos} archivos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
