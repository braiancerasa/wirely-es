"""Editor tests: place parts, draw wires with the mouse, move/rotate with wires following, undo, export.
They run without a screen (Qt 'offscreen').  Run:  python -m pytest tests"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])

from wirely.model.circuit import Circuit  # noqa: E402
from wirely.ui import export as EX  # noqa: E402
from wirely.ui.mainwindow import EXAMPLES, MainWindow  # noqa: E402


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from PySide6.QtCore import QSettings
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    w = MainWindow()
    w.resize(1200, 800)
    w.show()
    app.processEvents()
    w.view.resetTransform()
    w.view.scale(1.5, 1.5)
    w.view.centerOn(100, 50)
    app.processEvents()
    yield w
    w.undo.setClean()
    w.close()


def _send(w, kind, scene_pt, button=Qt.LeftButton, buttons=None, mods=Qt.NoModifier):
    vp = w.view.viewport()
    pos = QPointF(w.view.mapFromScene(QPointF(*scene_pt)))
    gpos = QPointF(vp.mapToGlobal(pos.toPoint()))
    if buttons is None:
        buttons = Qt.NoButton if kind == QEvent.MouseButtonRelease else button
    ev = QMouseEvent(kind, pos, gpos, button if kind != QEvent.MouseMove else Qt.NoButton, buttons, mods)
    QApplication.sendEvent(vp, ev)
    app.processEvents()


def press(w, pt, **k):
    _send(w, QEvent.MouseButtonPress, pt, **k)


def move(w, pt, held=True):
    _send(w, QEvent.MouseMove, pt, buttons=Qt.LeftButton if held else Qt.NoButton)


def release(w, pt):
    _send(w, QEvent.MouseButtonRelease, pt)


def drag(w, a, b, steps=6):
    press(w, a)
    for i in range(1, steps + 1):
        move(w, (a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps))
    release(w, b)


def click(w, pt):
    press(w, pt)
    release(w, pt)


def place(w, kind, x, y):
    w.scene.start_placing(kind)
    move(w, (x, y), held=False)
    click(w, (x, y))
    comps = [c for c in w.circuit.components.values() if c.kind == kind and (c.x, c.y) == (x, y)]
    assert comps, f"{kind} not placed at {(x, y)}"
    return comps[0]


def square(points):
    return all(a[0] == b[0] or a[1] == b[1] for a, b in zip(points, points[1:]))


# ------------------------------------------------------------------------------------------------- tests
def test_place_parts_by_clicking(win):
    r = place(win, "resistor", 0, 0)
    assert r.ref == "R1" and win.scene.mode == "select"
    r2 = place(win, "resistor", 0, 100)
    assert r2.ref == "R2"
    assert win.undo.count() == 2


def test_draw_wire_by_dragging_pin_to_pin(win):
    r = place(win, "resistor", 0, 0)
    led = place(win, "led", 150, 60)
    a = r.pin_positions()["2"]
    b = led.pin_positions()["A"]
    drag(win, a, b)
    assert len(win.circuit.wires) == 1
    w = next(iter(win.circuit.wires.values()))
    assert w.points[0] == a and w.points[-1] == b and square(w.points)
    net = win.circuit.net_of_pin(r.id, "2")
    assert (led.id, "A") in net.pins


def test_click_to_route_wire_with_corners(win):
    r = place(win, "resistor", 0, 0)
    c = place(win, "capacitor", 200, 150)
    click(win, r.pin_positions()["2"])            # start
    move(win, (80, -40), held=False)
    click(win, (80, -40))                         # a corner
    move(win, (300, -40), held=False)
    click(win, (300, -40))                        # another corner
    end = c.pin_positions()["2"]
    move(win, end, held=False)
    click(win, end)                               # finish on the pin
    assert len(win.circuit.wires) == 1
    w = next(iter(win.circuit.wires.values()))
    assert w.points[0] == r.pin_positions()["2"] and w.points[-1] == end and square(w.points)
    assert (80, -40) in w.points or (80, 0) in w.points


def test_moving_a_part_drags_its_wires(win):
    r = place(win, "resistor", 0, 0)
    led = place(win, "led", 150, 60)
    drag(win, r.pin_positions()["2"], led.pin_positions()["A"])
    win.scene.clearSelection()
    drag(win, (0, 0), (0, -60))                   # grab the resistor body and move it up
    assert (r.x, r.y) == (0, -60)
    w = next(iter(win.circuit.wires.values()))
    assert w.points[0] == r.pin_positions()["2"] and w.points[-1] == led.pin_positions()["A"]
    assert square(w.points)
    assert win.undo.undoText() == "Move"
    win.undo.undo()
    r = win.circuit.components[r.id]
    assert (r.x, r.y) == (0, 0)


def test_rotate_keeps_wires_connected(win):
    r = place(win, "resistor", 0, 0)
    led = place(win, "led", 150, 60)
    drag(win, r.pin_positions()["2"], led.pin_positions()["A"])
    win.scene.select_ids([r.id])
    win.a_rotate.trigger()
    assert r.rot == 1
    w = next(iter(win.circuit.wires.values()))
    assert w.points[0] == r.pin_positions()["2"] and square(w.points)
    assert win.circuit.unconnected_pins() and len(win.circuit.unconnected_pins()) == 2


def test_drag_wire_segment_sideways(win):
    win.circuit.add_wire([(0, 0), (100, 0), (100, 100), (200, 100)])
    win.scene.rebuild()
    drag(win, (100, 50), (140, 50))
    w = next(iter(win.circuit.wires.values()))
    assert (140, 0) in w.points and (140, 100) in w.points
    assert w.points[0] == (0, 0) and w.points[-1] == (200, 100)


def test_branch_off_a_wire_makes_a_junction(win):
    a = place(win, "resistor", 0, 0)
    b = place(win, "resistor", 200, 0)
    drag(win, a.pin_positions()["2"], b.pin_positions()["1"])
    win.scene.set_mode("wire")
    drag(win, (100, 0), (100, 80))
    assert (100, 0) in win.circuit.junctions()
    assert len(win.circuit.nets()) == 3     # a1, the middle net, b2


def test_delete_undo_redo(win):
    r = place(win, "resistor", 0, 0)
    win.scene.select_ids([r.id])
    win.a_delete.trigger()
    assert not win.circuit.components
    win.a_undo.trigger()
    assert r.id in win.circuit.components and len(win.scene.comp_items) == 1
    win.a_redo.trigger()
    assert not win.circuit.components and not win.scene.comp_items


def test_copy_paste_duplicate(win):
    r = place(win, "resistor", 0, 0)
    win.scene.select_ids([r.id])
    win.a_dup.trigger()
    assert len(win.circuit.components) == 2
    refs = sorted(c.ref for c in win.circuit.components.values())
    assert refs == ["R1", "R2"]


def test_edit_values(win):
    r = place(win, "resistor", 0, 0)
    win.scene.update_component(r.id, {"resistance": 4700.0}, "R7")
    assert r.props["resistance"] == 4700 and r.ref == "R7"
    from wirely.ui.items import label_lines
    assert label_lines(r) == ["R7", "4.7kΩ"]
    win.a_undo.trigger()
    assert win.circuit.components[r.id].props["resistance"] == 1000


def test_properties_dialog_reads_typed_values(win):
    from wirely.ui.dialogs import PropertiesDialog
    r = place(win, "resistor", 0, 0)
    d = PropertiesDialog(r, win.circuit, win)
    d.fields["resistance"][1].setText("2k2")
    out, ref, problems = d._read()
    assert out["resistance"] == pytest.approx(2200) and not problems
    d.fields["resistance"][1].setText("lots")
    _o, _r, problems = d._read()
    assert problems


def test_escape_cancels_wire(win):
    r = place(win, "resistor", 0, 0)
    click(win, r.pin_positions()["2"])
    move(win, (90, 60), held=False)
    win.scene.cancel()
    assert not win.circuit.wires and not win.scene.draft.isVisible()


def test_open_examples_have_no_loose_pins(win):
    names = sorted(os.listdir(EXAMPLES))
    assert len(names) >= 4
    for n in names:
        win.open_file(os.path.join(EXAMPLES, n))
        assert not win.circuit.is_empty()
        loose = [(cid, pin) for cid, pin, _pos in win.circuit.unconnected_pins()
                 if win.circuit.components[cid].kind not in ("counter4017", "relay")]   # unused outputs are fine
        assert loose == [], n


def test_export_png_svg_pdf(win, tmp_path):
    win.open_file(os.path.join(EXAMPLES, "LED and resistor.wirely"))
    for ext in ("png", "svg", "pdf"):
        p = tmp_path / f"out.{ext}"
        EX.export(win.scene, str(p), "LED and resistor")
        assert p.exists() and p.stat().st_size > 500, ext
    from PySide6.QtGui import QImage
    img = QImage(str(tmp_path / "out.png"))
    assert img.width() > 400
    # paper colours even in dark mode: the corner is white
    win.set_theme("dark")
    EX.export(win.scene, str(tmp_path / "dark.png"))
    img = QImage(str(tmp_path / "dark.png"))
    assert img.pixelColor(2, 2).name() == "#ffffff"
    win.set_theme("light")


def test_save_and_reopen(win, tmp_path):
    r = place(win, "resistor", 0, 0)
    led = place(win, "led", 150, 60)
    drag(win, r.pin_positions()["2"], led.pin_positions()["A"])
    win.path = str(tmp_path / "mine.wirely")
    assert win.save()
    assert win.undo.isClean()
    c = Circuit.load(win.path)
    assert len(c.components) == 2 and len(c.wires) == 1


def test_wire_avoids_running_through_a_part(win):
    b = place(win, "battery", 0, 80)
    win.scene.select_ids([b.id])
    win.a_rotate.trigger()
    win.a_rotate.trigger()
    win.a_rotate.trigger()                     # + at the bottom (0,110), - at the top (0,50)
    s = place(win, "resistor", 100, 0)
    drag(win, b.pin_positions()["+"], s.pin_positions()["1"])
    w = next(iter(win.circuit.wires.values()))
    # going straight up from + would cross the battery: the wire must go sideways first
    assert w.points[1][1] == 110
    assert len(win.circuit.nets()) == 3       # +, -, and the resistor's far end: no short circuit


def test_text_note_sizes_itself_and_stays_out_of_the_parts_list(win):
    n = place(win, "note", 0, 0)
    win.scene.update_component(n.id, {"text": "Press S1 to start\nthe motor"})
    it = win.scene.comp_items[n.id]
    assert it._body.height() > 30 and it._body.width() > 60
    assert all("note" not in r["description"].lower() for r in win.circuit.bill_of_materials())
    assert win.circuit.nets() == []


def test_right_click_menu_offers_the_right_things(win):
    r = place(win, "resistor", 0, 0)
    texts = [a.text() for a in win._context_menu(QPointF(0, 0)).actions() if a.text()]
    assert "Properties…" in texts and "Rotate" in texts and "Delete" in texts
    assert r.id in win.scene.selected_ids()[0]
    texts = [a.text() for a in win._context_menu(QPointF(500, 500)).actions() if a.text()]
    assert "Paste" in texts


def test_autosave_and_recovery(win, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    place(win, "resistor", 0, 0)
    win.autosave()
    data, meta = win._autosave_paths()
    assert os.path.exists(data)
    win.undo.setClean()
    win._set_circuit(Circuit(), None)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    assert win.offer_recovery()
    assert len(win.circuit.components) == 1 and not win.undo.isClean()
    win.clear_autosave()
    assert not os.path.exists(data)
