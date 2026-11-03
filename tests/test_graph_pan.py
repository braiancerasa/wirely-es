"""Paneo manual del gráfico: en pausa se puede arrastrar por el tiempo, con límites en el inicio de la
simulación y en el último instante dibujado, y al reanudar vuelve a seguir el trazo en vivo."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtCore import QPoint, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from wirely.ui.graph import GraphPanel  # noqa: E402


def make_panel(t_now=2.0):
    QApplication.instance() or QApplication([])
    g = GraphPanel()
    g.tval.setText("100")
    g.tunit.setCurrentText("ms")
    g._time_edited()                   # 100 ms por cuadro: la ventana muestra 1 s
    g.add_samples([(i * 0.01, {"A": 1.0}) for i in range(int(t_now / 0.01) + 1)], t_now)
    return g


def window(g):
    """Ventana de tiempo que se está dibujando (t0, t1), capturada de la cuadrícula."""
    seen = {}
    g._grid = lambda p, rect, area, t0, t1, *a, **k: seen.update(t0=t0, t1=t1)
    img = QImage(640, 320, QImage.Format_ARGB32)
    p = QPainter(img)
    g.paint_plot(p, QRectF(0, 0, 640, 320), None)
    p.end()
    del g._grid
    return seen["t0"], seen["t1"]


def test_while_running_the_graph_follows_the_live_trace():
    g = make_panel()
    assert not g.can_pan()
    g.pan_by(320, 640)                 # no hace nada: está dibujando en vivo
    assert g.pan == 0
    assert window(g) == (1.0, 2.0)


def test_when_paused_dragging_moves_the_window_back_in_time():
    g = make_panel()
    g.set_follow(False)
    assert g.can_pan()
    g.pan_by(320, 640)                 # media pantalla hacia la derecha: medio segundo atrás
    assert g.pan == 0.5
    assert window(g) == (0.5, 1.5)


def test_panning_stops_at_the_start_and_at_the_last_drawn_time():
    g = make_panel()
    g.set_follow(False)
    g.pan_by(100000, 640)              # mucho hacia atrás: el borde izquierdo llega al inicio (0 s)
    assert g.pan == 1.0
    assert window(g) == (0.0, 1.0)
    g.pan_by(-100000, 640)             # mucho hacia adelante: no pasa del último tiempo dibujado (2 s)
    assert g.pan == 0.0
    assert window(g) == (1.0, 2.0)


def test_resuming_resets_the_pan_to_follow_the_trace():
    g = make_panel()
    g.set_follow(False)
    g.pan_by(320, 640)
    assert g.pan == 0.5
    g.set_follow(True)                 # al reanudar, vuelve solo a donde estaba
    assert g.pan == 0
    assert window(g) == (1.0, 2.0)


def test_dragging_with_the_mouse_pans_the_plot():
    g = make_panel()
    g.set_follow(False)
    g.plot.resize(640, 320)
    QTest.mousePress(g.plot, Qt.LeftButton, pos=QPoint(320, 150))
    QTest.mouseMove(g.plot, QPoint(480, 150))
    QTest.mouseRelease(g.plot, Qt.LeftButton, pos=QPoint(480, 150))
    assert g.pan > 0
