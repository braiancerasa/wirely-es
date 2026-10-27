"""Colores y hojas de estilo Qt para los temas claro y oscuro (misma familia que FreeShape).

Otros módulos leen los colores como atributos de este módulo en tiempo de dibujo (theme.ACCENT, theme.CANVAS …),
así que apply("dark") / apply("light") cambia todo en su sitio.
"""
import os as _os

LIGHT = {
    "ACCENT": "#1f6fd1", "ACCENT_DARK": "#155bb0", "ACCENT_LIGHT": "#e3eefb", "ACCENT_SOFT": "#d3e4f8",
    "ACCENT_BORDER": "#c4d9f3", "TEXT": "#1f2328", "TEXT_MUTED": "#6a737d", "BORDER": "#d5d9de",
    "PANEL": "#ffffff", "PANEL_ALT": "#f5f6f8", "INPUT": "#ffffff", "ERROR": "#d93025", "OK_GREEN": "#2e9e44",
    "SELECTED_ROW": "#ffe9b8", "INVALID_BG": "#fdecea", "LOGO_TEXT": "#3b4250", "ICON_INK": "#3b4250",
    "SPARK": "#f5a524",
    # la hoja del circuito
    "CANVAS": "#ffffff", "CANVAS_OUTSIDE": "#eef0f3", "GRID_DOT": "#cfd5dc", "GRID_DOT_MAJOR": "#aab3be",
    "INK": "#1f2328", "WIRE": "#1f2328", "LABEL": "#3b4250", "LABEL_VALUE": "#1f6fd1",
    "SELECT": "#1f6fd1", "SELECT_HALO": "#d3e4f8", "HOVER": "#7fb0ea", "PIN_OPEN": "#d93025",
    "PIN_TARGET": "#2e9e44", "WIRE_DRAFT": "#1f6fd1",
    "FLOW_DOT": "#ffd43b", "FLOW_EDGE": "#8a5a00", "LCD_BG": "#14181f", "LCD_TEXT": "#5cf08a",
    "WARN": "#f08a24", "BLOWN": "#6a737d",
}

DARK = {
    "ACCENT": "#4c8ff0", "ACCENT_DARK": "#3a7be0", "ACCENT_LIGHT": "#2a3a52", "ACCENT_SOFT": "#2f4566",
    "ACCENT_BORDER": "#3d5a85", "TEXT": "#e6e8eb", "TEXT_MUTED": "#9aa3ae", "BORDER": "#3a3f46",
    "PANEL": "#23262b", "PANEL_ALT": "#1b1d21", "INPUT": "#2b2f35", "ERROR": "#ff6b5e", "OK_GREEN": "#4cc66a",
    "SELECTED_ROW": "#5a4720", "INVALID_BG": "#4a2522", "LOGO_TEXT": "#e6e8eb", "ICON_INK": "#d3d8df",
    "SPARK": "#f7b544",
    "CANVAS": "#1e2125", "CANVAS_OUTSIDE": "#16181b", "GRID_DOT": "#33383f", "GRID_DOT_MAJOR": "#4a515a",
    "INK": "#e3e6ea", "WIRE": "#e3e6ea", "LABEL": "#b9c0c9", "LABEL_VALUE": "#7fb0f5",
    "SELECT": "#5c9df5", "SELECT_HALO": "#2a3a52", "HOVER": "#3d6aa8", "PIN_OPEN": "#ff7a6e",
    "PIN_TARGET": "#4cc66a", "WIRE_DRAFT": "#5c9df5",
    "FLOW_DOT": "#ffe066", "FLOW_EDGE": "#7a5200", "LCD_BG": "#0c0f13", "LCD_TEXT": "#5cf08a",
    "WARN": "#ffa94d", "BLOWN": "#8b939e",
}

# colores de cable por voltaje: 0 V azul → verde → ámbar → rojo en el voltaje de alimentación más alto; por debajo de 0 V violeta
VOLT_STOPS = [(-1.0, "#9b5de5"), (0.0, "#2f7bff"), (0.33, "#12b886"), (0.66, "#f59f00"), (1.0, "#f03e3e")]


def volt_colour(v: float, vmax: float):
    """Color para un voltaje, como QColor (importado perezosamente para que este módulo siga sin Qt)."""
    from PySide6.QtGui import QColor
    f = 0.0 if vmax <= 0 else max(-1.0, min(1.0, v / vmax))
    for (f0, c0), (f1, c1) in zip(VOLT_STOPS, VOLT_STOPS[1:]):
        if f <= f1:
            t = 0.0 if f1 == f0 else (f - f0) / (f1 - f0)
            a, b = QColor(c0), QColor(c1)
            return QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t),
                          int(a.blue() + (b.blue() - a.blue()) * t))
    return QColor(VOLT_STOPS[-1][1])


# las exportaciones e impresiones siempre usan los colores "papel" claros
PAPER = {k: LIGHT[k] for k in ("CANVAS", "INK", "WIRE", "LABEL", "LABEL_VALUE")}

MODE = "light"


def apply(mode: str):
    global MODE
    MODE = "dark" if mode == "dark" else "light"
    globals().update(DARK if MODE == "dark" else LIGHT)


CHECK_ICON = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                           "assets", "check.svg").replace("\\", "/")


def stylesheet() -> str:
    g = globals()
    return f"""
* {{ font-family: "Inter", "Segoe UI", "Helvetica Neue", "Noto Sans", Arial, sans-serif; font-size: 13px; color: {g['TEXT']}; }}
QMainWindow, QWidget#central {{ background: {g['PANEL_ALT']}; }}
QWidget#topbar {{ background: {g['PANEL']}; border-bottom: 1px solid {g['BORDER']}; }}
QWidget#toolbar {{ background: {g['PANEL']}; border-bottom: 1px solid {g['BORDER']}; }}
QLabel#logo {{ font-weight: 600; font-size: 19px; color: {g['LOGO_TEXT']}; letter-spacing: 0.2px; }}
QLabel#docname {{ font-size: 14px; font-weight: 600; }}
QLabel#muted {{ color: {g['TEXT_MUTED']}; }}
QToolButton {{ border: 1px solid transparent; border-radius: 5px; padding: 3px; background: transparent; }}
QToolButton:hover {{ background: {g['ACCENT_LIGHT']}; border-color: {g['ACCENT_BORDER']}; }}
QToolButton:checked {{ background: {g['ACCENT_SOFT']}; border-color: {g['ACCENT']}; }}
QToolButton:disabled {{ color: {g['TEXT_MUTED']}; }}
QToolButton#menuButton {{ padding: 4px 8px; font-weight: 600; }}
QToolButton::menu-indicator {{ image: none; width: 0; }}
QFrame#sep {{ background: {g['BORDER']}; max-width: 1px; min-width: 1px; margin: 6px 4px; }}

QWidget#graphPanel {{ background: {g['PANEL']}; border-top: 1px solid {g['BORDER']}; }}
QWidget#leftpanel {{ background: {g['PANEL']}; border-right: 1px solid {g['BORDER']}; }}
QLabel#sectionHeader {{ font-weight: 700; padding: 8px 10px 4px 10px; color: {g['TEXT']}; }}
QLineEdit#filter {{ border: 1px solid {g['BORDER']}; border-radius: 5px; padding: 5px 8px; margin: 0 8px 6px 8px; background: {g['PANEL_ALT']}; }}
QToolButton#categoryHeader {{ border: none; border-radius: 0; padding: 7px 10px; font-weight: 600; text-align: left; color: {g['TEXT']}; }}
QToolButton#categoryHeader:hover {{ background: {g['PANEL_ALT']}; }}
QWidget#partTile {{ border: 1px solid transparent; border-radius: 6px; background: transparent; }}
QWidget#partTile:hover {{ background: {g['ACCENT_LIGHT']}; border-color: {g['ACCENT_BORDER']}; }}
QWidget#partTile[armed="true"] {{ background: {g['ACCENT_SOFT']}; border-color: {g['ACCENT']}; }}
QLabel#tileName {{ font-size: 11px; color: {g['TEXT']}; }}
QScrollArea {{ border: none; background: {g['PANEL']}; }}
QScrollArea > QWidget > QWidget {{ background: {g['PANEL']}; }}
QSplitter::handle {{ background: {g['BORDER']}; }}
QScrollBar:vertical {{ background: {g['PANEL']}; width: 10px; }}
QScrollBar::handle:vertical {{ background: {g['BORDER']}; border-radius: 4px; min-height: 24px; }}
QScrollBar:horizontal {{ background: {g['PANEL']}; height: 10px; }}
QScrollBar::handle:horizontal {{ background: {g['BORDER']}; border-radius: 4px; min-width: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

QFrame#propDialog {{ background: {g['PANEL']}; border: 1px solid {g['BORDER']}; border-radius: 8px; }}
QLabel#dialogTitle {{ font-weight: 700; font-size: 14px; }}
QLabel#dialogError {{ color: {g['ERROR']}; }}
QLabel#hint {{ color: {g['TEXT_MUTED']}; font-size: 12px; }}
QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {{ border: 1px solid {g['BORDER']}; border-radius: 5px; padding: 4px 7px; background: {g['INPUT']}; }}
QComboBox QAbstractItemView {{ background: {g['INPUT']}; border: 1px solid {g['BORDER']}; selection-background-color: {g['ACCENT_LIGHT']}; }}
QLineEdit:focus, QComboBox:focus {{ border-color: {g['ACCENT']}; }}
QLineEdit[invalid="true"] {{ border-color: {g['ERROR']}; background: {g['INVALID_BG']}; }}
QCheckBox {{ spacing: 6px; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {g['BORDER']}; border-radius: 3px; background: {g['INPUT']}; }}
QCheckBox::indicator:checked {{ background: {g['ACCENT']}; border-color: {g['ACCENT']}; image: url({CHECK_ICON}); }}
QSlider::groove:horizontal {{ height: 4px; background: {g['BORDER']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {g['ACCENT']}; border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 14px; margin: -6px 0; border-radius: 7px; background: {g['PANEL']}; border: 1px solid {g['TEXT_MUTED']}; }}
QMenu {{ background: {g['INPUT']}; border: 1px solid {g['BORDER']}; padding: 4px; }}
QMenu::item {{ padding: 5px 26px 5px 12px; border-radius: 4px; }}
QMenu::item:selected {{ background: {g['ACCENT_LIGHT']}; }}
QMenu::item:disabled {{ color: {g['TEXT_MUTED']}; }}
QMenu::separator {{ height: 1px; background: {g['BORDER']}; margin: 4px 6px; }}
QStatusBar {{ background: {g['PANEL']}; border-top: 1px solid {g['BORDER']}; }}
QStatusBar QLabel {{ color: {g['TEXT_MUTED']}; padding: 0 8px; }}
QMessageBox, QInputDialog, QDialog {{ background: {g['PANEL']}; }}
QPushButton {{ border: 1px solid {g['BORDER']}; border-radius: 5px; padding: 5px 16px; background: {g['INPUT']}; }}
QPushButton:hover {{ border-color: {g['ACCENT']}; }}
QPushButton#primary {{ background: {g['ACCENT']}; color: white; border-color: {g['ACCENT']}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {g['ACCENT_DARK']}; }}
QTableWidget {{ border: 1px solid {g['BORDER']}; gridline-color: {g['BORDER']}; background: {g['INPUT']}; }}
QHeaderView::section {{ background: {g['PANEL_ALT']}; border: none; border-bottom: 1px solid {g['BORDER']}; padding: 5px; font-weight: 600; }}
QToolTip {{ background: #2b2f36; color: white; border: none; padding: 5px 7px; }}
"""


apply("light")