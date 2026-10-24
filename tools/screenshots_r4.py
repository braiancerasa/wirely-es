"""Screenshots of the r4 features.  xvfb-run -a -s "-screen 0 1600x1000x24" python tools/screenshots_r4.py out/"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ.setdefault("WIRELY_NO_SOUND", "1")
from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])
import test_editor as T  # noqa: E402,F401
from wirely.ui.mainwindow import EXAMPLES, MainWindow  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(out, exist_ok=True)


def run_for(seconds):
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        app.processEvents()
        time.sleep(0.005)


def shot(name):
    run_for(0.3)
    w.grab().save(os.path.join(out, name))
    print("saved", name)


def find(kind):
    return next(c for c in w.circuit.components.values() if c.kind == kind)


w = MainWindow()
w.set_theme("light")
w.resize(1440, 900)
w.show()
run_for(0.3)

w.open_file(os.path.join(EXAMPLES, "Relay switching a lamp.wirely"))
w.a_play.trigger()
run_for(0.3)
sw = find("switch")
T.click(w, (sw.x, sw.y))
run_for(0.6)
q = find("npn")
T.move(w, (q.x + 10, q.y - 45), held=False)       # hover the coil wire
shot("r4_relay.png")
w.a_stop.trigger()

w.open_file(os.path.join(EXAMPLES, "Motor and load.wirely"))
find("motor").props["load"] = "Medium"
w.a_play.trigger()
run_for(0.2)
T.click(w, (find("switch").x, find("switch").y))
run_for(1.2)
m = find("motor")
T.move(w, (m.x, m.y), held=False)
run_for(0.3)
shot("r4_motor.png")
w.a_stop.trigger()
find("motor").props["load"] = "None"

w.open_file(os.path.join(EXAMPLES, "Burglar alarm (reed switch).wirely"))
w.a_play.trigger()
run_for(0.2)
T.click(w, (find("reed_switch").x, find("reed_switch").y))
run_for(0.6)
shot("r4_burglar.png")
w.a_stop.trigger()

w.set_theme("dark")
w.open_file(os.path.join(EXAMPLES, "Rain alarm (moisture sensor).wirely"))
find("moisture").props["moisture"] = 70.0
w.a_play.trigger()
run_for(0.6)
shot("r4_rain_dark.png")
w.a_stop.trigger()
w.set_theme("light")

w.open_file(os.path.join(EXAMPLES, "Relay switching a lamp.wirely"))
for cat in w.gallery.categories:
    cat.set_open(cat.name in ("Input sensors", "Switches", "Capacitors & inductors", "Labels"))
shot("r4_gallery.png")
w.undo.setClean()
w.close()
