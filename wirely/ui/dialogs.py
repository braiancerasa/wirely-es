"""Dialogs: part properties (double-click a part), bill of materials, keyboard shortcuts."""
from __future__ import annotations

import csv

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ..model import parts as P
from ..model.circuit import Circuit, Component
from ..model.units import fmt, parse
from . import symbols as S
from . import theme


class PropertiesDialog(QDialog):
    """Change a part's reference and values. Values are typed the normal way: 10k, 4k7, 100n …"""

    def __init__(self, comp: Component, circuit: Circuit, parent=None):
        super().__init__(parent)
        self.comp, self.circuit = comp, circuit
        part = comp.part
        self.setWindowTitle(f"{comp.ref} – {part.name}")
        self.setMinimumWidth(380)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(10)

        top = QHBoxLayout()
        pic = QLabel()
        pic.setPixmap(S.pixmap(part.key, 76, 50, QColor(theme.INK), QColor(theme.PANEL), comp.props))
        top.addWidget(pic)
        tv = QVBoxLayout()
        title = QLabel(part.name)
        title.setObjectName("dialogTitle")
        hint = QLabel(part.description)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        tv.addWidget(title)
        tv.addWidget(hint)
        top.addLayout(tv, 1)
        lay.addLayout(top)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        self.ref = QLineEdit(comp.ref)
        self.ref.setToolTip("The label on the diagram, e.g. R1")
        form.addRow("Label", self.ref)
        self.fields = {}
        for p in part.props:
            v = comp.value(p.key)
            if p.kind == "bool":
                w = QCheckBox()
                w.setChecked(bool(v))
            elif p.kind == "text":
                w = QPlainTextEdit(str(v))
                w.setFixedHeight(70)
                w.setTabChangesFocus(True)
            elif p.kind == "choice":
                w = QComboBox()
                for ch in p.choices:
                    if p.key == "colour" and ch in S.LED_RGB:
                        pm = QPixmap(14, 14)
                        pm.fill(QColor(S.LED_RGB[ch]))
                        w.addItem(QIcon(pm), ch)
                    else:
                        w.addItem(ch)
                w.setCurrentText(str(v))
            else:
                w = QLineEdit(fmt(v, p.unit))
                w.setPlaceholderText(f"e.g. {fmt(p.default, p.unit)}")
                tip = p.help or "Type values like 10k, 4k7, 2M2, 100n, 4.7µ"
                w.setToolTip(tip)
                w.textChanged.connect(self._validate)
            self.fields[p.key] = (p, w)
            form.addRow(p.label, w)
        lay.addLayout(form)
        self.error = QLabel("")
        self.error.setObjectName("dialogError")
        self.error.setWordWrap(True)
        lay.addWidget(self.error)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.ok = QPushButton("OK")
        self.ok.setObjectName("primary")
        self.ok.setDefault(True)
        self.ok.clicked.connect(self._accept)
        btns.addWidget(cancel)
        btns.addWidget(self.ok)
        lay.addLayout(btns)
        self.values = {}

    def _read(self):
        out, problems = {}, []
        for key, (p, w) in self.fields.items():
            if p.kind == "bool":
                out[key] = w.isChecked()
            elif p.kind == "text":
                out[key] = w.toPlainText().strip() or " "
            elif p.kind == "choice":
                out[key] = w.currentText()
            else:
                try:
                    v = parse(w.text(), p.unit)
                    if p.min is not None and v < p.min:
                        raise ValueError(f"{p.label} must be at least {fmt(p.min, p.unit)}")
                    if p.max is not None and v > p.max:
                        raise ValueError(f"{p.label} can be at most {fmt(p.max, p.unit)}")
                    out[key] = v
                    w.setProperty("invalid", "false")
                except ValueError as e:
                    problems.append(str(e))
                    w.setProperty("invalid", "true")
                w.style().unpolish(w)
                w.style().polish(w)
        ref = self.ref.text().strip()
        if not ref:
            problems.append("The label can't be empty")
        elif any(c.ref == ref and c.id != self.comp.id for c in self.circuit.components.values()):
            problems.append(f"Another part is already called {ref}")
        return out, ref, problems

    def _validate(self):
        _out, _ref, problems = self._read()
        self.error.setText(problems[0] if problems else "")
        self.ok.setEnabled(not problems)

    def _accept(self):
        out, ref, problems = self._read()
        if problems:
            self.error.setText(problems[0])
            return
        self.values, self.new_ref = out, ref
        self.accept()


class BomDialog(QDialog):
    def __init__(self, circuit: Circuit, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bill of materials")
        self.resize(560, 420)
        self.rows = circuit.bill_of_materials()
        lay = QVBoxLayout(self)
        title = QLabel(f"Parts list — {sum(r['qty'] for r in self.rows)} parts")
        title.setObjectName("dialogTitle")
        lay.addWidget(title)
        t = QTableWidget(len(self.rows), 3)
        t.setHorizontalHeaderLabels(["Qty", "Part", "Labels"])
        t.verticalHeader().hide()
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        t.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        t.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for i, r in enumerate(self.rows):
            q = QTableWidgetItem(str(r["qty"]))
            q.setTextAlignment(Qt.AlignCenter)
            t.setItem(i, 0, q)
            t.setItem(i, 1, QTableWidgetItem(r["description"]))
            t.setItem(i, 2, QTableWidgetItem(", ".join(r["refs"])))
        lay.addWidget(t, 1)
        btns = QHBoxLayout()
        copy = QPushButton("Copy")
        copy.clicked.connect(self._copy)
        save = QPushButton("Save as CSV…")
        save.clicked.connect(self._save)
        close = QPushButton("Close")
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        btns.addWidget(copy)
        btns.addWidget(save)
        btns.addStretch(1)
        btns.addWidget(close)
        lay.addLayout(btns)

    def _copy(self):
        text = "Qty\tPart\tLabels\n" + "\n".join(f"{r['qty']}\t{r['description']}\t{', '.join(r['refs'])}"
                                                   for r in self.rows)
        QApplication.clipboard().setText(text)

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save parts list", "parts list.csv", "CSV files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Qty", "Part", "Labels"])
            for r in self.rows:
                w.writerow([r["qty"], r["description"], " ".join(r["refs"])])


SHORTCUTS = [
    ("Place a part", "Click it in the gallery, then click on the sheet (or drag it across)"),
    ("Draw a wire", "Drag from one pin to another — or click a pin, click corners, click the end pin"),
    ("Branch off a wire", "W (wire tool), then press on the wire"),
    ("Move a wire", "Drag the wire sideways; drag a loose end to reconnect it"),
    ("Change a value", "Double-click the part (or select it and press Enter)"),
    ("Rotate / flip", "R  /  Shift+R  /  F"),
    ("Delete", "Delete or Backspace"),
    ("Copy / paste / duplicate", "Ctrl+C  /  Ctrl+V  /  Ctrl+D"),
    ("Undo / redo", "Ctrl+Z  /  Ctrl+Y"),
    ("Run / pause / stop", "F5  /  F6  /  Shift+F5 (or the buttons in the middle of the toolbar)"),
    ("While running", "Click switches, hold push switches, drag the sliders, hover to read voltages"),
    ("Graph (oscilloscope)", "Put graph probes (A–D) on wires, press Play; Ctrl+G shows / hides the graph"),
    ("Logic probe", "Touch it on a wire: H = high, L = low"),
    ("Sound", "Buzzers, speakers, motors and relays make sound while running — the speaker button turns it off"),
    ("Right-click", "A menu for whatever's under the mouse (rotate, delete, properties …)"),
    ("Notes", "Add a Text note (Labels) to explain your circuit; double-click to edit it"),
    ("Zoom", "Mouse wheel, or + and −;  Fit everything: Ctrl+0"),
    ("Pan", "Middle-drag, or hold Space and drag"),
    ("Stop what you're doing", "Esc (or right-click)"),
]


class ShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("How to use Wirely")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 14)
        title = QLabel("Mouse and keyboard")
        title.setObjectName("dialogTitle")
        lay.addWidget(title)
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(7)
        for a, b in SHORTCUTS:
            l = QLabel(f"<b>{a}</b>")
            r = QLabel(b)
            r.setWordWrap(True)
            form.addRow(l, r)
        w = QWidget()
        w.setLayout(form)
        lay.addWidget(w)
        ok = QPushButton("Close")
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        h = QHBoxLayout()
        h.addStretch(1)
        h.addWidget(ok)
        lay.addLayout(h)
