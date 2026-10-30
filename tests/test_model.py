"""Tests for the circuit model: values, parts, wiring connections, saving and loading.
Run:  python -m pytest tests"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wirely.model import parts as P
from wirely.model.circuit import Circuit, drag_end, move_segment, route, tidy, transform
from wirely.model.units import fmt, parse


# ---------------------------------------------------------------------------------------------- values
@pytest.mark.parametrize("text,unit,expected", [
    ("10k", "Ω", 10e3), ("10kΩ", "Ω", 10e3), ("4k7", "Ω", 4.7e3), ("2M2", "Ω", 2.2e6), ("4R7", "Ω", 4.7),
    ("470", "Ω", 470), ("1meg", "Ω", 1e6), ("100n", "F", 100e-9), ("100nF", "F", 100e-9),
    ("4.7uF", "F", 4.7e-6), ("4.7µF", "F", 4.7e-6), ("4n7", "F", 4.7e-9), ("9V", "V", 9), ("1.5", "V", 1.5),
    ("20mA", "A", 0.02), ("0,25", "W", 0.25), ("50Hz", "Hz", 50), ("1e3", "Ω", 1000), ("330 ohms", "Ω", 330),
])
def test_parse(text, unit, expected):
    assert parse(text, unit) == pytest.approx(expected)


@pytest.mark.parametrize("bad", ["", "abc", "10x", "k10"])
def test_parse_rejects_nonsense(bad):
    with pytest.raises(ValueError):
        parse(bad, "Ω")


@pytest.mark.parametrize("value,unit,text", [
    (10e3, "Ω", "10kΩ"), (4700, "Ω", "4.7kΩ"), (100e-9, "F", "100nF"), (4.7e-6, "F", "4.7µF"),
    (9, "V", "9V"), (1.5, "V", "1.5V"), (0.02, "A", "20mA"), (2.2e6, "Ω", "2.2MΩ"), (0, "V", "0V"),
    (50, "%", "50%"),
])
def test_fmt(value, unit, text):
    assert fmt(value, unit) == text


# ---------------------------------------------------------------------------------------------- parts
def test_every_pin_is_on_the_grid_and_names_unique():
    for part in P.PARTS.values():
        names = [n for n, _x, _y in part.pins]
        assert len(names) == len(set(names)), part.key
        for _n, x, y in part.pins:
            assert x % P.GRID == 0 and y % P.GRID == 0, (part.key, x, y)
        assert part.category in P.CATEGORIES


def test_rotation_keeps_pins_on_grid():
    for rot in range(4):
        for flip in (False, True):
            for part in P.PARTS.values():
                for _n, x, y in part.pins:
                    tx, ty = transform(x, y, rot, flip)
                    assert tx % P.GRID == 0 and ty % P.GRID == 0


def test_rotate_clockwise():
    assert transform(30, 0, 1, False) == (0, 30)      # right -> down
    assert transform(30, 0, 2, False) == (-30, 0)
    assert transform(30, 0, 0, True) == (-30, 0)


def test_refs_number_themselves():
    c = Circuit()
    assert c.add("resistor").ref == "R1"
    r2 = c.add("resistor")
    assert r2.ref == "R2"
    c.add("led")
    assert c.add("led").ref == "LED2"
    c.remove(r2.id)
    assert c.add("resistor").ref == "R2"      # fills the gap


# ---------------------------------------------------------------------------------------------- wires
def test_route_and_tidy():
    assert route((0, 0), (50, 30)) == [(0, 0), (50, 0), (50, 30)]
    assert route((0, 0), (50, 30), horizontal_first=False) == [(0, 0), (0, 30), (50, 30)]
    assert tidy([(0, 0), (10, 0), (20, 0), (20, 0), (20, 10)]) == [(0, 0), (20, 0), (20, 10)]


def test_drag_end_stays_square():
    pts = drag_end([(0, 0), (50, 0)], -1, (50, 30))
    assert pts[0] == (0, 0) and pts[-1] == (50, 30)
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        assert x1 == x2 or y1 == y2
    # a bent wire: the neighbouring corner follows
    pts = drag_end([(0, 0), (50, 0), (50, 40)], 0, (0, 10))
    assert pts == [(0, 10), (50, 10), (50, 40)]


def test_move_segment_keeps_ends():
    pts = move_segment([(0, 0), (40, 0), (40, 40), (80, 40)], 1, 20, 7)
    assert pts[0] == (0, 0) and pts[-1] == (80, 40)
    assert (60, 0) in pts and (60, 40) in pts
    # moving a straight wire sideways makes a little "staple" and keeps the ends
    pts = move_segment([(0, 0), (60, 0)], 0, 0, 20)
    assert pts == [(0, 0), (0, 20), (60, 20), (60, 0)]


def led_circuit():
    """9 V battery -> 470R -> red LED -> back to battery, with 0 V on the negative side."""
    c = Circuit()
    b = c.add("battery", 0, 100, rot=1)           # + at top (0,70), - at bottom (0,130)
    r = c.add("resistor", 60, 40, props={"resistance": 470})
    led = c.add("led", 140, 100, rot=1)           # anode top (140,70), cathode bottom (140,130)
    g = c.add("ground", 0, 160)
    bp = b.pin_positions()
    assert bp["+"] == (0, 70) and bp["-"] == (0, 130)
    c.add_wire([bp["+"], (0, 40), r.pin_positions()["1"]])
    c.add_wire([r.pin_positions()["2"], (140, 40), led.pin_positions()["A"]])
    c.add_wire([led.pin_positions()["K"], (140, 160), (0, 160)])
    c.add_wire([bp["-"], (0, 160)])
    return c, b, r, led, g


def test_nets_of_led_circuit():
    c, b, r, led, g = led_circuit()
    nets = c.nets()
    assert len(nets) == 3
    by_pin = {pin: n.name for n in nets for pin in n.pins}
    assert by_pin[(b.id, "+")] == by_pin[(r.id, "1")]
    assert by_pin[(r.id, "2")] == by_pin[(led.id, "A")]
    assert by_pin[(led.id, "K")] == by_pin[(b.id, "-")] == by_pin[(g.id, "1")] == "0"
    assert c.unconnected_pins() == []


def test_t_junction_and_crossing():
    c = Circuit()
    c.add_wire([(0, 0), (100, 0)])
    c.add_wire([(50, 0), (50, 50)])           # ends on the middle of the first: joined, with a dot
    c.add_wire([(80, -30), (80, 30)])         # crosses the first: NOT joined
    nets = c.nets()
    sizes = sorted(len(n.wires) for n in nets)
    assert sizes == [1, 2]
    assert c.junctions() == [(50, 0)]


def test_parts_touching_pin_to_pin_connect():
    c = Circuit()
    r1 = c.add("resistor", 0, 0)
    r2 = c.add("resistor", 60, 0)             # r1 pin 2 sits on r2 pin 1
    net = c.net_of_pin(r1.id, "2")
    assert (r2.id, "1") in net.pins


def test_save_and_load_round_trip(tmp_path):
    c, b, r, led, g = led_circuit()
    led.props["colour"] = "Verde"
    path = tmp_path / "led.wirely"
    c.save(str(path))
    d = Circuit.load(str(path))
    assert len(d.components) == 4 and len(d.wires) == 4
    assert d.components[led.id].props["colour"] == "Verde"
    assert d.components[r.id].props["resistance"] == 470
    assert sorted(len(n.pins) for n in d.nets()) == sorted(len(n.pins) for n in c.nets())


def test_load_rejects_other_files(tmp_path):
    p = tmp_path / "x.wirely"
    p.write_text('{"hello": 1}')
    with pytest.raises(ValueError):
        Circuit.load(str(p))


def test_bill_of_materials_groups_same_parts():
    c, *_ = led_circuit()
    c.add("resistor", 300, 300, props={"resistance": 470})
    bom = c.bill_of_materials()
    res = [row for row in bom if row["description"].startswith("Resistencia")]
    assert res[0]["qty"] == 2 and res[0]["refs"] == ["R1", "R2"]
    assert not any("0 V" in row["description"] for row in bom)


def test_old_sparkbench_files_still_open(tmp_path):
    import json
    c, *_ = led_circuit()
    d = c.to_dict()
    d["app"] = "Sparkbench"
    p = tmp_path / "old.spark"
    p.write_text(json.dumps(d))
    assert len(Circuit.load(str(p)).components) == 4
