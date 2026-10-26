"""US (ANSI) symbols as well as British (IEC) ones (1.5.2): only the look changes, and the choice is remembered."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from test_editor import app, win  # noqa: E402,F401

from PySide6.QtGui import QColor  # noqa: E402

from wirely.model import parts as P  # noqa: E402
from wirely.ui import symbols as S  # noqa: E402

CHANGED = ["resistor", "var_resistor", "potentiometer", "thermistor", "ldr", "fuse", "electrolytic", "lamp"]


def picture(kind, style):
    S.set_style(style)
    try:
        return S.pixmap(kind, 120, 60, QColor("black"), QColor("white"), dpr=1).toImage()
    finally:
        S.set_style("uk")


def test_us_symbols_look_different_where_they_should():
    for kind in CHANGED:
        assert picture(kind, "us") != picture(kind, "uk"), kind
    for kind in ("capacitor", "battery", "led", "npn", "and", "motor"):     # the same in both
        assert picture(kind, "us") == picture(kind, "uk"), kind


def test_every_part_draws_in_us_style():
    for pd in P.PARTS.values():
        picture(pd.key, "us")


def test_us_symbols_menu_switches_and_is_remembered(win):
    assert S.STYLE == "uk" and not win.a_us.isChecked()
    win.a_us.trigger()
    assert S.STYLE == "us" and win.a_us.isChecked()
    assert win.settings.value("symbols") == "us"
    win.a_us.trigger()
    assert S.STYLE == "uk" and win.settings.value("symbols") == "uk"


def test_no_mention_of_a_realistic_view_that_doesnt_exist():
    for pd in P.PARTS.values():
        assert "realistic" not in pd.description.lower()
