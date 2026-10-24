"""Screenshots of the r3 features.  xvfb-run -a -s "-screen 0 1440x900x24" python tools/screenshots_r3.py out/"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
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


w = MainWindow()
w.set_theme("light")
w.resize(1440, 900)
w.show()
run_for(0.3)


def demo(name, seconds, fname, before=None):
    w.open_file(os.path.join(EXAMPLES, name + ".wirely"))
    if before:
        before()
    w.a_play.trigger()
    run_for(seconds)
    shot(fname)
    w.a_stop.trigger()
    w.undo.setClean()


demo("555 LED flasher", 3.2, "r3_555_graph.png")
demo("LED chaser (555 + 4017)", 1.6, "r3_chaser.png")
demo("Logic gates", 0.6, "r3_logic.png",
     lambda: [setattr(s, "props", dict(s.props, closed=True)) for s in w.circuit.components.values()
              if s.kind == "switch" and s.x == 100])
demo("Binary to 7-segment", 0.6, "r3_7seg.png")
demo("Op-amp dark sensor", 0.6, "r3_opamp.png",
     lambda: [c.props.__setitem__("light", 2.0) for c in w.circuit.components.values() if c.kind == "ldr"])
w.set_theme("dark")
demo("RC filter on the graph", 1.6, "r3_rc_dark.png")
w.set_theme("light")
w.open_file(os.path.join(EXAMPLES, "MOSFET motor switch.wirely"))
w.gallery.search.setText("")
for cat in w.gallery.categories:
    cat.set_open(cat.name in ("Logic gates", "Integrated circuits"))
shot("r3_gallery.png")
w.undo.setClean()
w.close()
