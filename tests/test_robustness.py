"""Bugs found by checking every example step by step and stress-testing every part in random circuits (1.5.0):
pin currents must always be the ones the circuit was solved with, and mis-wired parts must not stall the solver."""
import glob
import itertools
import os
import sys
import time
from collections import defaultdict

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from test_sim import build  # noqa: E402

from wirely.model.circuit import Circuit  # noqa: E402
from wirely.sim import devices as D  # noqa: E402
from wirely.sim.engine import Simulator  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
EXAMPLES = sorted(glob.glob(os.path.join(ROOT, "examples", "*.wirely")))


def watch_pin_currents(sim):
    """Before each step is accepted, work out from each part's own equations the current it really passes at the
    solved voltages; after, compare with what it reports. Returns the list of mismatches found."""
    bad = []
    for d in sim.devices:
        orig = d.accept

        def acc(x, ctx, d=d, orig=orig):
            implied = None
            if not ctx.dc and d.comp.kind not in ("ground", "note", "scope_probe") and not d.blown:
                A = [[0.0] * sim.N for _ in range(sim.N)]
                b = [0.0] * sim.N
                saved = {k: getattr(d, k) for k in ("vd_last", "v_last", "_clamped") if hasattr(d, k)}
                d.stamp(D.Stamper(A, b), list(map(float, x)), ctx)
                for k, val in saved.items():
                    setattr(d, k, val)
                cur = np.array(A) @ np.array(x, dtype=float) - np.array(b)
                implied = {n: cur[n] for n in d.nodes if n >= 0}
            orig(x, ctx)
            if implied is None or not d.i_pins or d.blown:
                return
            reported = defaultdict(float)
            for k, n in enumerate(d.nodes):
                if n >= 0 and k < len(d.i_pins):
                    reported[n] += d.i_pins[k]
            for n, ip in reported.items():
                im = implied[n]
                if abs(ip - im) > 1e-6 and abs(ip - im) > 1e-3 * max(abs(ip), abs(im)):
                    bad.append(f"{d.comp.ref} ({d.comp.kind}) t={ctx.t:.5f}: reports {ip * 1e3:.3f} mA, "
                               f"solved {im * 1e3:.3f} mA")
        d.accept = acc
    return bad


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: os.path.basename(p)[:-7])
def test_parts_report_the_current_they_were_solved_with(path):
    """Regulators, 555s, logic chips, relays and motors used to report the current for the state they were
    switching *to* (e.g. a 7805 showed 137 A for a moment at switch-on), and the 555 left out CTRL's current."""
    c = Circuit.load(path)
    s = Simulator(c)
    s.h_max = 1e-3
    bad = watch_pin_currents(s)
    s.run_until(0.25, budget_s=60)
    assert not bad, bad[:5]


@pytest.mark.parametrize("kind", ["reg_fixed", "reg_adj"])
def test_a_regulator_wired_any_way_round_settles(kind):
    """Swapped input and output (a common mistake), GND on the supply … none may stall the simulation."""
    slow = []
    for pins in itertools.product(["v", "0", "a", "b"], repeat=3):
        c, comps = build([("dc_supply", ("v", "0"), {"voltage": 9}), (kind, pins, {}),
                          ("resistor", ("a", "0"), {"resistance": 1000}),
                          ("resistor", ("b", "v"), {"resistance": 100})])
        s = Simulator(c)
        s.h_max = 1e-3
        t0 = time.time()
        if not s.run_until(0.05, budget_s=3) or time.time() - t0 > 1.0:
            slow.append(pins)
    assert not slow


def test_7805_with_input_and_output_swapped_is_off():
    s, c = None, None
    c, comps = build([("dc_supply", ("v", "0"), {"voltage": 9}), ("reg_fixed", ("a", "0", "v"), {}),
                      ("resistor", ("a", "0"), {"resistance": 1000})])
    s = Simulator(c)
    s.run_until(0.05)
    reg = s.device(comps[1].id)
    assert reg.mode == "off"
    # the output's supply leaks back to IN through its protection diode, about 0.7 V down
    assert 7.8 < s.pin_voltage(comps[1].id, "IN") < 8.6


@pytest.mark.parametrize("model", ["TL431", "TLV431"])
def test_tl431_wired_any_way_round_settles(model):
    stuck = []
    for pins in itertools.product(["v", "0", "a", "b"], repeat=3):
        c, comps = build([("dc_supply", ("v", "0"), {"voltage": 9}), ("shunt_ref", pins, {"model": model}),
                          ("resistor", ("a", "0"), {"resistance": 1000}),
                          ("resistor", ("b", "v"), {"resistance": 1000})])
        s = Simulator(c)
        s.h_max = 1e-3
        if not s.run_until(0.02, budget_s=3) or s.struggling:
            stuck.append(pins)
    assert not stuck


def test_tl431_with_ref_on_the_supply_sinks_hard():
    c, comps = build([("dc_supply", ("v", "0"), {"voltage": 9}), ("shunt_ref", ("k", "0", "v"), {"model": "TLV431"}),
                      ("resistor", ("k", "v"), {"resistance": 1000})])
    s = Simulator(c)
    s.dc()
    assert s.pin_voltage(comps[1].id, "K") == pytest.approx(0.85, abs=0.1)


def test_opamp_output_held_above_its_supply_settles():
    c, comps = build([("dc_supply", ("v", "0"), {"voltage": 9}), ("opamp", ("a", "a", "v", "b", "0"), {}),
                      ("resistor", ("a", "0"), {"resistance": 1000}), ("resistor", ("b", "0"), {"resistance": 1000})])
    s = Simulator(c)
    s.h_max = 1e-3
    assert s.run_until(0.05, budget_s=5) and not s.struggling
    # its protection diode feeds V+ from the output, about 0.7 V down
    assert 7.8 < s.pin_voltage(comps[1].id, "V+") < 8.6


def test_opamp_on_a_reversed_supply_is_destroyed():
    c, comps = build([("dc_supply", ("v", "0"), {"voltage": 9}), ("opamp", ("a", "0", "c", "0", "v"), {}),
                      ("resistor", ("a", "0"), {"resistance": 1000}), ("resistor", ("c", "0"), {"resistance": 1000})])
    s = Simulator(c)
    s.run_until(0.01)
    assert s.device(comps[1].id).blown
    assert any("al revés" in t for _c, t in s.take_events())


def test_burnt_out_thyristor_doesnt_slow_the_simulation():
    """It used to keep switching its 'on' flag after burning out, forcing tiny steps for ever."""
    c, comps = build([("dc_supply", ("v", "0"), {"voltage": 9}), ("scr", ("v", "0", "v"), {})])
    s = Simulator(c)
    s.h_max = 1e-3
    t0 = time.time()
    s.run_until(0.15)
    assert time.time() - t0 < 1.0
    assert s.device(comps[1].id).blown
    assert len(s.take_events()) == 1
