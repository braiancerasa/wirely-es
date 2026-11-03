"""Escalas del gráfico: zoom vertical con la rueda, cero desplazable arrastrando las reglas laterales y
valores escritos con la unidad elegida (en vez de listas fijas)."""
import math
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402
from PySide6.QtCore import QPoint, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from wirely.ui.graph import DIVS_Y, GraphPanel  # noqa: E402


def make_graph(seconds=0.2):
    QApplication.instance() or QApplication([])
    g = GraphPanel()
    samples = []
    t = 0.0
    while t <= seconds:
        samples.append((t, {"A": 5.0 + math.sin(2 * math.pi * 100 * t),
                            "I1": 0.010 + 0.001 * math.sin(2 * math.pi * 100 * t)}))
        t += 1e-4
    g.add_samples(samples, seconds)
    return g


def spans(g):
    v0, v1 = g.volt_range(0.0, 0.2)
    a0, a1 = g.amp_range(0.0, 0.2)
    return v1 - v0, a1 - a0


def test_wheel_zoom_changes_both_vertical_scales_and_keeps_the_time():
    g = make_graph()
    g.tval.setText("100")
    g.tunit.setCurrentText("ms")
    g._time_edited()
    time_before = g.timebase()
    v_before, a_before = spans(g)
    v0, v1 = g.volt_range(0.0, 0.2)
    assert v0 == pytest.approx(-v1)                     # el cero arranca al medio

    g.zoom_vertical(1)                                  # un paso de rueda hacia arriba: acerca
    v_after, a_after = spans(g)
    assert g.timebase() == time_before                  # la rueda no toca el tiempo
    assert v_after < v_before and a_after < a_before
    assert v_before / v_after == pytest.approx(1.25)
    assert a_before / a_after == pytest.approx(1.25)
    v0, v1 = g.volt_range(0.0, 0.2)
    assert v0 == pytest.approx(-v1)                     # sigue centrado en cero
    assert g.scale_config()["volts"] and g.scale_config()["amps"]


def test_a_written_value_and_its_unit_set_the_scale_and_converting_the_unit_keeps_it():
    g = make_graph()
    g.tval.setText("0.25")
    g.tunit.setCurrentText("ms")
    g._time_edited()
    assert g.timebase() == pytest.approx(250e-6)
    g.tunit.setCurrentText("µs")                        # misma escala física, número convertido
    assert g.tval.text() == "250" and g.timebase() == pytest.approx(250e-6)

    g.vval.setText("10")
    g.vunit.setCurrentText("V")
    g._volt_edited()
    assert g.volt_div == pytest.approx(10.0)
    assert g.volt_range(0.0, 0.2) == pytest.approx((-40.0, 40.0))

    g.vunit.setCurrentText("mV")                        # misma escala física, número convertido
    assert g.volt_div == pytest.approx(10.0)
    assert g.vval.text() == "10000"

    g.vval.clear()                                      # vacío = Auto
    g._volt_edited()
    assert g.volt_div is None


def test_current_scale_accepts_intermediate_values_and_its_units():
    g = make_graph()
    g.aval.setText("2.5")
    g.aunit.setCurrentText("mA")
    g._amp_edited()
    assert g.amp_div == pytest.approx(2.5e-3)
    a0, a1 = g.amp_range(0.0, 0.2)
    assert (a0, a1) == pytest.approx((-0.01, 0.01))
    g.aunit.setCurrentText("µA")
    assert g.aval.text() == "2500" and g.amp_div == pytest.approx(2.5e-3)


def test_dragging_a_side_ruler_moves_only_that_zero():
    g = make_graph()
    g.set_follow(False)
    g.plot.resize(640, 320)
    axis, height = g.axis_at(10, 100, 640, 320)
    assert axis == "V" and height > 0
    QTest.mousePress(g.plot, Qt.LeftButton, pos=QPoint(10, 100))
    QTest.mouseMove(g.plot, QPoint(10, 80))
    QTest.mouseRelease(g.plot, Qt.LeftButton, pos=QPoint(10, 80))
    assert g.v_offset > 0                               # la regla subió: el cero también
    assert g.a_offset == 0
    assert g.pan == 0                                   # no es un paneo horizontal

    v0, v1 = g.volt_range(0.0, 0.2)
    a0, a1 = g.amp_range(0.0, 0.2)
    div = (v1 - v0) / DIVS_Y
    assert v0 <= 0 <= v1
    assert (v0 + v1) / 2 == pytest.approx(-g.v_offset * div)
    assert a0 == pytest.approx(-a1)

    g.reset_zero("V")
    assert g.v_offset == 0


def test_the_zero_can_move_to_an_edge_but_never_out_of_view():
    g = make_graph()
    _axis, height = g.axis_at(10, 100, 640, 320)
    g.zero_by("V", -100000, height)
    assert g.v_offset == pytest.approx(DIVS_Y / 2)
    v0, v1 = g.volt_range(0.0, 0.2)
    assert v0 <= 0 <= v1
    g.zero_by("V", 100000, height)
    assert g.v_offset == pytest.approx(-DIVS_Y / 2)
    v0, v1 = g.volt_range(0.0, 0.2)
    assert v0 <= 0 <= v1


def test_the_controls_keep_the_old_automatic_choice_when_the_box_is_empty():
    g = make_graph()
    g.vval.clear()
    g._volt_edited()
    g.aval.clear()
    g._amp_edited()
    assert g.volt_div is None and g.amp_div is None
    assert g.volt_unit == "V" and g.amp_unit == "mA"
    img = QImage(640, 320, QImage.Format_ARGB32)
    p = QPainter(img)
    g.paint_plot(p, QRectF(0, 0, 640, 320), None)
    p.end()
