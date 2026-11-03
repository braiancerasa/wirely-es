"""El panel del gráfico (osciloscopio): representa el voltaje o la corriente de cada sonda frente al tiempo
mientras el circuito se ejecuta."""
from __future__ import annotations

import bisect
import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy,
                               QToolButton, QVBoxLayout, QWidget)

from ..model.units import fmt
from ..sim.audio import frequency
from . import theme
from .symbols import CHANNEL_RGB

# La escala se escribe con un número y se elige solamente la unidad; el valor se guarda en unidades base
# (segundos, voltios, amperes) para que cambiar de unidad no altere lo que se ve.
TIME_UNITS = [("s", 1.0), ("ms", 1e-3), ("µs", 1e-6)]
VOLT_UNITS = [("V", 1.0), ("mV", 1e-3)]
AMP_UNITS = [("A", 1.0), ("mA", 1e-3), ("µA", 1e-6)]
VIEWS = [("Separados", "separated"), ("Superpuestos", "overlaid")]
# Escalas fijas de versiones anteriores: solo se usan para migrar las preferencias guardadas.
TIMEBASES = [("Auto", None), ("100 µs/div", 1e-4), ("1 ms/div", 1e-3), ("10 ms/div", 1e-2),
             ("100 ms/div", 0.1), ("0.5 s/div", 0.5), ("1 s/div", 1.0), ("5 s/div", 5.0)]
VOLTS = [("Auto", None), ("0.5 V/div", 0.5), ("1 V/div", 1.0), ("2 V/div", 2.0), ("5 V/div", 5.0)]
AMPS = [("Auto", None), ("1 mA/div", 1e-3), ("10 mA/div", 1e-2), ("100 mA/div", 0.1), ("1 A/div", 1.0)]
NICE = [1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 5e-2, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
MAX_POINTS = 400_000
DIVS_X, DIVS_Y = 10, 8
HINT = ("Coloque una sonda de tensión o de corriente (Medidores y sondas) en un cable, "
        "luego presione Ejecutar.")
MIN_VOLT_DIV, MAX_VOLT_DIV = 1e-6, 1e6
MIN_AMP_DIV, MAX_AMP_DIV = 1e-9, 1e3


def _factor(units, unit):
    """Cuántas unidades base hay en una unidad de la lista."""
    for name, factor in units:
        if name == unit:
            return factor
    return units[0][1]


def _valid_unit(units, unit, default):
    return unit if any(name == unit for name, _f in units) else default


def _parse_div(text, factor):
    """Número escrito por el usuario -> valor por división en unidades base. Vacío o «Auto» -> None."""
    text = str(text or "").strip().replace(",", ".")
    if not text or text.lower() == "auto":
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return value * factor


def _fmt_div(value, factor):
    if value is None:
        return ""
    return f"{value / factor:.8g}"


def _best_unit(value, units, default):
    """La unidad que deja un número cómodo (sin ceros de más) para el valor guardado."""
    if value is None:
        return default
    for name, factor in units:
        if abs(value / factor) >= 1.0:
            return name
    return units[-1][0]


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
        self.setToolTip("Rueda: acerca o aleja el voltaje y la corriente. Arrastre el gráfico para moverse por "
                        "el tiempo en pausa; arrastre una regla lateral para correr el cero.")
        self._mouse = None
        self._drag = None       # x del último movimiento mientras se arrastra para mover el gráfico
        self._zero = None       # (unidad, último y, alto del área) mientras se arrastra una regla lateral

    def refresh_cursor(self):
        if self._zero is not None:
            self.setCursor(Qt.SizeVerCursor)
        elif self._drag is not None:
            self.setCursor(Qt.ClosedHandCursor)
        elif self.panel.can_pan():
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.unsetCursor()

    def leaveEvent(self, e):
        self._mouse = None
        self.refresh_cursor()
        self.update()

    def _ruler(self, pos):
        axis, height = self.panel.axis_at(pos.x(), pos.y(), self.width(), self.height())
        return axis, height

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            axis, height = self._ruler(e.position())
            if axis is not None:
                self._zero = (axis, e.position().y(), height)
                self._mouse = None
                self.refresh_cursor()
                e.accept()
                return
            if self.panel.can_pan():
                self._drag = e.position().x()
                self._mouse = None
                self.refresh_cursor()
                e.accept()
                return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        pos = e.position()
        if self._zero is not None:
            axis, last_y, height = self._zero
            self.panel.zero_by(axis, pos.y() - last_y, height)
            self._zero = (axis, pos.y(), height)
            self._mouse = None
        elif self._drag is not None:
            dx = pos.x() - self._drag
            self._drag = pos.x()
            self.panel.pan_by(dx, self.width())
            self._mouse = None
        else:
            self._mouse = pos
            axis, _height = self._ruler(pos)
            if axis is not None:
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.refresh_cursor()
        self.update()

    def mouseReleaseEvent(self, e):
        if self._zero is not None and e.button() == Qt.LeftButton:
            self._zero = None
            self.refresh_cursor()
            e.accept()
            return
        if self._drag is not None and e.button() == Qt.LeftButton:
            self._drag = None
            self.refresh_cursor()
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        axis, _height = self._ruler(e.position())
        if axis is not None:
            self._zero = None
            self.panel.reset_zero(axis)
            self.refresh_cursor()
            e.accept()
            return
        super().mouseDoubleClickEvent(e)

    def wheelEvent(self, e):
        dy = e.angleDelta().y()
        if dy:
            self.panel.zoom_vertical(dy / 120.0)
            e.accept()
            return
        super().wheelEvent(e)

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
        self._init_state()
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 6, 10, 8)
        v.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(6)
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
        top.addWidget(QLabel("Vista"))
        top.addWidget(self.mbox)

        # Tiempo, voltaje y corriente: el número se escribe y la unidad se elige. Vacío = Auto.
        top.addWidget(QLabel("Tiempo"))
        self.tval, self.tunit = self._scale_widgets(TIME_UNITS, "Valor por cuadro horizontal. Vacío = Auto")
        top.addWidget(self.tval)
        top.addWidget(self.tunit)
        top.addWidget(QLabel("Voltaje"))
        self.vval, self.vunit = self._scale_widgets(VOLT_UNITS, "Voltaje por cuadro vertical. Vacío = Auto")
        top.addWidget(self.vval)
        top.addWidget(self.vunit)
        top.addWidget(QLabel("Corriente"))
        self.aval, self.aunit = self._scale_widgets(AMP_UNITS, "Corriente por cuadro vertical. Vacío = Auto")
        top.addWidget(self.aval)
        top.addWidget(self.aunit)

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
        self.tval.editingFinished.connect(self._time_edited)
        self.vval.editingFinished.connect(self._volt_edited)
        self.aval.editingFinished.connect(self._amp_edited)
        self.tunit.currentIndexChanged.connect(lambda _i: self._unit_changed("time"))
        self.vunit.currentIndexChanged.connect(lambda _i: self._unit_changed("volts"))
        self.aunit.currentIndexChanged.connect(lambda _i: self._unit_changed("amps"))
        self._load_prefs()
        self._refresh_scale_fields()
        self._sync_selectors()

    def _init_state(self):
        """Estado del gráfico sin construir los controles (la versión web usa esta parte sola)."""
        self.traces: dict[str, Trace] = {}
        self.t_now = 0.0
        self.pan = 0.0              # segundos que la vista está corrida hacia atrás (solo en pausa)
        self.following = True       # mientras ejecuta, el gráfico sigue el trazo en vivo
        self.vmax_hint = 9.0
        self.mode = "separated"
        self.time_div = None        # segundos por división; None = Auto
        self.time_unit = "ms"
        self.volt_div = None        # voltios por división; None = Auto
        self.volt_unit = "V"
        self.amp_div = None         # amperes por división; None = Auto
        self.amp_unit = "mA"
        self.v_offset = 0.0         # desplazamiento del cero, en divisiones (positivo = hacia arriba)
        self.a_offset = 0.0

    @staticmethod
    def _scale_widgets(units, tip):
        edit = QLineEdit()
        edit.setPlaceholderText("Auto")
        edit.setFixedWidth(58)
        edit.setToolTip(tip)
        box = QComboBox()
        for name, _factor in units:
            box.addItem(name)
        box.setMinimumWidth(54)
        return edit, box

    # ------------------------------------------------------------------ preferencias
    def _save(self, key, value):
        if self.settings is not None:
            self.settings.setValue(key, value)

    def _index(self, key):
        try:
            return int(self.settings.value(key, 0))
        except (TypeError, ValueError):
            return 0

    def _saved_div(self, key, legacy_key, legacy_list):
        """Escala nueva guardada o, si viene de una versión anterior, su índice fijo."""
        if self.settings is None:
            return None
        if self.settings.contains(key):
            value = self.settings.value(key, "")
            if value is None or value == "" or value == str(None):
                return None
            try:
                value = float(value)
            except (TypeError, ValueError):
                return None
            return value if value > 0 else None
        index = self._index(legacy_key)
        if 0 < index < len(legacy_list):
            return legacy_list[index][1]
        return None

    def _saved_unit(self, key, default, units, div):
        if self.settings is None:
            return _best_unit(div, units, default)
        return _valid_unit(units, str(self.settings.value(key, default)), default)

    def _load_prefs(self):
        if self.settings is None:
            return
        view = self.settings.value("graph_view", "separated")
        self.mode = "overlaid" if view == "overlaid" else "separated"
        self.time_div = self._saved_div("graph_time_div", "graph_time", TIMEBASES)
        self.volt_div = self._saved_div("graph_volt_div", "graph_volts", VOLTS)
        self.amp_div = self._saved_div("graph_amp_div", "graph_amps", AMPS)
        self.time_unit = self._saved_unit("graph_time_unit", _best_unit(self.time_div, TIME_UNITS, "ms"),
                                          TIME_UNITS, self.time_div)
        self.volt_unit = self._saved_unit("graph_volt_unit", _best_unit(self.volt_div, VOLT_UNITS, "V"),
                                          VOLT_UNITS, self.volt_div)
        self.amp_unit = self._saved_unit("graph_amp_unit", _best_unit(self.amp_div, AMP_UNITS, "mA"),
                                         AMP_UNITS, self.amp_div)
        self.v_offset = self._saved_offset("graph_v_offset")
        self.a_offset = self._saved_offset("graph_a_offset")
        self.mbox.blockSignals(True)
        self.mbox.setCurrentIndex(1 if self.mode == "overlaid" else 0)
        self.mbox.blockSignals(False)
        self._refresh_scale_fields()

    def _saved_offset(self, key):
        try:
            value = float(self.settings.value(key, 0.0))
        except (TypeError, ValueError):
            return 0.0
        return self._clamp_offset(value)

    def _view_changed(self, i):
        self.mode = "overlaid" if i == 1 else "separated"
        self._save("graph_view", self.mode)
        self.plot.update()

    def _save_scale(self, kind):
        names = {"time": ("graph_time_div", "graph_time_unit", "time_div", "time_unit"),
                 "volts": ("graph_volt_div", "graph_volt_unit", "volt_div", "volt_unit"),
                 "amps": ("graph_amp_div", "graph_amp_unit", "amp_div", "amp_unit")}
        div_key, unit_key, div_attr, unit_attr = names[kind]
        div = getattr(self, div_attr)
        self._save(div_key, "" if div is None else div)
        self._save(unit_key, getattr(self, unit_attr))

    def _refresh_scale_fields(self):
        """Lleva el estado interno a los cuadros de texto y a los desplegables de unidad."""
        if "tval" not in self.__dict__:
            return
        for edit, box, div, unit, units in (
                (self.tval, self.tunit, self.time_div, self.time_unit, TIME_UNITS),
                (self.vval, self.vunit, self.volt_div, self.volt_unit, VOLT_UNITS),
                (self.aval, self.aunit, self.amp_div, self.amp_unit, AMP_UNITS)):
            edit.blockSignals(True)
            edit.setText(_fmt_div(div, _factor(units, unit)))
            edit.blockSignals(False)
            box.blockSignals(True)
            index = box.findText(unit)
            if index >= 0:
                box.setCurrentIndex(index)
            box.blockSignals(False)

    def _read_scale(self, edit, box, units, default):
        unit = _valid_unit(units, box.currentText(), default)
        return _parse_div(edit.text(), _factor(units, unit)), unit

    def _apply_scale_edit(self, kind, edit, box, units, default, div_attr, unit_attr):
        old_div, old_unit = getattr(self, div_attr), getattr(self, unit_attr)
        div, unit = self._read_scale(edit, box, units, default)
        if edit.text().strip() and div is None:      # un número inválido no debe borrar la escala buena
            div, unit = old_div, old_unit
        setattr(self, unit_attr, unit)
        setattr(self, div_attr, div)
        edit.setText(_fmt_div(div, _factor(units, unit)))
        self._save_scale(kind)
        self.plot.update()

    def _time_edited(self):
        self._apply_scale_edit("time", self.tval, self.tunit, TIME_UNITS, "ms", "time_div", "time_unit")

    def _volt_edited(self):
        self._apply_scale_edit("volts", self.vval, self.vunit, VOLT_UNITS, "V", "volt_div", "volt_unit")

    def _amp_edited(self):
        self._apply_scale_edit("amps", self.aval, self.aunit, AMP_UNITS, "mA", "amp_div", "amp_unit")

    def _unit_changed(self, kind):
        """Cambiar la unidad conserva la escala física y solo reescribe el número."""
        state = {"time": (self.tval, self.tunit, TIME_UNITS, "ms", "time_div", "time_unit"),
                 "volts": (self.vval, self.vunit, VOLT_UNITS, "V", "volt_div", "volt_unit"),
                 "amps": (self.aval, self.aunit, AMP_UNITS, "mA", "amp_div", "amp_unit")}[kind]
        edit, box, units, default, div_attr, unit_attr = state
        old_unit = getattr(self, unit_attr)
        technical = _parse_div(edit.text(), _factor(units, old_unit))
        if technical is None:
            technical = getattr(self, div_attr)
        unit = _valid_unit(units, box.currentText(), default)
        setattr(self, unit_attr, unit)
        edit.setText(_fmt_div(technical, _factor(units, unit)))
        self._save_scale(kind)
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
        if self.time_div is not None:
            return self.time_div
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

    def _data_bounds(self, chans, t0, t1):
        lo, hi = 0.0, 0.0
        for ch in chans:
            _ts, vs = self.traces[ch].window(t0, t1)
            if vs:
                lo, hi = min(lo, min(vs)), max(hi, max(vs))
        return lo, hi

    def _auto_div(self, chans, t0, t1, floor):
        """Valor por división que deja el cero al medio y toda la señal a la vista."""
        lo, hi = self._data_bounds(chans, t0, t1)
        span = max(2.0 * max(abs(lo), abs(hi)), floor)
        return min([n for n in NICE + [10.0, 20.0, 50.0] if n * DIVS_Y >= span * 1.1] or [100.0])

    def _range(self, chans, div, t0, t1, floor, offset):
        if div is None:
            div = self._auto_div(chans, t0, t1, floor)
        # El cero queda al medio salvo que se haya corrido la regla, en divisiones.
        center = -offset * div
        half = div * DIVS_Y / 2
        return center - half, center + half

    def volt_range(self, t0, t1):
        return self._range(self._chans("V"), self.volt_div, t0, t1, 1.0, self.v_offset)

    def amp_range(self, t0, t1):
        return self._range(self._chans("A"), self.amp_div, t0, t1, 1e-6, self.a_offset)

    def _sync_selectors(self):
        has_v, has_a = bool(self._chans("V")), bool(self._chans("A"))
        if "vval" in self.__dict__:
            for widget in (self.vval, self.vunit):
                widget.setEnabled(has_v or not self.traces)
            for widget in (self.aval, self.aunit):
                widget.setEnabled(has_a or not self.traces)

    # ------------------------------------------------------------------ zoom y cero manual
    def _window_times(self):
        span = self.timebase() * DIVS_X
        self.pan = min(max(0.0, self.pan), self._max_pan(span))
        t1 = max(self.t_now, span) - self.pan
        return t1 - span, t1

    @staticmethod
    def _clamp_div(div, lo, hi):
        return max(lo, min(hi, div))

    def _clamp_offset(self, offset):
        # el cero puede llegar a un borde, pero no salir de la pantalla
        return max(-DIVS_Y / 2, min(DIVS_Y / 2, offset))

    def zoom_vertical(self, steps):
        """Rueda del mouse: cambia el rango de voltaje y de corriente a la vez, sin tocar el tiempo.

        Un paso hacia arriba acerca (menos unidades por división); hacia abajo aleja. Si la escala estaba en
        Auto, se fija en el valor que se estaba viendo para que el cambio sea continuo."""
        if not self.has_data():
            return
        t0, t1 = self._window_times()
        factor = 1.25 ** (-steps)
        if self._chans("V") or self.volt_div is not None:
            div = self.volt_div if self.volt_div is not None else self._auto_div(self._chans("V"), t0, t1, 1.0)
            self.volt_div = self._clamp_div(div * factor, MIN_VOLT_DIV, MAX_VOLT_DIV)
            self._save_scale("volts")
        if self._chans("A") or self.amp_div is not None:
            div = self.amp_div if self.amp_div is not None else self._auto_div(self._chans("A"), t0, t1, 1e-6)
            self.amp_div = self._clamp_div(div * factor, MIN_AMP_DIV, MAX_AMP_DIV)
            self._save_scale("amps")
        self._refresh_scale_fields()
        self.plot.update()

    def zero_by(self, unit, dy, height):
        """Arrastre de la regla lateral: corre el cero de ese eje, independiente del otro."""
        if height <= 0:
            return
        step = -dy / height * DIVS_Y
        if unit == "A":
            self.a_offset = self._clamp_offset(self.a_offset + step)
            self._save("graph_a_offset", self.a_offset)
        else:
            self.v_offset = self._clamp_offset(self.v_offset + step)
            self._save("graph_v_offset", self.v_offset)
        self.plot.update()

    def reset_zero(self, unit=None):
        if unit in (None, "V"):
            self.v_offset = 0.0
            self._save("graph_v_offset", 0.0)
        if unit in (None, "A"):
            self.a_offset = 0.0
            self._save("graph_a_offset", 0.0)
        self.plot.update()

    def _layout_areas(self, rect):
        """Mismas áreas de dibujo que usa paint_plot; también sirve para saber qué regla se arrastra."""
        volts, amps = self._chans("V"), self._chans("A")
        mode = self.plot_mode()
        if mode == "separated":
            h = (rect.height() - 10 - 22 - 16) / 2
            top = QRectF(rect.left() + 48, rect.top() + 10, rect.width() - 60, h)
            bot = QRectF(top.left(), top.bottom() + 16, top.width(), h)
            return {"mode": mode, "areas": [top, bot], "v": top, "a": bot,
                    "v_unit": "V", "a_unit": "A"}
        if mode == "overlaid":
            area = rect.adjusted(48, 10, -48, -22)
            return {"mode": mode, "areas": [area], "v": area, "a": area,
                    "v_unit": "V", "a_unit": "A"}
        area = rect.adjusted(48, 10, -12, -22)
        unit = "V" if volts else "A"
        return {"mode": mode, "areas": [area], "v": area if unit == "V" else None,
                "a": area if unit == "A" else None, "v_unit": unit, "a_unit": unit}

    def axis_at(self, x, y, width, height):
        """Devuelve (unidad, alto del área) si el punto está sobre una regla lateral; None si no."""
        lay = self._layout_areas(QRectF(0, 0, width, height))
        for key in ("v", "a"):
            area = lay.get(key)
            if area is None or not (area.top() <= y <= area.bottom()):
                continue
            left_rule = x < area.left()
            right_rule = lay["mode"] == "overlaid" and x > area.right()
            if left_rule or right_rule:
                return lay[key + "_unit"], area.height()
        return None, 0.0

    def scale_config(self):
        """Valores y unidades tal como van en los cuadros de texto (para la web y las pruebas)."""
        return {"time": _fmt_div(self.time_div, _factor(TIME_UNITS, self.time_unit)),
                "time_unit": self.time_unit,
                "volts": _fmt_div(self.volt_div, _factor(VOLT_UNITS, self.volt_unit)),
                "volt_unit": self.volt_unit,
                "amps": _fmt_div(self.amp_div, _factor(AMP_UNITS, self.amp_unit)),
                "amp_unit": self.amp_unit,
                "v_offset": self.v_offset, "a_offset": self.a_offset,
                "view": self.mode}

    def set_scales(self, time_text, time_unit, volt_text, volt_unit, amp_text, amp_unit):
        """Configura las escalas desde la web: texto vacío = Auto."""
        self.time_unit = _valid_unit(TIME_UNITS, time_unit, "ms")
        self.volt_unit = _valid_unit(VOLT_UNITS, volt_unit, "V")
        self.amp_unit = _valid_unit(AMP_UNITS, amp_unit, "mA")
        self.time_div = _parse_div(time_text, _factor(TIME_UNITS, self.time_unit))
        self.volt_div = _parse_div(volt_text, _factor(VOLT_UNITS, self.volt_unit))
        self.amp_div = _parse_div(amp_text, _factor(AMP_UNITS, self.amp_unit))

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
        t0, t1 = self._window_times()
        if not self.traces:
            area = rect.adjusted(48, 10, -12, -22)
            self._grid(p, rect, area, t0, t1)
            p.setPen(QColor(theme.TEXT_MUTED))
            p.drawText(area, Qt.AlignCenter, "Aún no hay señales — coloque una sonda de tensión o de corriente "
                                             "en un cable y presione Ejecutar.")
            return
        volts, amps = self._chans("V"), self._chans("A")
        lay = self._layout_areas(rect)
        if lay["mode"] == "separated":
            top, bot = lay["v"], lay["a"]
            v0, v1 = self.volt_range(t0, t1)
            a0, a1 = self.amp_range(t0, t1)
            self._grid(p, rect, top, t0, t1, v0, v1, "V")
            self._grid(p, rect, bot, t0, t1, a0, a1, "A", show_time=True)
            self._traces(p, top, volts, t0, t1, v0, v1)
            self._traces(p, bot, amps, t0, t1, a0, a1)
        elif lay["mode"] == "overlaid":
            area = lay["v"]
            v0, v1 = self.volt_range(t0, t1)
            a0, a1 = self.amp_range(t0, t1)
            self._grid(p, rect, area, t0, t1, v0, v1, "V", right=(a0, a1, "A"), show_time=True)
            self._traces(p, area, volts, t0, t1, v0, v1)
            self._traces(p, area, amps, t0, t1, a0, a1)
        else:
            area = lay["areas"][0]
            chans, unit = (volts, "V") if volts else (amps, "A")
            lo, hi = self.volt_range(t0, t1) if volts else self.amp_range(t0, t1)
            self._grid(p, rect, area, t0, t1, lo, hi, unit, show_time=True)
            self._traces(p, area, chans, t0, t1, lo, hi)
        self._hover(p, lay["areas"], t0, t1, mouse)

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
        if lo is not None and hi is not None and hi > lo and lo <= 0.0 <= hi:
            # el cero siempre visible, aunque la regla se haya corrido: línea más marcada y su número
            y = area.bottom() - (0.0 - lo) / (hi - lo) * area.height()
            p.setPen(QPen(QColor(theme.TEXT_MUTED), 1, Qt.SolidLine))
            p.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
            near_label = any(j % 2 == 0 and abs(lo + (hi - lo) * j / DIVS_Y) < (hi - lo) / DIVS_Y * 0.02
                             for j in range(DIVS_Y + 1))
            if not near_label:
                p.setPen(QColor(theme.TEXT_MUTED))
                p.drawText(QRectF(rect.left() + 2, y - 7, 42, 14), Qt.AlignRight | Qt.AlignVCenter, "0")
        if right is not None:
            rlo, rhi, runit = right
            if rhi > rlo and rlo <= 0.0 <= rhi:
                y = area.bottom() - (0.0 - rlo) / (rhi - rlo) * area.height()
                p.setPen(QPen(QColor(theme.TEXT_MUTED), 1, Qt.SolidLine))
                p.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
                near_label = any(j % 2 == 0 and abs(rlo + (rhi - rlo) * j / DIVS_Y) < (rhi - rlo) / DIVS_Y * 0.02
                                 for j in range(DIVS_Y + 1))
                if not near_label:
                    p.setPen(QColor(theme.TEXT_MUTED))
                    p.drawText(QRectF(area.right() + 4, y - 7, 42, 14), Qt.AlignLeft | Qt.AlignVCenter, "0")
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
