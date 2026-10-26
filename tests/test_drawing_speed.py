"""Drawing less while it runs (1.5.1): the grid is kept ready-drawn, parts and wires keep a picture that is only
redrawn when they change, and a frame where nothing looks any different isn't drawn at all — but nothing may
ever be left showing out of date."""
import glob
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from test_editor import app, win  # noqa: E402,F401

from wirely.model.circuit import Circuit  # noqa: E402
from wirely.sim.flow import FlowNetwork  # noqa: E402
from wirely.ui import export as EX  # noqa: E402
from wirely.ui import theme  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def lamp_circuit():
    c = Circuit()
    b = c.add("battery", 0, 0, rot=1)
    sw = c.add("switch", 80, -60)
    led = c.add("led", 160, 0, rot=1)
    r = c.add("resistor", 160, 90, rot=1, props={"resistance": 470})
    c.add_wire([b.pin_positions()["+"], (0, -60), sw.pin_positions()["1"]])
    c.add_wire([sw.pin_positions()["2"], (160, -60), led.pin_positions()["A"]])
    c.add_wire([led.pin_positions()["K"], r.pin_positions()["1"]])
    c.add_wire([r.pin_positions()["2"], (160, 150), (0, 150), b.pin_positions()["-"]])
    return c, sw, led


def ticks(w, n):
    for _ in range(n):
        time.sleep(0.02)                    # roughly a real frame's worth of time
        w.simc._tick()
        app.processEvents()


def start(w, c):
    w._set_circuit(c, None)
    w.a_flow.setChecked(False)
    w._toggle_flow()
    w.a_play.trigger()
    w.simc._timer.stop()          # step it by hand
    ticks(w, 5)


def test_a_settled_circuit_isnt_drawn_again_and_again(win):
    c, sw, led = lamp_circuit()
    start(win, c)
    ticks(win, 3)
    assert win.scene.frame_changed is False
    # switch it on: the LED and its wires change look, so they (and the frame) are drawn again
    win.scene.sim_set_value(sw.id, "closed", True)
    ticks(win, 1)
    assert win.scene.frame_changed is True
    assert win.scene.comp_items[led.id].look is not None
    ticks(win, 10)
    assert win.scene.live_part(led.id)["_glow"] > 0.5
    assert win.scene.frame_changed is False


def test_moving_current_dots_keep_drawing(win):
    c, sw, _led = lamp_circuit()
    sw.props["closed"] = True
    win._set_circuit(c, None)
    win.a_flow.setChecked(True)
    win._toggle_flow()
    win.a_play.trigger()
    win.simc._timer.stop()
    for _ in range(5):
        time.sleep(0.033)                   # a real frame's worth of time, so the dots move
        win.simc._tick()
        assert win.scene.frame_changed is True


def test_theme_and_voltage_colours_redraw_everything_even_when_paused(win):
    c, sw, led = lamp_circuit()
    sw.props["closed"] = True
    start(win, c)
    win.a_pause.trigger()
    wire = next(iter(win.scene.wire_items.values()))
    assert wire.look is not None                       # coloured by its voltage
    win.a_volts.setChecked(False)
    win._toggle_volts()
    assert wire.look is None                           # plain again straight away, not on the next frame
    win.a_volts.setChecked(True)
    win._toggle_volts()
    assert wire.look is not None
    win.set_theme("dark" if theme.MODE == "light" else "light")
    assert all(it.look != ("stale",) for it in win.scene.comp_items.values())
    win.a_stop.trigger()
    assert all(it.look is None for it in win.scene.comp_items.values())
    assert all(it.look is None for it in win.scene.wire_items.values())


def test_export_while_running_in_dark_theme_is_in_paper_colours(win):
    """Exporting must draw everything afresh in paper colours, never reuse the dark pictures kept for the screen:
    the picture is the same as one exported in the light theme with the simulation stopped."""
    c, _sw, _led = lamp_circuit()
    win._set_circuit(c, None)
    paper = EX.render_image(win.scene, 1.0)
    start(win, c)
    win.set_theme("dark")
    app.processEvents()
    img = EX.render_image(win.scene, 1.0)
    win.set_theme("light")
    assert img.size() == paper.size()
    differ = sum(1 for x in range(0, img.width(), 2) for y in range(0, img.height(), 2)
                 if img.pixelColor(x, y) != paper.pixelColor(x, y))
    assert differ == 0
    assert all(it.cacheMode() == it.CacheMode.DeviceCoordinateCache for it in win.scene.comp_items.values())


def test_flow_reuses_its_answer_only_when_the_currents_are_the_same():
    path = glob.glob(os.path.join(ROOT, "examples", "Night light*.wirely"))[0]
    c = Circuit.load(path)
    fs = FlowNetwork(c)
    currents = {}

    def pin_current(cid, pin):
        return currents.get((cid, pin), 0.0)
    b = next(cp for cp in c.components.values() if cp.kind == "led")
    currents[(b.id, "A")] = 0.01
    currents[(b.id, "K")] = -0.01
    first = fs.solve(pin_current)
    again = fs.solve(pin_current)
    assert first == again
    currents[(b.id, "A")] = 0.02
    currents[(b.id, "K")] = -0.02
    fresh = FlowNetwork(c).solve(pin_current)
    assert fs.solve(pin_current) == fresh             # changed currents: worked out again, not reused
    assert fresh != first
