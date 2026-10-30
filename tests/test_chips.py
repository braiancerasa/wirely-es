"""Tests for the r3 parts: 555 timer, op-amps, MOSFETs, logic gates and chips, signal generator.
Each is checked against the textbook formula (MOSFET and op-amp datasheet checks: test_mosfet.py, test_opamp.py)."""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from test_sim import build, op, vnet  # noqa: E402
from wirely.sim.engine import Simulator  # noqa: E402


def edges(sim, dev_fn, t_end):
    """Run until t_end, returning the times at which dev_fn() changed and its new value."""
    out, last = [], dev_fn()
    while sim.t < t_end:
        sim.step(t_end - sim.t)
        now = dev_fn()
        if now != last:
            out.append((sim.t, now))
            last = now
    return out


# ----------------------------------------------------------------------------------------------- 555
def astable(R1, R2, C, V=9.0):
    return build([("dc_supply", ("vcc", "0"), {"voltage": V}),
                  ("timer555", ("0", "th", "out", "vcc", "ctl", "th", "dis", "vcc"), {}),
                  ("resistor", ("vcc", "dis"), {"resistance": R1}),
                  ("resistor", ("dis", "th"), {"resistance": R2}),
                  ("capacitor", ("th", "0"), {"capacitance": C}),
                  ("capacitor", ("ctl", "0"), {"capacitance": 10e-9}),
                  ("resistor", ("out", "0"), {"resistance": 1000})])


@pytest.mark.parametrize("R1,R2,C", [(10e3, 47e3, 10e-6), (10e3, 100e3, 1e-6), (4.7e3, 22e3, 100e-9)])
def test_555_astable_matches_the_formula(R1, R2, C):
    c, comps = astable(R1, R2, C)
    s = Simulator(c)
    s.h_max = 0.02 * 0.693 * R2 * C
    dev = s.device(comps[1].id)
    period = 0.693 * (R1 + 2 * R2) * C
    ev = edges(s, lambda: dev.q, 6 * period)
    hi = [b[0] - a[0] for a, b in zip(ev, ev[1:]) if a[1]][1:]
    lo = [b[0] - a[0] for a, b in zip(ev, ev[1:]) if not a[1]][1:]
    assert hi and lo
    assert hi[-1] == pytest.approx(0.693 * (R1 + R2) * C, rel=0.01)
    assert lo[-1] == pytest.approx(0.693 * R2 * C, rel=0.01)
    assert 1 / (hi[-1] + lo[-1]) == pytest.approx(1.44 / ((R1 + 2 * R2) * C), rel=0.01)
    # output swings to about VCC − 1.7 V and 0.1 V
    s2 = Simulator(c)
    s2.run_until(0.3 * period)
    assert s2.device(comps[1].id).q and vnet(s2, comps[6], "1") == pytest.approx(9 - 1.7, abs=0.1)


def test_555_monostable_lasts_1_1_RC():
    R, C = 100e3, 10e-6
    c, comps = build([("dc_supply", ("vcc", "0"), {"voltage": 9}),
                      ("timer555", ("0", "tr", "out", "vcc", "ctl", "th", "th", "vcc"), {}),
                      ("resistor", ("vcc", "th"), {"resistance": R}),
                      ("capacitor", ("th", "0"), {"capacitance": C}),
                      ("resistor", ("vcc", "tr"), {"resistance": 10e3}),
                      ("push_make", ("tr", "0"), {"pressed": False}),
                      ("led", ("out", "k"), {}), ("resistor", ("k", "0"), {"resistance": 470})])
    s = Simulator(c)
    dev = s.device(comps[1].id)
    s.h_max = 0.01
    s.run_until(0.5)
    assert not dev.q
    s.set_value(comps[5].id, "pressed", True)
    s.run_until(0.52)
    s.set_value(comps[5].id, "pressed", False)
    t_on = None
    while s.t < 3.0:
        s.step(3.0 - s.t)
        if t_on is None and dev.q:
            t_on = s.t
        if t_on is not None and not dev.q:
            break
    assert s.t - 0.5 == pytest.approx(1.1 * R * C, rel=0.01)
    s.run_until(s.t + 0.01)
    assert s.device(comps[6].id).current < 1e-4      # LED off again


# ----------------------------------------------------------------------------------------------- op-amps
def dual_supply(*parts):
    return [("dc_supply", ("vp", "0"), {"voltage": 12}), ("dc_supply", ("0", "vn"), {"voltage": 12})] + list(parts)


@pytest.mark.parametrize("model", ["741", "Rail-to-rail"])
def test_opamp_non_inverting_gain(model):
    s, comps = op(dual_supply(("dc_supply", ("in", "0"), {"voltage": 0.5}),
                              ("opamp", ("fb", "in", "out", "vp", "vn"), {"model": model}),
                              ("resistor", ("out", "fb"), {"resistance": 10e3}),
                              ("resistor", ("fb", "0"), {"resistance": 1e3})))
    assert vnet(s, comps[3], "out") == pytest.approx(0.5 * 11, rel=2e-3)


def test_opamp_inverting_gain():
    s, comps = op(dual_supply(("dc_supply", ("in", "0"), {"voltage": 0.3}),
                              ("resistor", ("in", "fb"), {"resistance": 1e3}),
                              ("opamp", ("fb", "0", "out", "vp", "vn"), {}),
                              ("resistor", ("out", "fb"), {"resistance": 10e3})))
    assert vnet(s, comps[4], "out") == pytest.approx(-3.0, rel=2e-3)


# (output swing, bias current, supply current, bandwidth against datasheets: see test_opamp.py)


def test_opamp_powered_automatically_when_supply_pins_unused():
    """Light-sensor style comparator in a 9 V circuit, with V+ and V− left unconnected."""
    for vin, high in ((6.0, True), (3.0, False)):
        s, comps = op([("battery", ("vcc", "0"), {"voltage": 9}),
                       ("resistor", ("vcc", "ref"), {"resistance": 10e3}), ("resistor", ("ref", "0"),
                                                                             {"resistance": 10e3}),
                       ("dc_supply", ("in", "0"), {"voltage": vin}),
                       ("opamp", ("ref", "in", "out", "np", "nn"), {"model": "Rail-to-rail"}),
                       ("resistor", ("out", "0"), {"resistance": 10e3})])
        vout = vnet(s, comps[4], "out")
        assert (vout > 8.5) if high else (vout < 0.2), (vin, vout)


def test_opamp_integrator_ramps_at_vin_over_rc():
    c, comps = build(dual_supply(("dc_supply", ("0", "in"), {"voltage": 1.0}),       # −1 V in
                                 ("resistor", ("in", "fb"), {"resistance": 10e3}),
                                 ("opamp", ("fb", "0", "out", "vp", "vn"), {}),
                                 ("capacitor", ("fb", "out"), {"capacitance": 1e-6})))
    s = Simulator(c)
    s.h_max = 1e-3
    s.run_until(0.01)
    v1 = vnet(s, comps[4], "out")
    s.run_until(0.05)
    v2 = vnet(s, comps[4], "out")
    assert (v2 - v1) / 0.04 == pytest.approx(1.0 / (10e3 * 1e-6), rel=0.01)       # 100 V/s


def test_opamp_slew_rate_741():
    c, comps = build(dual_supply(("signal_gen", ("in", "0"), {"waveform": "Cuadrada", "frequency": 1000,
                                                             "amplitude": 5, "offset": 0}),
                                 ("opamp", ("out", "in", "out", "vp", "vn"), {"model": "741"}),
                                 ("resistor", ("out", "0"), {"resistance": 10e3})))
    s = Simulator(c)
    s.h_max = 2e-7
    trace = s.transient(0.0012, 2e-7, lambda sim: vnet(sim, comps[3], "out"))
    # the falling edge at 0.5 ms: −5 V → … it moves at about 0.5 V/µs, so ~20 µs for 10 V
    seg = [(t, vv) for t, vv in trace if 0.5e-3 + 2e-6 < t < 0.5e-3 + 12e-6]
    slope = (seg[-1][1] - seg[0][1]) / (seg[-1][0] - seg[0][0])
    assert slope == pytest.approx(-0.5e6, rel=0.1)


# ----------------------------------------------------------------------------------------------- MOSFET
# (on-resistance, threshold, gate charge and switching against datasheets and ngspice: see test_mosfet.py)
def test_mosfet_off_below_threshold_and_no_gate_current():
    s, comps = op([("dc_supply", ("vdd", "0"), {"voltage": 9}), ("dc_supply", ("g", "0"), {"voltage": 1.0}),
                   ("resistor", ("vdd", "d"), {"resistance": 1000}), ("nmos", ("g", "d", "0"), {})])
    assert vnet(s, comps[3], "D") > 8.99
    assert abs(s.device(comps[3].id).i_pins[0]) < 2e-9          # only the 1 GΩ gate leakage


def test_pmos_high_side_switch():
    s, comps = op([("dc_supply", ("vdd", "0"), {"voltage": 9}), ("dc_supply", ("g", "0"), {"voltage": 0.0}),
                   ("pmos", ("g", "d", "vdd"), {"model": "BS250"}), ("resistor", ("d", "0"), {"resistance": 1000})])
    assert vnet(s, comps[2], "D") > 8.5


# ----------------------------------------------------------------------------------------------- logic
TRUTH = {"and": lambda a, b: a and b, "or": lambda a, b: a or b, "nand": lambda a, b: not (a and b),
         "nor": lambda a, b: not (a or b), "xor": lambda a, b: a != b}


@pytest.mark.parametrize("kind", sorted(TRUTH))
def test_gate_truth_tables(kind):
    for a in (False, True):
        for b in (False, True):
            s, comps = op([("battery", ("vcc", "0"), {"voltage": 9}),
                           (kind, ("vcc" if a else "0", "vcc" if b else "0", "y"), {}),
                           ("resistor", ("y", "0"), {"resistance": 100e3})])
            vy = vnet(s, comps[1], "Y")
            assert (vy > 8.0) == TRUTH[kind](a, b), (kind, a, b, vy)
            assert vy > 8.0 or vy < 0.1


def test_not_gate_and_unconnected_input_reads_low():
    s, comps = op([("battery", ("vcc", "0"), {"voltage": 9}), ("not", ("free", "y"), {}),
                   ("resistor", ("y", "0"), {"resistance": 100e3})])
    assert vnet(s, comps[1], "Y") > 8.0


def test_logic_output_can_light_an_led_without_popping():
    c, comps = build([("battery", ("vcc", "0"), {"voltage": 9}), ("not", ("0", "y"), {}), ("led", ("y", "0"), {})])
    s = Simulator(c)
    s.run_until(0.2)
    led = s.device(comps[2].id)
    assert 0.01 < led.current < 0.03 and not led.blown


def test_schmitt_rc_oscillator_period():
    """Schmitt inverter with R from output to input and C to 0 V: period = 2·RC·ln 2 for 1/3 and 2/3 thresholds."""
    R, C = 100e3, 1e-6
    c, comps = build([("battery", ("vcc", "0"), {"voltage": 9}), ("schmitt_not", ("in", "y"), {}),
                      ("resistor", ("y", "in"), {"resistance": R}), ("capacitor", ("in", "0"), {"capacitance": C})])
    s = Simulator(c)
    s.h_max = 2e-3
    g = s.device(comps[1].id)
    ev = edges(s, lambda: g.out["Y"], 1.0)
    rises = [t for t, val in ev if val]
    period = rises[-1] - rises[-2]
    assert period == pytest.approx(2 * R * C * math.log(2) * (1 + 300 / R) , rel=0.01)


def square_clock(freq):
    return ("signal_gen", ("clk", "0"), {"waveform": "Cuadrada", "frequency": freq, "amplitude": 4.5, "offset": 4.5})


def test_d_flip_flop_and_reset():
    c, comps = build([("battery", ("vcc", "0"), {"voltage": 9}), square_clock(10),
                      ("dff", ("vcc", "clk", "rst", "q", "qn"), {}),
                      ("switch", ("vcc", "rst"), {"closed": False}), ("resistor", ("rst", "0"), {"resistance": 10e3})])
    s = Simulator(c)
    ff = s.device(comps[2].id)
    s.run_until(0.02)
    assert not ff.out["Q"]                          # the clock starting high at switch-on isn't an edge
    s.run_until(0.12)
    assert ff.out["Q"] and not ff.out["Qn"]        # first rising clock edge (0.1 s) copied D = 1
    s.set_value(comps[3].id, "closed", True)
    s.run_until(0.3)
    assert not ff.out["Q"]                          # held in reset
    s.set_value(comps[3].id, "closed", False)
    s.run_until(0.45)
    assert ff.out["Q"]


def test_4017_counts_clock_edges():
    c, comps = build([("battery", ("vcc", "0"), {"voltage": 9}), square_clock(10),
                      ("counter4017", ("clk", "0") + tuple(f"q{i}" for i in range(10)) + ("co",), {})])
    s = Simulator(c)
    s.h_max = 5e-3
    s.run_until(0.55)                               # rising edges at 0.1 … 0.5 s (high at switch-on isn't one)
    cnt = s.device(comps[2].id)
    assert cnt.count == 5 and cnt.out["Q5"] and not cnt.out["Q4"] and not cnt.out["CO"]
    assert vnet(s, comps[2], "Q5") > 8.0 and vnet(s, comps[2], "Q4") < 0.1


def test_4511_and_display_show_a_number():
    # D C B A = 0 1 1 1 → 7 → segments a, b, c
    c, comps = build([("battery", ("vcc", "0"), {"voltage": 9}),
                      ("decoder4511", ("vcc", "vcc", "vcc", "0") + tuple("abcdefg"), {}),
                      ("sevenseg", tuple("abcdefg") + ("0",), {})])
    s = Simulator(c)
    s.run_until(0.05)
    lit = s.device(comps[2].id).lit()
    assert [x > 0.5 for x in lit] == [True, True, True, False, False, False, False]
    assert s.device(comps[1].id).value() == 7


def test_square_wave_edges_land_exactly():
    c, comps = build([square_clock(50), ("resistor", ("clk", "0"), {"resistance": 1000})])
    s = Simulator(c)
    s.h_max = 3e-3
    ts = []
    last = None
    while s.t < 0.1:
        s.step(0.1 - s.t)
        hi = vnet(s, comps[1], "1") > 4.5
        if last is not None and hi != last:
            ts.append(s.t)
        last = hi
    for t in ts:
        assert abs(t * 100 - round(t * 100)) < 1e-6 * 100 + 1e-4      # every 10 ms


def test_mosfet_with_unconnected_gate_is_off():
    """+9 V → 1 kΩ → open push switch → gate: the gate is floating, so the lamp must stay off."""
    s, comps = op([("dc_supply", ("vdd", "0"), {"voltage": 9}), ("resistor", ("vdd", "r"), {"resistance": 1000}),
                   ("push_make", ("r", "g"), {"pressed": False}),
                   ("lamp", ("vdd", "d"), {"voltage": 12, "power": 0.5}), ("nmos", ("g", "d", "0"), {})])
    assert vnet(s, comps[4], "G") < 0.1
    assert abs(s.device(comps[3].id).i_pins[0]) < 1e-6
    s.set_value(comps[2].id, "pressed", True)
    s.dc()
    assert vnet(s, comps[4], "G") > 8.9 and s.device(comps[3].id).glow() > 0.5
