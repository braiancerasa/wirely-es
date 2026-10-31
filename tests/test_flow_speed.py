"""Velocidad del flujo de corriente: un control que solo mueve los puntos de los cables (nunca el circuito), una
escala corriente-velocidad que se note, y la opción de que el flujo siga la velocidad de simulación."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

from test_editor import app, win  # noqa: E402,F401

from wirely.ui.mainwindow import EXAMPLES  # noqa: E402
from wirely.ui.simcontrol import FLOW_MAX, FLOW_MIN, flow_dots_speed  # noqa: E402


def find(w, kind):
    return next(c for c in w.circuit.components.values() if c.kind == kind)


def advances(sim, dt):
    """Cuánto avanza la fase de cada cable al dibujar un cuadro de `dt` segundos de pantalla."""
    before = dict(sim._phase)
    sim._compute_frame(dt)
    return {k: sim._phase[k] - before.get(k, 0.0) for k in sim._phase}


def running_led(win):
    win.open_file(os.path.join(EXAMPLES, "LED y resistencia.wirely"))
    find(win, "switch").props["closed"] = True
    win.a_play.trigger()
    win.simc._timer.stop()                   # cuadros a mano, sin depender del reloj
    win.simc._compute_frame(0.0)
    return win.simc


def test_dot_speed_grows_with_current_but_stays_usable():
    assert flow_dots_speed(0.0) == FLOW_MIN
    assert flow_dots_speed(1e-9) == FLOW_MIN
    assert flow_dots_speed(1e-6) == pytest.approx(FLOW_MIN)
    assert flow_dots_speed(-0.01) == flow_dots_speed(0.01)
    slow, mid, fast = flow_dots_speed(1e-4), flow_dots_speed(1e-3), flow_dots_speed(1.0)
    assert slow < mid < fast
    assert fast / mid > 3                    # una rama con 1000 veces más corriente se nota a simple vista
    assert flow_dots_speed(100.0) == FLOW_MAX
    assert flow_dots_speed(1.0) < FLOW_MAX   # las corrientes normales no quedan todas al tope


def test_the_flow_control_only_moves_the_dots(win):
    sim = running_led(win)
    led = find(win, "led")
    current = win.scene.live_part(led.id)["i"]
    t = sim.sim.t
    full = advances(sim, 0.5)
    assert any(abs(d) > 1.0 for d in full.values())        # hay puntos y se mueven

    sim.set_flow_speed(0.25)
    quarter = advances(sim, 0.5)
    for key, d in full.items():
        assert quarter[key] == pytest.approx(d * 0.25)     # más lento, en la misma proporción

    sim.set_flow_speed(4.0)
    fast = advances(sim, 0.5)
    for key, d in full.items():
        assert fast[key] == pytest.approx(d * 4.0)

    # el circuito no cambió: misma corriente, mismo tiempo simulado, misma lectura
    assert win.scene.live_part(led.id)["i"] == current
    assert sim.sim.t == t
    assert sim.speed == 1.0
    win.a_stop.trigger()


def test_the_flow_can_follow_the_simulation_speed(win):
    sim = running_led(win)
    full = advances(sim, 0.5)
    sim.set_flow_speed(1.0)
    sim.set_flow_follow(True)
    sim.set_speed(0.1)
    slow = advances(sim, 0.5)
    for key, d in full.items():
        assert slow[key] == pytest.approx(d * 0.1)         # cámara lenta: el flujo se frena igual
    assert sim.flow_factor() == pytest.approx(0.1)
    # el multiplicador se aplica encima de la velocidad de simulación
    sim.set_flow_speed(2.0)
    assert sim.flow_follow and sim.flow_factor() == pytest.approx(0.2)
    sim.set_flow_follow(False)
    assert sim.flow_factor() == 2.0                        # de vuelta a una velocidad fija
    win.a_stop.trigger()


def test_toolbar_flow_control(win):
    win.open_file(os.path.join(EXAMPLES, "LED y resistencia.wirely"))
    labels = [win.flow_box.itemText(i) for i in range(win.flow_box.count())]
    assert labels == ["×¼", "×½", "×1", "×2", "×4"]
    win.flow_box.setCurrentText("×4")
    assert win.simc.flow_speed == 4.0
    win.flow_box.setCurrentText("×1")
    assert win.simc.flow_speed == 1.0
    # la opción de seguir la simulación está en el menú Simular y se guarda
    assert not win.a_flow_follow.isChecked() and not win.simc.flow_follow
    win.a_flow_follow.trigger()
    assert win.a_flow_follow.isChecked() and win.simc.flow_follow
    assert win.settings.value("flow_follow") == "true"
    win.a_flow_follow.trigger()
    assert not win.simc.flow_follow
    assert win.settings.value("flow_follow") == "false"

