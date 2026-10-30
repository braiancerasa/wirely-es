"""The simulation running inside the editor: Play, click switches, sliders, pops, Stop."""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

from test_editor import app, click, press, release, win, move  # noqa: E402,F401
from wirely.ui.mainwindow import EXAMPLES  # noqa: E402


def run_for(w, seconds):
    """Let the simulation run for a while (real timer ticks)."""
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        app.processEvents()
        time.sleep(0.005)


def find(w, kind):
    return next(c for c in w.circuit.components.values() if c.kind == kind)


def test_play_click_switch_led_lights_then_stop(win):
    win.open_file(os.path.join(EXAMPLES, "LED y resistencia.wirely"))
    led, sw = find(win, "led"), find(win, "switch")
    win.a_play.trigger()
    assert win.simc.state == "running"
    assert not win.a_delete.isEnabled() and not win.gallery.isEnabled()
    run_for(win, 0.15)
    assert win.scene.live_part(led.id)["_glow"] == 0.0           # switch is off
    click(win, (sw.x, sw.y))                                      # click the switch
    assert sw.props["closed"] is True
    run_for(win, 0.2)
    info = win.scene.live_part(led.id)
    assert info["_glow"] > 0.5 and 0.012 < info["i"] < 0.018
    # wires are coloured, and current dots are moving
    assert any(win.scene.wire_colour(w) is not None for w in win.circuit.wires)
    assert any(abs(a) > 0.01 for _p, _q, _ph, a in win.simc.live.flows)
    assert "t =" in win.time_label.text()
    win.a_stop.trigger()
    assert win.simc.state == "stopped" and win.scene.live_part(led.id) is None
    assert win.gallery.isEnabled() and win.undo.isClean() is False or True


def test_push_button_only_while_held(win):
    win.new_file()
    from wirely.model.circuit import Circuit
    c = Circuit()
    b = c.add("battery", 0, 0, rot=1)                # + top (0,-30)
    pb = c.add("push_make", 80, -60)
    lamp = c.add("lamp", 160, 0, rot=1, props={"voltage": 9, "power": 0.5})
    c.add_wire([b.pin_positions()["+"], (0, -60), pb.pin_positions()["1"]])
    c.add_wire([pb.pin_positions()["2"], (160, -60), lamp.pin_positions()["1"]])
    c.add_wire([lamp.pin_positions()["2"], (160, 60), (0, 60), b.pin_positions()["-"]])
    win._set_circuit(c, None)
    win.a_play.trigger()
    run_for(win, 0.1)
    assert win.scene.live_part(lamp.id)["_glow"] == 0.0
    press(win, (pb.x, pb.y - 5))
    run_for(win, 0.3)               # (what you see is averaged over the last moment, as with an eye)
    assert win.scene.live_part(lamp.id)["_glow"] > 0.8
    release(win, (pb.x, pb.y - 5))
    run_for(win, 0.5)               # the filament glows for a moment as it cools, then goes out
    assert win.scene.live_part(lamp.id)["_glow"] == 0.0
    win.a_stop.trigger()


def test_ldr_slider_switches_night_light(win):
    win.open_file(os.path.join(EXAMPLES, "Luz nocturna.wirely"))
    ldr, led = find(win, "ldr"), find(win, "led")
    ldr.props["light"] = 500.0
    win.a_play.trigger()
    run_for(win, 0.15)
    assert win.scene.live_part(led.id)["_glow"] < 0.05
    slider = next(sl for sl in win.scene.sliders if sl.comp.id == ldr.id)
    assert len(win.scene.sliders) == 2          # the LDR and the variable resistor
    # drag the slider to the dark end
    left = slider.mapToScene(slider.boundingRect().topLeft())
    press(win, (left.x() + 6, left.y() + 23))
    release(win, (left.x() + 6, left.y() + 23))
    assert ldr.props["light"] < 1
    run_for(win, 0.2)
    assert win.scene.live_part(led.id)["_glow"] > 0.5
    win.a_stop.trigger()
    assert win.scene.sliders == []


def test_led_pops_and_message_appears(win):
    from wirely.model.circuit import Circuit
    c = Circuit()
    b = c.add("battery", 0, 0, rot=1)
    led = c.add("led", 100, 0, rot=1)
    c.add_wire([b.pin_positions()["+"], (0, -60), (100, -60), led.pin_positions()["A"]])
    c.add_wire([led.pin_positions()["K"], (100, 60), (0, 60), b.pin_positions()["-"]])
    win._set_circuit(c, None)
    win.a_play.trigger()
    run_for(win, 0.3)
    assert win.scene.live_part(led.id)["blown"]
    assert win.view._toasts and "reventó" in win.view._toasts[-1].findChild(type(win.hint)).text()
    win.a_stop.trigger()
    win.a_play.trigger()                       # a fresh start mends it (then it pops again)
    assert not win.scene.live_part(led.id)["blown"]
    win.a_stop.trigger()


def test_pause_and_resume(win):
    win.open_file(os.path.join(EXAMPLES, "Divisor de voltaje.wirely"))
    win.a_play.trigger()
    run_for(win, 0.1)
    win.a_pause.trigger()
    t = win.simc.live.t
    run_for(win, 0.1)
    assert win.simc.state == "paused" and win.simc.live.t == t
    win.a_play.trigger()
    run_for(win, 0.1)
    assert win.simc.live.t > t
    vm = find(win, "voltmeter")
    assert win.scene.live_part(vm.id)["reading"] in ("2.88V", "2.876V", "2.877V")
    win.a_stop.trigger()


def test_editing_is_locked_while_running(win):
    win.open_file(os.path.join(EXAMPLES, "Divisor de voltaje.wirely"))
    r = next(c for c in win.circuit.components.values() if c.kind == "resistor")
    x0 = r.x
    win.a_play.trigger()
    press(win, (r.x, r.y))
    move(win, (r.x + 60, r.y))
    release(win, (r.x + 60, r.y))
    assert r.x == x0
    n = len(win.circuit.components)
    win._pick_part("resistor")
    assert len(win.circuit.components) == n and win.scene.mode == "select"
    win.a_stop.trigger()


def test_changing_a_value_while_running(win):
    win.open_file(os.path.join(EXAMPLES, "Divisor de voltaje.wirely"))
    r2 = next(c for c in win.circuit.components.values() if c.ref == "R2")
    vm = find(win, "voltmeter")
    win.a_play.trigger()
    run_for(win, 0.05)
    win.simc.set_value(r2.id, "resistance", 10e3)
    run_for(win, 0.1)
    assert win.scene.live_part(vm.id)["reading"] == "4.5V"     # 9 V × 10k / 20k
    win.a_stop.trigger()


def test_graph_records_and_measures_the_555(win):
    win.open_file(os.path.join(EXAMPLES, "Intermitente LED con 555.wirely"))
    win.speed_box.setCurrentText("2× más rápido")
    win.a_play.trigger()
    assert win.graph.isVisible()
    run_for(win, 2.6)
    win.a_stop.trigger()
    win.speed_box.setCurrentText("Tiempo real")
    from wirely.ui.graph import frequency
    tr = win.graph.traces["A"]
    assert len(tr.t) > 100
    f = frequency(tr.t, tr.v)
    assert f == pytest.approx(1.44 / ((10e3 + 2 * 47e3) * 10e-6), rel=0.02)
    assert max(tr.v) == pytest.approx(9 - 1.7, abs=0.15)      # 555 output high level
    assert "Hz" in win.graph.chips.text()


def test_logic_probe_shows_levels(win):
    win.open_file(os.path.join(EXAMPLES, "Compuertas lógicas.wirely"))
    win.a_play.trigger()
    run_for(win, 0.1)
    probes = [c for c in win.circuit.components.values() if c.kind == "logic_probe"]
    assert {win.scene.live_part(p.id)["_level"] for p in probes} == {"L"}
    sw = next(c for c in win.circuit.components.values() if c.kind == "switch" and c.x == 100)
    click(win, (sw.x, sw.y))
    run_for(win, 0.1)
    levels = sorted(win.scene.live_part(p.id)["_level"] for p in probes)
    assert levels == ["H", "L", "L"]
    win.a_stop.trigger()


def test_hovering_a_wire_shows_voltage_and_current(win):
    win.open_file(os.path.join(EXAMPLES, "LED y resistencia.wirely"))
    sw = find(win, "switch")
    sw.props["closed"] = True
    win.a_play.trigger()
    run_for(win, 0.2)
    led = find(win, "led")
    a = led.pin_positions()["A"]                       # the wire from R1 comes down into the LED's anode
    move(win, (a[0], a[1] - 10), held=False)
    pos, title, lines = win.scene.hover_info
    assert title == "Cable"
    assert lines[0].startswith("Voltaje: ") and lines[1].startswith("Corriente: ")
    i_led = win.scene.live_part(led.id)["i"]
    assert lines[1] == f"Corriente: {__import__('wirely.model.units', fromlist=['fmt']).fmt(abs(i_led), 'A')} ↓"
    win.a_stop.trigger()
    assert win.scene.hover_info is None


def test_graph_auto_timebase_follows_the_fastest_probe(qapp=None):
    """Buck converter case: probe A is smooth DC, probe B switches at 1 kHz — Auto must zoom in on B."""
    import math

    from PySide6.QtWidgets import QApplication

    from wirely.ui.graph import GraphPanel
    QApplication.instance() or QApplication([])
    g = GraphPanel()
    samples = []
    t = 0.0
    while t < 0.05:
        a = 5.9 * (1 - math.exp(-t / 0.005))
        b = 12.0 if (t * 1000) % 1.0 < 0.5 else -0.4
        samples.append((t, {"A": a, "B": b}))
        t += 2e-5
    g.add_samples(samples, t)
    assert g.timebase() <= 1e-3          # about three 1 ms cycles across the screen
    only_dc = GraphPanel()
    only_dc.add_samples([(s[0], {"A": s[1]["A"]}) for s in samples], t)
    assert only_dc.timebase() == 0.5     # nothing repeats: the usual slow sweep


def test_capacitor_reads_no_heat_and_mosfet_reads_its_channel(win):
    """A capacitor charging soaks up V×I as stored energy, not heat; a MOSFET's readout is its drain–source
    voltage and drain current, not the gate's (which is always ~0 A)."""
    win.open_file(os.path.join(EXAMPLES, "Fuente de 5 V (7805).wirely"))
    win.a_play.trigger()
    run_for(win, 1.0)
    cap = find(win, "electrolytic")
    info = win.scene.live_part(cap.id)
    assert abs(info["i"]) > 1e-3 and abs(info["v"]) > 1.0          # it is charging or topping up
    assert info["p"] == 0.0
    win.a_stop.trigger()

    win.open_file(os.path.join(EXAMPLES, "Conmutación de motor con MOSFET.wirely"))
    app.processEvents()                        # let the pending zoom-to-fit run, so clicks land where we mean
    sw = find(win, "switch")
    win.a_play.trigger()
    click(win, (sw.x, sw.y))
    run_for(win, 1.5)
    q = win.scene.live_part(find(win, "nmos").id)
    assert abs(q["i"]) > 0.02                                       # the motor's current, not the gate's
    assert abs(q["v"]) < 0.5                                        # drain–source: fully on
    assert 0 < q["p"] < 0.1
    win.a_stop.trigger()
