"""Sonda de corriente: mide el cable que tiene debajo (solo lectura, sin tocar el circuito), se reconecta cuando
se mueve el cable, y sus muestras llegan al gráfico con la unidad correcta y los dos modos de vista."""
import math
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402
from PySide6.QtCore import QRectF  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402

from test_editor import app, win  # noqa: E402,F401
from test_sim import build  # noqa: E402

from wirely.model.circuit import Circuit, on_segment  # noqa: E402
from wirely.sim.engine import Simulator  # noqa: E402


def series(volts=9.0, ohms=1000.0):
    """9 V sobre 1 kΩ: 9 mA por todos los cables."""
    return build([("cell", ("p", "0"), {"voltage": volts}),
                  ("resistor", ("p", "0"), {"resistance": ohms})])


def wire_of(circuit, comp, pin="1"):
    pos = comp.pin_positions()[pin]
    return next(w for w in circuit.wires.values()
                if any(on_segment(pos, a, b) for a, b in w.segments()))


def a_point_on(wire, offset=10):
    """Un punto de la cuadrícula sobre el primer tramo del cable."""
    a, b = wire.segments()[0]
    dx = (b[0] > a[0]) - (b[0] < a[0])
    dy = (b[1] > a[1]) - (b[1] < a[1])
    return a[0] + dx * offset, a[1] + dy * offset


def test_probe_measures_the_current_of_the_wire_under_it():
    c, (_cell, res) = series()
    w = wire_of(c, res)
    c.add("current_probe", *a_point_on(w))
    sim = Simulator(c)
    assert "I1" in sim.current_probes
    sim.recording = True
    sim.run_until(1e-3)
    last = sim.record[-1][1]
    assert "I1" in last
    assert abs(last["I1"]) == pytest.approx(abs(sim.device(res.id).i_pins[0]), rel=1e-6)
    assert abs(last["I1"]) == pytest.approx(9e-3, rel=0.01)


def test_the_probe_does_not_change_the_circuit():
    c1, (_c1, r1) = series()
    w = wire_of(c1, r1)
    c1.add("current_probe", *a_point_on(w))
    c2, (_c2, r2) = series()

    a, b = Simulator(c1), Simulator(c2)
    for sim in (a, b):
        sim.recording = True
        sim.run_until(5e-3)
    assert a.device(r1.id).i_pins[0] == pytest.approx(b.device(r2.id).i_pins[0], rel=1e-9)
    assert a.t == pytest.approx(b.t, rel=1e-9)
    assert any("I1" in vals for _t, vals in a.record)          # la sonda sí registra
    assert not any(ch.startswith("I") for _t, vals in b.record for ch in vals)   # y sin ella no hay canal I


def test_a_probe_off_the_wire_records_nothing():
    c, _comps = series()
    c.add("current_probe", 50000, 50000)          # lejos de todo cable
    sim = Simulator(c)
    assert sim.current_probes == {}
    sim.recording = True
    sim.run_until(1e-3)
    assert not any("I1" in vals for _t, vals in sim.record)


def test_moving_the_wire_reconnects_the_probe():
    c, (_cell, res) = series()
    w = wire_of(c, res)
    px, py = w.points[0]
    bx, lane = w.points[-1]
    probe = c.add("current_probe", px - 10, lane + 30)      # todavía no toca el cable

    sim = Simulator(c)
    assert sim.current_probes == {}

    # el cable se desvía y pasa por debajo de la sonda (los extremos quedan donde estaban)
    w.points = [(px, py), (px, lane), (px - 40, lane), (px - 40, lane + 30), (bx, lane + 30), (bx, lane)]
    sim = Simulator(c)
    assert "I1" in sim.current_probes
    sim.recording = True
    sim.run_until(1e-3)
    assert abs(sim.record[-1][1]["I1"]) == pytest.approx(9e-3, rel=0.01)
    assert probe.id in c.components

    # y si el cable se vuelve a mover lejos, deja de medir
    w.points = [(px, py), (px, lane), (bx, lane)]
    sim = Simulator(c)
    assert sim.current_probes == {}


def test_probe_is_saved_and_loaded_with_its_channel():
    c, _comps = series()
    c.add("current_probe", 50000, 50000, props={"channel": "I3"})
    again = Circuit.from_dict(c.to_dict())
    probe = next(x for x in again.components.values() if x.kind == "current_probe")
    assert probe.value("channel") == "I3"
    assert probe.ref.startswith("I")


def test_graph_units_and_the_two_views():
    from PySide6.QtWidgets import QApplication

    from wirely.ui.graph import GraphPanel
    QApplication.instance() or QApplication([])
    g = GraphPanel()
    samples = []
    t = 0.0
    while t < 0.02:
        samples.append((t, {"A": 5.0 + math.sin(2 * math.pi * 100 * t),
                            "I1": 0.010 + 0.001 * math.sin(2 * math.pi * 100 * t)}))
        t += 1e-4
    g.add_samples(samples, t)
    assert g.plot_mode() == "separated"
    assert "V" in g.chips.text() and "mA" in g.chips.text()
    g.mbox.setCurrentIndex(1)                       # Superpuestos
    assert g.mode == "overlaid" and g.plot_mode() == "overlaid"
    for _ in range(2):
        img = QImage(640, 320, QImage.Format_ARGB32)
        p = QPainter(img)
        g.paint_plot(p, QRectF(0, 0, 640, 320), None)
        p.end()
        g.mbox.setCurrentIndex(0)                   # Separados
    # con un solo tipo de sonda, el panel queda como siempre
    g.clear()
    g.add_samples([(0.0, {"A": 1.0}), (0.1, {"A": 2.0})], 0.1)
    assert g.plot_mode() == "single"
    assert g.abox.isEnabled() is False and g.vbox.isEnabled() is True
    g.clear()
    g.add_samples([(0.0, {"I2": 0.001}), (0.1, {"I2": 0.002})], 0.1)
    assert g.plot_mode() == "single" and g.vbox.isEnabled() is False and g.abox.isEnabled() is True


def test_graph_remembers_the_view_and_the_scales(win):
    from wirely.ui.graph import GraphPanel
    g = win.graph
    g.mbox.setCurrentIndex(1)
    g.abox.setCurrentIndex(2)
    g.vbox.setCurrentIndex(3)
    assert win.settings.value("graph_view") == "overlaid"
    assert win.settings.value("graph_amps") == 2
    again = GraphPanel(settings=win.settings)
    assert again.mode == "overlaid"
    assert again.abox.currentIndex() == 2 and again.vbox.currentIndex() == 3


def test_a_current_probe_opens_the_graph(win):
    win.open_file(os.path.join(os.path.dirname(__file__), "..", "examples", "LED y resistencia.wirely"))
    led = next(c for c in win.circuit.components.values() if c.kind == "led")
    w = wire_of(win.circuit, led, "A")
    win.circuit.add("current_probe", *a_point_on(w))
    win.a_play.trigger()
    assert win.graph.isVisible()
    win.a_stop.trigger()
