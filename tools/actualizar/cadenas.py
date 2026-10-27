"""Encuentra las cadenas visibles del proyecto y las compara con el catálogo guardado.

El catálogo (`datos/cadenas.json`) es una foto de todas las cadenas que ya están
traducidas. Después de fusionar una versión nueva del proyecto original, las
cadenas que aparecen en inglés son, casi siempre, las que no están en el catálogo.

Uso:
    python tools/actualizar/cadenas.py              # resumen: pendientes y sospechosas de inglés
    python tools/actualizar/cadenas.py --todo       # lista completa
    python tools/actualizar/cadenas.py --ingles     # solo las que parecen inglés
    python tools/actualizar/cadenas.py --guardar    # guarda el catálogo (después de traducir)

Código de salida: 0 si no hay nada pendiente, 1 si queda algo por revisar.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DATOS = HERE / "datos"
CATALOGO = DATOS / "cadenas.json"
VERSION = DATOS / "version.json"

SUFFIXES = {".py", ".js", ".html", ".wirely", ".iss", ".bat", ".sh", ".md", ".webmanifest"}
EXCLUDE_DIRS = {".git", ".opencode", ".venv", "build", "dist", "_site", "__pycache__", "node_modules",
                "actualizacion", "web-smoke", "pyodide-dl"}
EXCLUDE_FILES = {"LICENSE", "THIRD-PARTY-NOTICES.txt", "sw.js", "ACTUALIZAR.md", "ACTUALIZAR.bat"}

# Palabras que delatan inglés o español. No hace falta que estén todas: la idea es
# que la lista de sospechosas sea corta y que la IA la revise entera.
EN = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "when", "while", "with",
    "without", "from", "into", "onto", "for", "to", "of", "in", "on", "at", "by", "as",
    "is", "are", "was", "were", "be", "been", "being", "this", "that", "these", "those",
    "it", "its", "you", "your", "we", "our", "they", "their", "he", "she", "his", "her",
    "not", "no", "yes", "can", "cannot", "will", "would", "should", "could", "may",
    "might", "must", "do", "does", "did", "done", "have", "has", "had", "there", "here",
    "what", "which", "who", "how", "why", "all", "any", "each", "every", "some", "more",
    "most", "less", "least", "only", "also", "just", "than", "too", "very", "so", "such",
    "up", "down", "out", "over", "under", "about", "after", "before", "between",
    "through", "during", "same", "other", "new", "old", "use", "uses", "used", "using",
    "show", "shows", "shown", "make", "makes", "made", "click", "press", "drag", "hold",
    "release", "run", "stop", "start", "open", "save", "load", "file", "files", "part",
    "parts", "wire", "wires", "circuit", "circuits", "value", "values", "time", "times",
    "voltage", "current", "power", "resistance", "capacitor", "capacitors", "resistor",
    "resistors", "diode", "diodes", "transistor", "transistors", "switch", "switches",
    "motor", "motors", "lamp", "lamps", "led", "leds", "relay", "relays", "battery",
    "ground", "note", "notes", "example", "examples", "window", "button", "buttons",
    "menu", "tool", "tools", "add", "delete", "remove", "edit", "copy", "paste", "undo",
    "redo", "zoom", "grid", "sound", "graph", "probe", "reading", "readings", "settings",
    "help", "about", "version", "warning", "error", "ok", "cancel", "select", "choose",
    "enter", "name", "type", "size", "color", "colour", "light", "dark", "theme", "true",
    "false", "none", "off", "on", "you'll", "it's", "don't", "doesn't", "won't", "can't",
    "isn't", "aren't", "let's", "that's", "there's", "what's", "i'm", "we're", "they're",
}

ES = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al", "en", "con",
    "sin", "por", "para", "que", "y", "o", "u", "es", "son", "ser", "se", "su", "sus",
    "lo", "le", "les", "más", "menos", "como", "cuando", "donde", "si", "no", "sí", "pero",
    "este", "esta", "estos", "estas", "ese", "esa", "hay", "muy", "ya", "también", "solo",
    "desde", "hasta", "entre", "sobre", "tras", "cada", "todo", "toda", "todos", "todas",
    "otro", "otra", "mismo", "misma", "haga", "clic", "presione", "arrastre", "suelte",
    "ejecutar", "detener", "archivo", "archivos", "componente", "componentes", "cable",
    "cables", "circuito", "circuitos", "valor", "valores", "tiempo", "voltaje", "corriente",
    "potencia", "resistencia", "capacitor", "diodo", "transistor", "interruptor", "motor",
    "lámpara", "relé", "batería", "tierra", "nota", "notas", "ejemplo", "ejemplos",
    "ventana", "botón", "menú", "herramienta", "herramientas", "agregar", "eliminar",
    "quitar", "editar", "copiar", "pegar", "deshacer", "rehacer", "cuadrícula", "sonido",
    "gráfico", "sonda", "lectura", "lecturas", "ajustes", "ayuda", "acerca", "versión",
    "advertencia", "error", "aceptar", "cancelar", "seleccionar", "elegir", "nombre",
    "tipo", "tamaño", "color", "claro", "oscuro", "tema", "verdadero", "falso", "ninguno",
    "ninguna", "apagado", "encendido", "encender", "apagar", "durante", "puede", "pueden",
    "hace", "hacer", "tiene", "tienen", "está", "están", "fue", "era", "ahora", "antes",
    "después", "siempre", "nunca", "aquí", "allí", "así", "porque", "aunque", "mientras",
    "usted", "ustedes", "nos", "te", "mi", "tu", "nuestro", "nuestra", "del", "qué",
}

PALABRA = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][\w'’-]*")

# Texto que no se traduce aunque parezca inglés.
IGNORAR = {
    'Add python.exe to PATH',            # es el texto literal del instalador de Python
    "numpy didn't load; using Wirely's built-in fallback",   # solo va a la consola
    "input, select, textarea, button",   # selector de CSS
    "Files",                             # tipo de dato del navegador
    "Enter", "Delete", "Backspace",      # nombres de teclas
    "Zoom",                              # se usa igual en español
    "{}: {} parts, {} wires, {} nets, unconnected pins: {}",   # salida de la herramienta de ejemplos
    # palabras clave de búsqueda de parts.py: quedan en inglés a propósito
    "bicolour bicolor two colour dual red green led",
    "rgb colour mixing common cathode led",
    "transformer step down step up mains coil isolation",
    "relay double pole dpdt reversing motor electromagnet two changeover",
}


# ------------------------------------------------------------------ extracción

class _HTML(HTMLParser):
    ATRIBUTOS = ("title", "placeholder", "aria-label", "alt")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cadenas = []
        self._saltar = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._saltar += 1
        for clave, valor in attrs:
            if clave in self.ATRIBUTOS and valor and valor.strip():
                self.cadenas.append((self.getpos()[0], valor.strip()))

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._saltar:
            self._saltar -= 1

    def handle_data(self, data):
        if not self._saltar and data.strip():
            self.cadenas.append((self.getpos()[0], " ".join(data.split())))


def _extraer_py(fuente: str):
    try:
        arbol = ast.parse(fuente)
    except SyntaxError:
        return []
    documentos = set()
    claves = set()
    clases = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Dict):
            for clave in nodo.keys:
                if isinstance(clave, ast.Constant) and isinstance(clave.value, str):
                    claves.add(id(clave))
        elif isinstance(nodo, ast.ClassDef):
            clases.add(nodo.name)
        if isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            cuerpo = getattr(nodo, "body", [])
            if (cuerpo and isinstance(cuerpo[0], ast.Expr)
                    and isinstance(cuerpo[0].value, ast.Constant)
                    and isinstance(cuerpo[0].value.value, str)):
                documentos.add(id(cuerpo[0].value))
    dentro_de_f = set()
    salida = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.JoinedStr):
            partes = []
            for valor in nodo.values:
                if isinstance(valor, ast.Constant) and isinstance(valor.value, str):
                    partes.append(valor.value)
                    dentro_de_f.add(id(valor))
                elif isinstance(valor, ast.FormattedValue):
                    partes.append("{}")
            texto = "".join(partes)
            if texto.strip():
                salida.append((nodo.lineno, texto))
        elif isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
            if id(nodo) in documentos or id(nodo) in dentro_de_f or id(nodo) in claves:
                continue
            if nodo.value in clases:          # anotación de tipo, no texto visible
                continue
            if nodo.value.strip():
                salida.append((nodo.lineno, nodo.value))
    return salida


def _extraer_js(fuente: str):
    """Recorre el archivo y devuelve las cadenas entre comillas, salteando comentarios."""
    salida = []
    i, n, linea = 0, len(fuente), 1
    while i < n:
        c = fuente[i]
        if c == "\n":
            linea += 1
            i += 1
            continue
        if c in "'\"`":
            comilla = c
            inicio = linea
            j = i + 1
            trozos = []
            while j < n:
                d = fuente[j]
                if d == "\\" and j + 1 < n:
                    trozos.append(d)
                    trozos.append(fuente[j + 1])
                    if fuente[j + 1] == "\n":
                        linea += 1
                    j += 2
                    continue
                if d == comilla:
                    break
                if d == "\n":
                    linea += 1
                    if comilla != "`":
                        break
                trozos.append(d)
                j += 1
            salida.append((inicio, "".join(trozos)))
            i = j + 1
            continue
        if c == "/" and i + 1 < n and fuente[i + 1] == "/":
            j = fuente.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and i + 1 < n and fuente[i + 1] == "*":
            j = fuente.find("*/", i + 2)
            if j < 0:
                break
            linea += fuente.count("\n", i, j)
            i = j + 2
            continue
        i += 1
    return salida


def _extraer_html(fuente: str):
    analizador = _HTML()
    try:
        analizador.feed(fuente)
        analizador.close()
    except Exception:
        pass
    return analizador.cadenas


def _extraer_wirely(fuente: str):
    try:
        datos = json.loads(fuente)
    except json.JSONDecodeError:
        return []
    salida = []
    if isinstance(datos.get("title"), str):
        salida.append((0, datos["title"]))
    for comp in datos.get("components", []) or []:
        props = comp.get("props") or {}
        for clave, valor in props.items():
            if isinstance(valor, str) and valor.strip():
                salida.append((0, valor))
    return salida


def _extraer_comillas(fuente: str):
    return [(fuente.count("\n", 0, m.start()) + 1, m.group(1))
            for m in re.finditer(r'"([^"\n]*)"', fuente)]


def _extraer_md(fuente: str):
    salida = []
    en_bloque = False
    for numero, linea in enumerate(fuente.splitlines(), 1):
        limpia = linea.strip()
        if limpia.startswith("```"):
            en_bloque = not en_bloque
            continue
        if en_bloque or not limpia:
            continue
        salida.append((numero, limpia))
    return salida


EXTRACTORES = {
    ".py": _extraer_py,
    ".js": _extraer_js,
    ".html": _extraer_html,
    ".wirely": _extraer_wirely,
    ".iss": _extraer_comillas,
    ".bat": _extraer_comillas,
    ".sh": _extraer_comillas,
    ".webmanifest": _extraer_comillas,
    ".md": _extraer_md,
}


def archivos():
    for ruta in sorted(ROOT.rglob("*")):
        if not ruta.is_file():
            continue
        rel = ruta.relative_to(ROOT)
        if any(parte in EXCLUDE_DIRS for parte in rel.parts):
            continue
        if ruta.name in EXCLUDE_FILES or ruta.suffix.lower() not in SUFFIXES:
            continue
        if rel.parts[:2] == ("tools", "actualizar"):
            continue
        if rel.parts and rel.parts[0] == "tests":
            continue
        if rel.parts and rel.parts[0] == "tools" and rel.name != "make_examples.py":
            continue        # herramientas de desarrollo: no son texto visible de la app
        yield rel, ruta


# ------------------------------------------------------------------ filtros

def visible(texto: str) -> bool:
    """Descarta identificadores, claves, rutas, colores y demás texto no traducible."""
    s = texto.strip()
    if len(s) < 2:
        return False
    if not PALABRA.search(s):
        return False
    if s in IGNORAR:
        return False
    if s.count("{") + s.count("}") >= 2 and ";" in s:
        return False        # fragmento de código o de hoja de estilos
    if re.search(r"^\s*(import|from|def|class)\s", s, re.M):
        return False        # script incrustado, no texto visible
    if re.fullmatch(r"https?://\S+", s):
        return False
    if " " not in s and re.search(r"[\\/]", s):
        return False        # rutas y claves del registro
    if re.fullmatch(r"[\w./\\-]+\.(py|js|html|png|ico|svg|qm|ts|md|txt|wirely|exe|bat|sh|css|json|iss)", s):
        return False
    if re.fullmatch(r"#[0-9a-fA-F]{3,8}", s):
        return False
    palabras = PALABRA.findall(s)
    if len(palabras) == 1:
        # Una sola palabra: se conservan solo las etiquetas visibles (con mayúscula inicial).
        return s[:1].isupper()
    return True


ETIQUETA = re.compile(r"</?[A-Za-z][^>]*>")


def trozos(texto: str):
    """Si la cadena es una plantilla HTML, devuelve sus textos sueltos en vez del bloque entero."""
    if not ETIQUETA.search(texto):
        return [texto]
    partes = []
    for _numero, trozo in _extraer_html(texto):
        if re.fullmatch(r"\$\{[^}]*\}", trozo.strip()):
            continue
        partes.append(trozo)
    return partes


def parece_ingles(texto: str) -> bool:
    if re.search(r"[áéíóúüñ¿¡]", texto, re.I):
        return False
    # Las siglas (LED, AC, NOT, AND) y las palabras de una letra no cuentan:
    # son términos técnicos que se usan igual en los dos idiomas.
    palabras = [p.lower() for p in PALABRA.findall(texto) if len(p) > 1 and not p.isupper()]
    if not palabras:
        return False
    en = sum(p in EN for p in palabras)
    es = sum(p in ES for p in palabras)
    if len(palabras) == 1:
        return palabras[0] in EN and palabras[0] not in ES
    return en >= 2 and en > es


# ------------------------------------------------------------------ catálogo

def extraer_todo():
    """Devuelve {texto: (archivo, línea)} con todas las cadenas visibles."""
    encontradas = {}
    total = 0
    for rel, ruta in archivos():
        try:
            fuente = ruta.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for numero, texto in EXTRACTORES[ruta.suffix.lower()](fuente):
            for trozo in trozos(texto):
                trozo = trozo.strip()
                if not visible(trozo):
                    continue
                total += 1
                encontradas.setdefault(trozo, (rel.as_posix(), numero))
    return encontradas, total


def cargar_catalogo():
    if not CATALOGO.exists():
        return None
    return json.loads(CATALOGO.read_text(encoding="utf-8"))


def version_actual():
    try:
        return json.loads(VERSION.read_text(encoding="utf-8")).get("base", "?")
    except (OSError, json.JSONDecodeError):
        return "?"


def mostrar(titulo, items, limite):
    if not items:
        print(f"{titulo}: ninguno.")
        return
    print(f"{titulo}: {len(items)}")
    for texto, (archivo, linea) in list(items.items())[:limite]:
        ubicacion = f"{archivo}:{linea}" if linea else archivo
        recorte = texto.replace("\n", " / ")
        if len(recorte) > 150:
            recorte = recorte[:147] + "..."
        print(f"  {ubicacion}: {recorte}")
    if len(items) > limite:
        print(f"  ... y {len(items) - limite} más (usar --todo para verlas todas)")


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="Detecta cadenas nuevas o sin traducir.")
    ap.add_argument("--todo", action="store_true", help="mostrar la lista completa")
    ap.add_argument("--ingles", action="store_true", help="mostrar solo las que parecen inglés")
    ap.add_argument("--pendientes", action="store_true", help="mostrar solo las que no están en el catálogo")
    ap.add_argument("--guardar", action="store_true", help="guardar el catálogo con lo que hay ahora")
    ap.add_argument("--limite", type=int, default=400, help="cuántas mostrar por lista (0 = todas)")
    args = ap.parse_args(argv)

    encontradas, total = extraer_todo()
    catalogo = cargar_catalogo()

    if args.guardar:
        DATOS.mkdir(parents=True, exist_ok=True)
        datos = {
            "version": version_actual(),
            "guardado": date.today().isoformat(),
            "total": len(encontradas),
            "cadenas": sorted(encontradas),
        }
        CATALOGO.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"Catálogo guardado: {len(encontradas)} cadenas de {version_actual()} en {CATALOGO.relative_to(ROOT)}.")
        return 0

    conocidas = set(catalogo["cadenas"]) if catalogo else set()
    pendientes = {t: u for t, u in encontradas.items() if t not in conocidas}
    ingles = {t: u for t, u in encontradas.items() if parece_ingles(t)}
    limite = args.limite if args.limite > 0 else 10 ** 9

    print(f"Cadenas visibles: {len(encontradas)} únicas ({total} apariciones).")
    if catalogo:
        print(f"Catálogo: {len(conocidas)} cadenas de {catalogo.get('version', '?')} "
              f"(guardado el {catalogo.get('guardado', '?')}).")
    else:
        print("Catálogo: todavía no hay (crear con --guardar después de traducir).")

    if not (args.ingles or args.pendientes):
        mostrar("Pendientes de traducir", pendientes, limite)
        print()
        mostrar("Sospechosas de inglés", ingles, limite)
    else:
        if args.pendientes:
            mostrar("Pendientes de traducir", pendientes, limite)
        if args.ingles:
            mostrar("Sospechosas de inglés", ingles, limite)

    if not pendientes and not ingles:
        print("\nTodo traducido.")
        return 0
    print()
    if pendientes:
        print(f"Quedan {len(pendientes)} cadenas nuevas por traducir.")
    if ingles:
        print(f"Hay {len(ingles)} cadenas que parecen inglés.")
    print("Cuando termines: python tools/actualizar/cadenas.py --guardar")
    return 1


if __name__ == "__main__":
    sys.exit(main())
