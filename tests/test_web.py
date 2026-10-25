"""Tests for Wirely Web (the browser version, web/): its Qt stand-in, its glue code and its numpy fallback.

The web version runs the desktop app's own sheet / drawing / simulator code with web/py/qtshim.py standing in
for Qt. These tests run that code here, in ordinary Python, in a separate process (so the stand-in never
mixes with the real PySide6 the other tests use).
"""
from __future__ import annotations

import importlib.util
import json
import os
import random
import subprocess
import sys
import textwrap

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_PY = os.path.join(ROOT, "web", "py")
FALLBACK = os.path.join(WEB_PY, "fallback")


def run_web(code, lite=False, timeout=600):
    """Run code in a fresh Python with the web version's paths (and the numpy fallback if lite)."""
    path = [WEB_PY, ROOT] if not lite else [FALLBACK, WEB_PY, ROOT]
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(path))
    env.pop("QT_QPA_PLATFORM", None)
    r = subprocess.run([sys.executable, "-c", textwrap.dedent(code)], capture_output=True, text=True, env=env,
                       timeout=timeout, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def test_every_symbol_draws_without_qt():
    out = run_web("""
        import qtshim; assert qtshim.install()
        from PySide6.QtGui import QPainter, QColor
        from wirely.model import parts as P
        from wirely.ui import symbols as S
        n = 0
        for k, part in P.PARTS.items():
            for rot in range(4):
                for flip in (False, True):
                    p = QPainter()
                    props = dict(part.defaults(), _glow=0.6, _segs=[1] * 7, _on=True, _ir=0.5, _level="H")
                    S.apply_transform(p, rot, flip)
                    S.draw(p, k, props, "#1f2328", rot, flip, QColor("#ffffff"))
                    assert p.ops, k
                    n += 1
        print(n, len(P.PARTS))
    """)
    n, parts = map(int, out.split()[-2:])
    assert n == parts * 8 and parts >= 76


@pytest.mark.parametrize("lite", [False, True], ids=["numpy", "fallback-maths"])
def test_every_example_opens_draws_and_runs(lite):
    out = run_web("""
        import json, wirely_web
        print(json.dumps(wirely_web.selftest()))
    """, lite=lite)
    report = json.loads(out.strip().splitlines()[-1])
    assert len(report) == len([f for f in os.listdir(os.path.join(ROOT, "examples")) if f.endswith(".wirely")])


def test_build_a_circuit_with_the_mouse_and_run_it():
    out = run_web("""
        import json, time, wirely_web
        app = wirely_web.App()
        L = 1
        def click(x, y):
            app.move(x, y, 0, 0, x, y); app.press(x, y, L, L, 0, x, y); app.release(x, y, L, 0, 0, x, y)
        def drag(a, b):
            app.move(*a, 0, 0, *a); app.press(*a, L, L, 0, *a)
            for k in range(1, 9):
                x, y = a[0] + (b[0] - a[0]) * k / 8, a[1] + (b[1] - a[1]) * k / 8
                app.move(x, y, L, 0, x, y)
            app.release(*b, L, 0, 0, *b)
        for kind, x, y in [("battery", 0, 0), ("resistor", 120, -60), ("led", 200, 60)]:
            app.start_placing(kind); click(x, y)
        pins = {c.ref: c.pin_positions() for c in app.circuit.components.values()}
        drag(pins["B1"]["+"], pins["R1"]["1"])
        drag(pins["R1"]["2"], pins["LED1"]["A"])
        drag(pins["LED1"]["K"], pins["B1"]["-"])
        st = json.loads(app.state())
        assert st["counts"] == "3 parts · 3 wires", st["counts"]
        # double-click the resistor and change its value through the properties box
        r = app.circuit.components[[c.id for c in app.circuit.components.values() if c.kind == "resistor"][0]]
        click(r.x, r.y)
        cid = json.loads(app.dblclick(r.x, r.y, 0, r.x, r.y))["edit"]
        assert json.loads(app.check_form(cid, json.dumps({"resistance": "4k7x"})))["error"]
        assert app.apply_form(cid, json.dumps({"resistance": "470", "_ref": "R1"})) == ""
        assert r.props["resistance"] == 470
        app.run()
        for _ in range(6):
            time.sleep(0.035); app.tick()
        led = [c for c in app.circuit.components.values() if c.kind == "led"][0]
        glow = app.simc.live.parts[led.id]["_glow"]
        f = json.loads(app.frame(-400, -300, 400, 300))
        assert f["draw"] and f["defs"]
        app.stop()
        app.undo(); app.undo()
        print(glow, json.loads(app.state())["counts"])
    """)
    glow, counts = out.split()[0], " ".join(out.split()[1:])
    assert float(glow) > 0.3                    # the LED lights
    assert counts == "3 parts · 2 wires"         # undo: the resistor value, then the last wire


def test_fallback_numpy_solves_like_numpy():
    spec = importlib.util.spec_from_file_location("numpy_lite", os.path.join(FALLBACK, "numpy", "__init__.py"))
    lite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lite)
    rnd = random.Random(3)
    for n in (1, 2, 5, 12, 30):
        A = [[rnd.uniform(-1, 1) + (n if i == j else 0) for j in range(n)] for i in range(n)]
        b = [rnd.uniform(-5, 5) for _ in range(n)]
        x = lite.linalg.solve(lite.array(A), lite.array(b))
        assert np.allclose(list(x), np.linalg.solve(np.array(A), np.array(b)), rtol=1e-10, atol=1e-12)
    with pytest.raises(lite.linalg.LinAlgError):
        lite.linalg.solve(lite.array([[1.0, 2.0], [2.0, 4.0]]), lite.array([1.0, 2.0]))
    # least squares on a singular system still gives a usable answer
    x = lite.linalg.lstsq(lite.array([[1.0, -1.0], [-1.0, 1.0]]), lite.array([1.0, -1.0]))[0]
    assert abs((x[0] - x[1]) - 1.0) < 1e-6


def test_drag_a_pinned_reading_label():
    out = run_web("""
        import json, time, wirely_web
        app = wirely_web.App()
        L = 1
        app.load(open("examples/Thyristor alarm (latching).wirely").read(), "x")
        app.run()
        for _ in range(4):
            time.sleep(0.03); app.tick()
        w = next(iter(app.circuit.wires.values()))
        (a, b) = w.segments()[0]
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        app.press(mx, my, L, L, 0, mx, my); app.release(mx, my, L, 0, 0, mx, my)      # pin it
        app.frame(-2000, -2000, 4000, 4000)
        r = [h[0] for h in app.scene._tag_hits if h[1] == w.id][0]
        cx, cy = r.x() + r.width() / 2, r.y() + r.height() / 2
        app.press(cx, cy, L, L, 0, cx, cy)
        app.move(cx + 50, cy + 30, L, 0, cx + 50, cy + 30)
        app.release(cx + 50, cy + 30, L, 0, 0, cx + 50, cy + 30)
        f = json.loads(app.frame(-2000, -2000, 4000, 4000))
        r2 = [h[0] for h in app.scene._tag_hits if h[1] == w.id][0]
        app.stop()
        print(r2.x() - r.x(), r2.y() - r.y(), w.id in app.scene.pinned)
    """)
    dx, dy, still = out.split()[-3:]
    assert float(dx) == 50 and float(dy) == 30 and still == "True"
