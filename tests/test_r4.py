"""r4 parts: inductor, relay (with and without a flyback diode), motor with back-EMF and load, new sensors,
and the extra transistor / MOSFET / diode types."""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from test_sim import NGSPICE, build, ngspice_op, op, vnet  # noqa: E402
from wirely.sim import chips as CH  # noqa: E402
from wirely.sim import devices as D  # noqa: E402
from wirely.sim.engine import Simulator  # noqa: E402


# ------------------------------------------------------------------------------------------- inductor
def test_rl_current_rises_with_time_constant_L_over_R():
    L, R, V = 0.1, 100.0, 10.0
    c, comps = build([("dc_supply", ("a", "0"), {"voltage": V}), ("switch", ("a", "b"), {"closed": False}),
                      ("resistor", ("b", "k"), {"resistance": R}), ("inductor", ("k", "0"), {"inductance": L})])
    s = Simulator(c)
    s.set_value(comps[1].id, "closed", True)
    tau = L / (R + 0.03)
    trace = s.transient(5 * tau, tau / 30, lambda sim: sim.device(comps[2].id).i_pins[0])
    for t, i in trace[1:]:
        assert i == pytest.approx(V / (R + 0.03) * (1 - math.exp(-t / tau)), abs=0.005 * V / R)


def test_inductor_is_a_wire_in_steady_dc():
    s, comps = op([("dc_supply", ("a", "0"), {"voltage": 5}), ("resistor", ("a", "k"), {"resistance": 50}),
                   ("inductor", ("k", "0"), {"inductance": 1.0})])
    assert vnet(s, comps[2], "1") < 0.01


# ------------------------------------------------------------------------------------------- relay
def relay_driver(with_diode, V=9.0):
    parts = [("battery", ("vcc", "0"), {"voltage": V}),
             ("switch", ("vcc", "bsw"), {"closed": False}),
             ("resistor", ("bsw", "b"), {"resistance": 4700}),
             ("resistor", ("b", "0"), {"resistance": 47e3}),
             ("npn", ("b", "coil", "0"), {"model": "BC548"}),
             ("relay", ("vcc", "coil", "vcc", "nc", "no"), {"voltage": 9}),
             ("lamp", ("no", "0"), {"voltage": 9, "power": 0.5})]
    if with_diode:
        parts.append(("diode", ("coil", "vcc"), {"model": "1N4148"}))
    return build(parts)


def test_relay_pulls_in_and_lets_go():
    c, comps = relay_driver(with_diode=True)
    s = Simulator(c)
    s.h_max = 1e-3
    rl, lamp = s.device(comps[5].id), s.device(comps[6].id)
    s.run_until(0.05)
    assert not rl.on and lamp.glow() == 0
    s.set_value(comps[1].id, "closed", True)
    s.run_until(0.1)
    assert rl.on and lamp.glow() > 0.8
    assert rl.current == pytest.approx((9 - 0.1) / rl.Rc, rel=0.05)    # coil current with the transistor on
    s.set_value(comps[1].id, "closed", False)
    s.run_until(0.15)
    assert not rl.on and lamp.glow() == 0
    assert not s.device(comps[4].id).blown          # the diode protected the transistor
    assert rl.clicks == 2


def test_relay_without_diode_kills_the_transistor():
    c, comps = relay_driver(with_diode=False)
    s = Simulator(c)
    s.h_max = 1e-3
    s.run_until(0.02)
    s.set_value(comps[1].id, "closed", True)
    s.run_until(0.05)
    s.set_value(comps[1].id, "closed", False)
    s.run_until(0.08)
    q = s.device(comps[4].id)
    assert q.blown
    assert any("spike" in m and "diode" in m for _cid, m in s.take_events())


def test_relay_pull_in_and_drop_out_levels():
    """Feed the coil from an adjustable supply: on at 75 % of 9 V, off again only below 30 %."""
    def coil_on(volts, start_on):
        c, comps = build([("dc_supply", ("v", "0"), {"voltage": 9.0 if start_on else 0.0}),
                          ("relay", ("v", "0", "x", "nc", "no"), {"voltage": 9})])
        s = Simulator(c)
        s.run_until(0.02)
        assert s.device(comps[1].id).on == start_on
        s.set_value(comps[0].id, "voltage", volts)     # now turn the supply to the test voltage
        s.run_until(0.04)
        return s.device(comps[1].id).on
    assert not coil_on(6.5, False) and coil_on(7.0, False)       # pull in between 72 % and 78 %
    assert coil_on(3.0, True) and not coil_on(2.5, True)          # hold until about 30 %


# ------------------------------------------------------------------------------------------- motor
def motor(load="None", V=6.0):
    return build([("dc_supply", ("a", "0"), {"voltage": V}), ("switch", ("a", "m"), {"closed": False}),
                  ("motor", ("m", "0"), {"voltage": 6.0, "load": load})])


def test_motor_starting_current_then_running_current():
    c, comps = motor()
    s = Simulator(c)
    m = s.device(comps[2].id)
    s.set_value(comps[1].id, "closed", True)
    s.run_until(0.002)
    assert m.current == pytest.approx(6 / (m.R + 0.03), rel=0.05)        # stalled at the start: V / R
    s.run_until(1.0)
    assert m.current == pytest.approx(0.1 * m.I_STALL, rel=0.15)        # no-load current ≈ 10 % of stall
    assert m.rpm == pytest.approx(6000 * 0.9, rel=0.05)


def test_motor_slows_down_and_takes_more_current_under_load():
    speeds, currents = [], []
    for load in ("None", "Light", "Medium", "Heavy"):
        c, comps = motor(load)
        s = Simulator(c)
        s.set_value(comps[1].id, "closed", True)
        s.run_until(1.5)
        m = s.device(comps[2].id)
        speeds.append(m.rpm)
        currents.append(m.current)
    assert speeds == sorted(speeds, reverse=True) and currents == sorted(currents)
    assert speeds[-1] > 0


def test_motor_speed_follows_voltage():
    rpm = []
    for V in (3.0, 6.0):
        c, comps = motor(V=V)
        s = Simulator(c)
        s.set_value(comps[1].id, "closed", True)
        s.run_until(1.5)
        rpm.append(s.device(comps[2].id).rpm)
    assert rpm[1] / rpm[0] == pytest.approx(2.0, rel=0.03)


# ------------------------------------------------------------------------------------------- sensors
@pytest.mark.parametrize("kind,key", [("reed_switch", "magnet"), ("tilt_switch", "tilted")])
def test_reed_and_tilt_switches(kind, key):
    s, comps = op([("battery", ("a", "0"), {"voltage": 9}), (kind, ("a", "b"), {key: False}),
                   ("resistor", ("b", "0"), {"resistance": 1000})])
    assert abs(s.device(comps[2].id).i_pins[0]) < 1e-6
    s.set_value(comps[1].id, key, True)
    s.dc()
    assert s.device(comps[2].id).i_pins[0] == pytest.approx(9 / 1001.5, rel=1e-3)


@pytest.mark.parametrize("moist,R", [(0, 1e6), (50, 31.6e3), (100, 1e3)])
def test_moisture_sensor_resistance(moist, R):
    s, comps = op([("dc_supply", ("a", "0"), {"voltage": 10}), ("moisture", ("a", "0"), {"moisture": moist})])
    assert 10 / s.device(comps[1].id).i_pins[0] == pytest.approx(R, rel=0.01)


def test_phototransistor_conducts_more_in_brighter_light():
    vs = []
    for lux in (0, 100, 1000, 20000):
        s, comps = op([("dc_supply", ("a", "0"), {"voltage": 9}), ("resistor", ("a", "c"), {"resistance": 10e3}),
                       ("phototransistor", ("c", "0"), {"light": lux})])
        vs.append(vnet(s, comps[2], "C"))
    assert vs == sorted(vs, reverse=True)
    assert vs[0] > 8.99 and vs[-1] < 0.3
    # in between it is a current source: Ic ≈ β · 2 nA/lux
    assert (9 - vs[1]) / 10e3 == pytest.approx(300 * 2e-9 * 100, rel=0.05)


# ------------------------------------------------------------------------------------------- new types
@pytest.mark.parametrize("model", ["BS170", "IRLZ44N", "IRF530", "IRF3205", "AO3400"])
def test_new_nmos_types_switch_on_and_off(model):
    for vg, on in ((0.0, False), (10.0, True)):
        s, comps = op([("dc_supply", ("vdd", "0"), {"voltage": 12}), ("dc_supply", ("g", "0"), {"voltage": vg}),
                       ("resistor", ("vdd", "d"), {"resistance": 1000}), ("nmos", ("g", "d", "0"), {"model": model})])
        assert (vnet(s, comps[3], "D") < 0.2) == on


def test_logic_level_mosfet_is_on_at_5V_but_IRF540_only_partly():
    out = {}
    for model in ("IRLZ44N", "IRF540"):
        s, comps = op([("dc_supply", ("vdd", "0"), {"voltage": 12}), ("dc_supply", ("g", "0"), {"voltage": 3.3}),
                       ("resistor", ("vdd", "d"), {"resistance": 1}), ("nmos", ("g", "d", "0"), {"model": model})])
        out[model] = vnet(s, comps[3], "D")
    assert out["IRLZ44N"] < out["IRF540"]


@pytest.mark.parametrize("model", ["BS250", "IRF9530", "FQP27P06", "IRLML6402"])
def test_new_pmos_types(model):
    s, comps = op([("dc_supply", ("vdd", "0"), {"voltage": 9}), ("dc_supply", ("g", "0"), {"voltage": 0.0}),
                   ("pmos", ("g", "d", "vdd"), {"model": model}), ("resistor", ("d", "0"), {"resistance": 1000})])
    assert vnet(s, comps[2], "D") > 8.5


@pytest.mark.parametrize("model", ["BC547", "BC337", "2N2222", "TIP120"])
def test_new_npn_types_have_their_gain(model):
    s, comps = op([("dc_supply", ("a", "0"), {"voltage": 9}), ("resistor", ("a", "bb"), {"resistance": 2e6}),
                   ("resistor", ("a", "cc"), {"resistance": 100}), ("npn", ("bb", "cc", "0"), {"model": model})])
    d = s.device(comps[3].id)
    bf = D.BJTS[model][2]
    assert d.ic / d.ib == pytest.approx(bf, rel=0.05)


def test_schottky_drops_less_than_silicon():
    v = {}
    for model in ("1N4001", "1N5819"):
        s, comps = op([("dc_supply", ("a", "0"), {"voltage": 9}), ("resistor", ("a", "k"), {"resistance": 100}),
                       ("diode", ("k", "0"), {"model": model})])
        v[model] = s.device(comps[2].id).vd
    assert 0.25 < v["1N5819"] < 0.45 < 0.6 < v["1N4001"]


@pytest.mark.skipif(not NGSPICE, reason="ngspice not installed")
def test_rl_against_ngspice():
    """An RL circuit after 1 time constant, compared with ngspice."""
    import re
    import subprocess
    out = subprocess.run([NGSPICE, "-b", "/dev/stdin"], input="""Wirely check
* RL
V1 a 0 PULSE(0 10 0 1n 1n 1 2)
R1 a k 100
L1 k 0 0.1
.control
tran 10u 3m
print i(V1)
.endc
.end
""", capture_output=True, text=True, timeout=60).stdout
    pts = [(float(t), -float(i)) for t, i in re.findall(r"^\d+\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s*$", out, re.M)]
    t_ref, i_ref = min(pts, key=lambda p: abs(p[0] - 1e-3))
    c, comps = build([("dc_supply", ("a", "0"), {"voltage": 10}), ("switch", ("a", "b"), {"closed": False}),
                      ("resistor", ("b", "k"), {"resistance": 100}), ("inductor", ("k", "0"), {"inductance": 0.1})])
    s = Simulator(c)
    s.set_value(comps[1].id, "closed", True)
    s.h_max = 2e-5
    s.run_until(t_ref)
    assert s.device(comps[2].id).i_pins[0] == pytest.approx(i_ref, rel=0.01)


# ------------------------------------------------------------------------------------------- sound
def dominant_hz(samples):
    import numpy as np
    spec = np.abs(np.fft.rfft(samples * np.hanning(len(samples))))
    return np.argmax(spec[5:]) + 5 if len(spec) > 5 else 0


def test_synth_makes_the_frequency_asked_for():
    import numpy as np
    from wirely.sim.audio import RATE, Synth
    s = Synth()
    s.set("x", 440.0, 0.5, 0.0)
    s.render(RATE // 10)                       # let the volume glide up
    buf = s.render(RATE).astype(float)
    assert dominant_hz(buf) == pytest.approx(440, abs=2)
    assert np.max(np.abs(buf)) > 5000


def test_speaker_plays_the_simulated_frequency():
    """A 440 Hz square wave into a speaker: the sound engine must hear 440 Hz and a square shape."""
    from wirely.sim.audio import SpeakerWatch, Synth, update_from_sim
    c, comps = build([("signal_gen", ("a", "0"), {"waveform": "Square", "frequency": 440, "amplitude": 2,
                                                  "offset": 0}),
                      ("resistor", ("a", "s"), {"resistance": 10}), ("speaker", ("s", "0"), {})])
    sim = Simulator(c)
    sim.recording = True
    w = {cid: SpeakerWatch() for cid in sim.speakers}
    sim.run_until(0.1)
    for t, cid, vv in sim.spk_record:
        w[cid].add(t, vv)
    syn = Synth()
    update_from_sim(syn, sim, w)
    v = syn.voices[comps[2].id]
    assert v.freq == pytest.approx(440, rel=0.005)
    assert v.shape > 0.8 and v.target > 0.2


def test_buzzer_sounds_only_when_powered_the_right_way():
    from wirely.sim.audio import BUZZER_HZ, Synth, update_from_sim
    for polarity, loud in ((("a", "0"), True), (("0", "a"), False)):
        c, comps = build([("battery", ("a", "0"), {"voltage": 6}), ("buzzer", polarity, {})])
        sim = Simulator(c)
        sim.run_until(0.01)
        syn = Synth()
        update_from_sim(syn, sim, {})
        assert (comps[1].id in syn.voices and syn.voices[comps[1].id].freq == BUZZER_HZ) == loud


# ------------------------------------------------------------------------------------------- buck converter
def buck(duty, F=1000.0, L=10e-3, C=100e-6, R=10.0, VIN=12.0):
    """12 V buck converter: P-MOSFET switch (on while the drive is low), Schottky diode, LC filter, 10 Ω load."""
    return build([("dc_supply", ("vin", "0"), {"voltage": VIN}),
                  ("signal_gen", ("g", "0"), {"waveform": "Square", "frequency": F, "amplitude": 6, "offset": 6,
                                              "duty": 100 - duty}),
                  ("pmos", ("g", "sw", "vin"), {"model": "IRF9540"}),
                  ("diode", ("0", "sw"), {"model": "1N5819"}),
                  ("inductor", ("sw", "out"), {"inductance": L}),
                  ("capacitor", ("out", "0"), {"capacitance": C}),
                  ("resistor", ("out", "0"), {"resistance": R, "power": 5.0})])


def run_buck(duty, t_end=0.06):
    c, comps = buck(duty)
    s = Simulator(c)
    tr = s.transient(t_end, 1 / 1000 / 50, lambda sim: (sim.pin_voltage(comps[6].id, "1"),
                                                         sim.device(comps[4].id).i_prev))
    last = [(t, v, i) for t, (v, i) in tr if t > t_end - 0.005]
    # time-weighted averages (the steps aren't evenly spaced)
    def avg(k):
        tot = sum((b[0] - a[0]) * (a[k] + b[k]) / 2 for a, b in zip(last, last[1:]))
        return tot / (last[-1][0] - last[0][0])
    vs = [v for _t, v, _i in last]
    il = [i for _t, _v, i in last]
    return avg(1), max(vs) - min(vs), avg(2), max(il) - min(il), s


@pytest.mark.parametrize("duty", [25, 50, 75])
def test_buck_output_follows_duty_cycle(duty):
    vout, vr, il, ir, s = run_buck(duty)
    d = duty / 100
    vd = 0.33                                   # Schottky drop at about half an amp
    assert vout == pytest.approx(d * 12 - (1 - d) * vd, rel=0.04)
    assert il == pytest.approx(vout / 10, rel=0.03)          # inductor carries the load current on average
    assert ir == pytest.approx((12 - vout) * d / (1000 * 10e-3), rel=0.06)     # ripple = (Vin − Vout)·D/(f·L)
    assert not s.take_events()                  # nothing burns out


@pytest.mark.skipif(not NGSPICE, reason="ngspice not installed")
def test_buck_against_ngspice():
    import re
    import subprocess
    _, vt, kp, lam, *_ = CH.MOSFETS["IRF9540"]
    Is, n, Rs, _ = D.DIODES["1N5819"]
    net = f"""Sparkbench check
* buck converter
V1 vin 0 12
V2 g 0 PULSE(12 0 0.5m 1n 1n 0.5m 1m)
M1 sw g vin vin MP L=1u W=1u
.model MP PMOS(LEVEL=1 VTO=-{vt} KP={kp} LAMBDA={lam})
D1 0 sw DS
.model DS D(IS={Is} N={n} RS={Rs})
L1 sw out 10m
RP sw out 100k
C1 out 0 100u
R1 out 0 10
.control
tran 2u 60m 0 2u
let il = i(L1)
print v(out) il
.endc
.end
"""
    out = subprocess.run([NGSPICE, "-b", "/dev/stdin"], input=net, capture_output=True, text=True, timeout=300).stdout
    pts = [(float(a), float(b), float(c)) for a, b, c in
           re.findall(r"^\d+\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s*$", out, re.M)]
    last = [p for p in pts if p[0] > 0.055]
    v_ng = sum(p[1] for p in last) / len(last)
    il_ng = sum(p[2] for p in last) / len(last)
    vr_ng = max(p[1] for p in last) - min(p[1] for p in last)
    vout, vr, il, ir, _s = run_buck(50)
    assert vout == pytest.approx(v_ng, rel=0.005)
    assert il == pytest.approx(il_ng, rel=0.01)
    assert vr == pytest.approx(vr_ng, rel=0.03)
