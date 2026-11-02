"""Simulación destructiva: activada, las piezas se queman; desactivada, nada se rompe pero se avisa del calor."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

from test_sim import build  # noqa: E402

from wirely.sim import devices as D  # noqa: E402
from wirely.sim.engine import Simulator  # noqa: E402


@pytest.fixture(autouse=True)
def _breakable_again():
    """Cada prueba deja el interruptor como estaba: las demás pruebas esperan roturas normales."""
    yield
    D.Device.BREAKABLE = True


def overloaded_resistor():
    """9 V sobre 10 Ω son 8,1 W en una resistencia de 0,25 W: se quema enseguida."""
    return build([("battery", ("a", "0"), {"voltage": 9}),
                  ("resistor", ("a", "0"), {"resistance": 10, "power": 0.25})])


def test_with_destructive_on_a_resistor_burns():
    c, (_b, r) = overloaded_resistor()
    s = Simulator(c, destructive=True)
    s.run_until(0.5)
    assert s.device(r.id).blown
    assert any("se quemó" in text for _cid, text in s.take_events())


def test_with_destructive_off_nothing_burns_but_it_still_warns():
    c, (_b, r) = overloaded_resistor()
    s = Simulator(c, destructive=False)
    s.run_until(0.5)
    d = s.device(r.id)
    assert not d.blown
    assert d.warn == "hot"                                   # se sigue viendo que se calienta
    assert d.power > 2 * 0.25                                # y la potencia se puede leer
    assert not s.take_events()                               # ningún mensaje de rotura


def test_a_fuse_does_not_blow_with_destructive_off():
    c, (_b, f) = build([("battery", ("a", "0"), {"voltage": 9}),
                       ("fuse", ("a", "0"), {"rating": 0.1})])
    s = Simulator(c, destructive=False)
    s.run_until(0.2)
    d = s.device(f.id)
    assert not d.blown
    assert not s.take_events()
    assert abs(d.i_pins[0]) > 1.0                            # sigue conduciendo


def test_turning_it_off_repairs_what_already_burned():
    c, (_b, r) = overloaded_resistor()
    s = Simulator(c, destructive=True)
    s.run_until(0.5)
    d = s.device(r.id)
    assert d.blown and abs(d.i_pins[0]) < 1e-6               # abierta
    s.set_destructive(False)
    assert not d.blown
    s.run_until(0.6)
    assert abs(d.i_pins[0]) > 0.5                            # vuelve a conducir


def test_the_switch_only_controls_permanent_damage():
    c, (_b, r) = overloaded_resistor()
    s = Simulator(c, destructive=True)
    d = s.device(r.id)
    s.set_destructive(False)
    d.blown = True
    assert not d.blown
    s.set_destructive(True)
    d.blown = True
    assert d.blown
