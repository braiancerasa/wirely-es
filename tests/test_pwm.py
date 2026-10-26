"""LEDs and bulbs look as bright as an eye would see them (1.5.1): the light is averaged over each frame, so PWM —
switching fully on and off faster than the eye can follow — makes them look steadily dimmer instead of flickering."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from test_sim import build  # noqa: E402

from wirely.model.circuit import Circuit  # noqa: E402
from wirely.sim import devices as D  # noqa: E402
from wirely.sim.engine import Simulator  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def pwm_circuit(duty):
    if duty == 100:
        src = ("dc_supply", ("v", "0"), {"voltage": 5})
    else:
        src = ("signal_gen", ("v", "0"), {"waveform": "square", "frequency": 1000, "amplitude": 2.5,
                                          "offset": 2.5, "duty": duty})
    c, comps = build([src, ("resistor", ("v", "a"), {"resistance": 150}), ("led", ("a", "0"), {"colour": "Red"}),
                      ("lamp", ("v", "0"), {})])
    s = Simulator(c)
    s.h_max = 1e-4
    return s, s.device(comps[2].id), s.device(comps[3].id)


def looks(duty):
    s, led, lamp = pwm_circuit(duty)
    s.run_until(0.2)
    led.take_glow(), lamp.take_glow()
    s.run_until(0.22)
    led.take_glow(), lamp.take_glow()          # two frames: the eye's memory now only holds steady PWM
    s.run_until(0.24)
    return led.take_glow(), lamp.take_glow()


def test_pwm_dims_an_led_by_its_duty_cycle():
    seen = {d: looks(d)[0] for d in (10, 25, 50, 75, 100)}
    # brightness the eye sees ≈ duty^0.6: half the light looks more than half as bright
    for d in (10, 25, 50, 75):
        assert seen[d] == pytest.approx((d / 100) ** 0.6, abs=0.05), seen
    assert seen[100] == pytest.approx(1.0, abs=0.01)
    assert seen[10] < seen[25] < seen[50] < seen[75] < seen[100]


def test_pwm_dims_a_bulb_too():
    seen = [looks(d)[1] for d in (25, 50, 75, 100)]
    assert seen == sorted(seen) and seen[0] < 0.1 and seen[-1] > 0.5


def test_instant_glow_is_still_on_or_off():
    s, led, _lamp = pwm_circuit(25)
    s.run_until(0.2)
    assert led.glow() in (0.0, 1.0) or led.glow() > 0.99 or led.glow() < 0.01


def test_paused_keeps_showing_the_same_brightness():
    s, led, _lamp = pwm_circuit(50)
    s.run_until(0.2)
    first = led.take_glow()
    assert led.take_glow() == first           # nothing has happened since: same as before, not the instant value


def test_in_slow_motion_you_see_it_flicker():
    """Slowed right down, each frame covers a tenth of a millisecond: the LED is seen going on and off."""
    s, led, _lamp = pwm_circuit(50)
    s.run_until(0.2)
    led.take_glow()
    D.Device.eye_window = 0.066 / 1000          # 1/1000 speed: the eye's moment is a tiny stretch of simulated time
    frames = []
    for _ in range(12):
        s.run_until(s.t + 0.0001)
        frames.append(led.take_glow())
    D.Device.eye_window = 0.066
    assert min(frames) < 0.2 and max(frames) > 0.9


def test_running_slower_than_real_time_still_looks_steady():
    """A busy circuit the computer can't keep up with gives each frame only a little simulated time; at
    'Real time' it must still look like it would in real life (steady), not blink."""
    s, led, _lamp = pwm_circuit(50)
    s.run_until(0.2)
    led.take_glow()
    frames = []
    for _ in range(40):
        s.run_until(s.t + 0.0002)                  # far less than a PWM cycle per frame
        frames.append(led.take_glow())
    assert max(frames[-20:]) - min(frames[-20:]) < 0.08


def test_a_blown_led_looks_dark():
    s, led, _lamp = pwm_circuit(100)
    s.run_until(0.05)
    led.blown = True
    assert led.take_glow() == 0.0


def test_pwm_dimmer_example_knob_sets_the_brightness():
    c = Circuit.load(os.path.join(ROOT, "examples", "PWM dimmer (555).wirely"))
    seen = []
    for setting in (10, 50, 90):
        s = Simulator(c)
        vr = next(d for d in s.devices if d.comp.kind == "potentiometer")
        s.set_value(vr.cid, "setting", setting)
        led = next(d for d in s.devices if d.comp.kind == "led")
        lamp = next(d for d in s.devices if d.comp.kind == "lamp")
        s.run_until(0.3, budget_s=30)
        led.take_glow(), lamp.take_glow()
        s.run_until(0.33, budget_s=30)
        seen.append((led.take_glow(), lamp.take_glow()))
        assert not s.struggling
    assert seen[0][0] < 0.35 < seen[1][0] < 0.7 < seen[2][0]
    assert seen[0][1] < seen[1][1] < seen[2][1]


def test_rgb_led_mixes_by_average_light():
    """PWM on one colour of an RGB LED changes the mix (how real colour mixing with PWM works)."""
    c, comps = build([("dc_supply", ("v", "0"), {"voltage": 5}),
                      ("signal_gen", ("p", "0"), {"waveform": "square", "frequency": 1000, "amplitude": 2.5,
                                                  "offset": 2.5, "duty": 25}),
                      ("resistor", ("v", "r"), {"resistance": 220}), ("resistor", ("p", "b"), {"resistance": 100}),
                      ("led_rgb", ("r", "g", "b", "0"), {}), ("resistor", ("g", "0"), {"resistance": 1e6})])
    s = Simulator(c)
    s.h_max = 1e-4
    rgb = s.device(comps[4].id)
    s.run_until(0.2)
    rgb.live_extra()
    s.run_until(0.22)
    rgb.live_extra()
    s.run_until(0.24)
    g = rgb.live_extra()["_glows"]
    red, blue = g[0], g[2]
    assert red > 0.9 and 0.2 < blue < 0.7, g
