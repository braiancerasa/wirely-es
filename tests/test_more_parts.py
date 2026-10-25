"""Parts added in 1.4.0: bi-colour and RGB LEDs, the bridge rectifier, the thyristor, voltage regulators, the
transformer, the DPDT switch, the Hall effect sensor, the solenoid, the comparator and the 4026 / 4060 counters
— and the Readings display."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from test_sim import build, op  # noqa: E402

from wirely.model import parts as P  # noqa: E402
from wirely.model.circuit import Circuit  # noqa: E402
from wirely.model.types_info import TYPE_INFO  # noqa: E402
from wirely.sim.engine import Simulator  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def run(spec, t, h=1e-3):
    c, comps = build(spec)
    s = Simulator(c)
    s.h_max = h
    s.run_until(t)
    return s, comps


# ------------------------------------------------------------------------------------------- LEDs
def test_rgb_led_mixes_the_colours_that_are_on():
    s, c = op([("dc_supply", ("v", "0"), {"voltage": 9}),
               ("resistor", ("v", "r"), {"resistance": 470}), ("resistor", ("v", "g"), {"resistance": 470}),
               ("led_rgb", ("r", "g", "b", "0"), {})])
    d = s.device(c[3].id)
    look = d.live_extra()
    assert look["_glows"][0] > 0.9 and look["_glows"][1] > 0.8 and look["_glows"][2] == 0
    r, g, b = (int(look["_rgb"][k:k + 2], 16) for k in (1, 3, 5))
    assert r > 200 and g > 200 and b < 150                         # red + green = yellow
    # each LED takes (9 − Vf) / 470: red drops less than green
    assert d.i_pins[0] == pytest.approx((9 - 2.0) / 470, rel=0.05)
    assert d.i_pins[3] == pytest.approx(-(d.i_pins[0] + d.i_pins[1]))


def test_rgb_led_green_and_blue_share_one_resistor():
    """An RGB LED's green is the same kind of chip as its blue (about 3.1 V), so on one resistor they share the
    current and mix to cyan — but red, at about 2 V, takes it all if it's wired in too."""
    s, c = op([("dc_supply", ("v", "0"), {"voltage": 9}), ("resistor", ("k", "0"), {"resistance": 300}),
               ("led_rgb", ("0", "v", "v", "k"), {})])
    g = s.device(c[2].id).live_extra()["_glows"]
    assert g[0] == 0 and g[1] > 0.5 and g[2] > 0.5
    s, c = op([("dc_supply", ("v", "0"), {"voltage": 9}), ("resistor", ("k", "0"), {"resistance": 300}),
               ("led_rgb", ("v", "v", "0", "k"), {})])
    g = s.device(c[2].id).live_extra()["_glows"]
    assert g[0] > 0.9 and g[1] < 0.05


@pytest.mark.parametrize("forward,colour", [(True, 0), (False, 1)])
def test_two_leg_bicolour_led_colour_depends_on_direction(forward, colour):
    nets = ("x", "0") if forward else ("0", "x")
    s, c = op([("dc_supply", ("v", "0"), {"voltage": 9}), ("resistor", ("v", "x"), {"resistance": 470}),
               ("led_bi2", nets, {})])
    g = s.device(c[2].id).live_extra()["_glows"]
    assert g[colour] > 0.9 and g[1 - colour] == 0


def test_bicolour_led_pops_without_a_resistor():
    s, c = run([("dc_supply", ("v", "0"), {"voltage": 9}), ("led_bi3", ("v", "0x", "0"), {})], 0.1)
    d = s.device(c[1].id)
    assert d.blown and any("popped" in t for _c, t in s.take_events())


# ------------------------------------------------------------------------------------------- bridge rectifier
def test_bridge_rectifier_and_capacitor_make_smooth_dc():
    s, c = run([("ac_supply", ("a", "b"), {"voltage": 12, "frequency": 50}), ("bridge", ("a", "b", "p", "0"), {}),
                ("electrolytic", ("p", "0"), {"capacitance": 1000e-6}),
                ("resistor", ("p", "0"), {"resistance": 1000})], 0.2, 1e-4)
    vout = s.pin_voltage(c[2].id, "+")
    assert 10.0 < vout < 11.2                       # 12 V peak minus two diode drops, a little ripple
    assert not s.device(c[1].id).blown and not s.take_events()


def test_bridge_rectifier_output_is_positive_whichever_way_round():
    for nets in (("a", "b", "p", "0"), ("b", "a", "p", "0")):
        c, comps = build([("dc_supply", ("a", "b"), {"voltage": 9}), ("bridge", nets, {}),
                          ("resistor", ("p", "0"), {"resistance": 1000})])
        s = Simulator(c)
        s.dc()
        assert s.pin_voltage(comps[2].id, "1") == pytest.approx(9 - 1.4, abs=0.25)


# ------------------------------------------------------------------------------------------- thyristor
def scr_alarm():
    return build([("dc_supply", ("v", "0"), {"voltage": 9}), ("push_break", ("v", "w"), {}),
                  ("resistor", ("w", "a"), {"resistance": 470}), ("scr", ("a", "0", "g"), {"model": "C106D"}),
                  ("push_make", ("w", "p"), {}), ("resistor", ("p", "g"), {"resistance": 4700})])


def test_thyristor_latches_on_and_resets_when_the_current_stops():
    c, comps = scr_alarm()
    s = Simulator(c)
    s.h_max = 1e-3
    reset, scr, trig = comps[1], comps[3], comps[4]
    s.run_until(0.05)
    assert s.pin_voltage(scr.id, "A") == pytest.approx(9, abs=0.05)          # off
    s.set_value(trig.id, "pressed", True)
    s.run_until(0.1)
    s.set_value(trig.id, "pressed", False)
    s.run_until(0.3)
    assert s.pin_voltage(scr.id, "A") < 1.2                                   # still on: latched
    s.set_value(reset.id, "pressed", True)
    s.run_until(0.35)
    s.set_value(reset.id, "pressed", False)
    s.run_until(0.5)
    assert s.pin_voltage(scr.id, "A") == pytest.approx(9, abs=0.05)          # off again


def test_thyristor_lets_go_below_its_holding_current():
    """A big load resistor (current below the holding current) means it can't stay on."""
    s, c = run([("dc_supply", ("v", "0"), {"voltage": 9}), ("resistor", ("v", "a"), {"resistance": 10e3}),
                ("scr", ("a", "0", "g"), {"model": "C106D"}), ("dc_supply", ("p", "0"), {"voltage": 5}),
                ("switch", ("p", "q"), {"closed": True}), ("resistor", ("q", "g"), {"resistance": 4700})], 0.05)
    assert s.pin_voltage(c[2].id, "A") < 1.2                                 # held on by the gate
    s.set_value(c[4].id, "closed", False)
    s.run_until(0.1)
    assert s.pin_voltage(c[2].id, "A") > 8.5                                 # 0.8 mA < 3 mA holding: off


# ------------------------------------------------------------------------------------------- regulators
@pytest.mark.parametrize("model,vout", [("7805", 5.0), ("7809", 9.0), ("7812", 12.0), ("LM1117-3.3", 3.3)])
def test_fixed_regulators_hold_their_voltage(model, vout):
    s, c = op([("dc_supply", ("v", "0"), {"voltage": 15}), ("reg_fixed", ("v", "0", "o"), {"model": model}),
               ("resistor", ("o", "0"), {"resistance": 200})])
    assert s.pin_voltage(c[1].id, "OUT") == pytest.approx(vout, abs=0.02)


def test_7805_drops_out_when_the_input_is_too_low():
    s, c = op([("dc_supply", ("v", "0"), {"voltage": 6}), ("reg_fixed", ("v", "0", "o"), {"model": "7805"}),
               ("resistor", ("o", "0"), {"resistance": 100})])
    # a 7805 needs about 1.2 V to spare at light load (2 V at 1 A)
    assert s.pin_voltage(c[1].id, "OUT") == pytest.approx(6 - 1.2 - 0.53 * 0.048, abs=0.03)


def test_lm317_sets_its_voltage_with_two_resistors():
    s, c = op([("dc_supply", ("v", "0"), {"voltage": 15}), ("reg_adj", ("v", "a", "o"), {}),
               ("resistor", ("o", "a"), {"resistance": 240}), ("resistor", ("a", "0"), {"resistance": 720})])
    assert s.pin_voltage(c[1].id, "OUT") == pytest.approx(1.25 * (1 + 720 / 240) + 50e-6 * 720, abs=0.01)


@pytest.mark.parametrize("load", [100, 10, 5, 4, 3.6, 3.4, 3.2, 3, 2, 1])
def test_7805_on_a_9v_battery_with_any_load(load):
    """A battery's internal resistance makes its voltage sag under load, into the 7805's dropout or current
    limit — the simulation must still settle quickly."""
    s, c = run([("battery", ("v", "0"), {"voltage": 9}), ("reg_fixed", ("v", "0", "o"), {"model": "7805"}),
                ("resistor", ("o", "0"), {"resistance": load, "power": 100})], 0.1)
    assert s.t >= 0.1
    vo = s.pin_voltage(c[1].id, "OUT")
    assert vo <= 5.0 + 1e-3 and vo == pytest.approx(min(5.0, 1.5 * load, vo), abs=0.01)
    assert s.pin_voltage(c[1].id, "IN") - vo >= 1.0                           # never less than its dropout


def test_regulator_current_limit():
    s, c = op([("dc_supply", ("v", "0"), {"voltage": 12}), ("reg_fixed", ("v", "0", "o"), {"model": "7805"}),
               ("resistor", ("o", "0"), {"resistance": 1, "power": 100})])
    assert s.device(c[1].id).current == pytest.approx(1.5, rel=0.02)


def test_regulator_overheats_and_shuts_down_without_a_heatsink():
    s, c = run([("dc_supply", ("v", "0"), {"voltage": 24}), ("reg_fixed", ("v", "0", "o"), {"model": "7805"}),
                ("resistor", ("o", "0"), {"resistance": 10, "power": 10})], 2, 0.01)
    reg = s.device(c[1].id)
    assert reg.hot and s.pin_voltage(c[1].id, "OUT") < 0.1
    assert any("too hot" in t for _c, t in s.take_events())
    s2, c2 = run([("dc_supply", ("v", "0"), {"voltage": 24}),
                  ("reg_fixed", ("v", "0", "o"), {"model": "7805", "heatsink": True}),
                  ("resistor", ("o", "0"), {"resistance": 10, "power": 10})], 6, 0.01)
    assert not s2.device(c2[1].id).hot and s2.pin_voltage(c2[1].id, "OUT") == pytest.approx(5.0, abs=0.05)


# ------------------------------------------------------------------------------------------- transformer
def test_transformer_steps_ac_down_by_its_turns_ratio():
    c, comps = build([("ac_supply", ("p", "q"), {"voltage": 50, "frequency": 50}),
                      ("transformer", ("p", "q", "s", "0"), {"ratio": 5}),
                      ("resistor", ("s", "0"), {"resistance": 100})])
    s = Simulator(c)
    s.h_max = 2e-4
    peak = 0.0
    while s.t < 0.06:
        s.step(0.06 - s.t)
        peak = max(peak, abs(s.pin_voltage(comps[1].id, "S1")))
    assert peak == pytest.approx(10 * 100 / 100.5, rel=0.01)       # 50 / 5, less the 0.5 Ω winding


def test_transformer_on_dc_warns():
    s, c = run([("battery", ("p", "0"), {"voltage": 9}), ("transformer", ("p", "0", "s", "t"), {"ratio": 1}),
                ("resistor", ("s", "t"), {"resistance": 100})], 3)
    assert any("only works with AC" in t for _c, t in s.take_events())


# ------------------------------------------------------------------------------------------- switches, sensors, outputs
def test_dpdt_reverses_a_motor():
    c = Circuit.load(os.path.join(ROOT, "examples", "Reversing a motor (DPDT).wirely"))
    s = Simulator(c)
    s.h_max = 1e-3
    s.run_until(0.5)
    motor = next(d for d in s.devices if d.comp.kind == "motor")
    sw = next(d for d in s.devices if d.comp.kind == "dpdt")
    assert motor.rpm > 4000
    s.set_value(sw.cid, "position", "B")
    s.run_until(1.5)
    assert motor.rpm < -4000


def test_dpdt_relay_switches_both_contacts_together():
    s, c = run([("dc_supply", ("v", "0"), {"voltage": 9}), ("switch", ("v", "k"), {"closed": False}),
                ("relay_dpdt", ("k", "0", "v", "a", "b", "v", "c", "d"), {"voltage": 9}),
                ("diode", ("0", "k"), {"model": "1N4001"})] +
               [("resistor", (n, "0"), {"resistance": 1000}) for n in "abcd"], 0.05)
    rl = c[2].id
    volts = lambda: [round(s.pin_voltage(rl, p)) for p in ("NC1", "NO1", "NC2", "NO2")]
    assert volts() == [9, 0, 9, 0]
    s.set_value(c[1].id, "closed", True)
    s.run_until(0.1)
    assert volts() == [0, 9, 0, 9] and s.device(rl).clicks == 1
    s.set_value(c[1].id, "closed", False)
    s.run_until(0.15)
    assert volts() == [9, 0, 9, 0]


def test_hall_sensor_pulls_its_output_low_near_a_magnet():
    s, c = run([("dc_supply", ("v", "0"), {"voltage": 9}), ("hall", ("v", "0", "o"), {"magnet": False}),
                ("resistor", ("v", "o"), {"resistance": 10000})], 0.01)
    assert s.pin_voltage(c[1].id, "OUT") == pytest.approx(9, abs=0.01)
    s.set_value(c[1].id, "magnet", True)
    s.run_until(0.02)
    assert s.pin_voltage(c[1].id, "OUT") < 0.1
    assert not s.device(c[1].id).blown


def test_hall_sensor_needs_its_supply():
    s, c = run([("dc_supply", ("v", "0"), {"voltage": 3}), ("hall", ("v", "0", "o"), {"magnet": True}),
                ("resistor", ("v", "o"), {"resistance": 10000})], 0.01)
    assert s.pin_voltage(c[1].id, "OUT") == pytest.approx(3, abs=0.01)       # below 4.5 V it doesn't work


def test_solenoid_pulls_in_and_kicks_back_without_a_diode():
    s, c = run([("dc_supply", ("v", "0"), {"voltage": 12}), ("switch", ("v", "a"), {"closed": True}),
                ("solenoid", ("a", "0"), {"voltage": 12})], 0.05)
    sol = s.device(c[2].id)
    assert sol.on and sol.current == pytest.approx(0.25, rel=0.02)
    s.set_value(c[1].id, "closed", False)
    low = 0.0
    while s.t < 0.1:
        s.step(0.1 - s.t)
        low = min(low, s.pin_voltage(c[2].id, "1"))
    assert not sol.on and low < -100                     # the switch-off spike


def test_solenoid_spike_caught_by_a_diode():
    s, c = run([("dc_supply", ("v", "0"), {"voltage": 12}), ("switch", ("v", "a"), {"closed": True}),
                ("solenoid", ("a", "0"), {"voltage": 12}), ("diode", ("0", "a"), {"model": "1N4001"})], 0.05)
    s.set_value(c[1].id, "closed", False)
    low = 0.0
    while s.t < 0.1:
        s.step(0.1 - s.t)
        low = min(low, s.pin_voltage(c[2].id, "1"))
    assert low > -1.5


@pytest.mark.parametrize("vminus,low", [(3.0, False), (6.0, True)])
def test_comparator_output(vminus, low):
    s, c = op([("dc_supply", ("v", "0"), {"voltage": 9}), ("resistor", ("v", "p"), {"resistance": 10000}),
               ("resistor", ("p", "0"), {"resistance": 10000}), ("dc_supply", ("m", "0"), {"voltage": vminus}),
               ("comparator", ("p", "m", "o"), {"model": "LM393"}), ("resistor", ("v", "o"), {"resistance": 4700})])
    vo = s.pin_voltage(c[4].id, "OUT")
    if low:
        assert vo == pytest.approx(9 * 60 / 4760, abs=0.02)       # pulled down through its 60 Ω
    else:
        assert vo == pytest.approx(9, abs=0.01)                    # off: the pull-up wins


def test_comparator_switches_as_the_input_crosses():
    s, c = run([("dc_supply", ("v", "0"), {"voltage": 9}), ("signal_gen", ("p", "0"),
                {"waveform": "Triangle", "frequency": 10, "amplitude": 4, "offset": 4.5}),
                ("dc_supply", ("m", "0"), {"voltage": 4.5}), ("comparator", ("p", "m", "o"), {}),
                ("resistor", ("v", "o"), {"resistance": 4700})], 0.0)
    s.recording = False
    highs = lows = 0
    while s.t < 0.3:
        s.step(0.3 - s.t)
        vo = s.pin_voltage(c[3].id, "OUT")
        highs += vo > 8
        lows += vo < 0.5
    assert highs > 10 and lows > 10


# ------------------------------------------------------------------------------------------- motor driver
def l293d(a1, a2, en=True, load=("motor", {}), v2=9):
    return run([("dc_supply", ("v5", "0"), {"voltage": 5}), ("dc_supply", ("v9", "0"), {"voltage": v2}),
                ("l293d", ("v5" if en else "0", "v5" if a1 else "0", "v5" if a2 else "0", "0", "0", "0",
                           "y1", "y2", "y3", "y4", "v5", "v9", "0"), {}),
                (load[0], ("y1", "y2"), load[1])], 0.5)


@pytest.mark.parametrize("a1,a2,en,turns", [(1, 0, 1, 1), (0, 1, 1, -1), (1, 1, 1, 0), (0, 0, 1, 0), (1, 0, 0, 0)])
def test_l293d_drives_a_motor_forwards_backwards_or_stops(a1, a2, en, turns):
    s, c = l293d(a1, a2, en)
    rpm = s.device(c[3].id).rpm
    assert (rpm > 3000) if turns > 0 else (rpm < -3000) if turns < 0 else abs(rpm) < 1
    if turns:
        hi, lo = ("1Y", "2Y") if turns > 0 else ("2Y", "1Y")
        assert 7.0 < s.pin_voltage(c[2].id, hi) < 8.6 and 0.4 < s.pin_voltage(c[2].id, lo) < 1.4   # its drops


def test_l293d_reverses_a_spinning_motor_without_burning_out():
    c, comps = build([("dc_supply", ("v5", "0"), {"voltage": 5}), ("dc_supply", ("v9", "0"), {"voltage": 9}),
                      ("l293d", ("v5", "a", "b", "0", "0", "0", "y1", "y2", "y3", "y4", "v5", "v9", "0"), {}),
                      ("motor", ("y1", "y2"), {}), ("switch", ("v5", "a"), {"closed": True}),
                      ("switch", ("v5", "b"), {"closed": False})])
    s = Simulator(c)
    s.h_max = 1e-3
    s.run_until(0.6)
    s.set_value(comps[4].id, "closed", False)
    s.set_value(comps[5].id, "closed", True)
    s.run_until(1.4)
    assert s.device(comps[3].id).rpm < -3000 and not s.take_events()


def test_l293d_overloaded_gets_too_hot_and_switches_off():
    s, c = l293d(1, 0, load=("resistor", {"resistance": 4, "power": 100}), v2=12)
    s.run_until(2.0)
    ic = s.device(c[2].id)
    assert ic.hot and any("too hot" in t for _c, t in s.take_events())
    assert abs(s.pin_voltage(c[2].id, "1Y") - s.pin_voltage(c[2].id, "2Y")) < 0.05      # outputs off


# ------------------------------------------------------------------------------------------- counters
def test_4026_counts_and_drives_the_display():
    s, c = run([("signal_gen", ("clk", "0"), {"waveform": "Square", "frequency": 10, "amplitude": 4.5,
                                              "offset": 4.5}),
                ("dc_supply", ("v", "0"), {"voltage": 9}),
                ("ic4026", ("clk", "0", "0") + tuple("abcdefg") + ("co",), {}),
                ("sevenseg", tuple("abcdefg") + ("0",), {})], 0.33)
    cnt = s.device(c[2].id)
    lit = "".join(k for k, v in zip("abcdefg", s.device(c[3].id).lit()) if v > 0.5)
    assert cnt.count == 4 and lit == "bcfg"                         # a 4 on the display


def test_4026_carry_clocks_the_next_digit():
    s, c = run([("signal_gen", ("clk", "0"), {"waveform": "Square", "frequency": 20, "amplitude": 4.5,
                                              "offset": 4.5}),
                ("dc_supply", ("v", "0"), {"voltage": 9}),
                ("ic4026", ("clk", "0", "0") + tuple(f"u{s_}" for s_ in "abcdefg") + ("co",), {}),
                ("ic4026", ("co", "0", "0") + tuple(f"t{s_}" for s_ in "abcdefg") + ("co2",), {})], 0.33)
    ones, tens = s.device(c[2].id), s.device(c[3].id)
    o0, t0 = ones.count, tens.count
    s.run_until(0.33 + 1.25)                                     # 25 more pulses
    assert ones.count == (o0 + 5) % 10
    assert tens.count == t0 + 2 + (o0 + 5 >= 10)


def test_4060_oscillates_at_about_1_over_2_3_rc():
    s, c = run([("dc_supply", ("v", "0"), {"voltage": 9}),
                ("ic4060", ("pi", "po", "pon", "0") + tuple(f"q{n}" for n in (4, 5, 6, 7, 8, 9, 10, 12, 13, 14)), {}),
                ("capacitor", ("pon", "x"), {"capacitance": 1e-6}), ("resistor", ("po", "x"), {"resistance": 10000}),
                ("resistor", ("x", "pi"), {"resistance": 100000})], 1.0)
    n1 = s.device(c[1].id).count
    s.run_until(3.0)
    f = (s.device(c[1].id).count - n1) / 2.0
    assert f == pytest.approx(1 / (2.3 * 10e3 * 1e-6), rel=0.1)
    # Q4 is the count divided by 16
    assert s.pin_voltage(c[1].id, "Q4") == pytest.approx(9 if (s.device(c[1].id).count >> 3) & 1 else 0, abs=0.1)


# ------------------------------------------------------------------------------------------- the parts list
def test_new_parts_are_in_the_gallery_with_types_explained():
    for key in ("l293d", "relay_dpdt", "led_bi2", "led_bi3", "led_rgb", "bridge", "scr", "reg_fixed", "reg_adj", "transformer", "dpdt",
                "hall", "solenoid", "comparator", "ic4026", "ic4060"):
        assert key in P.PARTS
        mp = P.get(key).prop("model")
        if mp is not None:
            for ch in mp.choices:
                assert TYPE_INFO.get(ch), ch


@pytest.mark.parametrize("name,t", [("Thyristor alarm (latching)", 0.3), ("5 V power supply (7805)", 0.3),
                                    ("RGB colour mixer", 0.1), ("Counter (555 + 4026)", 1.5),
                                    ("Reversing a motor (DPDT)", 0.3), ("Motor driver (L293D)", 0.3),
                                    ("Relay reversing a motor (DPDT)", 0.3)])
def test_new_examples_run_cleanly(name, t):
    c = Circuit.load(os.path.join(ROOT, "examples", f"{name}.wirely"))
    s = Simulator(c)
    s.h_max = 1e-3
    s.run_until(t)
    assert not s.take_events() and not any(d.blown for d in s.devices)


def test_power_supply_example_gives_5_volts():
    c = Circuit.load(os.path.join(ROOT, "examples", "5 V power supply (7805).wirely"))
    s = Simulator(c)
    s.run_until(0.4)
    reg = next(d for d in s.devices if d.comp.kind == "reg_fixed")
    assert s.pin_voltage(reg.cid, "OUT") == pytest.approx(5.0, abs=0.02)
    assert 13 < s.pin_voltage(reg.cid, "IN") < 15.5


# ------------------------------------------------------------------------------------------- readings
def test_readings_show_on_the_sheet_and_pin_with_a_click():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QImage, QPainter
    from wirely.ui.scene import CircuitScene
    from wirely.ui.simcontrol import SimController
    c = Circuit.load(os.path.join(ROOT, "examples", "Voltage divider.wirely"))
    sc = CircuitScene(c)
    simc = SimController()
    sc.attach_sim(simc)
    simc.start(c)
    simc._tick()
    tags = []
    sc._tag = lambda p, x, y, text, pinned, anchor: tags.append((text, pinned))
    img = QImage(200, 200, QImage.Format_ARGB32)
    p = QPainter(img)
    sc.drawForeground(p, sc.sceneRect())
    assert not tags                                       # off by default
    sc.show_readings = True
    sc.drawForeground(p, sc.sceneRect())
    assert any("V" in t and "A" in t for t, _p in tags)   # wires with current: volts and amps
    # click a resistor while running: its reading is pinned (and shows with Readings off)
    sc.show_readings = False
    tags.clear()
    r = next(it for it in sc.comp_items.values() if it.comp.kind == "resistor")
    sc._sim_press(_Click(r.pos()))
    sc.drawForeground(p, sc.sceneRect())
    assert len(tags) == 1 and tags[0][1] and "W" in tags[0][0]
    sc._sim_press(_Click(r.pos()))                       # click again: unpinned
    tags.clear()
    sc.drawForeground(p, sc.sceneRect())
    assert not tags
    # Copy readings: a table that pastes into a spreadsheet
    table = sc.readings_text().splitlines()
    assert table[1].split("\t") == ["Part", "What", "Voltage (V)", "Current (A)", "Power (W)"]
    r1 = next(row.split("\t") for row in table if row.startswith("R1\t"))
    assert float(r1[2]) > 0 and float(r1[3]) > 0 and float(r1[4]) == pytest.approx(float(r1[2]) * float(r1[3]), rel=0.01)
    p.end()
    simc.stop()
    assert sc.readings_text() == ""


class _Click:
    def __init__(self, pos):
        self._p = pos

    def scenePos(self):
        return self._p

    def button(self):
        from PySide6.QtCore import Qt
        return Qt.LeftButton

    def accept(self):
        pass
