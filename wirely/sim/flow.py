"""Works out how much current flows along each piece of wire, for the animated current-flow dots (no Qt).

The solver only knows the current at each pin. Inside one net the wires form a little network; we split
the wires at every junction, give each piece the same tiny resistance and solve for how the pin currents
share out. For ordinary (tree-shaped) wiring this is exact; for loops of wire it splits current evenly.

0 V (ground) symbols are the exception: they don't report a current, because theirs goes back to the supply
(a +V rail, or a battery wired to another 0 V symbol) without a wire. So whatever current the pins of a net
don't account for is taken to flow into its 0 V symbols.
"""
from __future__ import annotations

import numpy as np

from ..model.circuit import Circuit, on_segment


class FlowNetwork:
    def __init__(self, circuit: Circuit, nets=None):
        self.circuit = circuit
        nets = nets if nets is not None else circuit.nets()
        pins = {}
        for c in circuit.components.values():
            for name, pos in c.pin_positions().items():
                pins[(c.id, name)] = pos
        specials = set(pins.values())
        for w in circuit.wires.values():
            specials.update(w.points)
        self.groups = []     # per net: (points list, edges [(i, j, wire_id)], pins [(cid, pin, i)])
        for net in nets:
            pts, index, edges = [], {}, []

            def idx(p):
                if p not in index:
                    index[p] = len(pts)
                    pts.append(p)
                return index[p]
            for wid in net.wires:
                w = circuit.wires[wid]
                for a, b in w.segments():
                    inner = [s for s in specials if s != a and s != b and on_segment(s, a, b)]
                    inner.sort(key=lambda s: abs(s[0] - a[0]) + abs(s[1] - a[1]))
                    chain = [a] + inner + [b]
                    for p, q in zip(chain, chain[1:]):
                        edges.append((idx(p), idx(q), wid))
            pin_nodes = [(cid, pin, idx(pins[(cid, pin)])) for cid, pin in net.pins]
            grounds = [i for cid, _pin, i in pin_nodes if circuit.components[cid].kind == "ground"]
            if edges:
                self.groups.append((pts, edges, pin_nodes, grounds))

    def solve(self, pin_current):
        """pin_current(cid, pin) = current INTO the part at that pin. Returns [((x1,y1),(x2,y2), amps)],
        amps > 0 meaning conventional current flows from the first point to the second."""
        out = []
        memo = self.__dict__.setdefault("_memo", {})
        for g, (pts, edges, pin_nodes, grounds) in enumerate(self.groups):
            n = len(pts)
            inj = np.zeros(n)
            for cid, pin, i in pin_nodes:
                inj[i] -= pin_current(cid, pin)      # current into a part leaves the wire network there
            if grounds:                              # the rest goes into (or comes out of) the 0 V symbols
                rest = -float(inj.sum()) / len(grounds)
                for i in grounds:
                    inj[i] += rest
            if not np.any(np.abs(inj) > 1e-12):
                out.extend((pts[a], pts[b], 0.0) for a, b, _w in edges)
                continue
            # same currents in as last frame (a circuit that has settled): same answer, no need to work it out again
            now = [float(v) for v in inj]
            last = memo.get(g)
            tol = 1e-12 + 1e-6 * max(abs(v) for v in now)
            if last is not None and len(last[0]) == n and all(abs(a - b) <= tol for a, b in zip(now, last[0])):
                out.extend(last[1])
                continue
            L = np.zeros((n, n))
            for a, b, _w in edges:
                L[a, a] += 1
                L[b, b] += 1
                L[a, b] -= 1
                L[b, a] -= 1
            # potentials: L·φ = −injection (pin currents flowing in raise the potential), fix one node per piece
            phi = np.linalg.lstsq(L + 1e-9 * np.eye(n), inj, rcond=None)[0]
            res = [(pts[a], pts[b], float(phi[a] - phi[b])) for a, b, _w in edges]
            memo[g] = (now, res)
            out.extend(res)
        return out
