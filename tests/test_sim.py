"""Tests for the circuit solver against answers worked out by hand (and, where ngspice is installed, against
ngspice itself running the same models).  Run:  python -m pytest tests"""
import math
import os
import re
import shutil
import subprocess
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wirely.model.circuit import Circuit
from wirely.sim import devices as D
from wirely.sim.engine import Simulator


# ----------------------------------------------------------------------------------------- helpers
def build(spec):
    """Make a real drawn circuit from a list of (kind, (net, net, …), props).

    Every pin gets its own wire: straight up (or down) to a private lane far from the parts, then along to
    its net's own vertical bus line. Lanes and buses only cross each other (never touch), so the only
    connections are the ones asked for."""
    c = Circuit()
    comps = []
    net_x = {}
    bus = {}
    k = 0
    for col, (kind, nets, props) in enumerate(spec):
        comp = c.add(kind, col * 3000, 0, props=props)
        comps.append(comp)
        names = [n for n, _x, _y in comp.part.pins]
        assert len(names) == len(nets), (kind, names)
        for name, net in zip(names, nets):
            k += 1
            x0 = net_x.setdefault(net, 100000 + 100 * len(net_x))
            px, py = comp.pin_positions()[name]
            dx, dy = px - comp.x, py - comp.y
            lane = -1000 - 20 * k if py <= 0 else 1000 + 20 * k
            if abs(dx) >= abs(dy) and dx != 0:
                # side pin: first step straight out sideways (each by its own amount), then up/down
                xs = px + (10 + 10 * k) * (1 if dx > 0 else -1)
                c.add_wire([(px, py), (xs, py), (xs, lane), (x0, lane)])
            else:
                c.add_wire([(px, py), (px, lane), (x0, lane)])
            bus.setdefault(net, []).append(lane)
    for net, ys in bus.items():
        x0 = net_x[net]
        if net == "0":
            c.add("ground", x0, -5000)
            ys = ys + [-5000]
        if len(ys) > 1:
            c.add_wire([(x0, min(ys)), (x0, max(ys))])
    return c, comps


def op(spec):
    c, comps = build(spec)
    s = Simulator(c)
    s.dc()
    return s, comps


def vnet(s, comp, pin):
    return s.pin_voltage(comp.id, pin)


# ----------------------------------------------------------------------------------------- the builder works
def test_builder_makes_the_nets_we_asked_for():
    c, comps = build([("battery", ("a", "0"), {}), ("resistor", ("a", "b"), {}), ("resistor", ("b", "0"), {})])
    names = {}
    for net in c.nets():
        for cid, pin in net.pins:
            names[(cid, pin)] = net
    b, r1, r2 = comps
    assert names[(b.id, "+")] is names[(r1.id, "1")]
    assert names[(r1.id, "2")] is names[(r2.id, "1")]
    assert names[(r2.id, "2")] is names[(b.id, "-")]
    assert len(c.nets()) == 3


# ----------------------------------------------------------------------------------------- resistive circuits
def test_voltage_divider():
    s, (b, r1, r2) = op([("dc_supply", ("a", "0"), {"voltage": 9}), ("resistor", ("a", "m"), {"resistance": 10e3}),
                        ("resistor", ("m", "0"), {"resistance": 4.7e3})])
    expected = 9 * 4.7e3 / (14.7e3 + D.R_INT["dc_supply"])
    assert vnet(s, r2, "1") == pytest.approx(expected, rel=1e-6)


def test_potentiometer_quarter_way():
    s, (b, pot) = op([("dc_supply", ("a", "0"), {"voltage": 10}),
                      ("potentiometer", ("a", "0", "w"), {"resistance": 10e3, "setting": 25})])
    assert vnet(s, pot, "wiper") == pytest.approx(7.5, rel=1e-3)


def test_battery_internal_resistance_and_short_circuit_warning():
    s, (b, r) = op([("battery", ("a", "0"), {"voltage": 9}), ("resistor", ("a", "0"), {"resistance": 0.001})])
    i = s.device(r.id).i_pins[0]
    assert i == pytest.approx(9 / (1.5 + 0.001), rel=1e-3)
    assert s.device(b.id).warn == "short"


def test_circuit_without_a_0V_symbol_uses_battery_negative():
    c = Circuit()
    bt = c.add("battery", 0, 0, props={"voltage": 6})
    r = c.add("resistor", 200, 0, props={"resistance": 100})
    c.add_wire([bt.pin_positions()["+"], (-30, -60), (170, -60), r.pin_positions()["1"]])
    c.add_wire([bt.pin_positions()["-"], (30, 60), (230, 60), r.pin_positions()["2"]])
    s = Simulator(c)
    s.dc()
    assert s.pin_voltage(bt.id, "-") == 0.0
    assert s.pin_voltage(bt.id, "+") == pytest.approx(6 * 100 / 101.5, rel=1e-6)


def test_open_switch_no_current_closed_switch_current():
    s, (b, sw, r) = op([("dc_supply", ("a", "0"), {"voltage": 5}), ("switch", ("a", "b"), {"closed": False}),
                        ("resistor", ("b", "0"), {"resistance": 1000})])
    assert abs(s.device(r.id).i_pins[0]) < 1e-8
    s.set_value(sw.id, "closed", True)
    s.dc()
    assert s.device(r.id).i_pins[0] == pytest.approx(5 / 1000.03, rel=1e-3)


def test_ammeter_and_voltmeter_read_correctly():
    s, (b, am, r, vm) = op([("dc_supply", ("a", "0"), {"voltage": 12}), ("ammeter", ("a", "b"), {}),
                            ("resistor", ("b", "0"), {"resistance": 240}), ("voltmeter", ("b", "0"), {})])
    assert s.device(am.id).reading()[0] == pytest.approx(0.05, rel=1e-3)
    assert s.device(vm.id).reading()[0] == pytest.approx(12.0, rel=1e-3)


# ----------------------------------------------------------------------------------------- diodes and LEDs
def solve_diode_series(V, R, Is, n, Rs):
    """Independent answer: bisection on V = I(R+Rs) + n·Vt·ln(I/Is + 1)."""
    lo, hi = 0.0, V / R
    for _ in range(200):
        i = (lo + hi) / 2
        if i * (R + Rs) + n * D.VT * math.log(i / Is + 1) > V:
            hi = i
        else:
            lo = i
    return (lo + hi) / 2


@pytest.mark.parametrize("model", ["1N4001", "1N4148"])
def test_diode_forward_current_matches_shockley_equation(model):
    s, (b, r, d) = op([("dc_supply", ("a", "0"), {"voltage": 5}), ("resistor", ("a", "k"), {"resistance": 470}),
                       ("diode", ("k", "0"), {"model": model})])
    Is, n, Rs, _ = D.DIODES[model]
    expected = solve_diode_series(5, 470 + D.R_INT["dc_supply"], Is, n, Rs)
    assert s.device(d.id).current == pytest.approx(expected, rel=1e-5)
    assert 0.55 < s.device(d.id).vd < 0.85


def test_diode_blocks_backwards():
    s, (b, r, d) = op([("dc_supply", ("a", "0"), {"voltage": 5}), ("resistor", ("a", "k"), {"resistance": 470}),
                       ("diode", ("0", "k"), {})])
    assert abs(s.device(d.id).current) < 1e-6


@pytest.mark.parametrize("colour,vf", [("Rojo", 1.95), ("Verde", 2.15), ("Azul", 3.1)])
def test_led_current_with_resistor(colour, vf):
    s, (b, r, led) = op([("dc_supply", ("a", "0"), {"voltage": 9}), ("resistor", ("a", "k"), {"resistance": 470}),
                         ("led", ("k", "0"), {"colour": colour})])
    d = s.device(led.id)
    expected = solve_diode_series(9, 470 + 0.02, D.led_is(colour), D.LED_N, D.LED_RS)
    assert d.current == pytest.approx(expected, rel=1e-5)
    # sanity: about (9 − Vf) / 470 and a sensible forward voltage
    assert d.current == pytest.approx((9 - vf) / 470, rel=0.05)
    assert vf - 0.15 < d.vd < vf + 0.05
    assert d.glow() > 0.5 and not d.blown


def test_led_without_resistor_pops():
    c, (b, led) = build([("battery", ("a", "0"), {"voltage": 9}), ("led", ("a", "0"), {})])
    s = Simulator(c)
    s.run_until(0.2)
    d = s.device(led.id)
    assert d.blown
    ev = s.take_events()
    assert any("reventó" in m for _cid, m in ev)
    assert abs(d.i_pins[0]) < 1e-6          # once popped, no current


def test_zener_regulates():
    s, (b, r, z) = op([("dc_supply", ("a", "0"), {"voltage": 12}), ("resistor", ("a", "k"), {"resistance": 1000}),
                       ("zener", ("0", "k"), {"voltage": 5.1})])
    assert vnet(s, r, "2") == pytest.approx(5.1, abs=0.15)


# ----------------------------------------------------------------------------------------- transistors
def test_npn_active_region_gain():
    # base fed with a known small current: Ic should be about BF × Ib
    s, (b, rb, rc, q) = op([("dc_supply", ("a", "0"), {"voltage": 9}),
                            ("resistor", ("a", "bb"), {"resistance": 1e6}),
                            ("resistor", ("a", "cc"), {"resistance": 1000}),
                            ("npn", ("bb", "cc", "0"), {"model": "BC548"})])
    d = s.device(q.id)
    vbe = vnet(s, q, "B")
    ib_expected = (9 - vbe) / 1e6
    _, Is, bf, br, _, _ = D.BJTS["BC548"]
    assert d.ib == pytest.approx(ib_expected, rel=1e-3)
    vbc = vbe - vnet(s, q, "C")
    ic_formula = Is * (math.exp(vbe / D.VT) - math.exp(vbc / D.VT)) - Is / br * (math.exp(vbc / D.VT) - 1)
    assert d.ic == pytest.approx(ic_formula, rel=1e-4)
    assert d.ic == pytest.approx(bf * d.ib, rel=0.02)
    assert 0.55 < vbe < 0.75


def test_npn_switch_saturates():
    s, (b, rb, rc, q) = op([("dc_supply", ("a", "0"), {"voltage": 9}),
                            ("resistor", ("a", "bb"), {"resistance": 4700}),
                            ("resistor", ("a", "cc"), {"resistance": 470}),
                            ("npn", ("bb", "cc", "0"), {"model": "BC548"})])
    vce = vnet(s, q, "C")
    assert vce < 0.2
    assert s.device(q.id).ic == pytest.approx((9 - vce) / 470, rel=0.01)


def test_pnp_switch_mirror_of_npn():
    s, (b, rb, rc, q) = op([("dc_supply", ("a", "0"), {"voltage": 9}),
                            ("resistor", ("bb", "0"), {"resistance": 4700}),
                            ("resistor", ("cc", "0"), {"resistance": 470}),
                            ("pnp", ("bb", "cc", "a"), {"model": "BC558"})])
    assert vnet(s, q, "C") > 8.8
    assert s.device(q.id).ic < -0.017       # current flows out of the collector


def test_night_light_example_turns_on_in_the_dark():
    path = os.path.join(os.path.dirname(__file__), "..", "examples", "Luz nocturna.wirely")
    c = Circuit.load(path)
    ldr = next(x for x in c.components.values() if x.kind == "ldr")
    led = next(x for x in c.components.values() if x.kind == "led")
    for lux, on in ((1, True), (500, False)):
        ldr.props["light"] = lux
        s = Simulator(c)
        s.dc()
        assert (s.device(led.id).current > 5e-3) == on, (lux, s.device(led.id).current)


# ----------------------------------------------------------------------------------------- time: capacitors
def rc_circuit(R=1000, C=100e-6, V=9):
    c, comps = build([("dc_supply", ("a", "0"), {"voltage": V}), ("switch", ("a", "b"), {"closed": False}),
                      ("resistor", ("b", "k"), {"resistance": R}), ("capacitor", ("k", "0"), {"capacitance": C})])
    return c, comps


def test_rc_charging_curve():
    R, C, V = 1000, 100e-6, 9.0
    c, (b, sw, r, cap) = rc_circuit(R, C, V)
    s = Simulator(c)
    s.set_value(sw.id, "closed", True)
    tau = (R + 0.01 + 0.02) * C
    trace = s.transient(5 * tau, tau / 20, lambda sim: sim.pin_voltage(cap.id, "1"))
    worst = 0.0
    for t, vc in trace:
        if t > 0:
            expected = V * (1 - math.exp(-t / tau))
            worst = max(worst, abs(vc - expected))
    assert worst < 0.005 * V, worst          # within 0.5 % of the supply everywhere on the curve
    assert trace[-1][1] == pytest.approx(V * (1 - math.exp(-5)), abs=0.02)


def test_rc_discharge_after_switch_opens():
    R, C, V = 2200, 47e-6, 6.0
    c, comps = build([("dc_supply", ("a", "0"), {"voltage": V}), ("spdt", ("k2", "a", "0"), {"position": "A"}),
                      ("resistor", ("k2", "k"), {"resistance": R}), ("capacitor", ("k", "0"), {"capacitance": C})])
    b, sw, r, cap = comps
    s = Simulator(c)
    tau = R * C
    s.h_max = tau / 20
    s.run_until(10 * tau)                     # fully charged
    assert s.pin_voltage(cap.id, "1") == pytest.approx(V, rel=1e-3)
    s.set_value(sw.id, "position", "B")       # now discharge through the resistor
    t0 = s.t
    trace = s.transient(t0 + 3 * tau, tau / 20, lambda sim: sim.pin_voltage(cap.id, "1"))
    for t, vc in trace[1:]:
        expected = V * math.exp(-(t - t0) / (R * C))
        assert vc == pytest.approx(expected, abs=0.005 * V)


def test_capacitor_blocks_dc_in_steady_state():
    c, (b, sw, r, cap) = rc_circuit()
    s = Simulator(c)
    s.set_value(sw.id, "closed", True)
    s.run_until(2.0)
    assert abs(s.device(r.id).i_pins[0]) < 1e-5


def test_led_fades_as_capacitor_discharges_through_it():
    """Capacitor charged to 9 V, then switched across an LED + resistor: the LED current decays."""
    c, comps = build([("dc_supply", ("a", "0"), {"voltage": 9}), ("spdt", ("k", "a", "x"), {"position": "A"}),
                      ("electrolytic", ("k", "0"), {"capacitance": 1000e-6}),
                      ("resistor", ("x", "y"), {"resistance": 220}), ("led", ("y", "0"), {})])
    b, sw, cap, r, led = comps
    s = Simulator(c)
    s.run_until(0.5)
    s.set_value(sw.id, "position", "B")
    s.run_until(0.6)
    i1 = s.device(led.id).current
    s.run_until(1.2)
    i2 = s.device(led.id).current
    assert i1 > 0.01 and 0 < i2 < i1


def test_half_wave_rectifier_peak():
    c, comps = build([("ac_supply", ("a", "0"), {"voltage": 10, "frequency": 50}),
                      ("diode", ("a", "k"), {"model": "1N4001"}), ("resistor", ("k", "0"), {"resistance": 1000})])
    b, d, r = comps
    s = Simulator(c)
    trace = s.transient(0.04, 1e-4, lambda sim: sim.pin_voltage(r.id, "1"))
    vmax = max(vv for _t, vv in trace)
    vmin = min(vv for _t, vv in trace)
    assert 9.0 < vmax < 9.5          # 10 V peak minus a diode drop
    assert vmin > -0.01              # nothing gets through backwards


def test_electrolytic_backwards_pops():
    c, comps = build([("dc_supply", ("a", "0"), {"voltage": 9}), ("resistor", ("a", "k"), {"resistance": 100}),
                      ("electrolytic", ("0", "k"), {"capacitance": 10e-6})])
    s = Simulator(c)
    s.run_until(0.5)
    assert s.device(comps[2].id).blown


def test_fuse_blows_on_short():
    c, comps = build([("dc_supply", ("a", "0"), {"voltage": 9}), ("fuse", ("a", "k"), {"rating": 1.0}),
                      ("resistor", ("k", "0"), {"resistance": 1.0})])
    s = Simulator(c)
    s.run_until(0.1)
    assert s.device(comps[1].id).blown
    assert abs(s.device(comps[2].id).i_pins[0]) < 1e-6


def test_real_time_speed():
    """The night light must simulate much faster than real time."""
    path = os.path.join(os.path.dirname(__file__), "..", "examples", "Luz nocturna.wirely")
    s = Simulator(Circuit.load(path))
    t0 = time.perf_counter()
    s.run_until(1.0)
    assert time.perf_counter() - t0 < 0.5


# ----------------------------------------------------------------------------------------- against ngspice
NGSPICE = shutil.which("ngspice")


def ngspice_op(netlist: str, probes):
    """Run ngspice in batch mode and return {probe: value}."""
    # ngspice reading stdin drops the first line and uses the next as the title: give it two to eat
    lines = "Wirely check\n* title\n" + netlist.strip() + "\n.control\nop\n" + "".join(f"print {p}\n" for p in probes) + ".endc\n.end\n"
    out = subprocess.run([NGSPICE, "-b", "/dev/stdin"], input=lines, capture_output=True, text=True,
                         timeout=60).stdout
    res = {}
    for p in probes:
        m = re.search(re.escape(p) + r"\s*=\s*([-+0-9.eE]+)", out, re.I)
        assert m, out
        res[p] = float(m.group(1))
    return res


@pytest.mark.skipif(not NGSPICE, reason="ngspice not installed")
def test_against_ngspice_led_and_transistor_switch():
    _, Is, bf, br, _, _ = D.BJTS["BC548"]
    led_is = D.led_is("Rojo")
    net = f"""* LED driven by an NPN switch
V1 a 0 9
Rb a b 10k
Rc a k 330
D1 k c LED
Q1 c b 0 QN
.model LED D(IS={led_is:.6e} N={D.LED_N} RS={D.LED_RS})
.model QN NPN(IS={Is:.6e} BF={bf} BR={br})
.options gmin=1e-12
"""
    ref = ngspice_op(net, ["v(b)", "v(c)", "v(k)", "i(V1)"])
    s, comps = op([("dc_supply", ("a", "0"), {"voltage": 9}),
                   ("resistor", ("a", "b"), {"resistance": 10e3}),
                   ("resistor", ("a", "k"), {"resistance": 330}),
                   ("led", ("k", "c"), {"colour": "Rojo"}),
                   ("npn", ("b", "c", "0"), {"model": "BC548"})])
    sup, rb, rc, led, q = comps
    # our supply has 0.02 Ω inside, ngspice's is ideal: allow 0.1 %
    assert vnet(s, q, "B") == pytest.approx(ref["v(b)"], rel=2e-3)
    assert vnet(s, q, "C") == pytest.approx(ref["v(c)"], rel=2e-2, abs=2e-3)
    assert vnet(s, led, "A") == pytest.approx(ref["v(k)"], rel=2e-3)
    assert -s.device(sup.id).i_pins[0] == pytest.approx(-ref["i(V1)"], rel=2e-3)


@pytest.mark.skipif(not NGSPICE, reason="ngspice not installed")
def test_against_ngspice_rc_transient():
    out = subprocess.run([NGSPICE, "-b", "/dev/stdin"], input="""Wirely check
* RC
V1 a 0 PULSE(0 5 0 1n 1n 1 2)
R1 a k 1k
C1 k 0 10u
.control
tran 10u 30m
print v(k)
.endc
.end
""", capture_output=True, text=True, timeout=60).stdout
    pts = [(float(t), float(vv)) for t, vv in re.findall(r"^\d+\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s*$", out, re.M)]
    assert len(pts) > 50
    c, (b, sw, r, cap) = rc_circuit(1000, 10e-6, 5.0)
    s = Simulator(c)
    s.set_value(sw.id, "closed", True)
    trace = s.transient(0.03, 1e-4, lambda sim: sim.pin_voltage(cap.id, "1"))
    import bisect
    ts = [t for t, _ in trace]
    for t, vref in pts[5::10]:
        i = min(bisect.bisect_left(ts, t), len(ts) - 1)
        if i > 0:   # linear interpolation in our trace
            (t0, v0), (t1, v1) = trace[i - 1], trace[i]
            vv = v0 + (v1 - v0) * (t - t0) / (t1 - t0) if t1 > t0 else v1
        else:
            vv = trace[0][1]
        assert vv == pytest.approx(vref, abs=0.03), (t, vv, vref)


# ----------------------------------------------------------------------------------------- current along wires
def test_current_flow_along_wires_follows_the_loop():
    from wirely.sim.flow import FlowNetwork
    path = os.path.join(os.path.dirname(__file__), "..", "examples", "LED y resistencia.wirely")
    c = Circuit.load(path)
    sw = next(x for x in c.components.values() if x.kind == "switch")
    led = next(x for x in c.components.values() if x.kind == "led")
    bat = next(x for x in c.components.values() if x.kind == "battery")
    sw.props["closed"] = True
    s = Simulator(c)
    s.dc()
    flows = FlowNetwork(c).solve(lambda cid, pin: s.pin_voltage and s.device(cid).i_pins[
        [n for n, _x, _y in s.device(cid).comp.part.pins].index(pin)])
    i_led = s.device(led.id).current
    assert i_led > 0.01
    # every piece of wire carries the full loop current (a single loop)
    for a, b, amps in flows:
        assert abs(abs(amps) - i_led) < 1e-6 * max(1, i_led) + 1e-9
    # leaving the battery's + terminal, current flows away from it
    plus = bat.pin_positions()["+"]
    out = [amps if a == plus else -amps for a, b, amps in flows if plus in (a, b)]
    assert out and all(v > 0 for v in out)


def test_current_splits_at_a_junction():
    from wirely.sim.flow import FlowNetwork
    c, comps = build([("dc_supply", ("a", "0"), {"voltage": 10}), ("resistor", ("a", "0"), {"resistance": 100}),
                      ("resistor", ("a", "0"), {"resistance": 400})])
    s = Simulator(c)
    s.dc()
    names = lambda cid: [n for n, _x, _y in s.device(cid).comp.part.pins]
    flows = FlowNetwork(c).solve(lambda cid, pin: s.device(cid).i_pins[names(cid).index(pin)])
    biggest = max(abs(a) for _p, _q, a in flows)
    assert biggest == pytest.approx(10 / 100.02 + 10 / 400.02, rel=1e-3)     # the supply's own wire
    amps = sorted(round(abs(a), 4) for _p, _q, a in flows)
    assert round(10 / 400.02, 4) in amps and round(10 / 100.02, 4) in amps
