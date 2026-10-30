"""1.5.0: crystal clock, stepper motor, rotary switch, keypad, JK flip-flop, Schmitt NAND — and the unit box
next to values in the properties box."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from test_sim import build  # noqa: E402

from wirely.model.circuit import Circuit  # noqa: E402
from wirely.model.units import join, split, unit_choices  # noqa: E402
from wirely.sim.engine import Simulator  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def run(spec, t, h=1e-3):
    c, comps = build(spec)
    s = Simulator(c)
    s.h_max = h
    s.run_until(t)
    return s, comps


def count_edges(s, cid, pin, t_end, vth=4.5):
    prev, n = None, 0
    while s.t < t_end:
        s.step(t_end - s.t)
        hi = s.pin_voltage(cid, pin) > vth
        if prev is not None and hi != prev:
            n += 1
        prev = hi
    return n


# ------------------------------------------------------------------------------------------- unit box
@pytest.mark.parametrize("value,unit,text,choice", [
    (4700, "Ω", "4.7", "kΩ"), (2.2e6, "Ω", "2.2", "MΩ"), (47, "Ω", "47", "Ω"), (1e-7, "F", "100", "nF"),
    (4.7e-6, "F", "4.7", "µF"), (22e-12, "F", "22", "pF"), (0.01, "H", "10", "mH"), (32768, "Hz", "32.768", "kHz")])
def test_values_split_into_a_number_and_its_size(value, unit, text, choice):
    assert split(value, unit) == (text, choice)
    assert join(text, choice, unit) == pytest.approx(value)


def test_typing_the_whole_value_beats_the_unit_box():
    assert join("4k7", "MΩ", "Ω") == pytest.approx(4700)
    assert join("100n", "µF", "F") == pytest.approx(100e-9)
    assert join("10", "MΩ", "Ω") == pytest.approx(10e6)
    assert unit_choices("Ω") == ["Ω", "kΩ", "MΩ"]
    with pytest.raises(ValueError):
        join("4.7x", "kΩ", "Ω")


def test_properties_box_has_a_unit_box():
    from PySide6.QtWidgets import QApplication
    from wirely.ui.dialogs import PropertiesDialog
    QApplication.instance() or QApplication([])
    c = Circuit()
    r = c.add("resistor", 0, 0, props={"resistance": 4700})
    d = PropertiesDialog(r, c)
    _p, w = d.fields["resistance"]
    box = d.unit_boxes["resistance"]
    assert (w.text(), box.currentText()) == ("4.7", "kΩ")
    w.setText("10")
    box.setCurrentText("MΩ")
    assert d._read()[0]["resistance"] == pytest.approx(10e6)
    w.setText("4k7")
    w.editingFinished.emit()                    # typed the whole value: it's tidied into number + size
    assert (w.text(), box.currentText()) == ("4.7", "kΩ")
    assert "power" not in d.unit_boxes          # watts: no box


def test_web_form_has_a_unit_box():
    sys.path.insert(0, os.path.join(ROOT, "web", "py"))
    import subprocess
    code = """
import json, wirely_web
app = wirely_web.App()
app.start_placing("capacitor"); app.press(0, 0, 1, 1, 0, 0, 0); app.release(0, 0, 1, 0, 0, 0, 0)
c = next(iter(app.circuit.components.values()))
f = json.loads(app.part_form(c.id))["fields"][0]
err = app.apply_form(c.id, json.dumps({"capacitance": "47", "capacitance__unit": "µF"}))
print(json.dumps([f["value"], f["unit"], f["units"], err, c.props["capacitance"], json.loads(app.tidy_value(c.id, "capacitance", "2n2", "µF"))]))
"""
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([os.path.join(ROOT, "web", "py"), ROOT]))
    env.pop("QT_QPA_PLATFORM", None)
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=ROOT, timeout=120)
    assert out.returncode == 0, out.stderr
    value, unit, units, err, cap, tidy = json.loads(out.stdout.strip().splitlines()[-1])
    assert (value, unit, units[:3], err) == ("100", "nF", ["pF", "nF", "µF"], "")
    assert cap == pytest.approx(47e-6) and tidy == ["2.2", "nF"]


# ------------------------------------------------------------------------------------------- new parts
@pytest.mark.parametrize("freq", [1, 10, 100])
def test_crystal_clock_is_exact(freq):
    c, comps = build([("dc_supply", ("v", "0"), {"voltage": 9}), ("xtal_clock", ("o",), {"frequency": freq}),
                      ("resistor", ("o", "0"), {"resistance": 10e3})])
    s = Simulator(c)
    s.h_max = 1e-3
    assert count_edges(s, comps[1].id, "OUT", 2.0 + 0.25 / freq) == 4 * freq


def test_jk_flip_flop_truth_table():
    def q_after(j, k, start):
        c, comps = build([("dc_supply", ("v", "0"), {"voltage": 9}),
                          ("xtal_clock", ("clk",), {"frequency": 10}),
                          ("jkff", ("v" if j else "0", "clk", "v" if k else "0", "s", "0", "q", "qn"), {}),
                          ("switch", ("v", "s"), {"closed": start})])
        s = Simulator(c)
        s.h_max = 1e-3
        s.run_until(0.05)                       # S sets the starting state
        s.set_value(comps[3].id, "closed", False)
        s.run_until(0.15)                       # one rising edge, at 0.1 s
        return s.pin_voltage(comps[2].id, "Q") > 4.5, s.pin_voltage(comps[2].id, "Qn") > 4.5
    assert q_after(0, 0, True) == (True, False)       # keep
    assert q_after(0, 0, False) == (False, True)
    assert q_after(1, 0, False) == (True, False)      # set
    assert q_after(0, 1, True) == (False, True)       # reset
    assert q_after(1, 1, True) == (False, True)       # toggle
    assert q_after(1, 1, False) == (True, False)


def test_jk_flip_flops_divide_by_two():
    c, comps = build([("dc_supply", ("v", "0"), {"voltage": 9}), ("xtal_clock", ("clk",), {"frequency": 10}),
                      ("jkff", ("v", "clk", "v", "0", "0", "q", "qn"), {})])
    s = Simulator(c)
    s.h_max = 1e-3
    assert count_edges(s, comps[2].id, "Q", 1.05) == 10          # 5 Hz


def test_schmitt_nand_oscillator():
    c, comps = build([("dc_supply", ("v", "0"), {"voltage": 9}), ("schmitt_nand", ("v", "b", "y"), {}),
                      ("resistor", ("y", "b"), {"resistance": 100e3}), ("capacitor", ("b", "0"), {"capacitance": 1e-6})])
    s = Simulator(c)
    s.h_max = 1e-3
    f = count_edges(s, comps[1].id, "Y", 2.0) / 4
    assert f == pytest.approx(1 / (2 * 0.1 * 0.693), rel=0.1)     # thresholds at 1/3 and 2/3


def test_schmitt_nand_held_off_by_its_enable():
    c, comps = build([("dc_supply", ("v", "0"), {"voltage": 9}), ("schmitt_nand", ("0", "b", "y"), {}),
                      ("resistor", ("y", "b"), {"resistance": 100e3}), ("capacitor", ("b", "0"), {"capacitance": 1e-6})])
    s = Simulator(c)
    s.h_max = 1e-3
    assert count_edges(s, comps[1].id, "Y", 1.0) == 0


def test_stepper_turns_one_step_per_coil_change():
    s, c = run([("dc_supply", ("v", "0"), {"voltage": 12}), ("stepper", ("a1", "0", "b1", "0"), {"steps": "48"}),
                ("switch", ("v", "a1"), {"closed": True}), ("switch", ("v", "b1"), {"closed": False})], 0.1)
    m = s.device(c[1].id)
    assert m.step_count == 0
    s.set_value(c[3].id, "closed", True)           # A and B: half way between
    s.set_value(c[2].id, "closed", False)          # just B: a full step
    s.run_until(0.2)
    assert m.step_count == 1 and m.angle == pytest.approx(7.5, abs=0.2)
    assert m.current == pytest.approx(12 / 40, rel=0.02)          # 12 V across a 40 Ω coil


def test_stepper_example_turns():
    c = Circuit.load(os.path.join(ROOT, "examples", "Motor paso a paso (reloj de cuarzo + L293D).wirely"))
    s = Simulator(c)
    s.h_max = 1e-3
    s.run_until(3.1)                            # a step every 0.25 s
    m = next(d for d in s.devices if d.comp.kind == "stepper")
    assert m.step_count == 12 and m.angle == pytest.approx(90, abs=1)
    assert not s.take_events()


def test_rotary_switch_picks_one_contact():
    s, c = run([("dc_supply", ("v", "0"), {"voltage": 9}), ("rotary", ("v", "a", "b", "c", "d"), {"position": "3"})]
               + [("resistor", (n, "0"), {"resistance": 1000}) for n in "abcd"], 0.01)
    assert [round(s.pin_voltage(c[1].id, p)) for p in "1234"] == [0, 0, 9, 0]


@pytest.mark.parametrize("key,row,col", [("1", 1, 1), ("5", 2, 2), ("9", 3, 3), ("*", 4, 1), ("0", 4, 2), ("#", 4, 3)])
def test_keypad_joins_the_keys_row_and_column(key, row, col):
    c, comps = build([("dc_supply", ("v", "0"), {"voltage": 9}),
                      ("keypad", ("r1", "r2", "r3", "r4", "c1", "c2", "c3"), {})]
                     + [("resistor", (f"r{i}", "0"), {"resistance": 1000}) for i in range(1, 5)]
                     + [("resistor", ("v", f"c{i}"), {"resistance": 1000}) for i in range(1, 4)])
    s = Simulator(c)
    s.run_until(0.01)
    s.set_value(comps[1].id, "_key", key)
    s.run_until(0.02)
    rows = [s.pin_voltage(comps[1].id, f"R{i}") > 1 for i in range(1, 5)]
    assert rows == [i == row for i in range(1, 5)]
    assert s.pin_voltage(comps[1].id, f"C{col}") == pytest.approx(4.5, abs=0.1)


def test_new_examples_behave():
    def load(name):
        c = Circuit.load(os.path.join(ROOT, "examples", f"{name}.wirely"))
        s = Simulator(c)
        s.h_max = 1e-3
        return s
    s = load("Contador binario (flip-flops JK)")
    leds = sorted((d for d in s.devices if d.comp.kind == "led"), key=lambda d: d.comp.ref)
    seq = []
    for k in range(1, 6):
        s.run_until(k * 0.5 - 0.1)
        seq.append("".join("1" if d.glow() > 0.3 else "0" for d in reversed(leds)))
    assert seq == ["00", "01", "10", "11", "00"]
    s = load("Conmutador rotatorio (elegir un LED)")
    sw = next(d for d in s.devices if d.comp.kind == "rotary")
    for pos, colour in zip("1234", ("Rojo", "Amarillo", "Verde", "Azul")):
        s.set_value(sw.cid, "position", pos)
        s.run_until(s.t + 0.05)
        assert [d.comp.value("colour") for d in s.devices if d.comp.kind == "led" and d.glow() > 0.3] == [colour]
    s = load("Teclado (qué tecla se presiona)")
    kp = next(d for d in s.devices if d.comp.kind == "keypad")
    s.run_until(0.02)
    s.set_value(kp.cid, "_key", "5")
    s.run_until(0.05)
    assert sorted(d.comp.value("colour") for d in s.devices if d.comp.kind == "led" and d.glow() > 0.3) == \
        ["Azul", "Naranja"]
    s = load("Intermitente con NAND Schmitt (4093)")
    led = next(d for d in s.devices if d.comp.kind == "led")
    s.run_until(0.5)
    assert led.glow() == 0                                            # off until S1 is closed


def test_clicking_a_keypad_key_while_running():
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtWidgets import QApplication, QGraphicsScene
    from wirely.ui.scene import CircuitScene
    from wirely.ui.simcontrol import SimController
    QApplication.instance() or QApplication([])

    class Click:
        def __init__(self, p):
            self.p = p

        def scenePos(self):
            return self.p

        def button(self):
            return Qt.LeftButton

        def accept(self):
            pass
    c = Circuit.load(os.path.join(ROOT, "examples", "Teclado (qué tecla se presiona).wirely"))
    sc = CircuitScene(c)
    simc = SimController()
    sc.attach_sim(simc)
    simc.start(c)
    simc._tick()
    kp = next(it for it in sc.comp_items.values() if it.comp.kind == "keypad")
    orig = QGraphicsScene.mouseReleaseEvent
    QGraphicsScene.mouseReleaseEvent = lambda self, e: None
    try:
        sc._sim_press(Click(kp.pos() + QPointF(0, -18)))               # the "5" key
        assert kp.comp.props.get("_key") == "5"
        sc._sim_release(Click(kp.pos() + QPointF(0, -18)))
        assert "_key" not in kp.comp.props
    finally:
        QGraphicsScene.mouseReleaseEvent = orig
        simc.stop()


def test_rotary_switch_steps_round_when_clicked():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from wirely.ui.scene import CircuitScene
    from wirely.ui.simcontrol import SimController
    QApplication.instance() or QApplication([])

    class Click:
        def __init__(self, p):
            self.p = p

        def scenePos(self):
            return self.p

        def button(self):
            return Qt.LeftButton

        def accept(self):
            pass
    c = Circuit.load(os.path.join(ROOT, "examples", "Conmutador rotatorio (elegir un LED).wirely"))
    sc = CircuitScene(c)
    simc = SimController()
    sc.attach_sim(simc)
    simc.start(c)
    sw = next(it for it in sc.comp_items.values() if it.comp.kind == "rotary")
    seen = []
    for _ in range(4):
        sc._sim_press(Click(sw.pos()))
        seen.append(sw.comp.value("position"))
    simc.stop()
    assert seen == ["2", "3", "4", "1"]
