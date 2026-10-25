"""Make a 1080p demo video of Wirely (MP4, H.264) — for Reddit, YouTube or a website.

    xvfb-run -a -s "-screen 0 2400x1400x24" python tools/make_video.py wirely-demo.mp4

The app runs on a pretend clock that moves exactly 1/30 s per video frame, so everything (the simulation,
current flow, LEDs flashing) plays at true speed in the video however long each frame takes to capture.
Needs ffmpeg on the PATH.
"""
import math
import os
import subprocess
import sys

os.environ.setdefault("QT_SCALE_FACTOR", "1.5")      # 1280×720 window drawn at 1920×1080: readable on phones
os.environ.setdefault("WIRELY_NO_SOUND", "1")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen,  # noqa: E402
                           QPixmap, QRadialGradient)
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402

app = QApplication.instance() or QApplication([])
import test_editor as T  # noqa: E402
from wirely import __version__  # noqa: E402
from wirely.model.circuit import Circuit  # noqa: E402
from wirely.ui import simcontrol  # noqa: E402
from wirely.ui.live_items import TRACK_Y  # noqa: E402
from wirely.ui.live_items import W as SLIDER_W  # noqa: E402
from wirely.ui.mainwindow import EXAMPLES, MainWindow  # noqa: E402

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "wirely-demo.mp4")
FPS = 30
VW, VH = 1920, 1080
ASSETS = os.path.join(ROOT, "wirely", "assets")


# ------------------------------------------------------------------ a pretend clock for the simulation
class Clock:
    t = 1000.0

    def __call__(self):
        return self.t


clock = Clock()
simcontrol.time.perf_counter = clock          # simcontrol does "import time"; this swaps its clock


def pump():
    for _ in range(3):
        app.processEvents()


# ------------------------------------------------------------------ the video writer
class Video:
    def __init__(self, path):
        self.ff = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}",
             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", path], stdin=subprocess.PIPE)
        self.n = 0
        self.last = None
        self.fade_from = None
        self.fade_n = 0

    def write(self, img: QImage):
        img = img.convertToFormat(QImage.Format_RGB888)
        if img.width() != VW or img.height() != VH:
            img = img.scaled(VW, VH, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        if self.fade_from is not None and self.fade_n > 0:       # cross-fade from the previous scene
            k = self.fade_n / 10
            out = QImage(img)
            p = QPainter(out)
            p.setOpacity(k)
            p.drawImage(0, 0, self.fade_from)
            p.end()
            img = out
            self.fade_n -= 1
        self.last = img
        ptr = img.constBits()
        bpl = img.bytesPerLine()
        raw = bytes(ptr)
        if bpl != VW * 3:
            raw = b"".join(raw[r * bpl:r * bpl + VW * 3] for r in range(VH))
        self.ff.stdin.write(raw)
        self.n += 1

    def crossfade(self):
        if self.last is not None:
            self.fade_from = QImage(self.last)
            self.fade_n = 10

    def close(self):
        self.ff.stdin.close()
        self.ff.wait()


vid = Video(OUT)


# ------------------------------------------------------------------ title and end cards
def card_image(lines, sub=None, logo=True):
    img = QImage(VW, VH, QImage.Format_RGB888)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, VW, VH)
    g.setColorAt(0, QColor(12, 16, 22))
    g.setColorAt(0.6, QColor(18, 26, 34))
    g.setColorAt(1, QColor(16, 40, 46))
    p.fillRect(img.rect(), g)
    for cx, cy, r, col in ((VW * 0.85, VH * 0.2, VW * 0.5, QColor(43, 125, 233)),
                           (VW * 0.6, VH * 1.0, VW * 0.5, QColor(16, 163, 163))):
        rg = QRadialGradient(QPointF(cx, cy), r)
        c0 = QColor(col)
        c0.setAlpha(70)
        c1 = QColor(col)
        c1.setAlpha(0)
        rg.setColorAt(0, c0)
        rg.setColorAt(1, c1)
        p.fillRect(img.rect(), rg)
    y = 300
    if logo:
        pm = QPixmap(os.path.join(ASSETS, "logo_256.png"))
        p.drawPixmap(QRectF(VW / 2 - 90, 170, 180, 180), pm, QRectF(pm.rect()))
        y = 390
    for i, (text, size, colour, bold) in enumerate(lines):
        f = QFont("DejaVu Sans")
        f.setPixelSize(size)
        f.setWeight(QFont.DemiBold if bold else QFont.Normal)
        p.setFont(f)
        p.setPen(QColor(colour))
        h = size * 1.45
        p.drawText(QRectF(0, y, VW, h), Qt.AlignHCenter | Qt.AlignVCenter, text)
        y += h + 10
    if sub:
        f = QFont("DejaVu Sans")
        f.setPixelSize(30)
        p.setFont(f)
        p.setPen(QColor(150, 166, 178))
        p.drawText(QRectF(0, VH - 120, VW, 50), Qt.AlignHCenter | Qt.AlignVCenter, sub)
    p.end()
    return img


def card(img, seconds):
    vid.crossfade()
    for _ in range(int(seconds * FPS)):
        vid.write(img)


# ------------------------------------------------------------------ recording the app
class Rec:
    caption = ""
    cap_age = 0
    cursor = None            # window point (logical)
    pressed = False

    def frame(self):
        clock.t += 1 / FPS
        if w.simc.state == "running":
            w.simc._tick()
        pump()
        pm = w.grab()
        img = pm.toImage()
        dpr = pm.devicePixelRatio()
        img.setDevicePixelRatio(1.0)             # paint the pointer and captions in real video pixels
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        if self.cursor is not None:
            x, y = self.cursor.x() * dpr, self.cursor.y() * dpr
            s = dpr * 1.25
            if self.pressed:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(255, 196, 0, 110))
                p.drawEllipse(QPointF(x, y), 16 * s, 16 * s)
            arrow = QPainterPath()
            for i, (dx, dy) in enumerate(((0, 0), (0, 17), (4.5, 13), (7.5, 20), (10, 19), (7, 12), (12.5, 12))):
                (arrow.moveTo if i == 0 else arrow.lineTo)(x + dx * s, y + dy * s)
            arrow.closeSubpath()
            p.setPen(QPen(QColor("white"), 1.6 * s))
            p.setBrush(QColor(20, 20, 20))
            p.drawPath(arrow)
        if self.caption:
            self.cap_age += 1
            alpha = min(1.0, self.cap_age / 8)
            f = QFont("DejaVu Sans")
            f.setPixelSize(42)
            f.setWeight(QFont.DemiBold)
            p.setFont(f)
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(self.caption)
            box = QRectF(VW / 2 - tw / 2 - 34, 118, tw + 68, 82)     # at the top: pop-up messages appear at the bottom
            p.setOpacity(alpha)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(15, 20, 28, 225))
            p.drawRoundedRect(box, 22, 22)
            p.setPen(QColor(255, 255, 255))
            p.drawText(box, Qt.AlignCenter, self.caption)
            p.setOpacity(1.0)
        p.end()
        vid.write(img)

    def say(self, text):
        self.caption = text
        self.cap_age = 0

    def wait(self, seconds):
        for _ in range(max(1, round(seconds * FPS))):
            self.frame()

    # pointer positions -------------------------------------------------
    @staticmethod
    def scene_to_win(pt):
        vp = w.view.viewport()
        return QPointF(vp.mapTo(w, w.view.mapFromScene(QPointF(*pt))))

    @staticmethod
    def widget_to_win(widget, pt=None):
        c = pt if pt is not None else widget.rect().center()
        return QPointF(widget.mapTo(w, QPoint(int(c.x()), int(c.y()))))

    def glide_win(self, target, seconds=0.5, on_step=None):
        a = self.cursor or target
        k = max(2, round(seconds * FPS))
        for i in range(1, k + 1):
            f = i / k
            f = f * f * (3 - 2 * f)              # ease in and out
            self.cursor = QPointF(a.x() + (target.x() - a.x()) * f, a.y() + (target.y() - a.y()) * f)
            if on_step:
                on_step(f)
            self.frame()

    def glide(self, pt, seconds=0.5, held=False):
        a = self.cursor
        start_scene = None
        if a is not None:
            sp = w.view.mapToScene(w.view.viewport().mapFrom(w, a.toPoint()))
            start_scene = (sp.x(), sp.y())
        else:
            start_scene = pt

        def step(f):
            T.move(w, (start_scene[0] + (pt[0] - start_scene[0]) * f, start_scene[1] + (pt[1] - start_scene[1]) * f),
                   held=held)
        self.glide_win(self.scene_to_win(pt), seconds, step)

    def click(self, pt, seconds=0.45):
        self.glide(pt, seconds)
        self.pressed = True
        T.click(w, pt)
        self.wait(0.12)
        self.pressed = False

    def drag(self, a, b, seconds=0.6):
        self.glide(a, 0.35)
        self.pressed = True
        T.press(w, a)
        self.wait(0.08)
        self.glide(b, seconds, held=True)
        T.release(w, b)
        self.pressed = False
        self.wait(0.12)

    def pick(self, kind, search, at):
        """Type in the gallery search, click the part's tile, then click on the sheet to place it."""
        box = w.gallery.search
        self.glide_win(self.widget_to_win(box), 0.45)
        box.clear()
        for ch in search:
            box.setText(box.text() + ch)
            self.wait(0.07)
        self.wait(0.2)
        tile = next(t for t in w.gallery.tiles() if t.part.key == kind and t.isVisible())
        self.glide_win(self.widget_to_win(tile), 0.45)
        self.pressed = True
        QTest.mouseClick(tile, Qt.LeftButton)
        self.wait(0.12)
        self.pressed = False
        self.glide(at, 0.6)
        T.click(w, at)
        self.wait(0.2)
        return next(c for c in w.circuit.components.values() if c.kind == kind and (c.x, c.y) == at)


def find(kind):
    return next(c for c in w.circuit.components.values() if c.kind == kind)


def zoom_on(cx, cy, scale):
    w.view.resetTransform()
    w.view.scale(scale, scale)
    w.view.centerOn(cx, cy)
    pump()


def fit():
    pump()
    rect = w.scene.itemsBoundingRect()
    rect = rect.adjusted(-30, -30 - rect.height() * 0.22, 30, 30)     # room above for the captions
    w.view.fitInView(rect, Qt.KeepAspectRatio)
    pump()


def play(do_fit=True):
    T.move(w, (-9000, -9000), held=False)
    w.a_play.trigger()
    w.simc._timer.stop()                      # the recorder drives the simulation, one tick per frame
    pump()
    if do_fit:
        fit()


def stop():
    w.a_stop.trigger()
    pump()


def example(name):
    w.open_file(os.path.join(EXAMPLES, name + ".wirely"))
    pump()
    w.undo.setClean()


w = MainWindow()
w.set_theme("light")
w.resize(1280, 720)
w.show()
pump()
assert w.grab().width() == VW, f"window grabbed at {w.grab().width()} px wide, wanted {VW}"
r = Rec()

# =================================================================== 0. title
card(card_image([("Wirely", 120, "#f5f7fa", True),
                 ("Draw a circuit, press play, watch it work", 46, "#aabac6", False)],
                sub=f"Free and open-source circuit simulator  ·  Windows · Mac · Linux  ·  version {__version__}"),
     3.2)

# =================================================================== 1. build a circuit from scratch
w.new_file()
w.show_graph(False)
zoom_on(130, 45, 2.0)
vid.crossfade()
r.cursor = QPointF(640, 400)
r.say("Pick parts from the gallery")
r.wait(0.6)
b = r.pick("battery", "batt", (0, 80))
w.scene.select_ids([b.id])
w.a_rotate.trigger()
w.scene.clearSelection()
r.wait(0.2)
sw = r.pick("switch", "switch", (80, 0))
res = r.pick("resistor", "resis", (180, 0))
led = r.pick("led", "led", (260, 80))
w.scene.select_ids([led.id])
w.a_rotate.trigger()
w.scene.clearSelection()
w.gallery.search.clear()
r.wait(0.3)
r.say("Drag from pin to pin to wire it up")
r.drag(b.pin_positions()["+"], sw.pin_positions()["1"])
r.drag(sw.pin_positions()["2"], res.pin_positions()["1"])
r.drag(res.pin_positions()["2"], led.pin_positions()["A"])
r.drag(led.pin_positions()["K"], b.pin_positions()["-"], 0.8)
w.scene.clearSelection()
r.wait(0.4)
r.say("Press play — then click the switch")
play_btn = next(b for b in w.findChildren(QToolButton) if b.defaultAction() is w.a_play and b.isVisible())
r.glide_win(r.widget_to_win(play_btn), 0.5)
r.pressed = True
r.wait(0.1)
play(do_fit=False)
r.pressed = False
r.wait(0.5)
r.click((sw.x, sw.y))
r.wait(1.2)
r.say("Hover over any wire to read its voltage and current")
r.glide((260, 30), 0.7)
r.wait(2.2)
r.glide((130, 160), 0.6)
r.wait(1.4)
r.say("Wires are coloured by voltage, and the dots show the current")
r.glide((330, -40), 0.6)
r.wait(2.4)
stop()

# =================================================================== 2. too much current: it pops
c = Circuit()
bb = c.add("battery", 0, 0, rot=1, props={"voltage": 9})
ll = c.add("led", 120, 0, rot=1, props={"colour": "Blue"})
ss = c.add("switch", 60, -60)
c.add_wire([bb.pin_positions()["+"], (0, -60), ss.pin_positions()["1"]])
c.add_wire([ss.pin_positions()["2"], (120, -60), ll.pin_positions()["A"]])
c.add_wire([ll.pin_positions()["K"], (120, 60), (0, 60), bb.pin_positions()["-"]])
w._set_circuit(c, None)
zoom_on(60, -15, 2.6)
vid.crossfade()
play(do_fit=False)
r.cursor = r.scene_to_win((140, 40))
r.say("Forget the resistor and the LED pops — and says why")
r.wait(0.8)
r.click((60, -60))
r.glide((150, 70), 0.5)
r.wait(2.6)
stop()
w.undo.setClean()

# =================================================================== 3. LED chaser
example("LED chaser (555 + 4017)")
vid.crossfade()
play()
r.cursor = None
r.say("555 timers, counters and logic chips")
r.wait(4.0)
stop()

# =================================================================== 4. night light: drag the light sensor
example("Night light")
vid.crossfade()
play()
ldr_item = w.scene.comp_items[find("ldr").id]
sl = next(s for s in w.scene.sliders if s.comp_item is ldr_item)


def knob(frac):
    p = sl.mapToScene(QPointF(6 + frac * (SLIDER_W - 12), TRACK_Y))
    return (p.x(), p.y())


start = knob(sl.scale.to_pos(sl.value()))
r.cursor = r.scene_to_win((start[0] + 40, start[1] + 40))
r.say("Drag sensors while it runs: make it dark and the light comes on")
r.wait(0.6)
r.glide(start, 0.4)
r.pressed = True
T.press(w, start)
r.glide(knob(0.02), 1.6, held=True)
r.wait(1.2)
r.glide(knob(0.95), 1.6, held=True)
T.release(w, knob(0.95))
r.pressed = False
r.wait(1.0)
stop()

# =================================================================== 5. motor
example("Motor and load")
vid.crossfade()
play()
s = find("switch")
m = find("motor")
r.cursor = r.scene_to_win((s.x - 60, s.y + 50))
r.say("Motors take a big current to start, then less as they speed up")
r.wait(0.6)
r.click((s.x, s.y))
r.glide((m.x + 50, m.y + 70), 0.6)
r.wait(3.0)
stop()

# =================================================================== 6. relay, and what happens without the flyback diode
example("Relay switching a lamp")
vid.crossfade()
play()
s = find("switch")
r.cursor = r.scene_to_win((s.x - 60, s.y + 60))
r.say("Relays click over and switch bigger loads")
r.wait(0.5)
r.click((s.x, s.y))
r.wait(1.4)
r.click((s.x, s.y))
r.wait(1.0)
stop()
d = find("diode")
r.say("Delete the protection diode…")
r.click((d.x, d.y))
r.wait(0.3)
w.a_delete.trigger()
r.wait(0.8)
play(do_fit=False)
r.say("…and the coil's voltage spike destroys the transistor")
r.click((s.x, s.y))
r.wait(1.2)
r.click((s.x, s.y))
r.glide((s.x + 120, s.y + 120), 0.5)
r.wait(2.8)
stop()
w.undo.setClean()

# =================================================================== 7. the graph
example("555 LED flasher")
vid.crossfade()
play()
r.cursor = None
r.say("A built-in oscilloscope: drop probes on any wire")
r.wait(4.5)
stop()

# =================================================================== 8. buck converter
example("Buck converter")
vid.crossfade()
play()
r.say("Real circuit maths — results match the ngspice simulator")
r.wait(4.5)
stop()

# =================================================================== 9. logic + 7-segment
example("Binary to 7-segment")
vid.crossfade()
play()
sws = sorted([c for c in w.circuit.components.values() if c.kind == "switch"], key=lambda c: c.x)
r.cursor = r.scene_to_win((sws[0].x - 40, sws[0].y + 60))
r.say("Logic gates, decoders and displays")
r.wait(0.5)
for k in (0, 1, 0, 2):
    r.click((sws[k].x, sws[k].y), 0.35)
    r.wait(0.45)
r.wait(0.8)
stop()

# =================================================================== 10. dark theme
w.set_theme("dark")
example("Capacitor charging")
vid.crossfade()
w.speed_box.setCurrentText("Real time")
play()
r.cursor = None
r.say("Light and dark themes")
r.wait(3.5)
stop()
w.set_theme("light")

# =================================================================== end card
card(card_image([("Wirely", 110, "#f5f7fa", True),
                 ("Free and open source (GPL-3)", 48, "#aabac6", False),
                 ("Windows  ·  Mac  ·  Linux", 48, "#aabac6", False),
                 ("github.com/richiewillmott/Wirely", 50, "#ffc83c", True)],
                sub="62 parts  ·  22 example circuits  ·  no account, runs on your own computer"),
     4.5)

w.undo.setClean()
w.close()
vid.close()
print(f"saved {OUT}: {vid.n} frames, {vid.n / FPS:.1f} s, {os.path.getsize(OUT) / 1e6:.1f} MB")
