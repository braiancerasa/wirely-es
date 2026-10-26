"""A tiny stand-in for the parts of PySide6 that Wirely's drawing code uses, for the browser version.

There is no Qt in the browser, so instead of painting pixels this QPainter writes down what it was asked to
draw ("ops"). The web page replays the ops on an HTML canvas, whose drawing commands are almost the same as
QPainter's. That way the browser shows exactly the same symbols as the desktop app, drawn by the same code
(wirely/ui/symbols.py), and new parts appear on the web without extra work.

    import qtshim; qtshim.install()      # before importing wirely.ui.symbols
"""
from __future__ import annotations

import math
import sys
import types


# ============================================================================================ QtCore
class _Flags(int):
    def __or__(self, o):
        return _Flags(int(self) | int(o))

    __ror__ = __or__

    def __and__(self, o):
        return _Flags(int(self) & int(o))

    __rand__ = __and__


class Qt:
    AlignLeft, AlignRight, AlignHCenter = _Flags(0x1), _Flags(0x2), _Flags(0x4)
    AlignTop, AlignBottom, AlignVCenter = _Flags(0x20), _Flags(0x40), _Flags(0x80)
    AlignCenter = _Flags(0x84)
    TextWordWrap = _Flags(0x1000)
    SolidLine, DashLine, DotLine, NoPen = 1, 2, 3, 0
    NoBrush = None
    RoundCap, FlatCap, SquareCap = "round", "butt", "square"
    RoundJoin, MiterJoin, BevelJoin = "round", "miter", "bevel"
    transparent = "transparent"
    white, black = "white", "black"
    # mouse, keys and cursors (for the scene code)
    NoButton, LeftButton, RightButton, MiddleButton = _Flags(0), _Flags(1), _Flags(2), _Flags(4)
    NoModifier, ShiftModifier, ControlModifier, AltModifier = _Flags(0), _Flags(0x2000000), _Flags(0x4000000), \
        _Flags(0x8000000)
    Key_Escape, Key_Backspace, Key_Space, Key_Delete = 0x1000000, 0x1000003, 0x20, 0x1000007
    ArrowCursor, CrossCursor, PointingHandCursor = "default", "crosshair", "pointer"
    OpenHandCursor, ClosedHandCursor = "grab", "grabbing"
    ToolTipRole = 3


class QPointF:
    __slots__ = ("_x", "_y")

    def __init__(self, x=0.0, y=0.0):
        if isinstance(x, QPointF):
            x, y = x._x, x._y
        self._x, self._y = float(x), float(y)

    def x(self):
        return self._x

    def y(self):
        return self._y

    def setX(self, v):
        self._x = float(v)

    def setY(self, v):
        self._y = float(v)

    def __add__(self, o):
        return QPointF(self._x + o._x, self._y + o._y)

    def __sub__(self, o):
        return QPointF(self._x - o._x, self._y - o._y)

    def __mul__(self, k):
        return QPointF(self._x * k, self._y * k)

    def manhattanLength(self):
        return abs(self._x) + abs(self._y)

    def __eq__(self, o):
        return isinstance(o, QPointF) and self._x == o._x and self._y == o._y

    def __repr__(self):
        return f"QPointF({self._x}, {self._y})"


QPoint = QPointF


class QRectF:
    __slots__ = ("_x", "_y", "_w", "_h")

    def __init__(self, x=0.0, y=0.0, w=0.0, h=0.0):
        if isinstance(x, QRectF):
            x, y, w, h = x._x, x._y, x._w, x._h
        elif isinstance(x, QPointF) and isinstance(y, QPointF):     # two corners
            a, b = x, y
            x, y, w, h = a._x, a._y, b._x - a._x, b._y - a._y
        self._x, self._y, self._w, self._h = float(x), float(y), float(w), float(h)

    def x(self):
        return self._x

    def y(self):
        return self._y

    def left(self):
        return self._x

    def top(self):
        return self._y

    def right(self):
        return self._x + self._w

    def bottom(self):
        return self._y + self._h

    def width(self):
        return self._w

    def height(self):
        return self._h

    def center(self):
        return QPointF(self._x + self._w / 2, self._y + self._h / 2)

    def topLeft(self):
        return QPointF(self._x, self._y)

    def topRight(self):
        return QPointF(self.right(), self._y)

    def bottomLeft(self):
        return QPointF(self._x, self.bottom())

    def bottomRight(self):
        return QPointF(self.right(), self.bottom())

    def isNull(self):
        return self._w == 0 and self._h == 0

    def isEmpty(self):
        return self._w <= 0 or self._h <= 0

    def adjusted(self, a, b, c, d):
        return QRectF(self._x + a, self._y + b, self._w - a + c, self._h - b + d)

    def translated(self, dx, dy=None):
        if isinstance(dx, QPointF):
            dx, dy = dx._x, dx._y
        return QRectF(self._x + dx, self._y + dy, self._w, self._h)

    def united(self, o):
        if self.isNull():
            return QRectF(o)
        if o.isNull():
            return QRectF(self)
        x0, y0 = min(self.left(), o.left()), min(self.top(), o.top())
        x1, y1 = max(self.right(), o.right()), max(self.bottom(), o.bottom())
        return QRectF(x0, y0, x1 - x0, y1 - y0)

    def intersects(self, o):
        return (min(self.right(), o.right()) > max(self.left(), o.left()) and
                min(self.bottom(), o.bottom()) > max(self.top(), o.top()))

    def contains(self, pt):
        return self.left() <= pt.x() <= self.right() and self.top() <= pt.y() <= self.bottom()

    def moveRight(self, x):
        self._x = x - self._w

    def moveBottom(self, y):
        self._y = y - self._h

    def moveTo(self, x, y=None):
        if isinstance(x, QPointF):
            x, y = x._x, x._y
        self._x, self._y = float(x), float(y)

    def __repr__(self):
        return f"QRectF({self._x}, {self._y}, {self._w}, {self._h})"


QRect = QRectF


class _BoundSignal:
    def __init__(self):
        self._slots = []

    def connect(self, fn):
        self._slots.append(fn)

    def disconnect(self, fn=None):
        self._slots = [] if fn is None else [s for s in self._slots if s != fn]

    def emit(self, *args):
        for fn in list(self._slots):
            fn(*args)


class Signal:
    """Works like a Qt signal: connect() functions, emit() calls them (one set per object)."""

    def __init__(self, *a, **k):
        self.name = "_signal"

    def __set_name__(self, owner, name):
        self.name = "_signal_" + name

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        b = obj.__dict__.get(self.name)
        if b is None:
            b = obj.__dict__[self.name] = _BoundSignal()
        return b


class QObject:
    def __init__(self, *a, **k):
        pass


# ============================================================================================ QtGui
_NAMED = {"white": (255, 255, 255), "black": (0, 0, 0), "red": (255, 0, 0), "green": (0, 128, 0),
          "blue": (0, 0, 255), "yellow": (255, 255, 0), "gray": (128, 128, 128), "grey": (128, 128, 128),
          "orange": (255, 165, 0)}


class QColor:
    __slots__ = ("r", "g", "b", "a")

    def __init__(self, *args):
        self.r, self.g, self.b, self.a = 0, 0, 0, 255
        if not args:
            return
        if len(args) >= 3:
            self.r, self.g, self.b = (int(v) for v in args[:3])
            self.a = int(args[3]) if len(args) > 3 else 255
            return
        v = args[0]
        if isinstance(v, QColor):
            self.r, self.g, self.b, self.a = v.r, v.g, v.b, v.a
        elif isinstance(v, str):
            s = v.strip()
            if s == "transparent":
                self.a = 0
            elif s.startswith("#"):
                h = s[1:]
                if len(h) == 3:
                    h = "".join(ch * 2 for ch in h)
                if len(h) == 8:                     # Qt's #AARRGGBB
                    self.a = int(h[0:2], 16)
                    h = h[2:]
                self.r, self.g, self.b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            elif s.lower() in _NAMED:
                self.r, self.g, self.b = _NAMED[s.lower()]

    def red(self):
        return self.r

    def green(self):
        return self.g

    def blue(self):
        return self.b

    def alpha(self):
        return self.a

    def alphaF(self):
        return self.a / 255.0

    def setAlpha(self, a):
        self.a = max(0, min(255, int(a)))

    def setAlphaF(self, a):
        self.a = max(0, min(255, int(round(float(a) * 255))))

    def setRgb(self, r, g, b, a=255):
        self.r, self.g, self.b, self.a = int(r), int(g), int(b), int(a)

    def name(self):
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    def lighter(self, f=150):
        k = f / 100.0
        return QColor(min(255, int(self.r * k)), min(255, int(self.g * k)), min(255, int(self.b * k)), self.a)

    def darker(self, f=200):
        k = 100.0 / f
        return QColor(int(self.r * k), int(self.g * k), int(self.b * k), self.a)

    def css(self):
        if self.a >= 255:
            return f"#{self.r:02x}{self.g:02x}{self.b:02x}"
        return f"rgba({self.r},{self.g},{self.b},{self.a / 255:.3g})"

    def __eq__(self, o):
        return isinstance(o, QColor) and (self.r, self.g, self.b, self.a) == (o.r, o.g, o.b, o.a)

    def __repr__(self):
        return f"QColor({self.css()})"


def _css(c):
    if c is None:
        return None
    if isinstance(c, QColor):
        return c.css()
    return QColor(c).css()


class _Gradient:
    def __init__(self):
        self.stops = []

    def setColorAt(self, t, col):
        self.stops.append((float(t), _css(col)))


class QRadialGradient(_Gradient):
    def __init__(self, c, r, *a):
        super().__init__()
        self.cx, self.cy, self.r = c.x(), c.y(), float(r)

    def op(self):
        return ["rg", self.cx, self.cy, self.r, self.stops]


class QLinearGradient(_Gradient):
    def __init__(self, a, b, *rest):
        super().__init__()
        if isinstance(a, QPointF):
            self.p = (a.x(), a.y(), b.x(), b.y())
        else:
            self.p = (float(a), float(b), float(rest[0]), float(rest[1]))

    def op(self):
        return ["lg", *self.p, self.stops]


class QBrush:
    def __init__(self, c=None):
        if isinstance(c, QBrush):
            self.fill = c.fill
        elif isinstance(c, _Gradient):
            self.fill = c
        else:
            self.fill = None if c is None else QColor(c)


class QPen:
    def __init__(self, *args):
        self.color = QColor("black")
        self.width = 1.0
        self.style = Qt.SolidLine
        self.cap = Qt.SquareCap
        self.join = Qt.BevelJoin
        if args:
            a = args[0]
            if isinstance(a, QPen):
                self.color, self.width, self.style, self.cap, self.join = QColor(a.color), a.width, a.style, a.cap, a.join
                return
            if a == Qt.NoPen and len(args) == 1 and not isinstance(a, QColor):
                self.style = Qt.NoPen
                return
            self.color = QColor(a)
            if len(args) > 1:
                self.width = float(args[1])
            if len(args) > 2:
                self.style = args[2]

    def setCapStyle(self, c):
        self.cap = c

    def setJoinStyle(self, j):
        self.join = j

    def setWidthF(self, w):
        self.width = float(w)

    setWidth = setWidthF

    def widthF(self):
        return self.width

    def setColor(self, c):
        self.color = QColor(c)

    def setCosmetic(self, _on):
        pass

    def setStyle(self, s):
        self.style = s


class QFont:
    def __init__(self, family="", *a):
        self.px = 13
        self.bold = False
        self.mono = "mono" in str(family).lower()

    def setPixelSize(self, px):
        self.px = int(px)

    def pixelSize(self):
        return self.px

    def setPointSizeF(self, pt):
        self.px = int(round(pt * 4 / 3))

    def setBold(self, b):
        self.bold = bool(b)

    def bold(self):
        return self.bold

    def setStyleHint(self, h):
        if h == QFont.Monospace:
            self.mono = True

    def setFamily(self, f):
        self.mono = "mono" in str(f).lower()

    Monospace = "mono"


# text measuring: the browser replaces this with the real canvas measureText
def _approx_width(text, px, bold, mono):
    if mono:
        return len(text) * px * 0.6
    w = 0.0
    for ch in text:
        if ch in "il.,:;|'!":
            w += 0.28
        elif ch in "mwMW":
            w += 0.85
        elif ch.isupper() or ch.isdigit():
            w += 0.64
        else:
            w += 0.53
    return w * px * (1.07 if bold else 1.0)


measure = _approx_width


class QFontMetricsF:
    def __init__(self, font):
        self.f = font

    def horizontalAdvance(self, text):
        return float(measure(str(text), self.f.px, self.f.bold, self.f.mono))

    width = horizontalAdvance

    def height(self):
        return self.f.px * 1.25


class QPolygonF(list):
    pass


class QPainterPath:
    def __init__(self, start=None):
        self.cmds = []
        self._cur = (0.0, 0.0)
        self._start = (0.0, 0.0)
        self._pts = []
        if start is not None:
            self.moveTo(start)

    @staticmethod
    def _xy(a, b):
        if isinstance(a, QPointF):
            return a.x(), a.y()
        return float(a), float(b)

    def moveTo(self, x, y=None):
        x, y = self._xy(x, y)
        self.cmds.append(["M", x, y])
        self._cur = self._start = (x, y)
        self._pts.append((x, y))

    def lineTo(self, x, y=None):
        x, y = self._xy(x, y)
        self.cmds.append(["L", x, y])
        self._cur = (x, y)
        self._pts.append((x, y))

    def quadTo(self, *a):
        if isinstance(a[0], QPointF):
            a = (a[0].x(), a[0].y(), a[1].x(), a[1].y())
        self.cmds.append(["Q", *map(float, a)])
        self._cur = (float(a[2]), float(a[3]))
        self._pts += [(a[0], a[1]), self._cur]

    def cubicTo(self, *a):
        if isinstance(a[0], QPointF):
            a = (a[0].x(), a[0].y(), a[1].x(), a[1].y(), a[2].x(), a[2].y())
        self.cmds.append(["C", *map(float, a)])
        self._cur = (float(a[4]), float(a[5]))
        self._pts += [(a[0], a[1]), (a[2], a[3]), self._cur]

    def arcTo(self, rect, start, sweep):
        """Qt: a line from the current point to the start of the arc, then the arc (degrees, anticlockwise)."""
        cx, cy = rect.center().x(), rect.center().y()
        rx, ry = rect.width() / 2, rect.height() / 2
        self.cmds.append(["A", cx, cy, rx, ry, float(start), float(sweep)])
        end = math.radians(start + sweep)
        self._cur = (cx + rx * math.cos(end), cy - ry * math.sin(end))
        self._pts += [(cx - rx, cy - ry), (cx + rx, cy + ry)]

    def closeSubpath(self):
        self.cmds.append(["Z"])
        self._cur = self._start

    def addRect(self, r, *a):
        if not isinstance(r, QRectF):
            r = QRectF(r, *a)
        self.cmds += [["M", r.left(), r.top()], ["L", r.right(), r.top()], ["L", r.right(), r.bottom()],
                      ["L", r.left(), r.bottom()], ["Z"]]
        self._pts += [(r.left(), r.top()), (r.right(), r.bottom())]

    def addEllipse(self, c, rx, ry=None):
        if isinstance(c, QRectF):
            rx, ry = c.width() / 2, c.height() / 2
            c = c.center()
        self.cmds.append(["E", c.x(), c.y(), float(rx), float(ry)])
        self._pts += [(c.x() - rx, c.y() - ry), (c.x() + rx, c.y() + ry)]

    def subtracted(self, other):
        """This shape with `other` cut out of it (the page draws it by clipping the other shape away)."""
        out = QPainterPath()
        out.cmds = [list(c) for c in self.cmds] + [["X", [list(c) for c in other.cmds]]]
        out._pts = list(self._pts)
        return out

    def currentPosition(self):
        return QPointF(*self._cur)

    def translated(self, dx, dy=None):
        if isinstance(dx, QPointF):
            dx, dy = dx.x(), dx.y()
        out = QPainterPath()
        for c in self.cmds:
            if c[0] in ("M", "L"):
                out.cmds.append([c[0], c[1] + dx, c[2] + dy])
            elif c[0] in ("A", "E"):
                out.cmds.append([c[0], c[1] + dx, c[2] + dy, *c[3:]])
            elif c[0] == "Q":
                out.cmds.append(["Q", c[1] + dx, c[2] + dy, c[3] + dx, c[4] + dy])
            elif c[0] == "C":
                out.cmds.append(["C", c[1] + dx, c[2] + dy, c[3] + dx, c[4] + dy, c[5] + dx, c[6] + dy])
            else:
                out.cmds.append(list(c))
        out._pts = [(x + dx, y + dy) for x, y in self._pts]
        return out

    def contains(self, pt):
        """Is the point inside? (Measured against the path's bounding box: right for the rectangles used.)"""
        return bool(self._pts) and self.boundingRect().contains(pt)

    def intersects(self, r):
        return bool(self._pts) and self.boundingRect().intersects(r)

    def boundingRect(self):
        if not self._pts:
            return QRectF()
        xs = [p[0] for p in self._pts]
        ys = [p[1] for p in self._pts]
        return QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


class QTransform:
    def m11(self):
        return 1.0


class QPainter:
    """Records drawing commands into self.ops (a list the web page replays on a canvas)."""
    Antialiasing = 1
    TextAntialiasing = 2
    SmoothPixmapTransform = 4

    def __init__(self, target=None):
        self.ops = target if isinstance(target, list) else []
        self._pen = QPen(QColor("black"))
        self._brush = None
        self._font = QFont()
        self._last_pen = self._last_brush = self._last_font = object()

    # ---- state
    def setRenderHint(self, *a):
        pass

    def save(self):
        self.ops.append(["save"])
        self._stack = getattr(self, "_stack", [])
        self._stack.append((self._pen, self._brush, self._font, self._last_pen, self._last_brush,
                            self._last_font))

    def restore(self):
        self.ops.append(["restore"])
        if getattr(self, "_stack", None):
            (self._pen, self._brush, self._font, self._last_pen, self._last_brush,
             self._last_font) = self._stack.pop()

    def end(self):
        pass

    def translate(self, dx, dy=None):
        if isinstance(dx, QPointF):
            dx, dy = dx.x(), dx.y()
        self.ops.append(["tr", float(dx), float(dy)])

    def rotate(self, deg):
        if deg:
            self.ops.append(["rot", float(deg)])

    def scale(self, sx, sy):
        self.ops.append(["sc", float(sx), float(sy)])

    def worldTransform(self):
        return QTransform()

    def resetTransform(self):
        self.ops.append(["reset"])

    def setOpacity(self, a):
        self.ops.append(["alpha", float(a)])

    def setPen(self, pen):
        if pen is None or (not isinstance(pen, (QPen, QColor, str)) and pen == Qt.NoPen):
            pen = QPen(Qt.NoPen)
        elif isinstance(pen, (QColor, str)):
            pen = QPen(QColor(pen), 1.0)
        self._pen = pen

    def setBrush(self, b):
        if b is None or b is Qt.NoBrush:
            self._brush = None
        elif isinstance(b, QBrush):
            self._brush = b.fill
        elif isinstance(b, _Gradient):
            self._brush = b
        else:
            self._brush = QColor(b)

    def setFont(self, f):
        self._font = f

    def font(self):
        return self._font

    def pen(self):
        return self._pen

    def brush(self):
        return QBrush(self._brush) if not isinstance(self._brush, _Gradient) else QBrush(self._brush)

    # ---- emit state only when it changed (keeps the op lists short)
    def _sync_pen(self):
        p = self._pen
        if p.style == Qt.NoPen:
            key = None
        else:
            key = (p.color.css(), round(p.width, 3), p.style, p.cap, p.join)
        if key != self._last_pen:
            self.ops.append(["pen", *key] if key else ["pen"])
            self._last_pen = key

    def _sync_brush(self):
        b = self._brush
        if isinstance(b, _Gradient):
            op = b.op()
            self.ops.append(["brush", op])
            self._last_brush = id(b)
            return
        key = None if b is None else b.css()
        if key != self._last_brush:
            self.ops.append(["brush", key] if key else ["brush"])
            self._last_brush = key

    def _sync_font(self):
        f = self._font
        key = (f.px, f.bold, f.mono)
        if key != self._last_font:
            self.ops.append(["font", f.px, 1 if f.bold else 0, 1 if f.mono else 0])
            self._last_font = key

    # ---- drawing
    def drawLine(self, *a):
        if len(a) == 2:
            x1, y1, x2, y2 = a[0].x(), a[0].y(), a[1].x(), a[1].y()
        else:
            x1, y1, x2, y2 = (float(v) for v in a)
        self._sync_pen()
        self.ops.append(["line", x1, y1, x2, y2])

    def drawLines(self, lines):
        for ln in lines:
            self.drawLine(*ln)

    def _rect_args(self, a):
        if isinstance(a[0], QRectF):
            r = a[0]
            return (r.x(), r.y(), r.width(), r.height()), a[1:]
        return tuple(float(v) for v in a[:4]), a[4:]

    def drawRect(self, *a):
        (x, y, w, h), _ = self._rect_args(a)
        self._sync_pen()
        self._sync_brush()
        self.ops.append(["rect", x, y, w, h])

    def fillRect(self, r, col):
        self.save()
        self.setPen(Qt.NoPen)
        self.setBrush(col)
        self.drawRect(r)
        self.restore()

    def drawRoundedRect(self, *a):
        (x, y, w, h), rest = self._rect_args(a)
        rx = float(rest[0]) if rest else 0.0
        ry = float(rest[1]) if len(rest) > 1 else rx
        self._sync_pen()
        self._sync_brush()
        self.ops.append(["rrect", x, y, w, h, rx, ry])

    def drawEllipse(self, *a):
        if isinstance(a[0], QPointF):
            cx, cy, rx, ry = a[0].x(), a[0].y(), float(a[1]), float(a[2])
        else:
            (x, y, w, h), _ = self._rect_args(a)
            cx, cy, rx, ry = x + w / 2, y + h / 2, w / 2, h / 2
        self._sync_pen()
        self._sync_brush()
        self.ops.append(["ell", cx, cy, rx, ry])

    def drawArc(self, rect, start16, span16):
        self._sync_pen()
        self.ops.append(["arc", rect.center().x(), rect.center().y(), rect.width() / 2, rect.height() / 2,
                         start16 / 16.0, span16 / 16.0])

    def drawPolygon(self, poly, *a):
        pts = [v for p in poly for v in (p.x(), p.y())]
        self._sync_pen()
        self._sync_brush()
        self.ops.append(["poly", 1, pts])

    def drawPolyline(self, poly, *a):
        pts = [v for p in poly for v in (p.x(), p.y())]
        self._sync_pen()
        self.ops.append(["poly", 0, pts])

    def drawPath(self, path):
        self._sync_pen()
        self._sync_brush()
        self.ops.append(["path", path.cmds])

    def drawPoints(self, pts):
        self._sync_pen()
        self.ops.append(["points", [v for p in pts for v in (p.x(), p.y())]])

    def drawText(self, *a):
        if isinstance(a[0], QRectF):
            r, flags, text = a[0], int(a[1]), str(a[2])
            box = [r.x(), r.y(), r.width(), r.height()]
        elif isinstance(a[0], QPointF):
            # baseline-anchored text at a point
            box, flags, text = [a[0].x(), a[0].y(), 0, 0], -1, str(a[1])
        else:
            box, flags, text = [float(a[0]), float(a[1]), 0, 0], -1, str(a[2])
        self._sync_pen()
        self._sync_font()
        self.ops.append(["text", *box, flags, text])

    def setClipRect(self, r, *a):
        self.ops.append(["clip", r.x(), r.y(), r.width(), r.height()])

    def drawPixmap(self, *a):
        pass


class QPixmap:
    def __init__(self, *a):
        pass

    def setDevicePixelRatio(self, *a):
        pass

    def fill(self, *a):
        pass


def _seg_dist2(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
    ex, ey = x1 + t * dx - px, y1 + t * dy - py
    return ex * ex + ey * ey


class _Stroke:
    """The outline of a path drawn with a thick pen: used to test whether the mouse is on a wire."""

    def __init__(self, path, width):
        self.path, self.half = path, width / 2
        self.pts = [(c[1], c[2]) for c in path.cmds if c[0] in ("M", "L")]

    def contains(self, pt):
        px, py = pt.x(), pt.y()
        h2 = self.half * self.half
        return any(_seg_dist2(px, py, *a, *b) <= h2 for a, b in zip(self.pts, self.pts[1:])) or \
            (len(self.pts) == 1 and _seg_dist2(px, py, *self.pts[0], *self.pts[0]) <= h2)

    def boundingRect(self):
        return self.path.boundingRect().adjusted(-self.half, -self.half, self.half, self.half)

    def intersects(self, r):
        r = r.adjusted(-self.half, -self.half, self.half, self.half)
        for (x1, y1), (x2, y2) in zip(self.pts, self.pts[1:]):
            seg = QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)).adjusted(-0.01, -0.01, 0.01, 0.01)
            if seg.intersects(r):
                return True
        return False

    def translated(self, *a):
        return self


class QPainterPathStroker:
    def __init__(self):
        self.w = 1.0

    def setWidth(self, w):
        self.w = float(w)

    def setCapStyle(self, *a):
        pass

    def createStroke(self, path):
        return _Stroke(path, self.w)


# ============================================================================================ QtWidgets (scene)
class QGraphicsItem:
    """Enough of QGraphicsItem for Wirely's sheet items: position, z order, selection, visibility."""
    ItemIsSelectable = 1
    ItemIsMovable = 2

    def __init__(self, *a):
        self._pos = QPointF(0, 0)
        self._z = 0.0
        self._sel = False
        self._vis = True
        self._opacity = 1.0
        self._scene = None
        self._selectable = False
        self._hover = False

    def setFlag(self, flag, on=True):
        if flag == QGraphicsItem.ItemIsSelectable:
            self._selectable = bool(on)

    def setAcceptHoverEvents(self, on):
        self._hover = bool(on)

    def acceptHoverEvents(self):
        return self._hover

    def setCursor(self, *a):
        pass

    def setToolTip(self, *a):
        pass

    NoCache, ItemCoordinateCache, DeviceCoordinateCache = 0, 1, 2

    def setCacheMode(self, *a):          # the page keeps its own ready-drawn pictures (App._def)
        pass

    def setZValue(self, z):
        self._z = float(z)

    def zValue(self):
        return self._z

    def setOpacity(self, o):
        self._opacity = float(o)

    def opacity(self):
        return self._opacity

    def prepareGeometryChange(self):
        pass

    def update(self, *a):
        pass

    def setPos(self, x, y=None):
        self._pos = QPointF(x) if isinstance(x, QPointF) else QPointF(x, y)

    def pos(self):
        return QPointF(self._pos)

    def x(self):
        return self._pos.x()

    def y(self):
        return self._pos.y()

    def scene(self):
        return self._scene

    def isSelected(self):
        return self._sel

    def setSelected(self, on):
        if self._selectable or not on:
            self._sel = bool(on)

    def isVisible(self):
        return self._vis

    def setVisible(self, on):
        self._vis = bool(on)

    def show(self):
        self._vis = True

    def hide(self):
        self._vis = False

    def boundingRect(self):
        return QRectF()

    def shape(self):
        p = QPainterPath()
        p.addRect(self.boundingRect())
        return p

    def contains_scene(self, pt):
        local = QPointF(pt.x() - self._pos.x(), pt.y() - self._pos.y())
        sh = self.shape()
        return sh.contains(local)

    def intersects_scene(self, r):
        local = r.translated(-self._pos.x(), -self._pos.y())
        sh = self.shape()
        return sh.intersects(local)


class SceneEvent:
    """A mouse / key / wheel event as the scene code expects it."""

    def __init__(self, x=0.0, y=0.0, button=0, buttons=0, modifiers=0, sx=None, sy=None, key=0, delta=0):
        self._scene_pos = QPointF(x, y)
        self._screen = QPointF(x if sx is None else sx, y if sy is None else sy)
        self._button, self._buttons, self._mods = _Flags(button), _Flags(buttons), _Flags(modifiers)
        self._key, self._delta = key, delta
        self._accepted = True
        self._local = QPointF(x, y)

    def scenePos(self):
        return QPointF(self._scene_pos)

    def screenPos(self):
        return QPointF(self._screen)

    def pos(self):
        return QPointF(self._local)

    def position(self):
        return QPointF(self._local)

    def button(self):
        return self._button

    def buttons(self):
        return self._buttons

    def modifiers(self):
        return self._mods

    def key(self):
        return self._key

    def isAutoRepeat(self):
        return False

    def delta(self):
        return self._delta

    def accept(self):
        self._accepted = True

    def ignore(self):
        self._accepted = False

    def isAccepted(self):
        return self._accepted

    def acceptProposedAction(self):
        self._accepted = True


class QGraphicsScene:
    """Keeps the items and hands mouse events to them, like Qt's scene (just what Wirely needs)."""

    def __init__(self, *a):
        self._items = []
        self._order = 0
        self._grabber = None
        self._hovered = None
        self._views = []

    def setSceneRect(self, *a):
        pass

    def addItem(self, it):
        if it._scene is self:
            return
        it._scene = self
        self._order += 1
        it._order = self._order
        self._items.append(it)

    def removeItem(self, it):
        if it in self._items:
            self._items.remove(it)
        it._scene = None
        if self._grabber is it:
            self._grabber = None
        if self._hovered is it:
            self._hovered = None

    def all_items(self):
        return sorted(self._items, key=lambda i: (i._z, i._order))

    def items(self, where=None):
        """Items under a point (or touching a rectangle), topmost first."""
        out = []
        for it in reversed(self.all_items()):
            if not it._vis:
                continue
            if where is None:
                out.append(it)
            elif isinstance(where, QPointF):
                if it.contains_scene(where):
                    out.append(it)
            elif it.intersects_scene(where):
                out.append(it)
        return out

    def selectedItems(self):
        return [it for it in self._items if it._sel]

    def clearSelection(self):
        for it in self._items:
            it._sel = False

    def views(self):
        return self._views

    def update(self, *a):
        pass

    # ---- default event handling: give the event to the item under the mouse (sliders), and hover
    def mousePressEvent(self, e):
        pos = e.scenePos()
        for it in self.items(pos):
            fn = getattr(it, "mousePressEvent", None)
            if fn is not None:
                e._local = QPointF(pos.x() - it.x(), pos.y() - it.y())
                fn(e)
                self._grabber = it
                return

    def mouseMoveEvent(self, e):
        pos = e.scenePos()
        if self._grabber is not None:
            e._local = QPointF(pos.x() - self._grabber.x(), pos.y() - self._grabber.y())
            fn = getattr(self._grabber, "mouseMoveEvent", None)
            if fn:
                fn(e)
            return
        top = None
        for it in self.items(pos):
            if it._hover:
                top = it
                break
        if top is not self._hovered:
            if self._hovered is not None and hasattr(self._hovered, "hoverLeaveEvent"):
                self._hovered.hoverLeaveEvent(e)
            self._hovered = top
            if top is not None and hasattr(top, "hoverEnterEvent"):
                top.hoverEnterEvent(e)

    def mouseReleaseEvent(self, e):
        g, self._grabber = self._grabber, None
        if g is not None and hasattr(g, "mouseReleaseEvent"):
            pos = e.scenePos()
            e._local = QPointF(pos.x() - g.x(), pos.y() - g.y())
            g.mouseReleaseEvent(e)

    def wheelEvent(self, e):
        pos = e.scenePos()
        for it in self.items(pos):
            fn = getattr(it, "wheelEvent", None)
            if fn is not None:
                e._local = QPointF(pos.x() - it.x(), pos.y() - it.y())
                fn(e)
                return
        e.ignore()

    def mouseDoubleClickEvent(self, e):
        pass

    def keyPressEvent(self, e):
        pass

    def leave(self):
        if self._hovered is not None and hasattr(self._hovered, "hoverLeaveEvent"):
            self._hovered.hoverLeaveEvent(None)
        self._hovered = None


class _Anything:
    """Placeholder for Qt classes the drawing code imports but never uses in the browser."""

    def __init__(self, *a, **k):
        pass

    def __getattr__(self, name):
        return _Anything()

    def __call__(self, *a, **k):
        return _Anything()


def install():
    """Make `import PySide6.QtCore / QtGui / QtWidgets` find this module's classes."""
    if "PySide6" in sys.modules and not getattr(sys.modules["PySide6"], "_wirely_shim", False):
        return False
    pkg = types.ModuleType("PySide6")
    pkg._wirely_shim = True
    pkg.__path__ = []
    core = types.ModuleType("PySide6.QtCore")
    for name in ("Qt", "QPointF", "QPoint", "QRectF", "QRect", "Signal", "QObject"):
        setattr(core, name, globals()[name])
    core.QTimer = _Anything
    gui = types.ModuleType("PySide6.QtGui")
    for name in ("QColor", "QBrush", "QPen", "QFont", "QFontMetricsF", "QPolygonF", "QPainterPath", "QPainter",
                 "QPixmap", "QRadialGradient", "QLinearGradient", "QPainterPathStroker", "QTransform"):
        setattr(gui, name, globals()[name])
    gui.QIcon = _Anything
    widgets = types.ModuleType("PySide6.QtWidgets")

    class _Widget:
        def __init__(self, *a, **k):
            pass

        def __getattr__(self, name):
            return _Anything()

    widgets.QGraphicsItem = QGraphicsItem
    widgets.QGraphicsScene = QGraphicsScene
    widgets.__getattr__ = lambda name: _Widget
    pkg.QtCore, pkg.QtGui, pkg.QtWidgets = core, gui, widgets
    sys.modules.update({"PySide6": pkg, "PySide6.QtCore": core, "PySide6.QtGui": gui, "PySide6.QtWidgets": widgets})
    return True
