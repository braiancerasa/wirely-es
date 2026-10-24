"""Draws Wirely's icons into wirely/assets (app logo and the .wirely file icon) as PNG, ICO and SVG.
Run:  python tools/make_icons.py      (needs PySide6 and Pillow)"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image  # noqa: E402
from PySide6.QtCore import QRectF, QSize  # noqa: E402
from PySide6.QtGui import QPainter  # noqa: E402
from PySide6.QtSvg import QSvgGenerator  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])
from wirely.ui import icons  # noqa: E402

OUT = os.path.join(ROOT, "wirely", "assets")
SIZES = [16, 24, 32, 48, 64, 128, 256, 512, 1024]


def save_set(prefix, make):
    paths = {}
    for s in SIZES:
        p = os.path.join(OUT, f"{prefix}_{s}.png")
        make(s, 1.0).save(p)
        paths[s] = p
    return paths


def ico(paths, name):
    imgs = [Image.open(paths[s]).convert("RGBA") for s in (16, 24, 32, 48, 64, 128, 256)]
    imgs[-1].save(os.path.join(OUT, name), sizes=[im.size for im in imgs], append_images=imgs[:-1])


def svg(draw, name):
    gen = QSvgGenerator()
    gen.setFileName(os.path.join(OUT, name))
    gen.setSize(QSize(256, 256))
    gen.setViewBox(QRectF(0, 0, 256, 256))
    gen.setTitle("Wirely")
    p = QPainter(gen)
    draw(p, 256)
    p.end()


logo = save_set("logo", icons.logo_pixmap)
doc = save_set("doc", icons.doc_pixmap)
ico(logo, "wirely.ico")
ico(doc, "wirely_doc.ico")
svg(icons.draw_logo, "logo.svg")
svg(icons.draw_doc_icon, "doc.svg")
print("icons written to", OUT)
