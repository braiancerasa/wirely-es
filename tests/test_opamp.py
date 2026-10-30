"""Op-amps against their datasheets: output swing under load, input bias current, supply current,
closed-loop bandwidth, current drawn through the supply pins, and over-voltage."""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from test_sim import build, op, vnet  # noqa: E402

from wirely.sim import chips as CH  # noqa: E402
from wirely.sim.engine import Simulator  # noqa: E402


def split(v=15.0, *parts):
    return [("dc_supply", ("vp", "0"), {"voltage": v}), ("dc_supply", ("0", "vn"), {"voltage": v})] + list(parts)


@pytest.mark.parametrize("model,rl,swing", [
    ("741", 10e3, 14.0), ("741", 2e3, 13.0),          # datasheet: ±14 V into 10 kΩ, ±13 V into 2 kΩ (±15 V)
    ("TL071", 10e3, 13.5), ("TL071", 2e3, 12.0),      # datasheet: ±13.5 V into 10 kΩ, ±12 V into 2 kΩ
])
def test_output_swing_under_load(model, rl, swing):
    for vin in (1.0, -1.0):
        s, comps = op(split(15.0, ("dc_supply", ("in", "0"), {"voltage": vin}),
                            ("opamp", ("0", "in", "out", "vp", "vn"), {"model": model}),
                            ("resistor", ("out", "0"), {"resistance": rl})))
        assert vnet(s, comps[3], "out") == pytest.approx(math.copysign(swing, vin), abs=0.3)


def test_lm358_output_reaches_0v_but_not_the_top_rail():
    """Single 30 V supply: the output gets within a few mV of 0 V, but only to about V+ − 1.5 V."""
    out = {}
    for vin in (1.0, -1.0):
        s, comps = op([("dc_supply", ("vp", "0"), {"voltage": 30}), ("dc_supply", ("ref", "0"), {"voltage": 15}),
                       ("dc_supply", ("in", "ref"), {"voltage": vin}),
                       ("opamp", ("ref", "in", "out", "vp", "0"), {"model": "LM358"}),
                       ("resistor", ("out", "0"), {"resistance": 10e3})])
        out[vin] = vnet(s, comps[3], "out")
    assert out[1.0] == pytest.approx(30 - 1.5, abs=0.3)      # datasheet: about 28 V with a 30 V supply
    assert out[-1.0] < 0.02                                   # datasheet: 5 mV


@pytest.mark.parametrize("model,ib", [("741", 80e-9), ("LM358", -20e-9), ("TL071", 30e-12)])
def test_input_bias_current_shows_up_with_big_resistors(model, ib):
    """Unity-gain inverting amp with 1 MΩ resistors and the input grounded: the bias current into the − input
    has to come through the feedback resistor, so the output sits at Ib × 1 MΩ instead of 0 V."""
    s, comps = op(split(15.0, ("resistor", ("0", "fb"), {"resistance": 1e6}),
                        ("opamp", ("fb", "0", "out", "vp", "vn"), {"model": model}),
                        ("resistor", ("out", "fb"), {"resistance": 1e6})))
    assert vnet(s, comps[3], "out") == pytest.approx(ib * 1e6, rel=0.1, abs=1e-4)


@pytest.mark.parametrize("model", list(CH.OPAMPS))
def test_supply_current_with_no_load(model):
    s, comps = op(split(9.0, ("opamp", ("out", "0", "out", "vp", "vn"), {"model": model})))
    i_supply = -s.device(comps[0].id).i_pins[0]
    assert i_supply == pytest.approx(CH.OPAMPS[model].iq, rel=0.05)


def test_load_current_comes_from_the_supply_pins():
    """Sourcing 5 mA into a load: the + supply provides it (plus the chip's own supply current)."""
    s, comps = op(split(15.0, ("dc_supply", ("in", "0"), {"voltage": 5.0}),
                        ("opamp", ("out", "in", "out", "vp", "vn"), {"model": "741"}),
                        ("resistor", ("out", "0"), {"resistance": 1e3})))
    i_pos = -s.device(comps[0].id).i_pins[0]      # out of the + supply's + terminal
    i_neg = s.device(comps[1].id).i_pins[1]       # into the − supply's − terminal (from the op-amp's V− pin)
    assert i_pos == pytest.approx(5e-3 + 1.7e-3, rel=0.02)
    assert i_neg == pytest.approx(1.7e-3, rel=0.05)


@pytest.mark.parametrize("model,gbw", [("741", 1e6), ("TL071", 3e6)])
def test_closed_loop_bandwidth(model, gbw):
    """A gain-of-11 amplifier rolls off at GBW / 11: at that frequency the gain is down to 11/√2."""
    f = gbw / 11
    c, comps = build(split(15.0, ("signal_gen", ("in", "0"), {"waveform": "Senoidal", "frequency": f,
                                                              "amplitude": 0.01, "offset": 0}),
                           ("opamp", ("fb", "in", "out", "vp", "vn"), {"model": model}),
                           ("resistor", ("out", "fb"), {"resistance": 10e3}),
                           ("resistor", ("fb", "0"), {"resistance": 1e3})))
    s = Simulator(c)
    tr = s.transient(12 / f, 1 / f / 200, lambda sim: vnet(sim, comps[3], "out"))
    late = [vv for t, vv in tr if t > 8 / f]
    amp = (max(late) - min(late)) / 2
    assert amp == pytest.approx(0.01 * 11 / math.sqrt(2), rel=0.08)


def test_too_much_supply_voltage_destroys_it():
    c, comps = build([("dc_supply", ("vp", "0"), {"voltage": 45}),
                      ("opamp", ("out", "0", "out", "vp", "0"), {"model": "LM358"})])
    s = Simulator(c)
    s.h_max = 1e-3
    s.run_until(0.2)
    assert s.device(comps[1].id).blown
    assert any("32 V como máximo" in text for _cid, text in s.take_events())
