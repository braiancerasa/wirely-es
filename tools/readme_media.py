"""Make the README pictures and animations.

    xvfb-run -a -s "-screen 0 1600x1000x24" python tools/readme_media.py docs/images

Needs ffmpeg on the PATH for the animated GIFs (PNG screenshots work without it).
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ.setdefault("WIRELY_NO_SOUND", "1")
from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])
import test_editor as T  # noqa: E402
from wirely.model.circuit import Circuit  # noqa: E402
from wirely.ui import export as EX  # noqa: E402
from wirely.ui.dialogs import BomDialog, PropertiesDialog  # noqa: E402
from wirely.ui.live_items import TRACK_Y  # noqa: E402
from wirely.ui.live_items import W as SLIDER_W  # noqa: E402
from wirely.ui.mainwindow import EXAMPLES, MainWindow  # noqa: E402

out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "docs/images")
os.makedirs(out, exist_ok=True)
FPS = 12
GIF_WIDTH = 960


def run_for(seconds):
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        app.processEvents()
        time.sleep(0.004)


def find(kind):
    return next(c for c in w.circuit.components.values() if c.kind == kind)


def shot(name, widget=None):
    run_for(0.3)
    (widget or w).grab().save(os.path.join(out, name))
    print("saved", name)


def example(name):
    w.open_file(os.path.join(EXAMPLES, name + ".wirely"))
    run_for(0.2)


# ------------------------------------------------------------------ GIF recorder (with a drawn mouse pointer)
class Recorder:
    def __init__(self, name, whole=False):
        self.name = name
        self.target = w if whole else w.split      # just the drawing (and graph) unless asked for the whole window
        self.dir = tempfile.mkdtemp(prefix="wirely_gif_")
        self.n = 0
        self.cursor = None          # scene point

    def frame(self):
        pm = self.target.grab()
        if self.cursor is not None:
            vp = w.view.viewport()
            pt = vp.mapTo(self.target, w.view.mapFromScene(QPointF(*self.cursor)))
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            x, y = pt.x(), pt.y()
            arrow = QPainterPath()
            for i, (dx, dy) in enumerate(((0, 0), (0, 17), (4.5, 13), (7.5, 20), (10, 19), (7, 12), (12.5, 12))):
                (arrow.moveTo if i == 0 else arrow.lineTo)(x + dx, y + dy)
            arrow.closeSubpath()
            p.setPen(QPen(QColor("white"), 1.6))
            p.setBrush(QColor(20, 20, 20))
            p.drawPath(arrow)
            p.end()
        pm.save(os.path.join(self.dir, f"f{self.n:04d}.png"))
        self.n += 1

    def wait(self, seconds):
        """Let the app run, taking frames as it goes."""
        for _ in range(max(1, round(seconds * FPS))):
            t0 = time.perf_counter()
            self.frame()
            run_for(max(0.0, 1 / FPS - (time.perf_counter() - t0)))

    def glide(self, b, seconds=0.5, held=False):
        """Move the pointer smoothly to scene point b (dragging if held)."""
        a = self.cursor or b
        k = max(2, round(seconds * FPS))
        for i in range(1, k + 1):
            self.cursor = (a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k)
            T.move(w, self.cursor, held=held)
            self.wait(1 / FPS)

    def click(self, pt, seconds=0.4):
        self.glide(pt, seconds)
        T.click(w, pt)
        self.wait(0.15)

    def drag(self, a, b, seconds=0.6):
        self.glide(a, 0.35)
        T.press(w, a)
        self.glide(b, seconds, held=True)
        T.release(w, b)
        self.wait(0.15)

    def save(self):
        if not shutil.which("ffmpeg"):
            print("ffmpeg not found: skipped", self.name)
            return
        dest = os.path.join(out, self.name)
        vf = (f"fps={FPS},scale={GIF_WIDTH}:-1:flags=lanczos,split[a][b];"
              "[a]palettegen=max_colors=160:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:"
              "diff_mode=rectangle")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i",
                        os.path.join(self.dir, "f%04d.png"), "-vf", vf, "-loop", "0", dest], check=True)
        shutil.rmtree(self.dir, ignore_errors=True)
        print("saved", self.name, f"({os.path.getsize(dest) // 1024} KB, {self.n} frames)")


def play(fit=True):
    T.move(w, (-9000, -9000), held=False)        # no hover bubble left over from the last recording
    w.a_play.trigger()
    run_for(0.15)
    if fit:
        run_for(0.1)
        rect = w.scene.itemsBoundingRect().adjusted(-30, -30, 30, 30)
        w.view.fitInView(rect, Qt.KeepAspectRatio)
        run_for(0.05)


def zoom_on(cx, cy, scale):
    w.view.resetTransform()
    w.view.scale(scale, scale)
    w.view.centerOn(cx, cy)
    run_for(0.1)


w = MainWindow()
w.set_theme("light")
w.resize(1280, 760)
w.show()
run_for(0.4)

# ============================================================== 1. the main demo: build a circuit, then run it
w.new_file()
w.show_graph(False)
zoom_on(130, 80, 2.2)
r = Recorder("demo.gif", whole=True)
r.cursor = (120, 60)
r.wait(0.5)
r.glide((0, 80))
b = T.place(w, "battery", 0, 80)
w.scene.select_ids([b.id])
w.a_rotate.trigger()
r.wait(0.3)
r.glide((80, 0))
sw = T.place(w, "switch", 80, 0)
r.wait(0.25)
r.glide((180, 0))
res = T.place(w, "resistor", 180, 0)
r.wait(0.25)
r.glide((260, 80))
led = T.place(w, "led", 260, 80)
w.scene.select_ids([led.id])
w.a_rotate.trigger()
w.scene.clearSelection()
r.wait(0.4)
r.drag(b.pin_positions()["+"], sw.pin_positions()["1"])
r.drag(sw.pin_positions()["2"], res.pin_positions()["1"])
a = res.pin_positions()["2"]
r.drag(a, led.pin_positions()["A"])
r.drag(led.pin_positions()["K"], b.pin_positions()["-"], 0.8)
w.scene.clearSelection()
r.wait(0.5)
play(fit=False)
r.wait(0.6)
r.click((sw.x, sw.y))
r.wait(1.0)
r.glide((260, 30), 0.6)          # hover the wire into the LED
r.wait(1.6)
r.click((sw.x, sw.y))
r.wait(0.6)
r.click((sw.x, sw.y))
r.wait(1.0)
r.save()
w.a_stop.trigger()
w.undo.setClean()

# ============================================================== 2. LED chaser
example("LED chaser (555 + 4017)")
play()
r = Recorder("chaser.gif")
r.wait(3.5)
r.save()
w.a_stop.trigger()

# ============================================================== 3. motor spinning up, with current flow
example("Motor and load")
play()
r = Recorder("motor.gif")
s = find("switch")
r.cursor = (s.x - 60, s.y + 40)
r.wait(0.4)
r.click((s.x, s.y))
m = find("motor")
r.glide((m.x + 40, m.y + 60), 0.6)
r.wait(2.0)
r.click((s.x, s.y))
r.glide((m.x + 40, m.y + 60), 0.6)
r.wait(1.0)
r.save()
w.a_stop.trigger()

# ============================================================== 4. night light: drag the light slider
example("Night light")
play()
run_for(0.5)
ldr_item = w.scene.comp_items[find("ldr").id]
sl = next(s for s in w.scene.sliders if s.comp_item is ldr_item)


def knob(frac):
    p = sl.mapToScene(QPointF(6 + frac * (SLIDER_W - 12), TRACK_Y))
    return (p.x(), p.y())


r = Recorder("night_light.gif")
start = knob(sl.scale.to_pos(sl.value()))
r.cursor = (start[0] + 30, start[1] + 30)
r.wait(0.4)
r.glide(start, 0.4)
T.press(w, start)
r.glide(knob(0.02), 1.4, held=True)
r.wait(1.0)
r.glide(knob(0.95), 1.6, held=True)
T.release(w, knob(0.95))
r.wait(1.0)
r.save()
w.a_stop.trigger()
w.undo.setClean()

# ============================================================== 5. too much current: an LED pops
c = Circuit()
bb = c.add("battery", 0, 0, rot=1, props={"voltage": 9})
ll = c.add("led", 120, 0, rot=1, props={"colour": "Blue"})
ss = c.add("switch", 60, -60)
c.add_wire([bb.pin_positions()["+"], (0, -60), ss.pin_positions()["1"]])
c.add_wire([ss.pin_positions()["2"], (120, -60), ll.pin_positions()["A"]])
c.add_wire([ll.pin_positions()["K"], (120, 60), (0, 60), bb.pin_positions()["-"]])
w._set_circuit(c, None)
zoom_on(60, 0, 2.6)
play(fit=False)
r = Recorder("pop.gif")
s = find("switch")
r.cursor = (s.x + 50, s.y + 50)
r.wait(0.5)
r.click((s.x, s.y))
r.wait(2.2)
r.save()
w.a_stop.trigger()
w.undo.setClean()

# ============================================================== 6. 555 flasher with the graph
example("555 LED flasher")
play()
r = Recorder("graph.gif")
r.wait(4.0)
r.save()
w.a_stop.trigger()

# ============================================================== still pictures
example("Relay switching a lamp")
play()
run_for(0.3)
T.click(w, (find("switch").x, find("switch").y))
run_for(0.6)
q = find("npn")
T.move(w, (q.x + 10, q.y - 45), held=False)
shot("hover_reading.png")
w.a_stop.trigger()

example("Buck converter")
play()
run_for(9.0)
shot("buck_converter.png")
w.a_stop.trigger()

for name, fname, secs, setup in (
        ("Binary to 7-segment", "seven_segment.png", 0.6, None),
        ("Logic gates", "logic_gates.png", 0.6,
         lambda: [s.props.__setitem__("closed", True) for s in w.circuit.components.values()
                  if s.kind == "switch" and s.x == 100]),
        ("Op-amp dark sensor", "opamp.png", 0.6,
         lambda: [c.props.__setitem__("light", 2.0) for c in w.circuit.components.values() if c.kind == "ldr"]),
        ("Burglar alarm (reed switch)", "burglar_alarm.png", 0.6, None),
        ("Rain alarm (moisture sensor)", "rain_alarm.png", 0.6,
         lambda: find("moisture").props.__setitem__("moisture", 70.0)),
        ("RC filter on the graph", "rc_filter.png", 1.6, None),
):
    example(name)
    if setup:
        setup()
    play()
    if name == "Burglar alarm (reed switch)":
        run_for(0.2)
        T.click(w, (find("reed_switch").x, find("reed_switch").y))
    run_for(secs)
    shot(fname)
    w.a_stop.trigger()
    w.undo.setClean()

# the editor, the parts gallery and the properties box
example("MOSFET motor switch")
for cat in w.gallery.categories:
    cat.set_open(cat.name in ("Power supplies", "Switches", "Transistors", "Output devices"))
shot("editor.png")
d = PropertiesDialog(find("nmos"), w.circuit, w)
d.show()
shot("properties.png", d)
d.close()
bom = BomDialog(w.circuit, w)
bom.show()
shot("parts_list.png", bom)
bom.close()

# dark theme
w.set_theme("dark")
example("Capacitor charging")
w.speed_box.setCurrentText("10× faster")
play()
run_for(0.45)
shot("dark_theme.png")
w.a_stop.trigger()
w.speed_box.setCurrentText("Real time")
w.set_theme("light")

# an export (always on white paper)
example("Two-way light switch")
EX.export_png(w.scene, os.path.join(out, "export.png"), 2.0)
print("saved export.png")

w.undo.setClean()
w.close()

# the start-up splash
from wirely.ui.splash import Splash  # noqa: E402
sp = Splash()
sp.show()
sp.step("Loading parts…", 0.55)
shot("splash.png", sp)
sp.close()
