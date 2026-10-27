"""Diálogos: propiedades de componentes (doble clic en un componente), lista de materiales, atajos de teclado."""
from __future__ import annotations

import csv

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ..model import parts as P
from ..model.circuit import Circuit, Component
from ..model.types_info import describe
from ..model.units import _NUM, fmt, has_unit_box, join, parse, split, unit_choices
from . import symbols as S
from . import theme


def _plain_number(text) -> bool:
    import re
    return re.fullmatch(_NUM, str(text).strip().replace(" ", "").replace(",", ".")) is not None


class PropertiesDialog(QDialog):
    """Cambiar la referencia y los valores de un componente. Los valores se escriben de la forma habitual: 10k, 4k7, 100n …"""

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
        self.ref.setToolTip("La etiqueta en el diagrama, p. ej. R1")
        form.addRow("Etiqueta", self.ref)
        self.fields = {}
        self.unit_boxes = {}
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
                if p.key == "model":
                    for ix, ch in enumerate(p.choices):
                        if describe(ch):
                            w.setItemData(ix, describe(ch), Qt.ToolTipRole)
            elif has_unit_box(p.unit):
                # el número, con un cuadro al lado para su escala: Ω / kΩ / MΩ, pF / nF / µF …
                num, choice = split(float(v), p.unit)
                w = QLineEdit(num)
                dnum, dchoice = split(float(p.default), p.unit)
                w.setPlaceholderText(f"p. ej. {dnum}")
                w.setToolTip(p.help or "Escriba el número y elija su escala — o escríbalo todo, como 4k7 o 100n")
                box = QComboBox()
                box.addItems(unit_choices(p.unit))
                box.setCurrentText(choice)
                box.setToolTip("Ω, kΩ (mil), MΩ (millón) … o pF, nF, µF …")
                w.textChanged.connect(self._validate)
                box.currentTextChanged.connect(self._validate)
                w.editingFinished.connect(lambda p=p, w=w, box=box: self._tidy(p, w, box))
                self.unit_boxes[p.key] = box
                row = QWidget()
                rl = QHBoxLayout(row)
                rl.setContentsMargins(0, 0, 0, 0)
                rl.setSpacing(6)
                rl.addWidget(w, 1)
                rl.addWidget(box)
                self.fields[p.key] = (p, w)
                form.addRow(p.label, row)
                continue
            else:
                w = QLineEdit(fmt(v, p.unit))
                w.setPlaceholderText(f"p. ej. {fmt(p.default, p.unit)}")
                tip = p.help or "Escriba valores como 10k, 4k7, 2M2, 100n, 4.7µ"
                w.setToolTip(tip)
                w.textChanged.connect(self._validate)
            self.fields[p.key] = (p, w)
            form.addRow(p.label, w)
            if p.kind == "choice" and p.key == "model":
                # para qué sirve este tipo — así puede ver por qué elegiría uno sobre otro
                info = QLabel(describe(w.currentText()))
                info.setObjectName("hint")
                info.setWordWrap(True)
                info.setMinimumWidth(300)
                w.currentTextChanged.connect(lambda t, lab=info: lab.setText(describe(t)))
                self.type_info = info
                form.addRow("", info)
        lay.addLayout(form)
        self.error = QLabel("")
        self.error.setObjectName("dialogError")
        self.error.setWordWrap(True)
        lay.addWidget(self.error)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        self.ok = QPushButton("Aceptar")
        self.ok.setObjectName("primary")
        self.ok.setDefault(True)
        self.ok.clicked.connect(self._accept)
        btns.addWidget(cancel)
        btns.addWidget(self.ok)
        lay.addLayout(btns)
        self.values = {}

    def _tidy(self, p, w, box):
        """Alguien escribió el valor completo (4k7, 100n): mostrarlo como un número y su escala en el cuadro."""
        try:
            v = join(w.text(), box.currentText(), p.unit)
        except ValueError:
            return
        num, choice = split(v, p.unit)
        if (num, choice) != (w.text().strip(), box.currentText()) and not _plain_number(w.text()):
            w.setText(num)
            box.setCurrentText(choice)

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
                    if key in self.unit_boxes:
                        v = join(w.text(), self.unit_boxes[key].currentText(), p.unit)
                    else:
                        v = parse(w.text(), p.unit)
                    if p.min is not None and v < p.min:
                        raise ValueError(f"{p.label} debe ser al menos {fmt(p.min, p.unit)}")
                    if p.max is not None and v > p.max:
                        raise ValueError(f"{p.label} puede ser como máximo {fmt(p.max, p.unit)}")
                    out[key] = v
                    w.setProperty("invalid", "false")
                except ValueError as e:
                    problems.append(str(e))
                    w.setProperty("invalid", "true")
                w.style().unpolish(w)
                w.style().polish(w)
        ref = self.ref.text().strip()
        if not ref:
            problems.append("La etiqueta no puede estar vacía")
        elif any(c.ref == ref and c.id != self.comp.id for c in self.circuit.components.values()):
            problems.append(f"Ya hay otro componente llamado {ref}")
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
        self.setWindowTitle("Lista de materiales")
        self.resize(560, 420)
        self.rows = circuit.bill_of_materials()
        lay = QVBoxLayout(self)
        title = QLabel(f"Lista de componentes — {sum(r['qty'] for r in self.rows)} componentes")
        title.setObjectName("dialogTitle")
        lay.addWidget(title)
        t = QTableWidget(len(self.rows), 3)
        t.setHorizontalHeaderLabels(["Cant.", "Componente", "Etiquetas"])
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
        copy = QPushButton("Copiar")
        copy.clicked.connect(self._copy)
        save = QPushButton("Guardar como CSV…")
        save.clicked.connect(self._save)
        close = QPushButton("Cerrar")
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        btns.addWidget(copy)
        btns.addWidget(save)
        btns.addStretch(1)
        btns.addWidget(close)
        lay.addLayout(btns)

    def _copy(self):
        text = "Cant.\tComponente\tEtiquetas\n" + "\n".join(f"{r['qty']}\t{r['description']}\t{', '.join(r['refs'])}"
                                                   for r in self.rows)
        QApplication.clipboard().setText(text)

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar lista de componentes", "lista de componentes.csv", "Archivos CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Cant.", "Componente", "Etiquetas"])
            for r in self.rows:
                w.writerow([r["qty"], r["description"], " ".join(r["refs"])])


SHORTCUTS = [
    ("Colocar un componente", "Haga clic en él en la galería, luego clic en la hoja (o arrástrelo)"),
    ("Dibujar un cable", "Arrastre de un pin a otro — o haga clic en un pin, clic en las esquinas, clic en el pin final"),
    ("Ramificar un cable", "W (herramienta cable), luego presione sobre el cable"),
    ("Mover un cable", "Arrastre el cable hacia un lado; arrastre un extremo suelto para reconectarlo"),
    ("Cambiar un valor", "Doble clic en el componente (o selecciónelo y presione Intro)"),
    ("Rotar / voltear", "R  /  Mayús+R  /  F"),
    ("Eliminar", "Supr o Retroceso"),
    ("Copiar / pegar / duplicar", "Ctrl+C  /  Ctrl+V  /  Ctrl+D"),
    ("Deshacer / rehacer", "Ctrl+Z  /  Ctrl+Y"),
    ("Ejecutar / pausar / detener", "F5  /  F6  /  Mayús+F5 (o los botones en el centro de la barra de herramientas)"),
    ("Durante la ejecución", "Haga clic en interruptores, mantenga presionados los pulsadores, arrastre los deslizadores, pase el mouse para leer voltajes"),
    ("Gráfico (osciloscopio)", "Coloque sondas de gráfico (A–D) en los cables, presione Ejecutar; Ctrl+G muestra / oculta el gráfico"),
    ("Lecturas", "Durante la ejecución, el botón Lecturas muestra el voltaje y la corriente en cada cable y componente — "
                 "o haga clic en cualquier cable o componente para fijar solo su lectura (clic de nuevo para desfijar). Arrastre una lectura para "
                 "moverla fuera del camino"),
    ("Sonda lógica", "Tóquela en un cable: H = alto, L = bajo"),
    ("Sonido", "Zumbadores, parlantes, motores y relés emiten sonido durante la ejecución — el botón de sonido lo desactiva"),
    ("Clic derecho", "Un menú para lo que esté bajo el mouse (rotar, eliminar, propiedades …)"),
    ("Notas", "Agregue una nota de texto (Etiquetas) para explicar su circuito; doble clic para editarla"),
    ("Zoom", "Rueda del mouse, o + y −;  Ajustar zoom: Ctrl+0"),
    ("Panorámica", "Arrastrar con el botón central, o mantener Espacio y arrastrar"),
    ("Detener lo que está haciendo", "Esc (o clic derecho)"),
]


class ShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cómo usar Wirely")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 14)
        title = QLabel("Mouse y teclado")
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
        ok = QPushButton("Cerrar")
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        h = QHBoxLayout()
        h.addStretch(1)
        h.addWidget(ok)
        lay.addLayout(h)