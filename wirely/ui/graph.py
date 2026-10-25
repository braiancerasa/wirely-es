"""The graph (oscilloscope) panel: plots the voltage at each graph probe against time while the circuit runs."""
from __future__ import annotations

import bisect

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QLabel, QPushButton, QToolButton, QVBoxLayout,
                               QWidget)

from ..model.units import fmt
from ..sim.audio import frequency
from . import theme
from .symbols import CHANNEL_RGB

TIMEBASES = [("Auto", None), ("100 µs/div", 1e-4), ("1 ms/div", 1e-3), ("10 ms/div", 1e-2),
             ("100 ms/div", 0.1), ("0.5 s/div", 0.5), ("1 s/div", 1.0), ("5 s/div", 5.0)]
VOLTS = [("Auto", None), ("0.5 V/div", 0.5), ("1 V/div", 1.0), ("2 V/div", 2.0), ("5 V/div", 5.0)]
NICE = [1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
MAX_POINTS = 400_000
DIVS_X, DIVS_Y = 10, 8


class Trace:
    def __init__(self):
        self.t, self.v = [], []

    def add(self, t, v):
        self.t.append(t)
        self.v.append(v)
        if len(self.t) > MAX_POINTS:
            del self.t[:MAX_POINTS // 4]
            del self.v[:MAX_POINTS // 4]

    def window(self, t0, t1):
        i = max(0, bisect.bisect_left(self.t, t0) - 1)
        j = bisect.bisect_right(self.t, t1) + 1
        return self.t[i:j], self.v[i:j]


class Plot(QWidget):
    def __init__(self, panel):
        super().__init__()
        self.panel = panel
        self.setMinimumHeight(150)
        self.setMouseTracking(True)
        self._mouse = None

    def leaveEvent(self, e):
        self._mouse = None
        self.update()

    def mouseMoveEvent(self, e):
        self._mouse = e.position()
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self.panel.paint_plot(p, QRectF(self.rect()), self._mouse)
        p.end()


class GraphPanel(QWidget):
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("graphPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.traces: dict[str, Trace] = {}
        self.t_now = 0.0
        self.vmax_hint = 9.0
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 6, 10, 8)
        v.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(8)
        title = QLabel("Graph")
        title.setObjectName("sectionHeader")
        title.setContentsMargins(0, 0, 0, 0)
        top.addWidget(title)
        self.chips = QLabel("Put a graph probe (Meters & probes) on a wire, then press Play.")
        self.chips.setObjectName("muted")
        self.chips.setTextFormat(Qt.RichText)
        top.addWidget(self.chips, 1)
        self.tbox = QComboBox()
        for name, _v in TIMEBASES:
            self.tbox.addItem(name)
        self.tbox.setToolTip("Time per square across")
        self.tbox.currentIndexChanged.connect(lambda _i: self.plot.update())
        self.vbox = QComboBox()
        for name, _v in VOLTS:
            self.vbox.addItem(name)
        self.vbox.setToolTip("Volts per square up")
        self.vbox.currentIndexChanged.connect(lambda _i: self.plot.update())
        top.addWidget(QLabel("Time"))
        top.addWidget(self.tbox)
        top.addWidget(QLabel("Volts"))
        top.addWidget(self.vbox)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.clear)
        save = QPushButton("Save picture…")
        save.clicked.connect(self.save_picture)
        top.addWidget(clear)
        top.addWidget(save)
        close = QToolButton()
        close.setText("✕")
        close.setToolTip("Hide the graph (View → Graph shows it again)")
        close.clicked.connect(self.closed.emit)
        top.addWidget(close)
        v.addLayout(top)
        self.plot = Plot(self)
        v.addWidget(self.plot, 1)

    # ------------------------------------------------------------------ data
    def clear(self):
        self.traces = {}
        self.t_now = 0.0
        self.chips.setText("Put a graph probe (Meters & probes) on a wire, then press Play.")
        self.plot.update()

    def add_samples(self, samples, t_now):
        for t, vals in samples:
            for ch, val in vals.items():
                self.traces.setdefault(ch, Trace()).add(t, val)
        self.t_now = t_now
        self._update_chips()
        self.plot.update()

    def has_data(self):
        return any(tr.t for tr in self.traces.values())

    # ------------------------------------------------------------------ scales
    def timebase(self):
        tdiv = TIMEBASES[self.tbox.currentIndex()][1]
        if tdiv is not None:
            return tdiv
        # auto: about three cycles of the fastest repeating signal on any probe, else 0.5 s per square.
        # (Looking at every probe matters: in a buck converter probe A is smooth DC and only B repeats.)
        fastest = None
        for ch in sorted(self.traces):
            ts, vs = self.traces[ch].window(self.t_now - 10.0, self.t_now)
            f = frequency(ts, vs)
            if f and (fastest is None or f > fastest):
                fastest = f
        if fastest:
            want = 3.0 / fastest / DIVS_X
            return min(NICE, key=lambda n: abs(n - want) if n >= want * 0.6 else 1e9)
        return 0.5

    def volt_range(self, t0, t1):
        vdiv = VOLTS[self.vbox.currentIndex()][1]
        lo, hi = 0.0, 0.0
        for tr in self.traces.values():
            _ts, vs = tr.window(t0, t1)
            if vs:
                lo, hi = min(lo, min(vs)), max(hi, max(vs))
        if vdiv is not None:
            mid = 0.0 if lo >= 0 else (lo + hi) / 2
            base = 0.0 if lo >= 0 else mid - vdiv * DIVS_Y / 2
            return base, base + vdiv * DIVS_Y
        span = max(hi - lo, 1.0)
        step = min([n for n in NICE + [10.0, 20.0, 50.0] if n * DIVS_Y >= span * 1.1] or [100.0])
        base = 0.0 if lo >= 0 else step * round(lo / step - 0.5)
        if base + step * DIVS_Y < hi:
            base = hi - step * DIVS_Y
        return base, base + step * DIVS_Y

    def _update_chips(self):
        if not self.traces:
            return
        bits = []
        for ch in sorted(self.traces):
            tr = self.traces[ch]
            if not tr.v:
                continue
            col = CHANNEL_RGB.get(ch, "#e0a800")
            ts, vs = tr.window(self.t_now - max(5.0, 10 * self.timebase()), self.t_now)
            f = frequency(ts, vs)
            extra = f" · {fmt(f, 'Hz')}" if f else ""
            now = tr.v[-1] if abs(tr.v[-1]) >= 1e-3 else 0.0
            bits.append(f"<span style='color:{col}; font-weight:700'>■ {ch}</span> "
                        f"<span style='color:{theme.TEXT}'>{fmt(now, 'V')}{extra}</span>")
        self.chips.setText("&nbsp;&nbsp;&nbsp;".join(bits))

    # ------------------------------------------------------------------ drawing
    def paint_plot(self, p: QPainter, rect: QRectF, mouse):
        bg = QColor(theme.CANVAS)
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.setBrush(bg)
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 6, 6)
        area = rect.adjusted(48, 10, -12, -22)
        tdiv = self.timebase()
        t1 = max(self.t_now, tdiv * DIVS_X)
        t0 = t1 - tdiv * DIVS_X
        v0, v1 = self.volt_range(t0, t1)
        f = QFont()
        f.setPixelSize(10)
        p.setFont(f)
        grid = QColor(theme.GRID_DOT)
        for i in range(DIVS_X + 1):
            x = area.left() + area.width() * i / DIVS_X
            p.setPen(QPen(grid, 1, Qt.SolidLine if i in (0, DIVS_X) else Qt.DotLine))
            p.drawLine(QPointF(x, area.top()), QPointF(x, area.bottom()))
        for j in range(DIVS_Y + 1):
            y = area.bottom() - area.height() * j / DIVS_Y
            p.setPen(QPen(grid, 1, Qt.SolidLine if j in (0, DIVS_Y) else Qt.DotLine))
            p.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
            if j % 2 == 0:
                p.setPen(QColor(theme.TEXT_MUTED))
                p.drawText(QRectF(rect.left() + 2, y - 7, 42, 14), Qt.AlignRight | Qt.AlignVCenter,
                           fmt(v0 + (v1 - v0) * j / DIVS_Y, "V"))
        p.setPen(QColor(theme.TEXT_MUTED))
        p.drawText(QRectF(area.left(), area.bottom() + 4, area.width() / 2, 14), Qt.AlignLeft,
                   f"{fmt(t0, 's')}")
        p.drawText(QRectF(area.center().x(), area.bottom() + 4, area.width() / 2, 14), Qt.AlignRight,
                   f"{fmt(t1, 's')}   ({fmt(tdiv, 's')} per square)")
        if not self.traces:
            p.drawText(area, Qt.AlignCenter, "No signals yet — put a graph probe on a wire and press Play.")
            return

        def X(t):
            return area.left() + (t - t0) / (t1 - t0) * area.width()

        def Y(val):
            return area.bottom() - (val - v0) / (v1 - v0) * area.height()
        p.save()
        p.setClipRect(area.adjusted(-1, -2, 1, 2))
        p.setBrush(Qt.NoBrush)          # outline only: a filled trace would hide the grid and the other traces
        cols = max(1, int(area.width()))
        for ch in sorted(self.traces):
            ts, vs = self.traces[ch].window(t0, t1)
            if len(ts) < 2:
                continue
            pen = QPen(QColor(CHANNEL_RGB.get(ch, "#e0a800")), 2.0)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            path = QPainterPath()
            if len(ts) > 3 * cols:
                # many points: draw each pixel column as its min/max
                bucket = {}
                for t, val in zip(ts, vs):
                    c = int((t - t0) / (t1 - t0) * cols)
                    lo_hi = bucket.get(c)
                    bucket[c] = (min(lo_hi[0], val), max(lo_hi[1], val), val) if lo_hi else (val, val, val)
                first = True
                for c in sorted(bucket):
                    lo, hi, last = bucket[c]
                    x = area.left() + c
                    if first:
                        path.moveTo(x, Y(lo))
                        first = False
                    path.lineTo(x, Y(lo))
                    path.lineTo(x, Y(hi))
                    path.lineTo(x, Y(last))
            else:
                path.moveTo(X(ts[0]), Y(vs[0]))
                for t, val in zip(ts[1:], vs[1:]):
                    path.lineTo(X(t), Y(val))
            p.drawPath(path)
        p.restore()
        if mouse is not None and area.contains(mouse):
            t = t0 + (mouse.x() - area.left()) / area.width() * (t1 - t0)
            p.setPen(QPen(QColor(theme.TEXT_MUTED), 1, Qt.DashLine))
            p.drawLine(QPointF(mouse.x(), area.top()), QPointF(mouse.x(), area.bottom()))
            lines = [f"t = {fmt(t, 's')}"]
            for ch in sorted(self.traces):
                tr = self.traces[ch]
                i = bisect.bisect_left(tr.t, t)
                if 0 < i < len(tr.t):
                    lines.append(f"{ch}: {fmt(tr.v[i], 'V')}")
            box = QRectF(mouse.x() + 8, area.top() + 6, 92, 14 * len(lines) + 8)
            if box.right() > area.right():
                box.moveRight(mouse.x() - 8)
            bgc = QColor(theme.PANEL)
            bgc.setAlpha(235)
            p.setPen(QPen(QColor(theme.BORDER), 1))
            p.setBrush(bgc)
            p.drawRoundedRect(box, 5, 5)
            p.setPen(QColor(theme.TEXT))
            for k, line in enumerate(lines):
                p.drawText(QRectF(box.left() + 6, box.top() + 4 + 14 * k, box.width() - 8, 14), Qt.AlignLeft, line)

    def save_picture(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save graph", "graph.png", "PNG picture (*.png)")
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            self.plot.grab().save(path, "PNG")
