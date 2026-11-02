"""La sonda de corriente muestra la fase real de la corriente: se adelanta en un circuito capacitivo,
se atrasa en uno inductivo y el sentido no depende de cómo se dibujó el cable."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

from test_current_probe import a_point_on, wire_of  # noqa: E402
from test_sim import build  # noqa: E402

from wirely.sim.engine import Simulator  # noqa: E402

FREQ = 1000.0


def ac_circuit(kind, value):
    if kind == "rc":
        return build([("ac_supply", ("a", "0"), {"voltage": 1.0, "frequency": FREQ}),
                      ("resistor", ("a", "b"), {"resistance": 1000.0}),
                      ("capacitor", ("b", "0"), {"capacitance": value})])
    return build([("ac_supply", ("a", "0"), {"voltage": 1.0, "frequency": FREQ}),
                  ("resistor", ("a", "b"), {"resistance": 1000.0}),
                  ("inductor", ("b", "0"), {"inductance": value})])


def rising_crossings(ts, ys):
    out = []
    for i in range(1, len(ys)):
        if ys[i - 1] < 0 <= ys[i]:
            out.append(ts[i - 1] + (ts[i] - ts[i - 1]) * (-ys[i - 1]) / (ys[i] - ys[i - 1]))
    return out


def lead_of_current(kind="rc", value=100e-9, pin="1"):
    """Cuánto adelanta la corriente registrada por la sonda respecto del voltaje de la fuente (grados)."""
    c, comps = ac_circuit(kind, value)
    src, element = comps[0], comps[-1]
    c.add("scope_probe", *a_point_on(wire_of(c, src, "1")), props={"channel": "A"})
    c.add("current_probe", *a_point_on(wire_of(c, element, pin)), props={"channel": "I1"})
    sim = Simulator(c)
    sim.recording = True
    sim.run_until(0.05)
    pts = [(t, v) for t, v in sim.record if t > 0.04]
    ts = [t for t, _v in pts]
    iv = [v.get("I1", 0.0) for _t, v in pts]
    vv = [v.get("A", 0.0) for _t, v in pts]
    ti, tv = rising_crossings(ts, iv), rising_crossings(ts, vv)
    leads = []
    for tv0 in tv:
        ti0 = min(ti, key=lambda t: abs(t - tv0))
        dt = tv0 - ti0
        if abs(dt) < 0.5 / FREQ:          # el cruce que corresponde al mismo ciclo
            leads.append(dt * FREQ * 360.0)        # adelanto en grados
    return sum(leads) / len(leads)


def test_capacitive_circuit_current_leads_the_voltage():
    # R = 1 kΩ, C = 100 nF a 1 kHz: la corriente adelanta atan(1/(ωRC)) ≈ 58°
    assert lead_of_current("rc", 100e-9) == pytest.approx(57.9, abs=3)


def test_inductive_circuit_current_lags_the_voltage():
    # R = 1 kΩ, L = 100 mH a 1 kHz: la corriente atrasa atan(ωL/R) ≈ 32°
    assert lead_of_current("rl", 0.1) == pytest.approx(-32.0, abs=3)


def test_the_phase_changes_with_the_capacitor():
    big_lead = lead_of_current("rc", 10e-9)              # más reactivo: casi 90°
    small_lead = lead_of_current("rc", 1e-6)             # más resistivo: unos 9°
    assert big_lead > small_lead + 40


def test_the_probe_polarity_does_not_depend_on_where_it_sits():
    # las dos patas del capacitor llevan la misma corriente: la sonda debe dibujar la misma fase
    assert lead_of_current("rc", 100e-9, "1") == pytest.approx(lead_of_current("rc", 100e-9, "2"), abs=0.5)
