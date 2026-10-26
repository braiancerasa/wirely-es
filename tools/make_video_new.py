"""Make a 1080p video of what's new in Wirely 1.4–1.5 (MP4, H.264) — Readings, the unit box, and the new parts.

    xvfb-run -a -s "-screen 0 2400x1400x24" python tools/make_video_new.py wirely-whats-new.mp4 [browser.png]

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
    overlay = None           # a dialog shown over the window (drawn into the frame)
    overlay_at = (0, 0)      # where its top-left goes, in window (logical) coordinates
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
        if self.overlay is not None:
            p.fillRect(img.rect(), QColor(0, 0, 0, 70))
            opm = self.overlay.grab()
            opm.setDevicePixelRatio(1.0)
            ox, oy = self.overlay_at[0] * dpr, self.overlay_at[1] * dpr
            p.setPen(Qt.NoPen)
            for k in range(6, 0, -1):                   # soft shadow
                p.setBrush(QColor(0, 0, 0, 14))
                p.drawRoundedRect(QRectF(ox - k * 2, oy - k + 6, opm.width() + k * 4, opm.height() + k * 2 + 4), 10, 10)
            p.drawPixmap(QPointF(ox, oy), opm)
            p.setPen(QPen(QColor(0, 0, 0, 60), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(ox, oy, opm.width(), opm.height()))
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

    def drag_via(self, a, corner, b, seconds=0.7):
        """Drag a wire round a corner (so it bends the way you lead it)."""
        self.glide(a, 0.35)
        self.pressed = True
        T.press(w, a)
        self.wait(0.08)
        self.glide(corner, seconds * 0.5, held=True)
        self.glide(b, seconds * 0.5, held=True)
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
    pump()                                   # (the view only knows its new scroll range after this)
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


from wirely.ui.dialogs import PropertiesDialog  # noqa: E402

BROWSER_PNG = sys.argv[2] if len(sys.argv) > 2 else None


def tool_button(action):
    return next(b for b in w.findChildren(QToolButton) if b.defaultAction() is action and b.isVisible())


def press_button(action):
    r.glide_win(r.widget_to_win(tool_button(action)), 0.5)
    r.pressed = True
    r.wait(0.1)
    action.trigger()
    r.pressed = False


def hold(pt, seconds=0.5):
    """Press and hold (push buttons, keypad keys)."""
    r.glide(pt, 0.35)
    r.pressed = True
    T.press(w, pt)
    r.wait(seconds)
    T.release(w, pt)
    r.pressed = False


def long_segment_mid(wire):
    a, b = max(wire.segments(), key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def tag_centre(key):
    for rect, k in w.scene._tag_hits:
        if k == key:
            c = rect.center()
            return (c.x(), c.y())
    return None


def edit_value(comp, key, number, unit_choice, say_first):
    """Open a part's properties over the window, type a new number and pick its size in the unit box."""
    d = PropertiesDialog(comp, w.circuit, w)
    d.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
    d.show()
    pump()
    d.adjustSize()
    pump()
    r.overlay = d
    r.overlay_at = ((1280 - d.width()) / 2, (720 - d.height()) / 2 + 40)
    vid.crossfade()
    r.say(say_first)
    _p, field = d.fields[key]
    box = d.unit_boxes[key]

    def at(widget):
        pos = widget.mapTo(d, widget.rect().center())
        return QPointF(r.overlay_at[0] + pos.x(), r.overlay_at[1] + pos.y())
    r.cursor = QPointF(r.overlay_at[0] + d.width() * 0.7, r.overlay_at[1] + d.height() + 30)
    r.wait(0.8)
    r.glide_win(at(field), 0.5)
    r.pressed = True
    r.wait(0.1)
    r.pressed = False
    field.selectAll()
    field.setFocus()
    r.wait(0.3)
    field.setText("")
    for ch in number:
        field.setText(field.text() + ch)
        r.wait(0.12)
    r.wait(0.3)
    r.glide_win(at(box), 0.45)
    r.pressed = True
    r.wait(0.1)
    r.pressed = False
    box.setCurrentText(unit_choice)
    r.wait(0.9)
    r.glide_win(at(d.ok), 0.45)
    r.pressed = True
    r.wait(0.12)
    r.pressed = False
    values, ref, problems = d._read()
    assert not problems, problems
    d.hide()
    r.overlay = None
    w.scene.update_component(comp.id, values, ref)
    pump()
    r.wait(0.3)


# a clean stage: Readings off (whatever was saved last time), no parts panel (so circuits fill the middle),
# and no hover bubbles over what's being clicked
w.a_readings.setChecked(False)
w.scene.show_readings = False
_real_hover = w.scene.update_hover
HOVER = {"on": False}


def _hover(pos=None):
    if HOVER["on"]:
        _real_hover(pos)
    else:
        w.scene.hover_info = None


w.scene.update_hover = _hover
pump()

# =================================================================== 0. title
card(card_image([("Wirely", 120, "#f5f7fa", True),
                 ("Draw a circuit, press play, watch it work", 46, "#aabac6", False)],
                sub=f"Free and open-source circuit simulator  ·  Windows · Mac · Linux · browser  ·  version {__version__}"),
     3.2)

# =================================================================== 1. build a circuit from scratch
w.new_file()
w.show_graph(False)
w.view.setSceneRect(QRectF(-3000, -3000, 6000, 6000))     # an empty sheet: room to centre the view
zoom_on(150, 105, 2.0)                     # the circuit below is a 300 × 210 square loop around (150, 105)
vid.crossfade()
r.cursor = QPointF(640, 400)
r.say("Pick parts from the gallery")
r.wait(0.6)
b = r.pick("battery", "batt", (0, 180))
w.scene.select_ids([b.id])
w.a_rotate.trigger()
w.scene.clearSelection()
r.wait(0.2)
sw = r.pick("switch", "switch", (90, 0))
res = r.pick("resistor", "resis", (210, 0))
led = r.pick("led", "led", (300, 180))
w.scene.select_ids([led.id])
w.a_rotate.trigger()
w.scene.clearSelection()
w.gallery.search.clear()
r.wait(0.3)
r.say("Drag from pin to pin to wire it up")
r.drag_via(b.pin_positions()["+"], (0, 0), sw.pin_positions()["1"])       # up, then across: a neat corner
r.drag(sw.pin_positions()["2"], res.pin_positions()["1"])
r.drag_via(res.pin_positions()["2"], (300, 0), led.pin_positions()["A"])
r.drag(led.pin_positions()["K"], b.pin_positions()["-"], 0.8)
w.scene.clearSelection()
r.wait(0.3)
r.glide((res.x, res.y), 0.5)
r.pressed = True
r.wait(0.12)
r.pressed = False
edit_value(res, "resistance", "470", "Ω", "Double-click a part to set its value")
r.say("Press play — then click the switch")
play_btn = tool_button(w.a_play)
r.glide_win(r.widget_to_win(play_btn), 0.5)
r.pressed = True
r.wait(0.1)
play(do_fit=False)
r.pressed = False
r.wait(0.4)
r.click((sw.x, sw.y))
r.wait(1.0)
HOVER["on"] = True
r.say("Hover over any wire to read its voltage and current")
r.glide((300, 75), 0.7)
r.wait(2.0)
HOVER["on"] = False
r.say("…or press Readings to see them all at once")
press_button(w.a_readings)
r.glide((450, 260), 0.5)
r.wait(2.4)
press_button(w.a_readings)
stop()
w.view.setSceneRect(QRectF())

# =================================================================== 2. pin a reading, drag it out of the way
example("Night light")
next(c for c in w.circuit.components.values() if c.kind == "ldr").props["light"] = 30.0      # dim: the LED is on
vid.crossfade()
play()
q = find("npn")
e_pin = q.pin_positions()["E"]
wire = next(wi for wi in w.circuit.wires.values() if e_pin in wi.points)
r.cursor = r.scene_to_win((330, 300))
r.say("Click any wire or part to pin its reading")
r.wait(0.4)
r.click(long_segment_mid(wire))
r.wait(0.3)
r.click((find("led").x, find("led").y))
r.wait(1.2)
r.say("…and drag it out of the way")
c0 = tag_centre(wire.id)
if c0:
    r.drag(c0, (c0[0] + 70, c0[1] - 60), 0.9)
r.wait(1.6)
stop()

# =================================================================== 3. stepper motor (dark theme from here to the counter)
w.set_theme("dark")
example("Stepper motor (crystal clock + L293D)")
vid.crossfade()
play()
r.cursor = None
r.say("Light and dark themes — here a stepper motor turning")
r.wait(5.5)
stop()

# =================================================================== 4. keypad
example("Keypad (which key is pressed)")
vid.crossfade()
play()
kp = find("keypad")
r.cursor = r.scene_to_win((kp.x + 60, kp.y + 120))
r.say("A 12-key keypad: hold a key and its row and column light")
r.wait(0.5)
for n in (0, 4, 8, 11, 10):                      # 1, 5, 9, #, 0
    pt = (kp.x - 20 + 20 * (n % 3), kp.y - 38 + 20 * (n // 3))
    hold(pt, 0.75)
    r.wait(0.25)
stop()

# =================================================================== 5. JK flip-flops
example("Binary counter (JK flip-flops)")
vid.crossfade()
play()
r.cursor = None
r.say("JK flip-flops counting in binary")
r.wait(4.6)
stop()
w.set_theme("light")

# =================================================================== 6. rotary switch
example("Rotary switch (pick an LED)")
vid.crossfade()
play()
rs = find("rotary")
r.cursor = r.scene_to_win((rs.x - 60, rs.y + 80))
r.say("Rotary switch — click to turn it")
r.wait(0.5)
for _ in range(5):
    r.click((rs.x, rs.y), 0.3)
    r.wait(0.55)
stop()

# =================================================================== 7. RGB LED
example("RGB colour mixer")
vid.crossfade()
play()
sws = sorted([c for c in w.circuit.components.values() if c.kind == "switch"], key=lambda c: c.x)
r.cursor = r.scene_to_win((sws[0].x - 40, sws[0].y + 60))
r.say("RGB and bi-colour LEDs mix their colours")
r.wait(0.8)
for k in (2, 0, 1):
    r.click((sws[k].x, sws[k].y), 0.4)
    r.wait(0.8)
stop()

# =================================================================== 8. thyristor alarm
example("Thyristor alarm (latching)")
vid.crossfade()
play()
pushes = {c.ref: c for c in w.circuit.components.values() if c.kind in ("push_make", "push_break")}
trig, reset = pushes["S2"], pushes["S1"]
r.cursor = r.scene_to_win((trig.x - 60, trig.y + 60))
r.say("Thyristors latch: tap the trigger and the alarm stays on")
r.wait(0.5)
hold((trig.x, trig.y), 0.3)
r.wait(1.6)
r.say("…until you press reset")
hold((reset.x, reset.y), 0.4)
r.wait(1.2)
stop()

# =================================================================== 9. L293D motor driver
example("Motor driver (L293D)")
vid.crossfade()
play()
sw_by = {c.ref: c for c in w.circuit.components.values() if c.kind == "switch"}
r.cursor = r.scene_to_win((sw_by["S1"].x + 40, sw_by["S1"].y + 80))
r.say("L293D motor driver: forwards and backwards")
r.wait(0.4)
r.click((sw_by["S1"].x, sw_by["S1"].y))
r.wait(1.8)
r.click((sw_by["S1"].x, sw_by["S1"].y))
r.click((sw_by["S2"].x, sw_by["S2"].y))
r.wait(2.0)
stop()

# =================================================================== 10. power supply
example("5 V power supply (7805)")
vid.crossfade()
play()
r.cursor = None
r.say("Transformer, bridge rectifier and 7805 regulator")
r.wait(4.0)
stop()


# =================================================================== 11. in the browser
def browser_card(path):
    img = card_image([], logo=False)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    shot = QImage(path)
    W, H = 1440, 810
    x0, y0 = (VW - W) / 2, 190
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 90))
    p.drawRoundedRect(QRectF(x0 - 6, y0 - 44, W + 12, H + 56), 16, 16)
    p.setBrush(QColor(236, 239, 243))
    p.drawRoundedRect(QRectF(x0, y0 - 40, W, H + 46), 12, 12)
    for i, col in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        p.setBrush(QColor(col))
        p.drawEllipse(QPointF(x0 + 24 + 22 * i, y0 - 20), 7, 7)
    p.setBrush(QColor("white"))
    p.drawRoundedRect(QRectF(x0 + 110, y0 - 33, 560, 26), 13, 13)
    f = QFont("DejaVu Sans")
    f.setPixelSize(16)
    p.setFont(f)
    p.setPen(QColor(60, 66, 74))
    p.drawText(QRectF(x0 + 130, y0 - 33, 540, 26), Qt.AlignVCenter, "wirely-app.github.io")
    p.drawImage(QRectF(x0, y0, W, H), shot)
    f.setPixelSize(54)
    f.setWeight(QFont.DemiBold)
    p.setFont(f)
    p.setPen(QColor("#f5f7fa"))
    p.drawText(QRectF(0, 40, VW, 90), Qt.AlignCenter, "It runs in your browser too — even on Chromebooks")
    p.end()
    return img


if BROWSER_PNG and os.path.exists(BROWSER_PNG):
    card(browser_card(BROWSER_PNG), 3.8)

# =================================================================== end card
n_examples = len([f for f in os.listdir(EXAMPLES) if f.endswith(".wirely")])
from wirely.model import parts as _P  # noqa: E402
card(card_image([("Wirely " + __version__, 110, "#f5f7fa", True),
                 (f"{len(_P.PARTS)} parts  ·  {n_examples} example circuits", 48, "#aabac6", False),
                 ("wirely-app.github.io", 52, "#ffc83c", True),
                 ("github.com/wirely-app/wirely-app.github.io", 44, "#aabac6", False)],
                sub="Free and open source (GPL-3)  ·  Windows · Mac · Linux · browser  ·  no account needed"),
     4.5)

w.undo.setClean()
w.close()
vid.close()
print(f"saved {OUT}: {vid.n} frames, {vid.n / FPS:.1f} s, {os.path.getsize(OUT) / 1e6:.1f} MB")
