"""The optoisolator (optocoupler): an infrared LED driving a phototransistor, with the two sides isolated."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from test_sim import NGSPICE, build, ngspice_op, vnet  # noqa: E402

from wirely.sim import chips as CH  # noqa: E402
from wirely.sim.engine import Simulator  # noqa: E402


def opto_circuit(r_led, r_load, model="PC817", v_in=5.0, v_out=10.0, closed=True):
    """Input side: battery – switch – resistor – opto LED.  Output side: its own battery – load – C–E.
    The output side has its own negative ("g2"), not joined to the input side at all."""
    return build([("battery", ("vin", "0"), {"voltage": v_in}),
                  ("switch", ("vin", "sw"), {"closed": closed}),
                  ("resistor", ("sw", "a"), {"resistance": r_led}),
                  ("optocoupler", ("a", "0", "c", "g2"), {"model": model}),
                  ("battery", ("vout", "g2"), {"voltage": v_out}),
                  ("resistor", ("vout", "c"), {"resistance": r_load})])


def test_led_drops_about_1v2_and_output_follows_the_ctr():
    c, comps = opto_circuit(r_led=330, r_load=100)
    s = Simulator(c)
    s.dc()
    u = s.device(comps[3].id)
    i_led = u.i_led
    assert 1.05 < u.vd < 1.35                              # infrared LED forward voltage
    assert i_led == pytest.approx((5 - u.vd) / 330, rel=0.02)
    ctr = CH.OPTOS["PC817"][0]
    i_c = u.i_pins[2]
    assert i_c == pytest.approx(ctr * i_led, rel=0.05)     # 100 Ω load: not saturated, Ic = CTR × If
    assert u.i_pins[2] + u.i_pins[3] == pytest.approx(0, abs=1e-12)   # what goes in at C comes out at E


def test_saturates_like_a_switch_with_a_big_load_resistor():
    c, comps = opto_circuit(r_led=330, r_load=10e3)
    s = Simulator(c)
    s.dc()
    vce = s.pin_voltage(comps[3].id, "C") - s.pin_voltage(comps[3].id, "E")
    assert vce < 0.3                                       # fully on
    assert s.device(comps[5].id).i_pins[0] == pytest.approx((10 - vce) / 10e3, rel=0.01)


def test_off_when_the_led_is_off():
    c, comps = opto_circuit(r_led=330, r_load=10e3, closed=False)
    s = Simulator(c)
    s.dc()
    u = s.device(comps[3].id)
    assert abs(u.i_pins[2]) < 1e-6
    vce = s.pin_voltage(comps[3].id, "C") - s.pin_voltage(comps[3].id, "E")
    assert vce == pytest.approx(10, abs=0.01)


def test_switch_while_running_and_the_two_sides_stay_isolated():
    c, comps = opto_circuit(r_led=470, r_load=1e3, closed=False)
    s = Simulator(c)
    s.h_max = 1e-3
    s.run_until(0.01)
    assert abs(s.device(comps[3].id).i_pins[2]) < 1e-6
    s.set_value(comps[1].id, "closed", True)
    s.run_until(0.02)
    u = s.device(comps[3].id)
    assert u.i_pins[2] > 5e-3                               # output switched on
    # no current crosses between the sides: each side's battery supplies only its own side
    assert s.device(comps[0].id).i_pins[0] == pytest.approx(-u.i_led, rel=1e-3)
    assert s.device(comps[4].id).i_pins[0] == pytest.approx(-u.i_pins[2], rel=1e-3)


def test_led_without_a_resistor_pops():
    c, comps = build([("battery", ("vin", "0"), {"voltage": 5}),
                      ("optocoupler", ("vin", "0", "c", "0"), {"model": "4N25"}),
                      ("resistor", ("c", "0"), {"resistance": 1e3})])
    s = Simulator(c)
    s.h_max = 1e-3
    s.run_until(0.2)
    u = s.device(comps[1].id)
    assert u.blown
    assert any("reventó" in text for _cid, text in s.take_events())


def test_darlington_type_has_more_gain():
    vals = {}
    for model in ("4N25", "6N139"):
        c, comps = opto_circuit(r_led=4.7e3, r_load=10, model=model)
        s = Simulator(c)
        s.dc()
        vals[model] = s.device(comps[3].id).i_pins[2]
    assert vals["6N139"] > 5 * vals["4N25"]


@pytest.mark.skipif(not NGSPICE, reason="ngspice not installed")
def test_against_ngspice():
    """The same model built from ngspice parts: a diode, a current-controlled current source and an NPN."""
    ctr = CH.OPTOS["PC817"][0]
    bf = 400.0
    net = f"""* optocoupler
V1 vin 0 5
R1 vin a 1k
D1 a k IRLED
Vs k 0 0
F1 c b Vs {ctr / bf}
Q1 c b g2 QP
V2 vout g2 12
R2 vout c 2.2k
Rref g2 0 1e9
.model IRLED D(IS={CH.OPTO_IS:.6e} N={CH.OPTO_N} RS={CH.OPTO_RS})
.model QP NPN(IS=1e-14 BF={bf} BR=5)
.options gmin=1e-12
"""
    ref = ngspice_op(net, ["v(a)", "v(c,g2)", "i(Vs)"])
    c, comps = build([("dc_supply", ("vin", "0"), {"voltage": 5}),
                      ("resistor", ("vin", "a"), {"resistance": 1e3}),
                      ("optocoupler", ("a", "0", "c", "g2"), {"model": "PC817"}),
                      ("dc_supply", ("vout", "g2"), {"voltage": 12}),
                      ("resistor", ("vout", "c"), {"resistance": 2.2e3})])
    s = Simulator(c)
    s.dc()
    u = s.device(comps[2].id)
    assert vnet(s, u.comp, "A") - vnet(s, u.comp, "K") == pytest.approx(ref["v(a)"], rel=3e-3)
    assert u.i_led == pytest.approx(ref["i(Vs)"], rel=3e-3)
    vce = vnet(s, u.comp, "C") - vnet(s, u.comp, "E")
    assert vce == pytest.approx(ref["v(c,g2)"], rel=0.03, abs=0.02)


def test_supply_type_on_the_isolated_side_does_not_matter():
    """Regression: the isolated output side needs its own 0 V reference (it used to float)."""
    for k2 in ("battery", "dc_supply", "cell"):
        c, comps = build([("dc_supply", ("vin", "0"), {"voltage": 5}),
                          ("resistor", ("vin", "a"), {"resistance": 1e3}),
                          ("optocoupler", ("a", "0", "c", "g2"), {"model": "PC817"}),
                          (k2, ("vout", "g2"), {"voltage": 12}),
                          ("resistor", ("vout", "c"), {"resistance": 2.2e3})])
        s = Simulator(c)
        s.dc()
        assert s.device(comps[2].id).i_pins[2] > 4e-3


def test_relay_contacts_on_a_separate_supply():
    """A relay switching a lamp on its own, separate battery (coil side and contact side not joined)."""
    c, comps = build([("dc_supply", ("v", "0"), {"voltage": 12}),
                      ("switch", ("v", "s"), {"closed": True}),
                      ("relay", ("s", "0", "com", "nc", "no"), {"voltage": 12}),
                      ("dc_supply", ("v2", "g2"), {"voltage": 24}),
                      ("resistor", ("v2", "com"), {"resistance": 10, "power": 5.0}),
                      ("lamp", ("no", "g2"), {"voltage": 24, "power": 5})])
    s = Simulator(c)
    s.h_max = 1e-3
    s.run_until(0.5)
    assert s.device(comps[2].id).on
    assert s.device(comps[5].id).glow() > 0.3
