"""Parts used beyond their voltage ratings: MOSFET avalanche breakdown (survivable when brief and small, fatal
when it lasts) and motors on far too much voltage."""
import os
import sys


sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from test_sim import build  # noqa: E402

from wirely.sim.engine import Simulator  # noqa: E402


def motor_switch(v, closed, model="IRF540", motor_v=9):
    """Richard's circuit: battery, switch to the gate (100 kΩ pull-down), motor from + to the drain, no diode."""
    return build([("battery", ("vcc", "0"), {"voltage": v}),
                  ("switch", ("vcc", "g"), {"closed": closed}),
                  ("resistor", ("g", "0"), {"resistance": 100e3}),
                  ("motor", ("vcc", "d"), {"voltage": motor_v}),
                  ("nmos", ("g", "d", "0"), {"model": model})])


def run(c, t=0.5):
    s = Simulator(c)
    s.h_max = 1e-3
    s.run_until(t)
    return s


def test_mosfet_off_with_more_than_its_rating_breaks_down_and_dies():
    """150 V across an IRF540 (100 V part) that's switched off: it avalanches at ~115 V, the motor's current
    flows through it, and it overheats."""
    c, comps = motor_switch(150, closed=False)
    s = run(c, 0.1)
    assert s.device(comps[4].id).blown
    msgs = [t for _cid, t in s.take_events()]
    assert any("Q1" in m and "soporta 100 V" in m for m in msgs), msgs


def test_mosfet_at_its_rating_is_fine():
    c, comps = motor_switch(90, closed=False, motor_v=90)
    s = run(c)
    assert not s.device(comps[4].id).blown
    assert abs(s.device(comps[4].id).id) < 1e-4          # off, and not breaking down


def test_nine_volt_motor_on_150_volts_burns_out():
    c2, comps2 = build([("battery", ("vcc", "0"), {"voltage": 150}), ("motor", ("vcc", "0"), {"voltage": 9})])
    s = run(c2, 1.5)
    assert s.device(comps2[1].id).blown
    assert any("motor de 9 V" in t for _cid, t in s.take_events())


def test_motor_at_its_own_voltage_is_fine():
    c, comps = build([("battery", ("vcc", "0"), {"voltage": 9}), ("motor", ("vcc", "0"), {"voltage": 9})])
    s = run(c, 2.0)
    assert not s.device(comps[1].id).blown
    assert s.device(comps[1].id).speed > 0.8


def relay_kick(model):
    """A MOSFET switching a 12 V relay coil with no diode, then switching it off."""
    c, comps = build([("dc_supply", ("vcc", "0"), {"voltage": 12}),
                      ("dc_supply", ("g", "0"), {"voltage": 10}),
                      ("relay", ("vcc", "d", "vcc", "nc", "no"), {"voltage": 12}),
                      ("nmos", ("g", "d", "0"), {"model": model})])
    s = Simulator(c)
    s.h_max = 1e-4
    s.run_until(0.05)
    s.set_value(comps[1].id, "voltage", 0.0)
    s.run_until(0.1)
    return s, comps


def test_power_mosfet_survives_a_small_coil_spike_by_avalanching():
    """Avalanche-rated power MOSFETs (IRF540: about 0.2 J) shrug off a relay coil's spike: the drain is clamped
    just above the rating instead of flying up to hundreds of volts."""
    s, comps = relay_kick("IRF540")
    assert not s.device(comps[3].id).blown


def test_small_signal_mosfet_is_killed_by_the_same_spike():
    s, comps = relay_kick("2N7000")
    assert s.device(comps[3].id).blown
