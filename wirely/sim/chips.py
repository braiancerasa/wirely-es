"""Models for MOSFETs, op-amps, the 555 timer, logic gates and logic chips, and the probes (no Qt).

Things that switch (comparators inside the 555, logic inputs, square waves) tell the engine *when* they are
about to switch via `crossing()`, so the engine can shorten the step and land exactly on the switching
moment. That keeps timing accurate (a 555's frequency matches the textbook formula) instead of being off by
up to a whole time step.

Logic chips and op-amps with unconnected supply pins are powered automatically from the highest supply
voltage in the circuit (`self.vlogic`, set by the engine).
"""
from __future__ import annotations

import math

from .devices import (BJT, GMIN, LED_N, LED_RS, R_OFF, R_ON, VT, Device, Source, led_is, pnjlim, sexp,
                      spike_message, v)

G_GATE = 1e-9            # MOSFET gate leakage to its source (1 GΩ)
ROUT_LOGIC = 300.0       # 4000-series CMOS output resistance at ~9 V
R_PULLDOWN = 10e6        # unconnected logic inputs read as low


def softplus(z, s):
    if z / s > 40:
        return z
    return s * math.log1p(math.exp(z / s))


def frac_cross(v0, v1, th, rising):
    """Fraction of the step at which v goes past th (or None)."""
    if rising and v0 < th <= v1:
        return (th - v0) / (v1 - v0)
    if not rising and v0 > th >= v1:
        return (v0 - th) / (v0 - v1)
    return None


def numeric_stamp(S, nodes, V0, f, ctx=None):
    """Stamp a device whose terminal currents are I = f(V) (into the device), using a numerical Jacobian."""
    I0 = f(V0)
    n = len(nodes)
    J = [[0.0] * n for _ in range(n)]
    for j in range(n):
        if nodes[j] < 0:
            continue
        d = 1e-6 * max(1.0, abs(V0[j]))
        Vp, Vm = list(V0), list(V0)
        Vp[j] += d
        Vm[j] -= d
        Ip, Im = f(Vp), f(Vm)
        for k in range(n):
            J[k][j] = (Ip[k] - Im[k]) / (2 * d)
    S.nonlinear(nodes, I0, J, V0)
    return I0


# ============================================================================================== MOSFET
MOSFETS = {  # polarity, |Vth|, KP (A/V²), lambda, max Id, max power
    "2N7000": (1, 2.1, 0.1, 0.01, 0.2, 0.4),
    "IRF540": (1, 3.0, 2.5, 0.005, 28.0, 2.0),
    "BS250": (-1, 2.5, 0.01, 0.01, 0.18, 0.83),
    "IRF9540": (-1, 3.0, 0.7, 0.005, 19.0, 2.0),
    "BS170": (1, 2.1, 0.12, 0.01, 0.5, 0.83),
    "IRLZ44N": (1, 1.5, 15.0, 0.005, 47.0, 3.0),        # logic level: fully on from about 4 V
    "IRF530": (1, 3.0, 1.5, 0.005, 14.0, 2.0),
    "IRF3205": (1, 3.0, 30.0, 0.003, 110.0, 3.0),
    "AO3400": (1, 1.05, 5.0, 0.01, 5.7, 1.4),
    "IRF9530": (-1, 3.0, 0.5, 0.005, 12.0, 2.0),
    "FQP27P06": (-1, 3.0, 3.0, 0.005, 27.0, 2.0),
    "IRLML6402": (-1, 0.8, 3.0, 0.01, 3.7, 1.3),
}
VDS_MAX = {"2N7000": 60, "BS170": 60, "IRLZ44N": 55, "IRF530": 100, "IRF540": 100, "IRF3205": 55, "AO3400": 30,
           "BS250": 45, "IRF9530": 100, "IRF9540": 100, "FQP27P06": 60, "IRLML6402": 20}


class MOSFET(Device):
    """Square-law (SPICE level 1) MOSFET with a smoothed threshold. Pins G, D, S."""
    nonlinear = True

    def update_params(self):
        default = "2N7000" if self.comp.kind == "nmos" else "BS250"
        pol, vt, kp, lam, idmax, pmax = MOSFETS.get(self.prop("model"), MOSFETS[default])
        self.pol = -1 if self.comp.kind == "pmos" else 1
        self.vt, self.kp, self.lam, self.idmax, self.pmax = vt, kp, lam, idmax, pmax
        self.vgs_acc = self.vds_acc = 0.0
        self.id = 0.0

    def begin_iter(self):
        self.vgs_last, self.vds_last = self.vgs_acc, self.vds_acc

    def ids(self, vgs, vds):
        """Drain current for an N-channel device (vgs, vds may be anything)."""
        if vds < 0:                       # source and drain swap roles
            return -self.ids(vgs - vds, -vds)
        vov = softplus(vgs - self.vt, 0.02)
        if vds < vov:
            i = self.kp * (vov * vds - 0.5 * vds * vds)
        else:
            i = 0.5 * self.kp * vov * vov
        return i * (1 + self.lam * vds)

    def _currents(self, V):
        vg, vd, vs = V
        p = self.pol
        i = p * self.ids(p * (vg - vs), p * (vd - vs))
        # a 1 GΩ gate-to-source leak: a gate left unconnected settles at the source voltage (off)
        return [G_GATE * (vg - vs), i, -i - G_GATE * (vg - vs)]

    def stamp(self, S, x, ctx):
        g, d, s = self.nodes
        if self.blown:
            S.g(d, s, 1 / R_OFF)
            S.g(g, s, 1 / R_OFF)
            return
        p = self.pol
        vg, vd, vs = v(x, g), v(x, d), v(x, s)
        vgs, vds = p * (vg - vs), p * (vd - vs)
        # limit how far one Newton step may move the gate and drain voltages
        lv = [vgs, vds]
        for i, (now, last, lim) in enumerate(((vgs, self.vgs_last, 1.0), (vds, self.vds_last, 4.0))):
            if abs(now - last) > lim:
                lv[i] = last + math.copysign(lim, now - last)
                ctx.limited = True
        self.vgs_last, self.vds_last = lv
        V0 = [vs + p * lv[0], vs + p * lv[1], vs]
        numeric_stamp(S, [g, d, s], V0, self._currents)

    def accept(self, x, ctx):
        g, d, s = self.nodes
        p = self.pol
        vg, vd, vs = v(x, g), v(x, d), v(x, s)
        if self.blown:
            self.id = 0.0
        else:
            self.vgs_acc, self.vds_acc = p * (vg - vs), p * (vd - vs)
            self.id = p * self.ids(self.vgs_acc, self.vds_acc)
        self.i_pins = [0.0, self.id, -self.id]
        self.power = self.id * (vd - vs)
        if self.blown:
            return
        vmax = VDS_MAX.get(self.prop("model"), 60)
        if abs(vd - vs) > 1.5 * vmax:
            self.blown = True
            self.event = spike_message(self.comp.ref, abs(vd - vs), vmax)
            return
        bad = abs(self.id) > 1.5 * self.idmax or self.power > 1.5 * self.pmax
        self.warn = "over" if (abs(self.id) > self.idmax or self.power > self.pmax) else None
        if self._overload(bad, ctx.h, 0.2):
            self.blown = True
            self.event = (f"{self.comp.ref} burnt out — {self.power:.1f} W is too much for a "
                          f"{self.prop('model')} without a heatsink.")


# ============================================================================================== op-amp
OPAMPS = {  # headroom below V+, headroom above V−, gain-bandwidth (Hz), slew rate (V/s), output current limit (A)
    "741": (1.5, 1.5, 1e6, 0.5e6, 0.025),
    "LM358": (1.5, 0.02, 1e6, 0.3e6, 0.03),
    "Rail-to-rail": (0.02, 0.02, 10e6, 10e6, 0.05),
    "TL071": (1.5, 1.5, 3e6, 13e6, 0.03),
}


class OpAmp(Device):
    """Macro-model: a transconductance stage with one dominant pole (gain 100 000, gain-bandwidth and slew
    rate as the real chip), then an output stage that can't go past its supply rails and limits its current.
    Pins: −, +, out, V+, V−."""
    n_internal = 1
    nonlinear = True
    A0, GM = 1e5, 1e-3

    def update_params(self):
        self.hd_hi, self.hd_lo, gbw, sr, self.ilim = OPAMPS.get(self.prop("model"), OPAMPS["741"])
        self.C1 = self.GM / (2 * math.pi * gbw)
        self.Imax = sr * self.C1
        self.G1 = self.GM / self.A0
        self.rout = 75.0
        self.vm_prev = 0.0
        self.auto_pos = self.auto_neg = False       # set by the engine when V+ / V− are left unconnected
        self.vlogic = 9.0

    def rails(self, x):
        vp = self.vlogic if self.auto_pos else v(x, self.nodes[3])
        vn = 0.0 if self.auto_neg else v(x, self.nodes[4])
        return vp, vn

    def _f(self, V):
        """Currents into the device at [−, +, out, V+, V−, m]."""
        vneg, vpos, vout, vp, vn, vm = V
        if self.auto_pos:
            vp = self.vlogic
        if self.auto_neg:
            vn = 0.0
        i1 = self.Imax * math.tanh(self.GM * (vpos - vneg) / self.Imax)
        lim = (vp - vn) / 2 + 1.0
        iclamp = 1e-3 * (softplus(vm - lim, 0.05) - softplus(-lim - vm, 0.05))
        u = (vp + vn) / 2 + vm
        lo, hi = vn + self.hd_lo, vp - self.hd_hi
        if hi < lo:
            hi = lo = (vp + vn) / 2
        vt = lo + softplus(u - lo, 0.05) - softplus(u - hi, 0.05)
        iout = self.ilim * math.tanh((vt - vout) / self.rout / self.ilim)
        return [GMIN * vneg, GMIN * vpos, -iout, 0.0, 0.0, self.G1 * vm + iclamp - i1]

    def stamp(self, S, x, ctx):
        neg, pos, out, vpn, vnn = self.nodes
        m = self.internal[0]
        if not ctx.dc:      # the dominant-pole capacitor (always backward Euler: no ringing)
            G = self.C1 / ctx.h
            S.g(m, -1, G)
            S.i(-1, m, G * self.vm_prev)
        # supply current (about 1.7 mA) when the supply pins are wired
        if not (self.auto_pos or self.auto_neg):
            S.g(vpn, vnn, 1 / 5000.0)
        nodes = [neg, pos, out, -1 if self.auto_pos else vpn, -1 if self.auto_neg else vnn, m]
        V0 = [v(x, n) for n in nodes]
        # keep this iteration's guess for the output and the internal node near the supply range
        vp_, vn_ = self.rails(x)
        span = abs(vp_ - vn_) / 2 + 2.0
        for i, (lo, hi) in ((2, (min(vp_, vn_) - 1.0, max(vp_, vn_) + 1.0)), (5, (-span, span))):
            if V0[i] < lo or V0[i] > hi:
                V0[i] = min(hi, max(lo, V0[i]))
                ctx.limited = True
        numeric_stamp(S, nodes, V0, self._f)

    def accept(self, x, ctx):
        neg, pos, out, vpn, vnn = self.nodes
        m = self.internal[0]
        V = [v(x, n) for n in (neg, pos, out, vpn, vnn, m)]
        I = self._f(V)
        self.vm_prev = V[5]
        self.i_pins = [I[0], I[1], I[2], 0.0, 0.0]
        self.vout = V[2]


# ============================================================================================== 555 timer
class Timer555(Device):
    """NE555: 3 × 5 kΩ divider (CTRL is the 2/3 point), two comparators, a flip-flop, output and discharge.
    Pin order: GND, TRIG, OUT, RESET, CTRL, THR, DIS, VCC."""
    n_internal = 1
    ROUT = 10.0

    def update_params(self):
        self.q = False
        self.changed = False

    def _levels(self, x):
        gnd, trig, out, reset, ctrl, thr, dis, vcc = self.nodes
        return (v(x, thr), v(x, ctrl), v(x, trig), v(x, self.internal[0]), v(x, reset) - v(x, gnd))

    def stamp(self, S, x, ctx):
        gnd, trig, out, reset, ctrl, thr, dis, vcc = self.nodes
        n13 = self.internal[0]
        G5 = 1 / 5000.0
        S.g(vcc, ctrl, G5)
        S.g(ctrl, n13, G5)
        S.g(n13, gnd, G5)
        S.g(vcc, gnd, 1 / 3000.0)                     # supply current
        G = 1 / self.ROUT
        if self.q:      # output high: about 1.7 V below VCC
            S.g(vcc, out, G)
            S.i(out, vcc, G * 1.7)
            S.g(dis, gnd, 1 / R_OFF)
        else:           # output low; discharge transistor on
            S.g(out, gnd, G)
            S.i(gnd, out, G * 0.1)
            S.g(dis, gnd, 1 / 10.0)
        for n in (trig, thr, reset):
            S.g(n, gnd, GMIN)

    def next_q(self, x):
        vthr, vctrl, vtrig, v13, vres = self._levels(x)
        if vres < 0.7:
            return False
        if vtrig < v13:
            return True
        if vthr > vctrl:
            return False
        return self.q

    def crossing(self, xo, xn, t0, t1):
        a = self._levels(xo)
        b = self._levels(xn)
        fr = []
        # threshold rising past 2/3 VCC while high; trigger falling below 1/3 VCC while low; reset falling
        if self.q:
            f = frac_cross(a[0] - a[1], b[0] - b[1], 0.0, True)
            if f is not None:
                fr.append(f)
        else:
            f = frac_cross(a[2] - a[3], b[2] - b[3], 0.0, False)
            if f is not None:
                fr.append(f)
        f = frac_cross(a[4], b[4], 0.7, False)
        if f is not None:
            fr.append(f)
        return min(fr) if fr else None

    def accept(self, x, ctx):
        q = self.next_q(x)
        if q != self.q:
            self.q = q
            self.changed = True
        gnd, trig, out, reset, ctrl, thr, dis, vcc = self.nodes
        G = 1 / self.ROUT
        if self.q:
            iout = G * (v(x, vcc) - v(x, out) - 1.7)
            idis = 0.0
        else:
            iout = -G * (v(x, out) - v(x, gnd) - 0.1)
            idis = (v(x, dis) - v(x, gnd)) / 10.0
        icc = (v(x, vcc) - v(x, ctrl)) / 5000.0 + (v(x, vcc) - v(x, gnd)) / 3000.0 + (iout if self.q else 0.0)
        self.i_pins = [0.0, 0.0, -iout, 0.0, 0.0, 0.0, idis, icc]
        self.i_pins[0] = -sum(self.i_pins[1:])
        self.out_high = self.q


# ============================================================================================== logic
class Digital(Device):
    """Base for logic: inputs read as high above 55 % of the logic supply and low below 45 % (a little
    hysteresis), outputs drive 0 V or the logic supply through ROUT_LOGIC."""
    inputs: tuple = ()
    outputs: tuple = ()
    schmitt = False

    def update_params(self):
        names = [n for n, _x, _y in self.comp.part.pins]
        self.in_idx = [names.index(n) for n in self.inputs]
        self.out_idx = [names.index(n) for n in self.outputs]
        self.level = {n: False for n in self.inputs}
        self.out = {n: False for n in self.outputs}
        self.vlogic = 9.0
        self.changed = False
        self.reset_state()
        self.out = self.compute()

    def reset_state(self):
        pass

    def thresholds(self):
        if self.schmitt:
            return 2 / 3 * self.vlogic, 1 / 3 * self.vlogic
        return 0.55 * self.vlogic, 0.45 * self.vlogic

    def compute(self) -> dict:
        return {}

    def clock(self, rising: dict):
        """Called with the inputs that just went high (edge-triggered chips)."""

    def stamp(self, S, x, ctx):
        for i in self.in_idx:
            S.g(self.nodes[i], -1, 1 / R_PULLDOWN)
        G = 1 / ROUT_LOGIC
        for name, i in zip(self.outputs, self.out_idx):
            n = self.nodes[i]
            S.g(n, -1, G)
            if self.out[name]:
                S.i(-1, n, self.vlogic * G)

    def crossing(self, xo, xn, t0, t1):
        hi, lo = self.thresholds()
        best = None
        for name, i in zip(self.inputs, self.in_idx):
            n = self.nodes[i]
            f = frac_cross(v(xo, n), v(xn, n), lo if self.level[name] else hi, not self.level[name])
            if f is not None and (best is None or f < best):
                best = f
        return best

    def accept(self, x, ctx):
        hi, lo = self.thresholds()
        rising = {}
        for name, i in zip(self.inputs, self.in_idx):
            vv = v(x, self.nodes[i])
            old = self.level[name]
            new = vv >= hi if not old else vv > lo
            if new and not old:
                rising[name] = True
            self.level[name] = new
        self.clock(rising)
        out = self.compute()
        if out != self.out:
            self.out = out
            self.changed = True
        G = 1 / ROUT_LOGIC
        pins = [0.0] * len(self.nodes)
        for i in self.in_idx:
            pins[i] = v(x, self.nodes[i]) / R_PULLDOWN
        for name, i in zip(self.outputs, self.out_idx):
            pins[i] = (v(x, self.nodes[i]) - (self.vlogic if self.out[name] else 0.0)) * G
        self.i_pins = pins


class Gate(Digital):
    def update_params(self):
        k = self.comp.kind
        self.inputs = ("A",) if k in ("not", "schmitt_not") else ("A", "B")
        self.outputs = ("Y",)
        self.schmitt = k == "schmitt_not"
        super().update_params()

    def compute(self):
        k = self.comp.kind
        a = self.level["A"]
        b = self.level.get("B", False)
        y = {"not": not a, "schmitt_not": not a, "and": a and b, "or": a or b, "nand": not (a and b),
             "nor": not (a or b), "xor": a != b}[k]
        return {"Y": y}


class DFF(Digital):
    inputs = ("D", "CLK", "R")
    outputs = ("Q", "Qn")

    def reset_state(self):
        self.q = False

    def clock(self, rising):
        if self.level["R"]:
            self.q = False
        elif rising.get("CLK"):
            self.q = self.level["D"]

    def compute(self):
        return {"Q": self.q, "Qn": not self.q}


class Counter4017(Digital):
    inputs = ("CLK", "RST")
    outputs = tuple(f"Q{i}" for i in range(10)) + ("CO",)

    def reset_state(self):
        self.count = 0

    def clock(self, rising):
        if self.level["RST"]:
            self.count = 0
        elif rising.get("CLK"):
            self.count = (self.count + 1) % 10

    def compute(self):
        out = {f"Q{i}": i == self.count for i in range(10)}
        out["CO"] = self.count < 5
        return out


SEGMENTS = {0: "abcdef", 1: "bc", 2: "abdeg", 3: "abcdg", 4: "bcfg", 5: "acdfg", 6: "acdefg", 7: "abc",
            8: "abcdefg", 9: "abcdfg"}


class Decoder4511(Digital):
    inputs = ("A", "B", "C", "D")
    outputs = tuple("abcdefg")

    def compute(self):
        n = sum(1 << i for i, k in enumerate("ABCD") if self.level[k])
        lit = SEGMENTS.get(n, "")
        return {s: s in lit for s in "abcdefg"}

    def value(self):
        return sum(1 << i for i, k in enumerate("ABCD") if self.level[k])


# ============================================================================================== displays & probes
class SevenSeg(Device):
    """Seven LEDs (with built-in 330 Ω resistors) from the segment pins to the common cathode."""
    n_internal = 7
    nonlinear = True
    R = 330.0

    def update_params(self):
        self.Is = led_is(self.prop("colour"))
        self.nvt = LED_N * VT
        self.vcrit = self.nvt * math.log(self.nvt / (math.sqrt(2) * self.Is))
        self.vd_last = [0.0] * 7
        self.vd_acc = [0.0] * 7
        self.seg_i = [0.0] * 7

    def begin_iter(self):
        self.vd_last = list(self.vd_acc)

    def stamp(self, S, x, ctx):
        com = self.nodes[7]
        for k in range(7):
            pin, mid = self.nodes[k], self.internal[k]
            S.g(pin, mid, 1 / (self.R + LED_RS))
            vd = v(x, mid) - v(x, com)
            vl = pnjlim(vd, self.vd_last[k], self.nvt, self.vcrit)
            if abs(vl - vd) > 1e-9:
                ctx.limited = True
            self.vd_last[k] = vl
            e = sexp(vl / self.nvt)
            i, g = self.Is * (e - 1) + GMIN * vl, self.Is * e / self.nvt + GMIN
            S.g(mid, com, g)
            S.i(mid, com, i - g * vl)

    def accept(self, x, ctx):
        com = self.nodes[7]
        pins = [0.0] * 8
        for k in range(7):
            mid = self.internal[k]
            vd = v(x, mid) - v(x, com)
            self.vd_acc[k] = vd
            i = self.Is * (sexp(vd / self.nvt) - 1)
            self.seg_i[k] = i
            pins[k] = i
        pins[7] = -sum(pins[:7])
        self.i_pins = pins

    def lit(self):
        return [max(0.0, min(1.0, (i - 1e-4) / 0.01)) ** 0.6 for i in self.seg_i]


class SignalGen(Source):
    """Signal generator: square, sine or triangle around an offset."""

    def update_params(self):
        self.wave = self.prop("waveform")
        self.freq = float(self.prop("frequency"))
        self.amp = float(self.prop("amplitude"))
        self.off = float(self.prop("offset"))
        self.duty = min(0.99, max(0.01, float(self.prop("duty") if self.comp.value("duty") is not None
                                              else 50.0) / 100.0))
        self.Rint = 0.05
        self.V = abs(self.off) + self.amp
        self._high = None
        self.changed = False

    def emf(self, t):
        ph = (t * self.freq) % 1.0
        if self.wave == "Sine":
            return self.off + self.amp * math.sin(2 * math.pi * ph)
        if self.wave == "Triangle":
            tri = 4 * ph - 1 if ph < 0.5 else 3 - 4 * ph
            return self.off + self.amp * tri
        return self.off + (self.amp if ph < self.duty else -self.amp)

    def crossing(self, xo, xn, t0, t1):
        """Land exactly on the edges of a square wave (rising at the start of each cycle, falling after
        `duty` of it)."""
        if self.wave != "Square" or self.freq <= 0:
            return None
        T = 1.0 / self.freq
        n = math.floor(t0 / T)
        eps = 1e-9 * T
        for te in ((n + self.duty) * T, (n + 1) * T, (n + 1 + self.duty) * T):
            if te > t0 + eps:
                if te < t1 - eps:
                    return (te - t0) / (t1 - t0)
                return None
        return None

    def accept(self, x, ctx):
        super().accept(x, ctx)
        if self.wave == "Square":
            high = ((ctx.t * self.freq) % 1.0) < self.duty
            if self._high is not None and high != self._high:
                self.changed = True        # an edge: the engine restarts its step size cleanly after it
            self._high = high



class Probe(Device):
    """Graph probes and logic probes: they only look."""

    def stamp(self, S, x, ctx):
        pass

    def accept(self, x, ctx):
        self.vd = v(x, self.nodes[0])
        self.i_pins = [0.0]


# ============================================================================================== coils
class Inductor(Device):
    """An inductor (trapezoidal companion model, backward Euler after a jump) with 100 kΩ across it — real
    coils have some loss, and it keeps the spike finite when the current is suddenly cut off."""
    reactive = True
    RP = 100e3

    def update_params(self):
        self.L = float(self.prop("inductance"))
        if not hasattr(self, "i_prev"):
            self.i_prev = self.v_prev = 0.0

    def companion(self, ctx):
        if ctx.method == "trap":
            G = ctx.h / (2 * self.L)
            return G, self.i_prev + G * self.v_prev
        G = ctx.h / self.L
        return G, self.i_prev

    def stamp(self, S, x, ctx):
        a, c = self.nodes
        S.g(a, c, 1 / self.RP)
        if ctx.dc:
            S.g(a, c, 1e3)                     # in steady DC a coil is just a wire
            return
        G, Ieq = self.companion(ctx)
        S.g(a, c, G)
        S.i(a, c, Ieq)

    def accept(self, x, ctx):
        a, c = self.nodes
        vd = v(x, a) - v(x, c)
        if ctx.dc:
            i = vd * 1e3
        else:
            G, Ieq = self.companion(ctx)
            i = G * vd + Ieq
        self.i_prev, self.v_prev, self.vd = i, vd, vd
        tot = i + vd / self.RP
        self.i_pins = [tot, -tot]
        self.power = vd * tot

    def after_dc(self):
        pass                                   # keep the DC current as the starting current


class Relay(Device):
    """Relay: coil (resistance + inductance) from C1 to C2; contacts COM–NC (at rest) or COM–NO (energised).
    It pulls in at 75 % of the coil current it's designed for and lets go below 30 %."""
    n_internal = 1
    reactive = True
    RP = 100e3

    def update_params(self):
        self.Vc = float(self.prop("voltage"))
        self.Rc = max(1.0, self.Vc / 0.06)          # about 60 mA coil current
        self.L = self.Rc * 5e-4                      # coil time constant 0.5 ms
        self.i_pull = 0.75 * self.Vc / self.Rc
        self.i_drop = 0.30 * self.Vc / self.Rc
        if not hasattr(self, "on"):
            self.on = False
            self.i_prev = self.v_prev = 0.0
            self.clicks = 0
            self.changed = False

    def companion(self, ctx):
        if ctx.method == "trap":
            G = ctx.h / (2 * self.L)
            return G, self.i_prev + G * self.v_prev
        G = ctx.h / self.L
        return G, self.i_prev

    def stamp(self, S, x, ctx):
        c1, c2, com, nc, no = self.nodes
        k = self.internal[0]
        S.g(c1, k, 1 / self.Rc)
        S.g(c1, c2, 1 / self.RP)
        if ctx.dc:
            S.g(k, c2, 1e3)
        else:
            G, Ieq = self.companion(ctx)
            S.g(k, c2, G)
            S.i(k, c2, Ieq)
            self._G, self._Ieq = G, Ieq
        S.g(com, no, 1 / (R_ON if self.on else R_OFF))
        S.g(com, nc, 1 / (R_OFF if self.on else R_ON))

    def coil_current(self, x, ctx):
        c1, c2 = self.nodes[0], self.nodes[1]
        k = self.internal[0]
        if ctx.dc:
            return (v(x, k) - v(x, c2)) * 1e3
        G, Ieq = self.companion(ctx)
        return G * (v(x, k) - v(x, c2)) + Ieq

    def crossing(self, xo, xn, t0, t1):
        i0 = abs(self.i_prev)
        k, c2 = self.internal[0], self.nodes[1]
        i1 = abs(getattr(self, "_G", 0.0) * (v(xn, k) - v(xn, c2)) + getattr(self, "_Ieq", 0.0))
        if not self.on:
            return frac_cross(i0, i1, self.i_pull, True)
        return frac_cross(i0, i1, self.i_drop, False)

    def accept(self, x, ctx):
        c1, c2, com, nc, no = self.nodes
        k = self.internal[0]
        i = self.coil_current(x, ctx)
        self.i_prev, self.v_prev = i, v(x, k) - v(x, c2)
        on = (abs(i) >= self.i_pull) if not self.on else (abs(i) > self.i_drop)
        if on != self.on:
            self.on = on
            self.changed = True
            self.clicks += 1
        icoil = i + (v(x, c1) - v(x, c2)) / self.RP
        ino = (v(x, com) - v(x, no)) / (R_ON if self.on else R_OFF)
        inc = (v(x, com) - v(x, nc)) / (R_OFF if self.on else R_ON)
        self.i_pins = [icoil, -icoil, ino + inc, -inc, -ino]
        self.current = i
        self.vd = v(x, c1) - v(x, c2)

    def after_dc(self):
        pass


class PhotoTransistor(BJT):
    """NPN phototransistor: light makes a base current inside it (about 2 nA per lux), so it conducts more
    the brighter it is. Pins C, E."""
    n_internal = 1

    def update_params(self):
        self.pol, self.Is, self.bf, self.br, self.icmax, self.pmax = 1, 1e-14, 300.0, 5.0, 0.05, 0.15
        self.vcrit = VT * math.log(VT / (math.sqrt(2) * self.Is))
        self.vbe_last = self.vbc_last = self.vbe_acc = self.vbc_acc = 0.0
        self.ic = self.ib = 0.0
        self.iph = 2e-9 * max(0.0, float(self.prop("light")))

    def _bce(self):
        return (self.internal[0], self.nodes[0], self.nodes[1])

    def stamp(self, S, x, ctx):
        super().stamp(S, x, ctx)
        if not self.blown:
            S.i(self.nodes[0], self.internal[0], self.iph)     # light: collector → base inside the device

    def accept(self, x, ctx):
        super().accept(x, ctx)
        ib, ic, ie = self.i_pins
        self.i_pins = [ic + self.iph, ie]


FACTORY = {
    "inductor": Inductor, "relay": Relay, "phototransistor": PhotoTransistor,
    "nmos": MOSFET, "pmos": MOSFET, "opamp": OpAmp, "timer555": Timer555,
    "not": Gate, "and": Gate, "or": Gate, "nand": Gate, "nor": Gate, "xor": Gate, "schmitt_not": Gate,
    "dff": DFF, "counter4017": Counter4017, "decoder4511": Decoder4511,
    "sevenseg": SevenSeg, "signal_gen": SignalGen, "scope_probe": Probe, "logic_probe": Probe,
}
