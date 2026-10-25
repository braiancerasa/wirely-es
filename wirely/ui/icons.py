"""Toolbar icons and the Wirely logo, drawn with QPainter so the app needs no image files."""
from __future__ import annotations

import math
from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

from . import theme


def _ink():
    return QColor(theme.ICON_INK)


def _pen(c, w=2.0):
    p = QPen(c, w)
    p.setCapStyle(Qt.RoundCap)
    p.setJoinStyle(Qt.RoundJoin)
    return p


def _poly(p, pts, fill):
    p.setPen(Qt.NoPen)
    p.setBrush(fill)
    p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in pts]))


def _arrowhead(p, x, y, ang, c, s=5.0):
    _poly(p, [(x, y), (x - s * math.cos(ang - 0.5), y - s * math.sin(ang - 0.5)),
              (x - s * math.cos(ang + 0.5), y - s * math.sin(ang + 0.5))], c)


W_POINTS = [(6.0, 9.5), (11.0, 23.0), (16.0, 13.5), (21.0, 23.0), (26.0, 9.5)]


def w_path(s=1.0, ox=0.0, oy=0.0) -> QPainterPath:
    """The Wirely mark: a W drawn as a wire."""
    path = QPainterPath()
    x, y = W_POINTS[0]
    path.moveTo(ox + x * s, oy + y * s)
    for x, y in W_POINTS[1:]:
        path.lineTo(ox + x * s, oy + y * s)
    return path


def draw_mark(p: QPainter, s=1.0, ox=0.0, oy=0.0, tile=True):
    """The Wirely logo in a 32 × 32 box scaled by s: a blue-to-teal tile with a white wire W, junction dots,
    and an amber dot of current running along it."""
    from PySide6.QtGui import QLinearGradient, QRadialGradient
    p.save()
    p.translate(ox, oy)
    p.scale(s, s)
    p.setRenderHint(QPainter.Antialiasing)
    if tile:
        g = QLinearGradient(2, 2, 30, 30)
        g.setColorAt(0.0, QColor("#2b7de9"))
        g.setColorAt(1.0, QColor("#10a3a3"))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(QRectF(1, 1, 30, 30), 7.5, 7.5)
        # soft highlight across the top
        hl = QLinearGradient(0, 1, 0, 16)
        hl.setColorAt(0, QColor(255, 255, 255, 46))
        hl.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(hl)
        p.drawRoundedRect(QRectF(1, 1, 30, 15), 7.5, 7.5)
    pen = QPen(QColor("#ffffff"), 2.7)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawPath(w_path())
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#ffffff"))
    for x, y in W_POINTS:
        p.drawEllipse(QPointF(x, y), 2.25, 2.25)
    # current flowing along the wire
    cx, cy = 18.6, 18.2
    glow = QRadialGradient(QPointF(cx, cy), 4.6)
    glow.setColorAt(0, QColor(255, 196, 60, 230))
    glow.setColorAt(1, QColor(255, 196, 60, 0))
    p.setBrush(glow)
    p.drawEllipse(QPointF(cx, cy), 4.6, 4.6)
    p.setBrush(QColor("#ffc83c"))
    p.drawEllipse(QPointF(cx, cy), 1.9, 1.9)
    p.restore()


def draw_logo(p: QPainter, size: float):
    draw_mark(p, size / 32.0)


def draw_doc_icon(p: QPainter, size: float):
    """File icon for .wirely circuits: a page with a folded corner, the Wirely mark and a little circuit."""
    s = size / 32.0
    p.save()
    p.scale(s, s)
    p.setRenderHint(QPainter.Antialiasing)
    page = QPainterPath()
    page.moveTo(5.5, 2)
    page.lineTo(20, 2)
    page.lineTo(27, 9)
    page.lineTo(27, 29)
    page.quadTo(27, 30.5, 25.5, 30.5)
    page.lineTo(5.5, 30.5)
    page.quadTo(4, 30.5, 4, 29)
    page.lineTo(4, 3.5)
    page.quadTo(4, 2, 5.5, 2)
    p.setPen(QPen(QColor("#9aa6b2"), 0.8))
    p.setBrush(QColor("#ffffff"))
    p.drawPath(page)
    fold = QPainterPath()
    fold.moveTo(20, 2)
    fold.lineTo(20, 7.5)
    fold.quadTo(20, 9, 21.5, 9)
    fold.lineTo(27, 9)
    fold.closeSubpath()
    p.setBrush(QColor("#dfe6ee"))
    p.drawPath(fold)
    # a tiny circuit: resistor and wire across the top of the page
    pen = QPen(QColor("#5b6b7c"), 0.9)
    p.setPen(pen)
    p.drawLine(QPointF(7, 7), QPointF(9.5, 7))
    p.drawRect(QRectF(9.5, 5.6, 5, 2.8))
    p.drawLine(QPointF(14.5, 7), QPointF(17.5, 7))
    p.restore()
    draw_mark(p, s * 0.56, size * 0.215, size * 0.36)


def doc_pixmap(size: int, dpr: float = 1.0) -> QPixmap:
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    draw_doc_icon(p, size)
    p.end()
    return pm


def logo_pixmap(size: int, dpr: float = 2.0) -> QPixmap:
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    draw_logo(p, size)
    p.end()
    return pm


def app_icon() -> QIcon:
    ic = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        ic.addPixmap(logo_pixmap(s, 1.0))
    return ic


def draw(name: str, p: QPainter):
    ink = _ink()
    acc = QColor(theme.ACCENT)
    p.setBrush(Qt.NoBrush)
    p.setPen(_pen(ink))
    if name == "new":
        p.drawPolyline(QPolygonF([QPointF(19, 5), QPointF(8, 5), QPointF(8, 27), QPointF(24, 27), QPointF(24, 10),
                                  QPointF(19, 5), QPointF(19, 10), QPointF(24, 10)]))
        p.setPen(_pen(acc, 2.2))
        p.drawLine(QPointF(16, 14), QPointF(16, 22))
        p.drawLine(QPointF(12, 18), QPointF(20, 18))
    elif name == "open":
        p.drawPolyline(QPolygonF([QPointF(5, 25), QPointF(5, 8), QPointF(12, 8), QPointF(14, 11), QPointF(25, 11),
                                  QPointF(25, 14)]))
        p.setBrush(QColor(theme.ACCENT_SOFT))
        p.drawPolygon(QPolygonF([QPointF(5, 25), QPointF(9, 15), QPointF(28, 15), QPointF(24, 25)]))
    elif name == "save":
        p.drawRoundedRect(QRectF(6, 6, 20, 20), 2.5, 2.5)
        p.drawRect(QRectF(11, 6, 10, 6))
        p.setBrush(QColor(theme.ACCENT_SOFT))
        p.drawRect(QRectF(10, 17, 12, 9))
    elif name == "export":
        p.drawPolyline(QPolygonF([QPointF(12, 9), QPointF(7, 9), QPointF(7, 26), QPointF(25, 26), QPointF(25, 20)]))
        p.setPen(_pen(acc, 2.2))
        p.drawLine(QPointF(14, 19), QPointF(25, 8))
        _arrowhead(p, 26, 7, -math.pi / 4, acc, 7)
    elif name in ("undo", "redo"):
        if name == "redo":
            p.translate(32, 0)
            p.scale(-1, 1)
        path = QPainterPath()
        path.moveTo(9, 13)
        path.cubicTo(14, 7, 26, 8, 25, 18)
        path.cubicTo(24, 24, 18, 25, 14, 24)
        p.drawPath(path)
        _poly(p, [(5, 9), (13, 9), (7, 17)], ink)
    elif name == "select":
        p.setBrush(ink)
        p.setPen(_pen(ink, 1.2))
        p.drawPolygon(QPolygonF([QPointF(9, 5), QPointF(9, 25), QPointF(14, 20), QPointF(18, 28),
                                 QPointF(21, 27), QPointF(17, 19), QPointF(24, 19)]))
    elif name == "wire":
        p.setPen(_pen(ink, 2.2))
        p.drawPolyline(QPolygonF([QPointF(6, 24), QPointF(16, 24), QPointF(16, 9), QPointF(26, 9)]))
        p.setBrush(acc)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(6, 24), 3, 3)
        p.drawEllipse(QPointF(26, 9), 3, 3)
    elif name in ("rotate", "rotate_ccw"):
        if name == "rotate_ccw":
            p.translate(32, 0)
            p.scale(-1, 1)
        p.drawArc(QRectF(7, 7, 18, 18), 120 * 16, 270 * 16)
        _arrowhead(p, 12.5, 8.5, math.radians(200), ink, 7)
        p.setPen(_pen(acc, 2))
        p.drawRect(QRectF(13, 13, 6, 6))
    elif name == "flip":
        p.setPen(_pen(ink, 1.4))
        p.drawLine(QPointF(16, 4), QPointF(16, 28))
        _poly(p, [(13, 9), (13, 23), (5, 23)], QColor(theme.ACCENT_SOFT))
        p.setPen(_pen(ink, 1.6))
        p.setBrush(Qt.NoBrush)
        p.drawPolygon(QPolygonF([QPointF(13, 9), QPointF(13, 23), QPointF(5, 23)]))
        _poly(p, [(19, 9), (19, 23), (27, 23)], acc)
    elif name == "delete":
        p.drawLine(QPointF(7, 9), QPointF(25, 9))
        p.drawLine(QPointF(13, 9), QPointF(13, 6))
        p.drawLine(QPointF(13, 6), QPointF(19, 6))
        p.drawLine(QPointF(19, 6), QPointF(19, 9))
        p.drawPolyline(QPolygonF([QPointF(9, 9), QPointF(10.5, 27), QPointF(21.5, 27), QPointF(23, 9)]))
        p.setPen(_pen(ink, 1.5))
        p.drawLine(QPointF(14, 13), QPointF(14, 23))
        p.drawLine(QPointF(18, 13), QPointF(18, 23))
    elif name == "zoom_fit":
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            cx, cy = 16 - 10 * sx, 16 - 10 * sy
            p.drawLine(QPointF(cx, cy), QPointF(cx + 6 * sx, cy))
            p.drawLine(QPointF(cx, cy), QPointF(cx, cy + 6 * sy))
        p.setPen(_pen(acc, 2))
        p.drawRect(QRectF(11, 12, 10, 8))
    elif name in ("zoom_in", "zoom_out"):
        p.drawEllipse(QPointF(14, 14), 8, 8)
        p.drawLine(QPointF(20, 20), QPointF(27, 27))
        p.drawLine(QPointF(10, 14), QPointF(18, 14))
        if name == "zoom_in":
            p.drawLine(QPointF(14, 10), QPointF(14, 18))
    elif name == "play":
        _poly(p, [(10, 6), (26, 16), (10, 26)], QColor(theme.OK_GREEN))
    elif name == "pause":
        p.setPen(Qt.NoPen)
        p.setBrush(ink)
        p.drawRoundedRect(QRectF(9, 7, 5, 18), 1.5, 1.5)
        p.drawRoundedRect(QRectF(18, 7, 5, 18), 1.5, 1.5)
    elif name == "stop":
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.ERROR))
        p.drawRoundedRect(QRectF(8, 8, 16, 16), 2.5, 2.5)
    elif name == "theme":
        path = QPainterPath()
        path.addEllipse(QPointF(16, 16), 10, 10)
        cut = QPainterPath()
        cut.addEllipse(QPointF(21, 11), 9, 9)
        p.setBrush(ink)
        p.setPen(Qt.NoPen)
        p.drawPath(path.subtracted(cut))
    elif name == "grid":
        p.setPen(Qt.NoPen)
        p.setBrush(ink)
        for x in (8, 16, 24):
            for y in (8, 16, 24):
                p.drawEllipse(QPointF(x, y), 1.8, 1.8)
    elif name == "bom":
        p.drawRoundedRect(QRectF(6, 5, 20, 22), 2, 2)
        for y in (11, 16, 21):
            p.setPen(_pen(acc, 2))
            p.drawLine(QPointF(10, y), QPointF(12, y))
            p.setPen(_pen(ink, 1.6))
            p.drawLine(QPointF(15, y), QPointF(22, y))
    elif name == "text":
        p.setPen(_pen(ink, 2.4))
        p.drawLine(QPointF(8, 8), QPointF(24, 8))
        p.drawLine(QPointF(16, 8), QPointF(16, 26))
    elif name == "volts":
        from .theme import VOLT_STOPS
        cols = [QColor(c) for _f, c in VOLT_STOPS[1:]]
        pts = [(5, 24), (12, 24), (12, 10), (20, 10), (20, 20), (27, 20)]
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            p.setPen(_pen(cols[min(i, len(cols) - 1)], 3.0))
            p.drawLine(QPointF(*a), QPointF(*b))
    elif name == "sound":
        p.setPen(Qt.NoPen)
        p.setBrush(ink)
        p.drawPolygon(QPolygonF([QPointF(5, 12), QPointF(10, 12), QPointF(16, 6), QPointF(16, 26), QPointF(10, 20),
                                 QPointF(5, 20)]))
        p.setBrush(Qt.NoBrush)
        p.setPen(_pen(acc, 2))
        p.drawArc(QRectF(13, 10, 8, 12), -55 * 16, 110 * 16)
        p.drawArc(QRectF(13, 6, 14, 20), -55 * 16, 110 * 16)
    elif name == "graph":
        p.setPen(_pen(ink, 1.4))
        p.drawRoundedRect(QRectF(4, 6, 24, 20), 3, 3)
        path = QPainterPath()
        path.moveTo(7, 20)
        for i in range(1, 21):
            x = 7 + 18 * i / 20
            path.lineTo(x, 16 - 6 * math.sin(i / 20 * 2 * math.pi * 1.5))
        p.setPen(_pen(QColor("#e0a800"), 2))
        p.drawPath(path)
    elif name == "readings":
        p.setPen(_pen(ink, 2.2))
        p.drawLine(QPointF(4, 26), QPointF(28, 26))
        p.drawLine(QPointF(16, 26), QPointF(16, 20))
        p.setPen(_pen(QColor(theme.ACCENT), 1.8))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(3, 5, 26, 15), 3.5, 3.5)
        f = QFont()
        f.setPixelSize(9)
        f.setBold(True)
        p.setFont(f)
        p.setPen(ink)
        p.drawText(QRectF(3, 5, 26, 15), Qt.AlignCenter, "V·A")
    elif name == "flow":
        p.setPen(_pen(ink, 2.2))
        p.drawLine(QPointF(4, 16), QPointF(28, 16))
        p.setPen(_pen(QColor("#8a5a00"), 1.2))
        p.setBrush(QColor("#ffd43b"))
        for x in (9, 17, 25):
            p.drawEllipse(QPointF(x, 16), 3.2, 3.2)
        _arrowhead(p, 28, 9, 0, ink, 5)
        p.setPen(_pen(ink, 1.6))
        p.drawLine(QPointF(19, 9), QPointF(27, 9))
    elif name == "spark":
        draw_mark(p, 1.0)
    else:
        p.drawRect(QRectF(8, 8, 16, 16))


@lru_cache(maxsize=None)
def _icon(name: str, mode: str) -> QIcon:
    ic = QIcon()
    for size in (32, 64):
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(size / 32, size / 32)
        draw(name, p)
        p.end()
        ic.addPixmap(pm)
        faint = QPixmap(size, size)
        faint.fill(Qt.transparent)
        p = QPainter(faint)
        p.setOpacity(0.28)
        p.drawPixmap(0, 0, pm)
        p.end()
        ic.addPixmap(faint, QIcon.Disabled)
    return ic


def icon(name: str) -> QIcon:
    return _icon(name, theme.MODE)
