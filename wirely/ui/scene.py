"""La hoja del circuito: muestra un Circuit y maneja colocar, seleccionar, mover y cablear con el mouse.

El Circuit (modelo) es siempre la verdad. Las acciones del mouse cambian el modelo, mantienen los elementos en sincronía, y cuando una
acción termina se emite `edited` para que la ventana registre un paso de deshacer.
"""
from __future__ import annotations

import json
import re

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QGraphicsScene

from ..model import parts as P
from ..model.circuit import Circuit, Component, Wire, drag_end, move_segment, route, snap, tidy
from ..model.circuit import on_segment as _on_seg
from . import theme
from .items import ComponentItem, DraftWire, WireItem, live_look_key

MIME_PART = "application/x-wirely-part"
MIME_CLIP = "application/x-wirely-clip"
DRAG_START = 4          # píxeles antes de que una pulsación se convierta en arrastre


def _pt(p: QPointF):
    return (snap(p.x()), snap(p.y()))


class CircuitScene(QGraphicsScene):
    edited = Signal(str)            # una acción terminó: etiqueta para la lista de deshacer
    editRequested = Signal(str)     # componente con doble clic (id del componente)
    status = Signal(str)            # breve indicación para la barra de estado
    modeChanged = Signal(str)       # "select" | "wire" | "place"

    def __init__(self, circuit: Circuit | None = None):
        super().__init__()
        self.setSceneRect(-4000, -3000, 8000, 6000)
        self.circuit = circuit or Circuit()
        self.comp_items: dict[str, ComponentItem] = {}
        self.wire_items: dict[str, WireItem] = {}
        self.mode = "select"
        self.show_grid = True
        self.exporting = False
        self._junctions, self._open_pins = [], []
        self._hover_pin = None
        self._drag = None           # qué está haciendo el arrastre actual con el botón izquierdo
        self._ghost = None          # componente esperando ser colocado
        self._place_kind = None
        self._place_keep = False
        self.draft = DraftWire()
        self.addItem(self.draft)
        self.draft.hide()
        self._wiring = None         # {"fixed": [...], "click": bool}
        # simulación en vivo
        self.sim = None             # SimController mientras se ejecuta / pausa
        self.show_volts = True
        self.show_flow = True
        self.show_readings = False
        self.pinned = set()         # cables y componentes cuya lectura se muestra durante la ejecución (clicados)
        self.tag_offsets = {}       # etiquetas de lectura arrastradas a otro sitio: id de cable/componente -> (dx, dy)
        self._tag_hits = []         # dónde se dibujaron las etiquetas de lectura en el último fotograma: (rect, id)
        self._drag_tag = None       # (id, inicio del mouse, desplazamiento al inicio) mientras se arrastra una etiqueta de lectura
        self.anim_t = 0.0
        self.sliders = []
        self._held = None           # pulsador que se mantiene presionado
        self._junction_net = {}
        self.hover_info = None      # (punto de escena, título, líneas) para la burbuja de lectura
        self.rebuild()

    # ================================================================== modelo <-> elementos
    def rebuild(self):
        """Recrear cada elemento desde el modelo (tras cargar, deshacer …)."""
        for it in list(self.comp_items.values()) + list(self.wire_items.values()):
            self.removeItem(it)
        self.comp_items.clear()
        self.wire_items.clear()
        for c in self.circuit.components.values():
            self._add_comp_item(c)
        for w in self.circuit.wires.values():
            self._add_wire_item(w)
        self.refresh_connections()

    def _add_comp_item(self, c: Component):
        it = ComponentItem(c)
        self.addItem(it)
        self.comp_items[c.id] = it
        return it

    def _add_wire_item(self, w: Wire):
        it = WireItem(w)
        self.addItem(it)
        self.wire_items[w.id] = it
        return it

    def set_circuit(self, circuit: Circuit):
        self.cancel()
        self.pinned = set()
        self.tag_offsets = {}
        self.circuit = circuit
        self.rebuild()

    def refresh_connections(self):
        self._junctions = self.circuit.junctions()
        self._open_pins = [pos for _c, _n, pos in self.circuit.unconnected_pins()]
        self.update()

    def sync_component(self, cid):
        it = self.comp_items.get(cid)
        if it:
            it.sync()

    # ================================================================== ayudantes
    def tolerance(self) -> float:
        v = self.views()
        s = v[0].transform().m11() if v else 1.0
        return max(4.0, 8.0 / max(s, 0.05))

    def pin_at(self, pos: QPointF, exclude=()):
        """(componente, nombre de pin, posición) del pin más cercano al alcance, o None."""
        tol = self.tolerance()
        best, best_d = None, tol * tol
        for c in self.circuit.components.values():
            if c.id in exclude:
                continue
            for name, (x, y) in c.pin_positions().items():
                d = (x - pos.x()) ** 2 + (y - pos.y()) ** 2
                if d <= best_d:
                    best, best_d = (c, name, (x, y)), d
        return best

    def wire_end_at(self, pos: QPointF):
        tol = self.tolerance()
        for w in self.circuit.wires.values():
            for end in (0, -1):
                x, y = w.points[end]
                if (x - pos.x()) ** 2 + (y - pos.y()) ** 2 <= tol * tol:
                    return w, end
        return None

    def item_at(self, pos: QPointF):
        for it in self.items(pos):
            if isinstance(it, (ComponentItem, WireItem)) and it.isVisible() and not getattr(it, "ghost", False):
                return it
        return None

    def selected_ids(self):
        comps = [it.comp.id for it in self.selectedItems() if isinstance(it, ComponentItem)]
        wires = [it.wire.id for it in self.selectedItems() if isinstance(it, WireItem)]
        return comps, wires

    def selected_components(self):
        return [it.comp for it in self.selectedItems() if isinstance(it, ComponentItem)]

    def select_ids(self, ids):
        self.clearSelection()
        for i in ids:
            it = self.comp_items.get(i) or self.wire_items.get(i)
            if it:
                it.setSelected(True)

    # ================================================================== simulación en vivo
    def sim_active(self) -> bool:
        return self.sim is not None and self.sim.active()

    def attach_sim(self, controller):
        self.sim = controller
        controller.frame.connect(self._on_frame)
        controller.stateChanged.connect(self._on_sim_state)

    def _on_sim_state(self, state):
        from .live_items import SliderItem
        from .simcontrol import ADJUSTABLE
        for sl in self.sliders:
            self.removeItem(sl)
        self.sliders = []
        self._held = None
        self.hover_info = None
        if state != "stopped":
            self.cancel()
            self.clearSelection()
            for it in self.comp_items.values():
                key = ADJUSTABLE.get(it.comp.kind)
                if key:
                    sl = SliderItem(it, key, self.sim_set_value)
                    self.addItem(sl)
                    self.sliders.append(sl)
            # a qué red pertenece cada punto de unión (para su color)
            self._junction_net = {}
            for net in self.sim.sim.nets:
                for pt in self._junctions:
                    if pt in net.points:
                        self._junction_net[pt] = net.name
        self.repaint_all()

    def _on_frame(self):
        self.anim_t = self.sim.live.t if self.sim else 0.0
        self.update_hover()
        changed = self.refresh_look()
        fg = self._foreground_key()
        # nada en pantalla se ve diferente: no dibujar la misma imagen de nuevo (ahorra mucha CPU)
        self.frame_changed = bool(changed or fg != self._last_fg)
        if self.frame_changed:
            self._last_fg = fg
            self.update()

    _last_fg = None
    frame_changed = True

    def repaint_all(self):
        """Dibujar cada componente y cable de nuevo (cambió el tema, los colores de voltaje o el estado de simulación)."""
        for it in list(self.comp_items.values()) + list(self.wire_items.values()):
            it.look = ("stale",)
            it.update()
        self._last_fg = None
        self.refresh_look()
        self.update()

    def refresh_look(self) -> bool:
        """Componentes y cables mantienen una imagen ya dibujada; redibujar solo aquellos cuyo aspecto en vivo ha cambiado (un resplandor,
        una lectura, el color de voltaje de un cable …). Devuelve True si alguno lo hizo."""
        active = self.sim_active()
        changed = False
        for it in self.comp_items.values():
            k = live_look_key(self.live_part(it.comp.id), it.comp.kind, self.anim_t) if active else None
            if k != it.look:
                it.look = k
                it.update()
                changed = True
        colours = active and self.show_volts
        wire_v, vmax = (self.sim.live.wire_v, self.sim.live.vmax) if colours else ({}, 1.0)
        for wid, it in self.wire_items.items():
            v = wire_v.get(wid)            # su color viene de su voltaje (pasos más finos de lo que se puede ver)
            k = (round(v / max(vmax, 1e-9) * 400), round(vmax, 2)) if v is not None else None
            if k != it.look:
                it.look = k
                it.update()
                changed = True
        return changed

    def _foreground_key(self):
        """De qué se dibujan los puntos, uniones, lecturas y la clave de color, con la precisión que se puede ver."""
        if not self.sim_active():
            return None
        live = self.sim.live
        h = self.hover_info
        bubble = (round(h[0].x(), 1), round(h[0].y(), 1), h[1], tuple(h[2])) if h else None

        def r3(v):
            return float(f"{v:.3g}") if isinstance(v, float) else v
        k = [round(live.vmax, 2), self.show_flow, self.show_volts, self.show_readings, tuple(sorted(self.pinned)),
             tuple(sorted(self.tag_offsets.items())), bubble]
        if self.show_volts:
            k.append(tuple((n, round(v, 2)) for n, v in sorted(live.net_v.items())))
        if self.show_flow:
            k.append(tuple((round(ph, 1), r3(a)) for _a, _b, ph, a in live.flows))
        if self.show_readings or self.pinned:
            k.append(tuple((wid, r3(v)) for wid, v in sorted(live.wire_v.items())))
            k.append(tuple(r3(a) for _a, _b, _ph, a in live.flows))
            for cid in sorted(live.parts):
                info = live.parts[cid]
                k.append((cid, info.get("reading"), r3(info.get("v")), r3(info.get("i")), r3(info.get("p"))))
        return tuple(k)

    def sim_set_value(self, cid, key, value):
        if self.sim_active():
            self.sim.set_value(cid, key, value)
            it = self.comp_items.get(cid)
            if it:
                it.update()

    def live_part(self, cid):
        if not self.sim_active():
            return None
        return self.sim.live.parts.get(cid)

    def wire_colour(self, wid):
        if not (self.sim_active() and self.show_volts):
            return None
        v = self.sim.live.wire_v.get(wid)
        if v is None:
            return None
        return theme.volt_colour(v, self.sim.live.vmax)

    def _wire_current(self, wire, pos):
        """Corriente en el trozo de este cable más cercano al mouse, y en qué dirección fluye (una flecha)."""
        best = None
        px, py = pos.x(), pos.y()
        for (x1, y1), (x2, y2), _ph, amps in self.sim.live.flows:
            # solo trozos que pertenecen a este cable
            if not any(_on_seg((x1, y1), a_, b_) and _on_seg((x2, y2), a_, b_) for a_, b_ in wire.segments()):
                continue
            dx, dy = x2 - x1, y2 - y1
            L = dx * dx + dy * dy
            t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
            d = (x1 + t * dx - px) ** 2 + (y1 + t * dy - py) ** 2
            if best is None or d < best[0]:
                if amps < 0:
                    dx, dy = -dx, -dy
                arrow = ("→" if dx > 0 else "←") if abs(dx) >= abs(dy) else ("↓" if dy > 0 else "↑")
                best = (d, abs(amps), arrow)
        return (best[1], best[2]) if best else (0.0, "")

    def _probe_info(self, pos):
        """(título, líneas) para mostrar junto al mouse mientras la simulación se ejecuta, o None."""
        from ..model.units import fmt
        item = self.item_at(pos)
        live = self.sim.live
        if isinstance(item, WireItem):
            v = live.wire_v.get(item.wire.id)
            if v is None:
                return None
            amps, arrow = self._wire_current(item.wire, pos)
            cur = f"{fmt(amps, 'A')} {arrow}" if amps >= 1e-6 else "sin corriente"
            return "Cable", [f"Voltaje: {fmt(v if abs(v) >= 1e-3 else 0.0, 'V')}", f"Corriente: {cur}"]
        if isinstance(item, ComponentItem):
            info = live.parts.get(item.comp.id)
            if not info or "v" not in info:
                return None
            lines = [f"Voltaje: {fmt(abs(info['v']), 'V')}", f"Corriente: {fmt(abs(info['i']), 'A')}"]
            if self.power_only(item.comp):
                lines = [f"Potencia: {fmt(abs(info.get('p', 0.0)), 'W')}"]
            elif abs(info.get("p", 0)) > 1e-6 and item.comp.kind not in ("cell", "battery", "dc_supply", "ac_supply",
                                                                          "rail_pos", "signal_gen"):
                lines.append(f"Potencia: {fmt(abs(info['p']), 'W')}")
            if "rpm" in info:
                lines.append(f"Velocidad: {abs(info['rpm']):.0f} rpm")
            if info.get("blown"):
                lines.append("Roto — presione Detener para repararlo")
            return item.comp.ref, lines

    def _probe_text(self, pos):
        info = self._probe_info(pos)
        return None if info is None else f"{info[0]}:  " + "   ".join(info[1])

    def update_hover(self, pos=None):
        """Actualizar la burbuja de lectura en el mouse (llamado en movimientos del mouse y en cada fotograma)."""
        if pos is not None:
            self._mouse_pos = pos
        p = getattr(self, "_mouse_pos", None)
        if self._drag_tag is not None or (p is not None and self.tag_at(p) is not None):
            self.hover_info = None             # sobre una etiqueta de lectura (o arrastrándola): sin burbuja encima
            return
        info = self._probe_info(p) if (p is not None and self.sim_active()) else None
        self.hover_info = (p, info[0], info[1]) if info else None

    def _sim_press(self, e):
        from .simcontrol import INTERACTIVE, TOGGLES
        pos = e.scenePos()
        for it in self.items(pos):
            if it in self.sliders:
                QGraphicsScene.mousePressEvent(self, e)
                return
        tag = self.tag_at(pos)
        if tag is not None and e.button() == Qt.LeftButton:       # una etiqueta de lectura: arrastrarla fuera del camino
            self._drag_tag = (tag, QPointF(pos), self.tag_offsets.get(tag, (0.0, 0.0)))
            e.accept()
            return
        item = self.item_at(pos)
        if isinstance(item, ComponentItem) and item.comp.kind in INTERACTIVE and e.button() == Qt.LeftButton:
            c = item.comp
            if c.kind in TOGGLES:
                key = TOGGLES[c.kind]
                self.sim_set_value(c.id, key, not c.value(key))
            elif c.kind in ("spdt", "dpdt"):
                self.sim_set_value(c.id, "position", "B" if c.value("position") == "A" else "A")
            elif c.kind == "rotary":
                self.sim_set_value(c.id, "position", str(int(c.value("position")) % 4 + 1))
            elif c.kind == "keypad":
                key = self._keypad_key(item, pos)
                if key:
                    self.sim_set_value(c.id, "_key", key)
                    self._held = c.id
            else:
                self.sim_set_value(c.id, "pressed", True)
                self._held = c.id
        elif isinstance(item, (ComponentItem, WireItem)) and e.button() == Qt.LeftButton:
            # hacer clic en un cable o componente para fijar su lectura en la hoja (clic de nuevo para quitarla)
            key = item.comp.id if isinstance(item, ComponentItem) else item.wire.id
            self.pinned.symmetric_difference_update({key})
            self.update()
        e.accept()

    def tag_at(self, pos):
        """El cable o componente cuya etiqueta de lectura está bajo pos (la de arriba), o None."""
        for r, key in reversed(self._tag_hits):
            if r.adjusted(-2, -2, 2, 2).contains(pos):
                return key
        return None

    def _keypad_key(self, item, pos):
        """Qué tecla de un teclado está bajo pos (teniendo en cuenta que el teclado esté girado)."""
        from . import symbols as S
        local = pos - item.pos()
        q = S._rotvec(QPointF(local.x(), local.y()), item.comp.rot, item.comp.flip, inverse=True)
        return S.keypad_key_at(q.x(), q.y())

    def _sim_release(self, e):
        if self._drag_tag is not None:
            self._drag_tag = None
            e.accept()
            return
        if self._held:
            comp = self.circuit.components.get(self._held)
            if comp is not None and comp.kind == "keypad":
                self.sim_set_value(self._held, "_key", "")
                comp.props.pop("_key", None)
            else:
                self.sim_set_value(self._held, "pressed", False)
            self._held = None
        QGraphicsScene.mouseReleaseEvent(self, e)

    def _sim_move(self, e):
        from .simcontrol import INTERACTIVE
        pos = e.scenePos()
        if self._drag_tag is not None:
            key, start, (ox, oy) = self._drag_tag
            self.tag_offsets[key] = (ox + pos.x() - start.x(), oy + pos.y() - start.y())
            self._mouse_pos = pos
            self.hover_info = None
            self.update()
            return
        QGraphicsScene.mouseMoveEvent(self, e)
        if self.tag_at(pos) is not None:
            self._mouse_pos = pos
            self.hover_info = None
            for v in self.views():
                v.viewport().setCursor(Qt.OpenHandCursor)
            self.status.emit("Arrastre la lectura para moverla fuera del camino")
            return
        item = self.item_at(pos)
        clickable = isinstance(item, ComponentItem) and item.comp.kind in INTERACTIVE
        for v in self.views():
            v.viewport().setCursor(Qt.PointingHandCursor if clickable else Qt.ArrowCursor)
        self.update_hover(pos)
        if self.sim.state != "running":        # pausado: no llegan fotogramas, así que mostrar la burbuja moviéndose ahora
            self.update()
        text = self._probe_text(pos)
        if clickable:
            what = {"reed_switch": "haga clic para mover el imán", "hall": "haga clic para mover el imán",
                    "tilt_switch": "haga clic para inclinarlo", "rotary": "haga clic para girarlo a la siguiente posición",
                    "keypad": "mantenga presionada una tecla para presionarla"}.get(
                item.comp.kind, "mantenga presionado para presionar" if item.comp.kind.startswith("push") else "haga clic para conmutar")
            text = f"{text}   ·   {what}" if text else what.capitalize()
        elif isinstance(item, (ComponentItem, WireItem)) and text:
            key = item.comp.id if isinstance(item, ComponentItem) else item.wire.id
            text += "   ·   haga clic para " + ("desfijar su lectura" if key in self.pinned else "fijar su lectura")
        self.status.emit(text or "Ejecutando — haga clic en interruptores, arrastre deslizadores, pase el mouse sobre los cables para leer voltajes.")

    # ================================================================== modos
    def set_mode(self, mode: str):
        self.cancel()
        self.mode = mode
        self.modeChanged.emit(mode)
        if mode == "wire":
            self.status.emit("Cable: presione sobre un pin o un cable y arrastre a otro pin. Haga clic para agregar esquinas, Esc para terminar.")
        else:
            self.status.emit("")
        for v in self.views():
            v.viewport().setCursor(Qt.CrossCursor if mode == "wire" else Qt.ArrowCursor)

    def start_placing(self, kind: str, keep=False):
        """Recoger un componente de la galería: sigue al mouse hasta que haga clic en la hoja."""
        self.cancel()
        self._place_kind = kind
        self._place_keep = keep
        comp = Component(kind, 0, 0, props=P.get(kind).defaults(), ref=self.circuit.next_ref(P.get(kind).prefix))
        self._ghost = ComponentItem(comp, ghost=True)
        self.addItem(self._ghost)
        self._ghost.hide()
        self.mode = "place"
        self.modeChanged.emit("place")
        self.status.emit(f"Haga clic en la hoja para colocar el {P.get(kind).name.lower()}. "
                         "R rota, F voltea, Esc cancela.")

    def _move_ghost(self, pos: QPointF):
        if self._ghost:
            self._ghost.comp.x, self._ghost.comp.y = _pt(pos)
            self._ghost.sync()
            self._ghost.show()

    def _drop_ghost(self, pos: QPointF):
        g = self._ghost.comp
        c = self.circuit.add(g.kind, *_pt(pos), rot=g.rot, flip=g.flip, props=dict(g.props))
        self._add_comp_item(c)
        self.clearSelection()
        self.comp_items[c.id].setSelected(True)
        self.refresh_connections()
        self.edited.emit(f"Agregar {c.ref}")
        if self._place_keep:
            self._ghost.comp.ref = self.circuit.next_ref(P.get(g.kind).prefix)
            self._ghost.sync()
        else:
            self.cancel()
            self.set_mode("select")
        return c

    def cancel(self):
        """Detener lo que esté a medias (colocar un componente, dibujar un cable, arrastrar)."""
        if self._ghost is not None:
            self.removeItem(self._ghost)
            self._ghost = None
            self._place_kind = None
            if self.mode == "place":
                self.mode = "select"
                self.modeChanged.emit("select")
        if self._wiring is not None:
            self._wiring = None
            self.draft.hide()
        if self._drag is not None and self._drag.get("restore"):
            self._drag["restore"]()
            self._drag = None
            self.refresh_connections()
        self._drag = None
        self.status.emit("")

    # ================================================================== operaciones de edición
    def _apply_moves(self, moves: dict, orig_comps: dict, orig_wires: dict, translate_wires: set, delta=(0, 0)):
        """Poner los componentes en nuevos lugares (moves: id -> (x, y, rot, flip)) y hacer que los cables sigan.

        orig_comps / orig_wires guardan el estado de antes de la acción, así un arrastre siempre se calcula desde
        donde empezó (sin deriva). Los cables en translate_wires se mueven en bloque por delta."""
        moved_pins = {}
        for cid, (x, y, rot, flip) in moves.items():
            c = self.circuit.components[cid]
            ox, oy, orot, oflip = orig_comps[cid]
            c.x, c.y, c.rot, c.flip = ox, oy, orot, oflip
            old = c.pin_positions()
            c.x, c.y, c.rot, c.flip = x, y, rot, flip
            new = c.pin_positions()
            for name, pos in old.items():
                moved_pins[pos] = new[name]
            self.sync_component(cid)
        dx, dy = delta
        for wid in translate_wires:
            w = self.circuit.wires.get(wid)
            if w:
                w.points = [(x + dx, y + dy) for x, y in orig_wires[wid]]
                for e in (orig_wires[wid][0], orig_wires[wid][-1]):
                    moved_pins.setdefault(e, (e[0] + dx, e[1] + dy))
        for wid, pts in orig_wires.items():
            if wid in translate_wires or wid not in self.circuit.wires:
                continue
            a, b = pts[0], pts[-1]
            na, nb = moved_pins.get(a), moved_pins.get(b)
            w = self.circuit.wires[wid]
            if na and nb and (na[0] - a[0], na[1] - a[1]) == (nb[0] - b[0], nb[1] - b[1]):
                ddx, ddy = na[0] - a[0], na[1] - a[1]
                w.points = [(x + ddx, y + ddy) for x, y in pts]
            else:
                new = list(pts)
                if na:
                    new = drag_end(new, 0, na)
                if nb:
                    new = drag_end(new, -1, nb)
                w.points = new if len(new) >= 2 else [na or a, nb or b]
        for wid in self.wire_items:
            self.wire_items[wid].sync()

    def _snapshot_geometry(self, comp_ids=None):
        comps = {cid: (c.x, c.y, c.rot, c.flip) for cid, c in self.circuit.components.items()
                 if comp_ids is None or cid in comp_ids}
        wires = {wid: list(w.points) for wid, w in self.circuit.wires.items()}
        return comps, wires

    def rotate_selected(self, clockwise=True):
        if self._ghost is not None:
            g = self._ghost.comp
            g.rot = (g.rot + (1 if clockwise else 3)) % 4
            self._ghost.sync()
            return
        comps = self.selected_components()
        if not comps:
            return
        oc, ow = self._snapshot_geometry()
        moves = {c.id: (c.x, c.y, (c.rot + (1 if clockwise else 3)) % 4, c.flip) for c in comps}
        self._apply_moves(moves, oc, ow, set())
        self.refresh_connections()
        self.edited.emit("Rotar")

    def flip_selected(self):
        if self._ghost is not None:
            self._ghost.comp.flip = not self._ghost.comp.flip
            self._ghost.sync()
            return
        comps = self.selected_components()
        if not comps:
            return
        oc, ow = self._snapshot_geometry()
        moves = {c.id: (c.x, c.y, c.rot, not c.flip) for c in comps}
        self._apply_moves(moves, oc, ow, set())
        self.refresh_connections()
        self.edited.emit("Voltear")

    def delete_selected(self):
        comps, wires = self.selected_ids()
        if not comps and not wires:
            return
        for cid in comps:
            self.removeItem(self.comp_items.pop(cid))
            self.circuit.remove(cid)
        for wid in wires:
            self.removeItem(self.wire_items.pop(wid))
            self.circuit.remove(wid)
        self.refresh_connections()
        self.edited.emit("Eliminar")

    def select_all(self):
        for it in list(self.comp_items.values()) + list(self.wire_items.values()):
            it.setSelected(True)

    def copy_data(self) -> str | None:
        comps, wires = self.selected_ids()
        if not comps and not wires:
            return None
        d = {"components": [self.circuit.components[c].to_dict() for c in comps],
             "wires": [self.circuit.wires[w].to_dict() for w in wires]}
        return json.dumps(d)

    def paste_data(self, text: str, offset=(20, 20)):
        try:
            d = json.loads(text)
        except (ValueError, TypeError):
            return False
        new_ids = []
        dx, dy = offset
        for cd in d.get("components", []):
            part = P.PARTS.get(cd.get("kind"))
            if not part:
                continue
            c = self.circuit.add(cd["kind"], cd["x"] + dx, cd["y"] + dy, cd.get("rot", 0), cd.get("flip", False),
                                 cd.get("props"))
            self._add_comp_item(c)
            new_ids.append(c.id)
        for wd in d.get("wires", []):
            w = self.circuit.add_wire([(x + dx, y + dy) for x, y in wd["points"]])
            if w:
                self._add_wire_item(w)
                new_ids.append(w.id)
        if not new_ids:
            return False
        self.select_ids(new_ids)
        self.refresh_connections()
        self.edited.emit("Pegar")
        return True

    def update_component(self, cid, props: dict, ref: str | None = None):
        c = self.circuit.components[cid]
        c.props.update(props)
        if ref:
            c.ref = ref
        self.sync_component(cid)
        self.edited.emit(f"Editar {c.ref}")

    # ================================================================== mouse
    def mousePressEvent(self, e):
        if self.sim_active():
            self._sim_press(e)
            return
        pos = e.scenePos()
        if e.button() != Qt.LeftButton:
            if e.button() == Qt.RightButton and (self._wiring or self._ghost):
                self.cancel()
                if self.mode == "place":
                    self.set_mode("select")
                e.accept()
                return
            super().mousePressEvent(e)
            return
        e.accept()
        if self._ghost is not None:
            self._drop_ghost(pos)
            return
        if self._wiring is not None:            # modo de enrutado por clics: agregar una esquina o terminar
            self._wiring_click(pos)
            return
        mods = e.modifiers()
        pin = self.pin_at(pos)
        if pin is not None:
            self._start_wire(pin[2], from_pin=True)
            return
        if self.mode == "wire":
            end = self.wire_end_at(pos)
            self._start_wire(end[0].points[end[1]] if end else _pt(pos), from_pin=False)
            return
        end = self.wire_end_at(pos)
        item = self.item_at(pos)
        if end is not None and isinstance(item, WireItem) and item.wire is end[0]:
            # agarrar el extremo suelto de un cable y moverlo
            w, idx = end
            if not (mods & (Qt.ControlModifier | Qt.ShiftModifier)):
                self.clearSelection()
            item.setSelected(True)
            orig = list(w.points)

            def restore(w=w, orig=orig):
                w.points = orig
                self.wire_items[w.id].sync()
            self._drag = {"kind": "wire_end", "wire": w, "end": idx, "orig": orig, "start": e.screenPos(),
                          "moved": False, "restore": restore}
            return
        if item is None:
            if not (mods & (Qt.ControlModifier | Qt.ShiftModifier)):
                self.clearSelection()
            e.ignore()           # permite a la vista dibujar un rectángulo de selección
            return
        if mods & Qt.ControlModifier:
            item.setSelected(not item.isSelected())
            return
        if not item.isSelected():
            if not (mods & Qt.ShiftModifier):
                self.clearSelection()
            item.setSelected(True)
        comps, wires = self.selected_ids()
        oc, ow = self._snapshot_geometry()
        if isinstance(item, WireItem) and not comps and len(wires) == 1:
            seg = item.segment_at(pos)
            orig = list(item.wire.points)

            def restore(w=item.wire, orig=orig):
                w.points = orig
                self.wire_items[w.id].sync()
            self._drag = {"kind": "segment", "wire": item.wire, "seg": seg, "orig": orig, "anchor": _pt(pos),
                          "start": e.screenPos(), "moved": False, "restore": restore}
            return

        def restore(oc=oc, ow=ow):
            for cid, (x, y, r, f) in oc.items():
                c = self.circuit.components.get(cid)
                if c:
                    c.x, c.y, c.rot, c.flip = x, y, r, f
                    self.sync_component(cid)
            for wid, pts in ow.items():
                if wid in self.circuit.wires:
                    self.circuit.wires[wid].points = pts
                    self.wire_items[wid].sync()
        self._drag = {"kind": "move", "comps": comps, "wires": set(wires), "oc": oc, "ow": ow,
                      "anchor": _pt(pos), "start": e.screenPos(), "moved": False, "restore": restore}

    def mouseMoveEvent(self, e):
        if self.sim_active():
            self._sim_move(e)
            return
        pos = e.scenePos()
        if self._ghost is not None:
            self._move_ghost(pos)
            return
        if self._wiring is not None:
            self._update_wire(pos)
            return
        d = self._drag
        if d is not None and e.buttons() & Qt.LeftButton:
            if not d["moved"]:
                if (e.screenPos() - d["start"]).manhattanLength() < DRAG_START:
                    return
                d["moved"] = True
            if d["kind"] == "move":
                ax, ay = d["anchor"]
                nx, ny = _pt(pos)
                dx, dy = nx - ax, ny - ay
                moves = {cid: (d["oc"][cid][0] + dx, d["oc"][cid][1] + dy, d["oc"][cid][2], d["oc"][cid][3])
                         for cid in d["comps"]}
                self._apply_moves(moves, d["oc"], d["ow"], d["wires"], (dx, dy))
            elif d["kind"] == "segment":
                ax, ay = d["anchor"]
                nx, ny = _pt(pos)
                d["wire"].points = move_segment(d["orig"], d["seg"], nx - ax, ny - ay)
                self.wire_items[d["wire"].id].sync()
            elif d["kind"] == "wire_end":
                pin = self.pin_at(pos)
                target = pin[2] if pin else _pt(pos)
                d["wire"].points = drag_end(d["orig"], d["end"], target)
                self.wire_items[d["wire"].id].sync()
            self.refresh_connections()
            return
        # solo pasando el mouse: mostrar desde qué pin empezaría un cable
        pin = self.pin_at(pos)
        hp = pin[2] if pin else None
        if hp != self._hover_pin:
            self._hover_pin = hp
            for v in self.views():
                v.viewport().setCursor(Qt.CrossCursor if (hp or self.mode == "wire") else Qt.ArrowCursor)
            if hp:
                self.status.emit("Arrastre desde este pin para dibujar un cable.")
            self.update()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.sim_active():
            self._sim_release(e)
            return
        if e.button() != Qt.LeftButton:
            super().mouseReleaseEvent(e)
            return
        if self._wiring is not None:
            w = self._wiring
            if not w["click"]:
                if w["dragged"]:
                    self._finish_wire(e.scenePos())
                else:
                    w["click"] = True       # fue un clic: seguir enrutando con clics
                    self.status.emit("Haga clic para agregar esquinas; haga clic en un pin o cable para terminar. "
                                     "Doble clic para parar aquí, Esc cancela, Retroceso deshace una esquina.")
            return
        d, self._drag = self._drag, None
        if d is None:
            super().mouseReleaseEvent(e)
            return
        if d["moved"]:
            if d["kind"] in ("segment", "wire_end"):
                w = d["wire"]
                w.points = tidy(w.points)
                if len(w.points) < 2:
                    self.removeItem(self.wire_items.pop(w.id))
                    self.circuit.remove(w.id)
                else:
                    self.wire_items[w.id].sync()
            self.refresh_connections()
            self.edited.emit({"move": "Mover", "segment": "Mover cable", "wire_end": "Mover extremo de cable"}[d["kind"]])

    def mouseDoubleClickEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if self._wiring is not None and not self.sim_active():
            self._finish_wire(e.scenePos(), here=True)
            return
        item = self.item_at(e.scenePos())
        if self.sim_active():
            from .simcontrol import INTERACTIVE
            if isinstance(item, ComponentItem) and item.comp.kind in INTERACTIVE:
                self._sim_press(e)       # un doble clic rápido en un interruptor lo conmuta dos veces: mantener el ritmo
                return
        if isinstance(item, ComponentItem):
            self.editRequested.emit(item.comp.id)
        e.accept()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            busy = self._wiring is not None or self._ghost is not None or self._drag is not None
            self.cancel()
            if not busy:
                self.clearSelection()
                if self.mode != "select":
                    self.set_mode("select")
            e.accept()
            return
        if e.key() == Qt.Key_Backspace and self._wiring is not None:
            self.undo_corner()
            e.accept()
            return
        super().keyPressEvent(e)

    # ================================================================== dibujar cables
    def undo_corner(self):
        """Retroceso mientras se dibuja un cable: quitar la última esquina (o parar si no hay)."""
        if self._wiring is None:
            return
        fixed = self._wiring["fixed"]
        if len(fixed) > 1:
            fixed.pop()
            self._update_wire(self._wiring["last_pos"])
        else:
            self.cancel()

    def _start_wire(self, start, from_pin):
        self.clearSelection()
        self._wiring = {"fixed": [tuple(start)], "click": False, "dragged": False, "from_pin": from_pin,
                        "last_pos": QPointF(*start), "path": [tuple(start)], "target": None}
        self.draft.set([start])
        self.draft.show()

    def _wire_target(self, pos: QPointF):
        """Dónde terminaría el cable: un pin, un extremo de cable, un punto en un cable, o simplemente el punto de la cuadrícula."""
        pin = self.pin_at(pos)
        if pin:
            return pin[2], True
        end = self.wire_end_at(pos)
        if end:
            return end[0].points[end[1]], True
        p = _pt(pos)
        item = self.item_at(pos)
        if isinstance(item, WireItem):
            from ..model.circuit import on_segment
            if any(on_segment(p, a, b) for a, b in item.wire.segments()):
                return p, True
        return p, False

    def _update_wire(self, pos: QPointF):
        w = self._wiring
        w["last_pos"] = pos
        start = w["fixed"][-1]
        target, snapped = self._wire_target(pos)
        if target != start:
            w["dragged"] = True
        dx, dy = target[0] - start[0], target[1] - start[1]
        prefer = abs(dx) >= abs(dy)
        a, b = route(start, target, prefer), route(start, target, not prefer)
        leg = b if self._crossings(a) > self._crossings(b) else a
        path = w["fixed"][:-1] + leg
        w["path"] = path
        w["target"] = target if snapped else None
        self.draft.set(path, w["target"])

    def _crossings(self, pts) -> int:
        """Cuántos cuerpos de componentes atravesaría un cable propuesto (para poder elegir la mejor esquina)."""
        n = 0
        bodies = []
        for it in self.comp_items.values():
            r = it._body.translated(it.pos())
            bodies.append(r.adjusted(2, 2, -2, -2))
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            seg = QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)).adjusted(-0.5, -0.5, 0.5, 0.5)
            n += sum(1 for r in bodies if r.intersects(seg))
        return n

    def _wiring_click(self, pos: QPointF):
        w = self._wiring
        self._update_wire(pos)
        target, snapped = self._wire_target(pos)
        if snapped and target != w["fixed"][0]:
            self._finish_wire(pos)
            return
        # agregar una esquina aquí
        w["fixed"] = tidy(w["path"]) if len(w["path"]) > 1 else w["fixed"]
        if w["fixed"][-1] != target:
            w["fixed"].append(target)

    def _finish_wire(self, pos: QPointF, here=False):
        w = self._wiring
        self._update_wire(pos)
        pts = tidy(w["path"])
        self._wiring = None
        self.draft.hide()
        if len(pts) < 2:
            return
        wire = self.circuit.add_wire(pts)
        if wire:
            self._add_wire_item(wire)
            self.refresh_connections()
            self.edited.emit("Agregar cable")
        if self.mode == "wire":
            self.status.emit("Cable agregado. Dibuje otro, o presione Esc.")

    # ================================================================== arrastrar y soltar desde la galería
    def dragEnterEvent(self, e):
        if self.sim_active():
            e.ignore()
            return
        if e.mimeData().hasFormat(MIME_PART):
            kind = bytes(e.mimeData().data(MIME_PART)).decode()
            self.start_placing(kind)
            self._move_ghost(e.scenePos())
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if self._ghost is not None:
            self._move_ghost(e.scenePos())
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        if self._ghost is not None:
            self._ghost.hide()

    def dropEvent(self, e):
        if self._ghost is not None:
            self._drop_ghost(e.scenePos())
            e.acceptProposedAction()

    # ================================================================== pintar la hoja
    def drawBackground(self, p, rect: QRectF):
        p.fillRect(rect, QColor(theme.CANVAS))
        if self.exporting or not self.show_grid:
            return
        s = self.views()[0].transform().m11() if self.views() else 1.0
        step = P.GRID if s >= 0.9 else P.GRID * 2 if s >= 0.45 else P.GRID * 5
        x0 = int(rect.left() // step) * step
        y0 = int(rect.top() // step) * step
        minor, major = [], []
        y = y0
        while y <= rect.bottom():
            x = x0
            while x <= rect.right():
                (major if (x % 100 == 0 and y % 100 == 0) else minor).append(QPointF(x, y))
                x += step
            y += step
        pen = QPen(QColor(theme.GRID_DOT), max(1.2 / s, 1.0) * 1.0)
        pen.setCapStyle(Qt.RoundCap)
        pen.setCosmetic(True)
        pen.setWidthF(1.6 if s >= 0.9 else 1.3)
        p.setPen(pen)
        p.drawPoints(minor)
        pen.setColor(QColor(theme.GRID_DOT_MAJOR))
        pen.setWidthF(2.4)
        p.setPen(pen)
        p.drawPoints(major)

    def _draw_flow(self, p, live, rect):
        """Puntos en movimiento a lo largo de los cables: corriente convencional, más rápida para corrientes mayores."""
        spacing = 16.0
        p.setPen(QPen(QColor(theme.FLOW_EDGE), 0.8))
        p.setBrush(QColor(theme.FLOW_DOT))
        vis = rect.adjusted(-20, -20, 20, 20)
        for (x1, y1), (x2, y2), phase, amps in live.flows:
            if abs(amps) < 1e-6:
                continue
            L = abs(x2 - x1) + abs(y2 - y1)
            if L < 1 or not vis.intersects(QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1) + 1, abs(y2 - y1) + 1)):
                continue
            ux, uy = (x2 - x1) / L, (y2 - y1) / L
            off = phase % spacing
            r = 2.1 + 0.5 * min(1.0, abs(amps) / 0.05)
            d = off
            while d < L:
                p.drawEllipse(QPointF(x1 + ux * d, y1 + uy * d), r, r)
                d += spacing

    # lecturas: lo que mostraría un multímetro, escrito en la hoja
    NO_READING = {"ground", "note", "scope_probe", "logic_probe", "voltmeter", "ammeter"}
    SOURCES = {"cell", "battery", "dc_supply", "ac_supply", "rail_pos", "signal_gen"}

    def _tag(self, p, x, y, text, pinned, anchor, key=None):
        """Una pequeña etiqueta de lectura en (x, y): el ancla "above" la sitúa encima del punto, "right" al lado. Si se
        ha arrastrado a otro sitio, se dibuja allí con una línea discontinua de vuelta a (x, y)."""
        from PySide6.QtGui import QFont, QFontMetricsF
        f = QFont()
        f.setPixelSize(8)
        p.setFont(f)
        w = QFontMetricsF(f).horizontalAdvance(text) + 8
        h = 12
        if anchor == "above":
            r = QRectF(x - w / 2, y - h - 4, w, h)
        elif anchor == "below":
            r = QRectF(x - w / 2, y + 3, w, h)
        elif anchor == "under":                  # alineado a la izquierda, justo debajo de (x, y)
            r = QRectF(x, y + 1, w, h)
        else:
            r = QRectF(x + 5, y - h / 2, w, h)
        dx, dy = self.tag_offsets.get(key, (0.0, 0.0))
        if dx or dy:
            r = r.translated(dx, dy)
            # una línea discontinua desde lo que pertenece, al punto más cercano de la etiqueta
            px = min(max(x, r.left()), r.right())
            py = min(max(y, r.top()), r.bottom())
            if abs(px - x) + abs(py - y) > 4:
                pen = QPen(QColor(theme.ACCENT if pinned else theme.BORDER), 0.9, Qt.DashLine)
                p.setPen(pen)
                p.drawLine(QPointF(x, y), QPointF(px, py))
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(theme.ACCENT if pinned else theme.BORDER))
                p.drawEllipse(QPointF(x, y), 1.8, 1.8)
        if key is not None:
            self._tag_hits.append((QRectF(r), key))
        bg = QColor(theme.PANEL)
        bg.setAlpha(232)
        p.setPen(QPen(QColor(theme.ACCENT if pinned else theme.BORDER), 1.0 if pinned else 0.8))
        p.setBrush(bg)
        p.drawRoundedRect(r, 3, 3)
        p.setPen(QColor(theme.TEXT))
        p.drawText(r, Qt.AlignCenter, text)

    @staticmethod
    def power_only(comp) -> bool:
        """Chips (y componentes con varias patas separadas): un voltaje y corriente entre sus dos primeros pines
        no significaría nada, así que solo se muestra su potencia."""
        return comp.part.category == "Circuitos integrados" or comp.kind in ("led_rgb", "led_bi3", "dpdt")

    def readings_text(self) -> str:
        """El voltaje, la corriente y la potencia de cada componente como tabla (separado por tabulaciones, para que se pegue en una hoja de cálculo como
        columnas). Vacío cuando no se está ejecutando nada."""
        if not self.sim_active():
            return ""
        live = self.sim.live
        if live is None:
            return ""

        def num(x, floor):
            x = abs(x)
            return f"{x:.4g}" if x >= floor else "0"

        def ref_key(c):
            m = re.match(r"([A-Za-z]*)(\d*)", c.ref or "")
            return (m.group(1), int(m.group(2) or 0), c.ref)

        rows = []
        for comp in sorted((it.comp for it in self.comp_items.values()), key=ref_key):
            if comp.kind in self.NO_READING:
                continue
            info = live.parts.get(comp.id)
            if not info or "v" not in info:
                continue
            power = num(info.get("p", 0.0), 1e-6) if comp.kind not in self.SOURCES else ""
            name = comp.part.short or comp.part.name
            if self.power_only(comp):
                rows.append("\t".join((comp.ref, name, "", "", power)))
            else:
                rows.append("\t".join((comp.ref, name, num(info["v"], 1e-3), num(info["i"], 1e-6), power)))
        t = getattr(self.sim, "sim", None)
        when = f"Lecturas en {t.t:.3g} s" if t is not None else "Lecturas"
        return "\n".join([when, "Componente\tQué\tVoltaje (V)\tCorriente (A)\tPotencia (W)"] + rows) + "\n"

    def _draw_readings(self, p, live):
        from ..model.units import fmt
        show_all = self.show_readings
        net_of = {wid: net.name for net in self.sim.sim.nets for wid in net.wires} if self.sim else {}
        labelled = set()
        # primero los cables que llevan corriente (siempre reciben una etiqueta), luego una etiqueta de voltaje por cada red restante
        order = []
        for wid, it in self.wire_items.items():
            pinned = wid in self.pinned
            if not (show_all or pinned) or wid not in live.wire_v:
                continue
            w = it.wire
            a, b = max(w.segments(), key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            amps, arrow = self._wire_current(w, QPointF(mx, my))
            length = abs(b[0] - a[0]) + abs(b[1] - a[1])
            order.append((amps < 1e-6, -length, wid, pinned, a, b, mx, my, amps, arrow))
        order.sort(key=lambda t: (t[0], t[1]))
        for idle, _l, wid, pinned, a, b, mx, my, amps, arrow in order:
            net = net_of.get(wid)
            if idle and not pinned and net in labelled:
                continue                         # el mismo voltaje ya se muestra en esta red
            labelled.add(net)
            vv = live.wire_v[wid]
            text = fmt(vv if abs(vv) >= 1e-3 else 0.0, "V")
            if amps >= 1e-6:
                text += f"   {fmt(amps, 'A')} {arrow}"
            self._tag(p, mx, my, text, pinned, "above" if a[1] == b[1] else "right", key=wid)
        for cid, it in self.comp_items.items():
            pinned = cid in self.pinned
            kind = it.comp.kind
            if not (pinned or (show_all and kind not in self.NO_READING)):
                continue
            info = live.parts.get(cid)
            if not info or "v" not in info:
                continue
            def tidy(x, floor):          # la fuga (pA, nV) se lee como 0, como un medidor real
                x = abs(x)
                return x if x >= floor else 0.0
            if self.power_only(it.comp):
                bits = [fmt(tidy(info.get("p", 0.0), 1e-6), "W")]
            else:
                bits = [fmt(tidy(info["v"], 1e-3), "V"), fmt(tidy(info["i"], 1e-6), "A")]
                if abs(info.get("p", 0)) > 1e-6 and kind not in self.SOURCES:
                    bits.append(fmt(tidy(info["p"], 1e-6), "W"))
            # junto a la etiqueta propia del componente (su nombre y valor), para que quede claro a qué componente pertenece
            lab, lines, align = it._label
            if lines:
                r = lab.translated(it.pos())
                if align == Qt.AlignLeft:            # etiqueta al lado de un componente de pie: lectura debajo
                    self._tag(p, r.left(), r.bottom(), "  ".join(bits), pinned, "under", key=cid)
                else:                                # etiqueta encima de un componente acostado: lectura debajo
                    sym = it._sym.translated(it.pos())
                    self._tag(p, sym.center().x(), sym.bottom() + (22 if "reading" in info else 0),
                              "  ".join(bits), pinned, "below", key=cid)
            else:
                sym = it._sym.translated(it.pos())
                y = sym.bottom() + (22 if "reading" in info else 0)
                self._tag(p, sym.center().x(), y, "  ".join(bits), pinned, "below", key=cid)

    def drawForeground(self, p, rect: QRectF):
        from PySide6.QtGui import QPainter
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        live = self.sim.live if (self.sim_active() and not self.exporting) else None
        for x, y in self._junctions:
            col = QColor(theme.WIRE)
            if live is not None and self.show_volts and (x, y) in self._junction_net:
                col = theme.volt_colour(live.net_v.get(self._junction_net[(x, y)], 0.0), live.vmax)
            p.setBrush(col)
            p.drawEllipse(QPointF(x, y), 3.8 if live else 3.6, 3.8 if live else 3.6)
        if self.exporting:
            return
        if live is not None and self.show_flow:
            self._draw_flow(p, live, rect)
        self._tag_hits = []
        if live is not None and (self.show_readings or self.pinned):
            self._draw_readings(p, live)
        if self.sim_active():
            return
        # pines sin nada conectado: pequeños círculos abiertos para que pueda ver dónde conectar
        p.setBrush(QColor(theme.CANVAS))
        p.setPen(QPen(QColor(theme.PIN_OPEN), 1.3))
        for x, y in self._open_pins:
            p.drawEllipse(QPointF(x, y), 2.6, 2.6)
        if self._hover_pin and self._wiring is None and self._drag is None:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(theme.PIN_TARGET), 2))
            p.drawEllipse(QPointF(*self._hover_pin), 6, 6)