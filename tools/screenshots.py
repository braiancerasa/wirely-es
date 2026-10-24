"""Takes screenshots of Wirely for checking and for the README.  Run (Linux):
    xvfb-run -a -s "-screen 0 1440x900x24" python tools/screenshots.py docs/images
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from PySide6.QtCore import QPointF, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

import test_editor as T  # noqa: E402  (reuses the mouse helpers)
from wirely.ui.mainwindow import EXAMPLES, MainWindow  # noqa: E402
from wirely.ui import export as EX  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(out, exist_ok=True)


def settle(ms=350):
    end = QTimer()
    end.setSingleShot(True)
    loop_done = []
    end.timeout.connect(lambda: loop_done.append(1))
    end.start(ms)
    while not loop_done:
        app.processEvents()


def shot(w, name):
    settle()
    w.grab().save(os.path.join(out, name))
    print("saved", name)


w = MainWindow()
w.set_theme("light")
w.resize(1360, 820)
w.show()
settle()

# 1. empty sheet
shot(w, "01_empty.png")

# 2. an example circuit
w.open_file(os.path.join(EXAMPLES, "Night light.wirely"))
shot(w, "02_night_light.png")

# 3. building a circuit by hand: parts placed, one wire half drawn
w.new_file()
w.view.resetTransform()
w.view.scale(2.0, 2.0)
w.view.centerOn(110, 70)
settle()
b = T.place(w, "battery", 0, 80)
w.scene.select_ids([b.id])
w.a_rotate.trigger()                     # + at the top
sw = T.place(w, "push_make", 80, 0)
r = T.place(w, "resistor", 180, 0)
led = T.place(w, "led", 250, 80)
w.scene.select_ids([led.id])
w.a_rotate.trigger()
T.drag(w, b.pin_positions()["+"], sw.pin_positions()["1"])
T.drag(w, sw.pin_positions()["2"], r.pin_positions()["1"])
w.scene.clearSelection()
a = r.pin_positions()["2"]
T.press(w, a)
for i in range(1, 7):
    T.move(w, (a[0] + (250 - a[0]) * i / 7, a[1] + (50 - a[1]) * i / 7))
T.move(w, led.pin_positions()["A"])
shot(w, "03_drawing_a_wire.png")
T.release(w, led.pin_positions()["A"])
w.scene.cancel()
w.scene.set_mode("wire")
T.drag(w, led.pin_positions()["K"], (250, 160))
T.drag(w, (250, 160), (0, 160))
T.drag(w, (0, 160), b.pin_positions()["-"])
w.scene.set_mode("select")
w.scene.select_ids([r.id])
w.scene.comp_items[r.id].hover = False
shot(w, "04_finished_selected.png")

# 4. the properties box
from wirely.ui.dialogs import PropertiesDialog  # noqa: E402
d = PropertiesDialog(led, w.circuit, w)
d.show()
settle()
d.grab().save(os.path.join(out, "05_properties.png"))
print("saved 05_properties.png")
d.close()

# 5. dark theme
w.scene.clearSelection()
w.set_theme("dark")
w.open_file(os.path.join(EXAMPLES, "Voltage divider.wirely"))
w.scene.select_ids([next(c.id for c in w.circuit.components.values() if c.ref == "R2")])
shot(w, "06_dark.png")
w.set_theme("light")

# 6. an export (always on white paper)
w.open_file(os.path.join(EXAMPLES, "Two-way light switch.wirely"))
EX.export_png(w.scene, os.path.join(out, "07_export.png"), 2.0)
print("saved 07_export.png")
w.undo.setClean()
w.close()


# ---------------------------------------------------------------------------- r2: the simulation running
import time  # noqa: E402


def run_for(seconds):
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        app.processEvents()
        time.sleep(0.005)


def find(kind):
    return next(c for c in w.circuit.components.values() if c.kind == kind)


w = MainWindow()
w.set_theme("light")
w.resize(1360, 820)
w.show()
settle()

w.open_file(os.path.join(EXAMPLES, "Night light.wirely"))
find("ldr").props["light"] = 2.0
w.a_play.trigger()
run_for(0.8)
shot(w, "08_sim_night_light.png")
w.a_stop.trigger()

w.open_file(os.path.join(EXAMPLES, "LED and resistor.wirely"))
w.a_play.trigger()
run_for(0.2)
T.click(w, (find("switch").x, find("switch").y))
run_for(0.6)
shot(w, "09_sim_led.png")
w.a_stop.trigger()

from wirely.model.circuit import Circuit  # noqa: E402
c = Circuit()
b = c.add("battery", 0, 0, rot=1)
led = c.add("led", 120, 0, rot=1, props={"colour": "Blue"})
c.add_wire([b.pin_positions()["+"], (0, -60), (120, -60), led.pin_positions()["A"]])
c.add_wire([led.pin_positions()["K"], (120, 60), (0, 60), b.pin_positions()["-"]])
w._set_circuit(c, None)
w.a_play.trigger()
run_for(0.6)
shot(w, "10_sim_pop.png")
w.a_stop.trigger()
w.undo.setClean()

w.set_theme("dark")
w.open_file(os.path.join(EXAMPLES, "Capacitor charging.wirely"))
w.speed_box.setCurrentText("10× faster")
w.a_play.trigger()
run_for(0.45)
shot(w, "11_sim_capacitor_dark.png")
w.a_stop.trigger()
w.speed_box.setCurrentText("Real time")

w.set_theme("light")
w.open_file(os.path.join(EXAMPLES, "Buzzer and motor.wirely"))
w.a_play.trigger()
run_for(0.2)
T.click(w, (find("switch").x, find("switch").y))
T.press(w, (find("push_make").x, find("push_make").y - 5))
run_for(0.7)
shot(w, "12_sim_buzzer_motor.png")
T.release(w, (find("push_make").x, find("push_make").y - 5))
w.a_stop.trigger()
w.undo.setClean()
w.close()
