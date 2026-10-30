"""Parts added in 1.3.0 (requested by users): TL431/TLV431 shunt regulators, the TLP3122A solid-state relay,
the 4051 analogue switch, 74HC164/165/595/597 shift registers and the 2N7002 — checked against their
datasheets and truth tables."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from test_sim import build, op  # noqa: E402

from wirely.model import parts as P  # noqa: E402
from wirely.model.types_info import TYPE_INFO  # noqa: E402
from wirely.sim.engine import Simulator  # noqa: E402


# ------------------------------------------------------------------------------------------- TL431 / TLV431
@pytest.mark.parametrize("model,vin,vref", [("TL431", 12, 2.495), ("TLV431", 5, 1.24)])
def test_shunt_ref_as_a_fixed_reference(model, vin, vref):
    """REF tied to K, fed through a resistor: the cathode sits at Vref (plus a whisker for its 0.2 Ω)."""
    s, comps = op([("dc_supply", ("v", "0"), {"voltage": vin}),
                   ("resistor", ("v", "k"), {"resistance": 1000}),
                   ("shunt_ref", ("k", "0", "k"), {"model": model})])
    vk = s.pin_voltage(comps[2].id, "K")
    assert vk == pytest.approx(vref, abs=0.005)


def test_tl431_sets_any_voltage_with_two_resistors():
    """Vout = 2.495 × (1 + R1/R2) (+ Iref × R1): 10 k / 10 k gives about 5 V."""
    s, comps = op([("dc_supply", ("v", "0"), {"voltage": 12}),
                   ("resistor", ("v", "k"), {"resistance": 470}),
                   ("resistor", ("k", "r"), {"resistance": 10e3}),
                   ("resistor", ("r", "0"), {"resistance": 10e3}),
                   ("shunt_ref", ("k", "0", "r"), {"model": "TL431"})])
    assert s.pin_voltage(comps[4].id, "K") == pytest.approx(2.495 * 2 + 2e-6 * 10e3, rel=0.01)


def test_shunt_ref_off_below_its_reference():
    s, comps = op([("dc_supply", ("v", "0"), {"voltage": 5}),
                   ("resistor", ("v", "k"), {"resistance": 1000}),
                   ("dc_supply", ("r", "0"), {"voltage": 1.0}),
                   ("shunt_ref", ("k", "0", "r"), {"model": "TL431"})])
    assert s.pin_voltage(comps[3].id, "K") == pytest.approx(5.0, abs=0.01)     # sinks (almost) nothing


def test_shunt_ref_burns_out_without_enough_series_resistance():
    c, comps = build([("dc_supply", ("v", "0"), {"voltage": 12}),
                      ("resistor", ("v", "k"), {"resistance": 47, "power": 10}),
                      ("shunt_ref", ("k", "0", "k"), {"model": "TL431"})])
    s = Simulator(c)
    s.h_max = 1e-3
    s.run_until(0.3)
    assert s.device(comps[2].id).blown
    assert any("TL431 puede absorber" in t for _c, t in s.take_events())


def test_tlv431_destroyed_above_6v():
    c, comps = build([("dc_supply", ("v", "0"), {"voltage": 12}),
                      ("resistor", ("v", "k"), {"resistance": 1000}),
                      ("shunt_ref", ("k", "0", "0"), {"model": "TLV431"})])
    s = Simulator(c)
    s.h_max = 1e-3
    s.run_until(0.05)
    assert s.device(comps[2].id).blown


# ------------------------------------------------------------------------------------------- solid-state relay
def ssr_circuit(load_v=24, r_load=24, r_led=1000):
    return build([("dc_supply", ("vin", "0"), {"voltage": 5}),
                  ("switch", ("vin", "s"), {"closed": False}),
                  ("resistor", ("s", "a"), {"resistance": r_led}),
                  ("ssr", ("a", "0", "o1", "g2"), {"model": "TLP3122A"}),
                  ("dc_supply", ("vl", "g2"), {"voltage": load_v}),
                  ("resistor", ("vl", "o1"), {"resistance": r_load, "power": 50})])


def test_ssr_switches_a_load_on_its_own_supply_after_a_millisecond():
    c, comps = ssr_circuit()
    s = Simulator(c)
    s.h_max = 1e-4
    s.run_until(0.01)
    k = s.device(comps[3].id)
    assert abs(k.i_pins[2]) < 1e-6                          # off
    s.set_value(comps[1].id, "closed", True)
    s.run_until(0.0102)
    assert abs(k.i_pins[2]) < 0.5                           # not on yet: it takes about a millisecond
    s.run_until(0.015)
    i = abs(k.i_pins[2])
    assert i == pytest.approx(24 / (24 + 0.15), rel=0.01)  # on: 1 A, with 0.15 Ω inside
    s.set_value(comps[1].id, "closed", False)
    s.run_until(0.02)
    assert abs(k.i_pins[2]) < 1e-3                          # and off again


def test_ssr_works_with_the_load_supply_either_way_round():
    """Two MOSFETs back to back: it switches AC or DC, so the output polarity doesn't matter."""
    c, comps = build([("dc_supply", ("vin", "0"), {"voltage": 5}),
                      ("resistor", ("vin", "a"), {"resistance": 1000}),
                      ("ssr", ("a", "0", "o1", "g2"), {"model": "TLP3122A"}),
                      ("dc_supply", ("g2", "vl"), {"voltage": 12}),          # reversed
                      ("resistor", ("vl", "o1"), {"resistance": 120, "power": 5})])
    s = Simulator(c)
    s.h_max = 1e-4
    s.run_until(0.02)
    assert abs(s.device(comps[2].id).i_pins[2]) == pytest.approx(0.1, rel=0.01)


def test_ssr_led_without_a_resistor_pops():
    c, comps = ssr_circuit(r_led=0.01)
    s = Simulator(c)
    s.h_max = 1e-4
    s.set_value(comps[1].id, "closed", True)
    s.run_until(0.05)
    assert s.device(comps[3].id).blown


# ------------------------------------------------------------------------------------------- 4051 mux
def mux(model, cba, inh=0.0, vsupply=5.0):
    spec = [("dc_supply", ("vcc", "0"), {"voltage": vsupply}),
            ("resistor", ("vcc", "y5"), {"resistance": 1e-3}),
            ("resistor", ("com", "0"), {"resistance": 10e3})]
    for name, bit in zip("ABC", (cba & 1, cba >> 1 & 1, cba >> 2 & 1)):
        spec.append(("dc_supply", (name.lower(), "0"), {"voltage": vsupply * bit}))
    spec.append(("dc_supply", ("inh", "0"), {"voltage": inh}))
    nets = ["com", "a", "b", "c", "inh"] + [("y5" if i == 5 else f"y{i}") for i in range(8)]
    spec.append(("mux4051", tuple(nets), {"model": model}))
    s, comps = op(spec)
    return s.pin_voltage(comps[-1].id, "COM")


@pytest.mark.parametrize("model,ron", [("CD4051B", 470.0), ("74HC4051", 96.5)])
def test_mux_connects_the_selected_channel_through_its_on_resistance(model, ron):
    vcom = mux(model, 0b101)
    assert vcom == pytest.approx(5.0 * 10e3 / (10e3 + ron), rel=0.005)


def test_mux_other_channel_or_inhibit_is_off():
    assert mux("CD4051B", 0b100) < 1e-3          # channel 4 picked: Y5 not connected
    assert mux("CD4051B", 0b101, inh=5.0) < 1e-3  # INH high: everything off


def test_cd4051_resistance_falls_at_higher_supply():
    assert mux("CD4051B", 0b101, vsupply=15.0) / 15.0 == pytest.approx(10e3 / (10e3 + 125), rel=0.005)


# ------------------------------------------------------------------------------------------- shift registers
class Bench:
    """Drives a chip's inputs from 5 V sources and reads its outputs."""

    def __init__(self, kind, inputs, outputs, extra=()):
        spec = [("dc_supply", ("vcc", "0"), {"voltage": 5.0})]
        self.src = {}
        for name in inputs:
            spec.append(("dc_supply", (f"in_{name}", "0"), {"voltage": 0.0}))
            self.src[name] = len(spec) - 1
        for name in outputs:
            spec.append(("resistor", (f"out_{name}", "0"), {"resistance": 100e3}))
        pins = [n for n, _x, _y in P.PARTS[kind].pins]
        nets = [f"in_{n}" if n in inputs else f"out_{n}" if n in outputs else f"nc_{n}" for n in pins]
        spec.append((kind, tuple(nets), dict(extra)))
        c, self.comps = build(spec)
        self.chip = self.comps[-1]
        self.s = Simulator(c)
        self.s.h_max = 1e-5
        self.s.run_until(1e-4)

    def set(self, name, high):
        self.s.set_value(self.comps[self.src[name]].id, "voltage", 5.0 if high else 0.0)
        self.s.run_until(self.s.t + 1e-4)

    def pulse(self, name):
        self.set(name, True)
        self.set(name, False)

    def get(self, name):
        return self.s.pin_voltage(self.chip.id, name) > 2.5

    def volts(self, name):
        return self.s.pin_voltage(self.chip.id, name)


def test_74hc164_shifts_bits_along():
    b = Bench("sr164", ["DSA", "DSB", "CP", "MR"], [f"Q{i}" for i in range(8)])
    b.set("MR", True)
    b.set("DSB", True)
    for bit in (1, 0, 1, 1):
        b.set("DSA", bool(bit))
        b.pulse("CP")
    assert [b.get(f"Q{i}") for i in range(4)] == [True, True, False, True]     # newest bit in Q0
    b.set("MR", False)
    assert not any(b.get(f"Q{i}") for i in range(8))                          # MR low clears it


def test_74hc595_latches_and_switches_its_outputs_off():
    b = Bench("sr595", ["DS", "SHCP", "STCP", "MR", "OE"], [f"Q{i}" for i in range(8)] + ["Q7S"])
    b.set("MR", True)
    pattern = [1, 0, 1, 1, 0, 0, 1, 0]          # sent Q7's bit first
    for bit in pattern:
        b.set("DS", bool(bit))
        b.pulse("SHCP")
    assert not any(b.get(f"Q{i}") for i in range(8))      # nothing shows until the latch clock
    b.pulse("STCP")
    assert [b.get(f"Q{7 - i}") for i in range(8)] == [bool(x) for x in pattern]
    assert b.get("Q7S") == bool(pattern[0])
    b.set("OE", True)                                     # outputs off: they float (pulled to 0 V by the load)
    assert b.volts("Q7") < 0.1
    b.set("OE", False)
    assert b.get("Q7")


def test_74hc165_loads_in_parallel_and_shifts_out():
    data = [1, 1, 0, 1, 0, 0, 1, 0]            # D0 … D7
    b = Bench("sr165", [f"D{i}" for i in range(8)] + ["DS", "CP", "CE", "PL"], ["Q7", "Q7N"])
    for i, bit in enumerate(data):
        b.set(f"D{i}", bool(bit))
    b.set("PL", False)                          # load (no clock needed)
    b.set("PL", True)
    got = []
    for _ in range(8):
        got.append(int(b.get("Q7")))
        assert b.get("Q7N") != b.get("Q7")
        b.pulse("CP")
    assert got == list(reversed(data))          # D7 comes out first


def test_74hc597_latches_inputs_then_shifts_out():
    data = [0, 1, 1, 0, 1, 0, 0, 1]
    b = Bench("sr597", [f"D{i}" for i in range(8)] + ["DS", "SHCP", "STCP", "PL", "MR"], ["Q7"])
    b.set("MR", True)
    for i, bit in enumerate(data):
        b.set(f"D{i}", bool(bit))
    b.pulse("STCP")                             # capture the inputs
    for i in range(8):
        b.set(f"D{i}", False)                   # … the inputs can change now: the latch keeps them
    b.set("PL", False)
    b.set("PL", True)                           # copy the latch into the shift register
    got = []
    for _ in range(8):
        got.append(int(b.get("Q7")))
        b.pulse("SHCP")
    assert got == list(reversed(data))


def test_74hc_chip_on_9v_warns_it_would_be_damaged():
    c, comps = build([("battery", ("v", "0"), {"voltage": 9}),
                      ("sr164", ("v", "v", "0", "v") + tuple(f"q{i}" for i in range(8)), {})])
    s = Simulator(c)
    s.h_max = 1e-3
    s.run_until(0.01)
    assert any("se dañaría" in t for _c, t in s.take_events())


# ------------------------------------------------------------------------------------------- type descriptions
def test_every_part_type_has_a_description():
    missing = [ch for d in P.PARTS.values() for p in d.props if p.key == "model" for ch in p.choices
               if ch not in TYPE_INFO]
    assert not missing


def test_properties_box_explains_the_type(qapp=None):
    from PySide6.QtWidgets import QApplication

    from wirely.model.circuit import Circuit
    from wirely.ui.dialogs import PropertiesDialog
    QApplication.instance() or QApplication([])
    c = Circuit()
    q = c.add("nmos", 0, 0, props={"model": "AO3400"})
    d = PropertiesDialog(q, c)
    assert "2N7002" in d.type_info.text()        # explains why you'd pick it over a 2N7002
    d.fields["model"][1].setCurrentText("2N7002")
    assert "SOT-23" in d.type_info.text()
