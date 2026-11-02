"""El panel del gráfico (osciloscopio): representa el voltaje o la corriente de cada sonda frente al tiempo
mientras el circuito se ejecuta."""
from __future__ import annotations

import bisect

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QToolButton,
                               QVBoxLayout, QWidget)

from ..model.units import fmt
from ..sim.audio import frequency
from . import theme
from .symbols import CHANNEL_RGB

TIMEBASES = [("Auto", None), ("100 µs/div", 1e-4), ("1 ms/div", 1e-3), ("10 ms/div", 1e-2),
             ("100 ms/div", 0.1), ("0.5 s/div", 0.5), ("1 s/div", 1.0), ("5 s/div", 5.0)]
VOLTS = [("Auto", None), ("0.5 V/div", 0.5), ("1 V/div", 1.0), ("2 V/div", 2.0), ("5 V/div", 5.0)]
AMPS = [("Auto", None), ("1 mA/div", 1e-3), ("10 mA/div", 1e-2), ("100 mA/div", 0.1), ("1 A/div", 1.0)]
VIEWS = [("Separados", "separated"), ("Superpuestos", "overlaid")]
NICE = [1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
MAX_POINTS = 400_000
DIVS_X, DIVS_Y = 10, 8
HINT = ("Coloque una sonda de tensión o de corriente (Medidores y sondas) en un cable, "
        "luego presione Ejecutar.")


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
        self.setToolTip("Arrastre el gráfico para moverse por el tiempo mientras la simulación está en pausa")
        self._mouse = None
        self._drag = None       # x del último movimiento mientras se arrastra para mover el gráfico

    def refresh_cursor(self):
        if self._drag is not None:
            self.setCursor(Qt.ClosedHandCursor)
        elif self.panel.can_pan():
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.unsetCursor()

    def leaveEvent(self, e):
        self._mouse = None
        self.refresh_cursor()
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.panel.can_pan():
            self._drag = e.position().x()
            self._mouse = None
            self.refresh_cursor()
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        pos = e.position()
        if self._drag is not None:
            dx = pos.x() - self._drag
            self._drag = pos.x()
            self.panel.pan_by(dx, self.width())
            self._mouse = None
        else:
            self._mouse = pos
            self.refresh_cursor()
        self.update()

    def mouseReleaseEvent(self, e):
        if self._drag is not None and e.button() == Qt.LeftButton:
            self._drag = None
            self.refresh_cursor()
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self.panel.paint_plot(p, QRectF(self.rect()), self._mouse)
        p.end()


class GraphPanel(QWidget):
    closed = Signal()

    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setObjectName("graphPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.settings = settings
        self.traces: dict[str, Trace] = {}
        self.t_now = 0.0
        self.pan = 0.0              # segundos que la vista está corrida hacia atrás (solo en pausa)
        self.following = True       # mientras ejecuta, el gráfico sigue el trazo en vivo
        self.vmax_hint = 9.0
        self.mode = "separated"
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 6, 10, 8)
        v.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(8)
        title = QLabel("Gráfico")
        title.setObjectName("sectionHeader")
        title.setContentsMargins(0, 0, 0, 0)
        top.addWidget(title)
        self.chips = QLabel(HINT)
        self.chips.setObjectName("muted")
        self.chips.setTextFormat(Qt.RichText)
        # las lecturas no deben ensanchar la ventana: si no entran, se recortan
        self.chips.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        top.addWidget(self.chips, 1)
        self.mbox = QComboBox()
        for name, _key in VIEWS:
            self.mbox.addItem(name)
        self.mbox.setToolTip("Gráficos separados (voltaje arriba, corriente abajo) o superpuestos en uno solo")
        self.tbox = QComboBox()
        for name, _v in TIMEBASES:
            self.tbox.addItem(name)
        self.tbox.setToolTip("Tiempo por cuadro horizontal")
        self.vbox = QComboBox()
        for name, _v in VOLTS:
            self.vbox.addItem(name)
        self.vbox.setToolTip("Voltios por cuadro vertical")
        self.abox = QComboBox()
        for name, _v in AMPS:
            self.abox.addItem(name)
        self.abox.setToolTip("Amperes por cuadro vertical")
        top.addWidget(QLabel("Vista"))
        top.addWidget(self.mbox)
        top.addWidget(QLabel("Tiempo"))
        top.addWidget(self.tbox)
        top.addWidget(QLabel("Voltios"))
        top.addWidget(self.vbox)
        top.addWidget(QLabel("Amperes"))
        top.addWidget(self.abox)
        clear = QPushButton("Limpiar")
        clear.clicked.connect(self.clear)
        save = QPushButton("Guardar imagen…")
        save.clicked.connect(self.save_picture)
        top.addWidget(clear)
        top.addWidget(save)
        close = QToolButton()
        close.setText("✕")
        close.setToolTip("Ocultar el gráfico (Ver → Gráfico lo muestra de nuevo)")
        close.clicked.connect(self.closed.emit)
        top.addWidget(close)
        v.addLayout(top)
        self.plot = Plot(self)
        v.addWidget(self.plot, 1)
        self.mbox.currentIndexChanged.connect(self._view_changed)
        self.tbox.currentIndexChanged.connect(lambda _i: self._pref_changed("graph_time", self.tbox))
        self.vbox.currentIndexChanged.connect(lambda _i: self._pref_changed("graph_volts", self.vbox))
        self.abox.currentIndexChanged.connect(lambda _i: self._pref_changed("graph_amps", self.abox))
        self._load_prefs()
        self._sync_selectors()

    # ------------------------------------------------------------------ preferencias
    def _save(self, key, value):
        if self.settings is not None:
            self.settings.setValue(key, value)

    def _index(self, key):
        try:
            return int(self.settings.value(key, 0))
        except (TypeError, ValueError):
            return 0

    def _load_prefs(self):
        if self.settings is None:
            return
        view = self.settings.value("graph_view", "separated")
        self.mode = "overlaid" if view == "overlaid" else "separated"
        boxes = ((self.mbox, 1 if self.mode == "overlaid" else 0),
                 (self.tbox, self._index("graph_time")),
                 (self.vbox, self._index("graph_volts")),
                 (self.abox, self._index("graph_amps")))
        for box, i in boxes:
            if 0 <= i < box.count():
                box.blockSignals(True)
                box.setCurrentIndex(i)
                box.blockSignals(False)

    def _view_changed(self, i):
        self.mode = "overlaid" if i == 1 else "separated"
        self._save("graph_view", self.mode)
        self.plot.update()

    def _pref_changed(self, key, box):
        self._save(key, box.currentIndex())
        self.plot.update()

    # ------------------------------------------------------------------ datos
    def clear(self):
        self.traces = {}
        self.t_now = 0.0
        self.pan = 0.0
        self.chips.setText(HINT)
        self._sync_selectors()
        self.plot.update()

    def set_follow(self, on: bool):
        """Con la simulación en marcha el gráfico sigue el trazo en vivo; en pausa se puede arrastrar."""
        self.following = bool(on)
        if self.following:
            self.pan = 0.0          # al reanudar vuelve a donde estaba para seguir dibujando
        self.plot.refresh_cursor()
        self.plot.update()

    def can_pan(self):
        """Se puede mover a mano solo cuando no está dibujando en vivo y hay algo para mirar."""
        return not self.following and self.has_data()

    def _max_pan(self, span=None):
        """Cuánto se puede retroceder: hasta el inicio de la simulación (el borde izquierdo llega a 0)."""
        span = span if span is not None else self.timebase() * DIVS_X
        return max(0.0, max(self.t_now, span) - span)

    def pan_by(self, dx, width):
        """Mueve la vista dx píxeles: a la derecha se ven tiempos anteriores, a la izquierda, posteriores."""
        if not self.can_pan() or width <= 0:
            return
        span = self.timebase() * DIVS_X
        self.pan = min(max(0.0, self.pan + dx / width * span), self._max_pan(span))
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

    # ------------------------------------------------------------------ escalas
    @staticmethod
    def _unit(ch):
        """I1–I4 son corrientes; A–D, voltajes."""
        return "A" if ch.startswith("I") else "V"

    def _chans(self, unit):
        return [ch for ch in sorted(self.traces) if self._unit(ch) == unit]

    def plot_mode(self):
        """single (un solo tipo de sonda), separated (dos ventanas) u overlaid (dos ejes en una)."""
        if self._chans("V") and self._chans("A"):
            return "overlaid" if self.mode == "overlaid" else "separated"
        return "single"

    def timebase(self):
        tdiv = TIMEBASES[self.tbox.currentIndex()][1]
        if tdiv is not None:
            return tdiv
        # auto: aproximadamente tres ciclos de la señal repetitiva más rápida en cualquier sonda, si no 0,5 s por cuadro.
        # (Mirar todas las sondas importa: en un convertidor buck la sonda A es DC suave y solo B se repite.)
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

    def _range(self, chans, div, t0, t1, floor):
        lo, hi = 0.0, 0.0
        for ch in chans:
            _ts, vs = self.traces[ch].window(t0, t1)
            if vs:
                lo, hi = min(lo, min(vs)), max(hi, max(vs))
        if div is not None:
            mid = 0.0 if lo >= 0 else (lo + hi) / 2
            base = 0.0 if lo >= 0 else mid - div * DIVS_Y / 2
            return base, base + div * DIVS_Y
        span = max(hi - lo, floor)
        step = min([n for n in NICE + [10.0, 20.0, 50.0] if n * DIVS_Y >= span * 1.1] or [100.0])
        base = 0.0 if lo >= 0 else step * round(lo / step - 0.5)
        if base + step * DIVS_Y < hi:
            base = hi - step * DIVS_Y
        return base, base + step * DIVS_Y

    def volt_range(self, t0, t1):
        return self._range(self._chans("V"), VOLTS[self.vbox.currentIndex()][1], t0, t1, 1.0)

    def amp_range(self, t0, t1):
        return self._range(self._chans("A"), AMPS[self.abox.currentIndex()][1], t0, t1, 1e-6)

    def _sync_selectors(self):
        has_v, has_a = bool(self._chans("V")), bool(self._chans("A"))
        self.vbox.setEnabled(has_v or not self.traces)
        self.abox.setEnabled(has_a or not self.traces)

    def _update_chips(self):
        self._sync_selectors()
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
            floor = 1e-6 if self._unit(ch) == "A" else 1e-3
            now = tr.v[-1] if abs(tr.v[-1]) >= floor else 0.0
            bits.append(f"<span style='color:{col}; font-weight:700'>■ {ch}</span> "
                        f"<span style='color:{theme.TEXT}'>{fmt(now, self._unit(ch))}{extra}</span>")
        self.chips.setText("&nbsp;&nbsp;&nbsp;".join(bits))

    # ------------------------------------------------------------------ dibujo
    def paint_plot(self, p: QPainter, rect: QRectF, mouse):
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.setBrush(QColor(theme.CANVAS))
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 6, 6)
        f = QFont()
        f.setPixelSize(10)
        p.setFont(f)
        tdiv = self.timebase()
        span = tdiv * DIVS_X
        self.pan = min(max(0.0, self.pan), self._max_pan(span))
        t1 = max(self.t_now, span) - self.pan
        t0 = t1 - span
        if not self.traces:
            area = rect.adjusted(48, 10, -12, -22)
            self._grid(p, rect, area, t0, t1)
            p.setPen(QColor(theme.TEXT_MUTED))
            p.drawText(area, Qt.AlignCenter, "Aún no hay señales — coloque una sonda de tensión o de corriente "
                                             "en un cable y presione Ejecutar.")
            return
        volts, amps = self._chans("V"), self._chans("A")
        mode = self.plot_mode()
        if mode == "separated":
            h = (rect.height() - 10 - 22 - 16) / 2
            top = QRectF(rect.left() + 48, rect.top() + 10, rect.width() - 60, h)
            bot = QRectF(top.left(), top.bottom() + 16, top.width(), h)
            v0, v1 = self.volt_range(t0, t1)
            a0, a1 = self.amp_range(t0, t1)
            self._grid(p, rect, top, t0, t1, v0, v1, "V")
            self._grid(p, rect, bot, t0, t1, a0, a1, "A", show_time=True)
            self._traces(p, top, volts, t0, t1, v0, v1)
            self._traces(p, bot, amps, t0, t1, a0, a1)
            areas = [top, bot]
        elif mode == "overlaid":
            area = rect.adjusted(48, 10, -48, -22)
            v0, v1 = self.volt_range(t0, t1)
            a0, a1 = self.amp_range(t0, t1)
            self._grid(p, rect, area, t0, t1, v0, v1, "V", right=(a0, a1, "A"), show_time=True)
            self._traces(p, area, volts, t0, t1, v0, v1)
            self._traces(p, area, amps, t0, t1, a0, a1)
            areas = [area]
        else:
            area = rect.adjusted(48, 10, -12, -22)
            chans, unit = (volts, "V") if volts else (amps, "A")
            lo, hi = self.volt_range(t0, t1) if volts else self.amp_range(t0, t1)
            self._grid(p, rect, area, t0, t1, lo, hi, unit, show_time=True)
            self._traces(p, area, chans, t0, t1, lo, hi)
            areas = [area]
        self._hover(p, areas, t0, t1, mouse)

    def _grid(self, p, rect, area, t0, t1, lo=None, hi=None, unit="V", right=None, show_time=False):
        grid = QColor(theme.GRID_DOT)
        for i in range(DIVS_X + 1):
            x = area.left() + area.width() * i / DIVS_X
            p.setPen(QPen(grid, 1, Qt.SolidLine if i in (0, DIVS_X) else Qt.DotLine))
            p.drawLine(QPointF(x, area.top()), QPointF(x, area.bottom()))
        for j in range(DIVS_Y + 1):
            y = area.bottom() - area.height() * j / DIVS_Y
            p.setPen(QPen(grid, 1, Qt.SolidLine if j in (0, DIVS_Y) else Qt.DotLine))
            p.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
            if lo is None or j % 2:
                continue
            p.setPen(QColor(theme.TEXT_MUTED))
            p.drawText(QRectF(rect.left() + 2, y - 7, 42, 14), Qt.AlignRight | Qt.AlignVCenter,
                       fmt(lo + (hi - lo) * j / DIVS_Y, unit))
            if right is not None:            # segundo eje: corriente a la derecha
                rlo, rhi, runit = right
                p.drawText(QRectF(area.right() + 4, y - 7, 42, 14), Qt.AlignLeft | Qt.AlignVCenter,
                           fmt(rlo + (rhi - rlo) * j / DIVS_Y, runit))
        if show_time:
            p.setPen(QColor(theme.TEXT_MUTED))
            p.drawText(QRectF(area.left(), area.bottom() + 4, area.width() / 2, 14), Qt.AlignLeft,
                       f"{fmt(t0, 's')}")
            p.drawText(QRectF(area.center().x(), area.bottom() + 4, area.width() / 2, 14), Qt.AlignRight,
                       f"{fmt(t1, 's')}   ({fmt(self.timebase(), 's')} por cuadro)")

    @staticmethod
    def _y(area, lo, hi, val):
        return area.bottom() - (val - lo) / (hi - lo) * area.height()

    def _traces(self, p, area, chans, t0, t1, lo, hi):
        if not chans or hi <= lo:
            return
        p.save()
        p.setClipRect(area.adjusted(-1, -2, 1, 2))
        p.setBrush(Qt.NoBrush)          # solo contorno: un trazo relleno ocultaría la cuadrícula y los demás trazos
        cols = max(1, int(area.width()))
        for ch in chans:
            ts, vs = self.traces[ch].window(t0, t1)
            if len(ts) < 2:
                continue
            pen = QPen(QColor(CHANNEL_RGB.get(ch, "#e0a800")), 2.0)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            pts = []
            if len(ts) > cols:
                # más puntos que píxeles de ancho: dibujar cada columna de píxeles como su mín/máx (se ve igual)
                bucket = {}
                for t, val in zip(ts, vs):
                    c = int((t - t0) / (t1 - t0) * cols)
                    lo_hi = bucket.get(c)
                    bucket[c] = (min(lo_hi[0], val), max(lo_hi[1], val), val) if lo_hi else (val, val, val)
                for c in sorted(bucket):
                    blo, bhi, last = bucket[c]
                    x = area.left() + c
                    pts += [(x, self._y(area, lo, hi, blo)), (x, self._y(area, lo, hi, bhi)),
                            (x, self._y(area, lo, hi, last))]
            else:
                sx = area.width() / (t1 - t0)
                sy = -area.height() / (hi - lo)
                ax, ay = area.left() - t0 * sx, area.bottom() - lo * sy
                pts = [(ax + t * sx, ay + val * sy) for t, val in zip(ts, vs)]
            # omitir puntos en medio de un tramo nivelado (una onda cuadrada es casi toda plana): misma imagen,
            # mucho menos que dibujar
            line = []
            for x, y in pts:
                if len(line) >= 2 and abs(line[-1][1] - y) < 0.25 and abs(line[-2][1] - y) < 0.25:
                    line[-1] = (x, y)
                else:
                    line.append((x, y))
            p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in line]))
        p.restore()

    def _hover(self, p, areas, t0, t1, mouse):
        if mouse is None:
            return
        area = next((a for a in areas if a.contains(mouse)), None)
        if area is None:
            return
        t = t0 + (mouse.x() - area.left()) / area.width() * (t1 - t0)
        p.setPen(QPen(QColor(theme.TEXT_MUTED), 1, Qt.DashLine))
        for a in areas:
            p.drawLine(QPointF(mouse.x(), a.top()), QPointF(mouse.x(), a.bottom()))
        lines = [f"t = {fmt(t, 's')}"]
        for ch in sorted(self.traces):
            tr = self.traces[ch]
            i = bisect.bisect_left(tr.t, t)
            if 0 < i < len(tr.t):
                lines.append(f"{ch}: {fmt(tr.v[i], self._unit(ch))}")
        box = QRectF(mouse.x() + 8, area.top() + 6, 104, 14 * len(lines) + 8)
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
        path, _ = QFileDialog.getSaveFileName(self, "Guardar gráfico", "grafico.png", "Imagen PNG (*.png)")
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            self.plot.grab().save(path, "PNG")
