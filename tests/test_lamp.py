"""Filament lamps: resistance rising as the filament heats (the GCSE/A-level I–V curve), the switch-on surge,
and the filament taking a moment to heat up and cool down."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from test_sim import build, op  # noqa: E402

from wirely.sim.engine import Simulator  # noqa: E402


def lamp_at(v):
    s, comps = op([("dc_supply", ("a", "0"), {"voltage": v}),
                   ("lamp", ("a", "0"), {"voltage": 6, "power": 0.36})])
    d = s.device(comps[1].id)
    return d.vd, d.current


def test_rated_voltage_gives_rated_current():
    v, i = lamp_at(6.0)
    assert i == pytest.approx(0.36 / 6, rel=0.01)           # 60 mA at 6 V


def test_resistance_rises_with_voltage_so_the_iv_graph_curves():
    pts = [lamp_at(v) for v in (0.5, 1, 2, 3, 4, 5, 6)]
    rs = [v / i for v, i in pts]
    assert all(b > a for a, b in zip(rs, rs[1:]))          # R = V / I goes up as it gets hotter
    v3, i3 = pts[3]
    v6, i6 = pts[6]
    assert i3 > i6 / 2 * 1.2                               # half the voltage gives well over half the current
    assert i3 / i6 == pytest.approx((v3 / v6) ** 0.6, rel=0.01)   # I ∝ V^0.6, as real tungsten lamps measure


def test_cold_filament_takes_a_surge_at_switch_on():
    c, comps = build([("dc_supply", ("a", "0"), {"voltage": 6}),
                      ("switch", ("a", "b"), {"closed": False}),
                      ("lamp", ("b", "0"), {"voltage": 6, "power": 0.36})])
    s = Simulator(c)
    s.h_max = 2e-4
    s.run_until(0.01)
    s.set_value(comps[1].id, "closed", True)
    s.run_until(0.0105)
    lamp = s.device(comps[2].id)
    assert lamp.current > 8 * 0.06                         # cold: about 12× the running current
    s.run_until(0.5)
    assert lamp.current == pytest.approx(0.06, rel=0.02)   # hot: back to 60 mA
    assert lamp.glow() > 0.95
    s.set_value(comps[1].id, "closed", False)
    s.run_until(0.53)
    assert 0 < lamp.glow() < 0.95                          # still glowing as it cools …
    s.run_until(1.0)
    assert lamp.glow() == 0.0                              # … then out
    assert not lamp.blown


def test_switch_on_surge_does_not_burn_out_a_suitable_resistor():
    """A lamp with a series resistor rated for the running current: the brief surge doesn't burn it out."""
    c, comps = build([("dc_supply", ("a", "0"), {"voltage": 12}),
                      ("resistor", ("a", "b"), {"resistance": 100, "power": 0.5}),
                      ("lamp", ("b", "0"), {"voltage": 6, "power": 0.36})])
    s = Simulator(c)
    s.h_max = 1e-3
    s.run_until(1.0)
    assert not s.device(comps[1].id).blown
    assert not s.take_events()
