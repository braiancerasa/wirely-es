"""MOSFETs against their datasheets (on-resistance, threshold, body diode, gate charge) and against ngspice
running the same model (switching transients with the gate and drain capacitances)."""
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spice_models import mosfet_subckt  # noqa: E402
from test_sim import NGSPICE, build, op  # noqa: E402

from wirely.sim import chips as CH  # noqa: E402
from wirely.sim.engine import Simulator  # noqa: E402

POINTS = [(m, vgs, r) for m, d in CH.MOSFET_DATA.items() for vgs, r in d[3]]


def kind(model):
    return "nmos" if CH.MOSFETS[model].pol > 0 else "pmos"


@pytest.mark.parametrize("model,vgs,rds", POINTS)
def test_on_resistance_matches_the_datasheet(model, vgs, rds):
    P = CH.MOSFETS[model]
    i_test = 0.1 * P.idmax
    vdd = 1.0
    rload = vdd / i_test
    if P.pol > 0:
        spec = [("dc_supply", ("vdd", "0"), {"voltage": vdd}), ("dc_supply", ("g", "0"), {"voltage": vgs}),
                ("resistor", ("vdd", "d"), {"resistance": rload}), ("nmos", ("g", "d", "0"), {"model": model})]
    else:
        spec = [("dc_supply", ("0", "vn"), {"voltage": vdd}), ("dc_supply", ("0", "g"), {"voltage": vgs}),
                ("resistor", ("d", "vn"), {"resistance": rload}), ("pmos", ("g", "d", "0"), {"model": model})]
    s, comps = op(spec)
    q = s.device(comps[3].id)
    vds = s.pin_voltage(comps[3].id, "D") - s.pin_voltage(comps[3].id, "S")
    tol = 0.02 if len(CH.MOSFET_DATA[model][3]) == 1 else 0.12      # several points: a best fit through them
    assert vds / q.id == pytest.approx(rds, rel=tol)


@pytest.mark.parametrize("model", list(CH.MOSFET_DATA))
def test_threshold_matches_the_datasheet(model):
    """Vgs(th) is measured with the gate tied to the drain, at the datasheet's test current."""
    P = CH.MOSFETS[model]
    if P.pol > 0:
        spec = [("dc_supply", ("a", "0"), {"voltage": P.vth}), ("nmos", ("a", "a", "0"), {"model": model})]
    else:
        spec = [("dc_supply", ("0", "a"), {"voltage": P.vth}), ("pmos", ("a", "a", "0"), {"model": model})]
    s, comps = op(spec)
    assert abs(s.device(comps[1].id).id) == pytest.approx(P.ith, rel=0.1)


@pytest.mark.parametrize("model", ["IRF540", "AO3400", "IRF9540", "2N7000"])
def test_body_diode_conducts_backwards(model):
    """With the channel off, current forced from source to drain flows through the body diode (~0.7 V)."""
    P = CH.MOSFETS[model]
    i = P.idmax / 6
    if P.pol > 0:
        spec = [("dc_supply", ("0", "neg"), {"voltage": 5}), ("resistor", ("d", "neg"), {"resistance": 5 / i}),
                ("nmos", ("0", "d", "0"), {"model": model})]
    else:
        spec = [("dc_supply", ("pos", "0"), {"voltage": 5}), ("resistor", ("pos", "d"), {"resistance": 5 / i}),
                ("pmos", ("0", "d", "0"), {"model": model})]
    s, comps = op(spec)
    vsd = abs(s.pin_voltage(comps[2].id, "D"))
    assert 0.6 < vsd < 0.85 + P.rser * i


def gate_charge(model, vdd, i_load, v_gate):
    """Charge a MOSFET's gate with a steady 1 mA (1000 V through 1 MΩ) while it switches a load drawing
    i_load from vdd. Returns (total gate charge to reach v_gate, charge taken on the Miller plateau)."""
    P = CH.MOSFETS[model]
    if P.pol > 0:
        spec = [("dc_supply", ("vdd", "0"), {"voltage": vdd}),
                ("resistor", ("vdd", "d"), {"resistance": vdd / i_load, "power": 2000.0}),
                ("dc_supply", ("hv", "0"), {"voltage": 1000}), ("resistor", ("hv", "g"), {"resistance": 1e6}),
                ("nmos", ("g", "d", "0"), {"model": model})]
    else:
        spec = [("dc_supply", ("0", "vn"), {"voltage": vdd}),
                ("resistor", ("d", "vn"), {"resistance": vdd / i_load, "power": 2000.0}),
                ("dc_supply", ("0", "hv"), {"voltage": 1000}), ("resistor", ("g", "hv"), {"resistance": 1e6}),
                ("pmos", ("g", "d", "0"), {"model": model})]
    c, comps = build(spec)
    s = Simulator(c)
    gid = comps[4].id
    s.set_value(comps[2].id, "voltage", 0.0)        # start with the gate at 0 V …
    s.dc()
    s.set_value(comps[2].id, "voltage", 1000.0)     # … then switch on the 1 mA gate current
    s.h_max = 2e-9
    q, q_flat = 0.0, 0.0
    prev = 0.0
    while s.t < 1e-3:
        h = s.step()
        dq = abs(s.device(gid).i_pins[0]) * h
        q += dq
        vg = abs(s.pin_voltage(gid, "G"))
        if dq > 0 and abs(vg - prev) / (dq * 1e9) < 0.25:      # under 0.25 V per nC: on the plateau
            q_flat += dq
        prev = vg
        if vg >= v_gate:
            break
    return q, q_flat


@pytest.mark.parametrize("model,vdd,i_load,v_gate,qg,qgd", [
    ("AO3400", 15, 5.7, 4.5, 6e-9, 1.8e-9),       # datasheet: Qg 6 nC, Qgd 1.8 nC at 4.5 V, 15 V, 5.7 A
    ("FQP27P06", 48, 27, 10, 33e-9, 18e-9),       # datasheet: Qg 33 nC, Qgd 18 nC at −10 V, −48 V, −27 A
])
def test_gate_charge_and_miller_plateau(model, vdd, i_load, v_gate, qg, qgd):
    q, q_flat = gate_charge(model, vdd, i_load, v_gate)
    assert q == pytest.approx(qg, rel=0.25)
    assert q_flat == pytest.approx(qgd, rel=0.5)       # the gate stands still while the drain swings (Miller)


@pytest.mark.skipif(not NGSPICE, reason="ngspice not installed")
@pytest.mark.parametrize("model,vdd,rl,rgate", [("IRF540", 24, 12, 100), ("2N7000", 12, 120, 1000)])
def test_switching_against_ngspice(model, vdd, rl, rgate):
    """Turn a MOSFET on and off through a gate resistor; the drain's fall and rise (set by the Miller
    capacitance) must happen at the same moments as in ngspice."""
    period = 40e-6 if model == "IRF540" else 200e-6
    net = f"""Wirely check
* switching
{mosfet_subckt(model, 1)}
V1 vdd 0 {vdd}
VG gin 0 PULSE(0 10 {period / 8} 1n 1n {period / 2} {period})
RG gin g {rgate}
RL vdd d {rl}
XM d g 0 W{model}
.control
tran {period / 4000} {period}
meas tran tf when v(d)={vdd / 2} fall=1
meas tran tr when v(d)={vdd / 2} rise=1
.endc
.end
"""
    out = subprocess.run([NGSPICE, "-b", "/dev/stdin"], input=net, capture_output=True, text=True,
                         timeout=120).stdout
    tf_ng = float(re.search(r"tf\s*=\s*([-+0-9.eE]+)", out).group(1))
    tr_ng = float(re.search(r"tr\s*=\s*([-+0-9.eE]+)", out).group(1))
    c, comps = build([("dc_supply", ("vdd", "0"), {"voltage": vdd}),
                      ("signal_gen", ("gin", "0"), {"waveform": "Square", "frequency": 1 / period, "amplitude": 5,
                                                    "offset": 5, "duty": 50}),
                      ("resistor", ("gin", "g"), {"resistance": rgate}),
                      ("resistor", ("vdd", "d"), {"resistance": rl, "power": 100.0}),
                      ("nmos", ("g", "d", "0"), {"model": model})])
    s = Simulator(c)
    # our square wave is high for the first half of each period: rising edges at n·T, falling at (n + ½)·T
    tr = s.transient(period * 1.9, period / 4000, lambda sim: sim.pin_voltage(comps[4].id, "D"))
    pts = [(t, vv) for t, vv in tr if t > period * 0.9]

    def cross(falling):
        for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
            if (v0 > vdd / 2 >= v1) if falling else (v0 < vdd / 2 <= v1):
                return t0 + (t1 - t0) * (v0 - vdd / 2) / (v0 - v1)
        return None
    tf, trr = cross(True), cross(False)
    assert tf is not None and trr is not None
    on_delay, off_delay = tf - period, trr - 1.5 * period
    ng_on, ng_off = tf_ng - period / 8, tr_ng - (period / 8 + period / 2)
    print(f"{model}: turn-on delay {on_delay * 1e9:.0f} ns (ngspice {ng_on * 1e9:.0f}), "
          f"turn-off {off_delay * 1e9:.0f} ns (ngspice {ng_off * 1e9:.0f})")
    assert on_delay == pytest.approx(ng_on, rel=0.15, abs=20e-9)
    assert off_delay == pytest.approx(ng_off, rel=0.15, abs=20e-9)
