"""Electrical models of every part, for the circuit solver (no Qt).

Each device "stamps" its contribution into the nodal equations A·x = b, the same way SPICE does:
  - linear parts (resistors, batteries) stamp conductances and current sources,
  - capacitors use a companion model (a conductance plus a current source that remembers the last step),
  - diodes, LEDs and transistors are non-linear: they are linearised around the current guess and the
    solver repeats (Newton–Raphson) until the answer stops changing. Junction voltage steps are limited
    the SPICE way (pnjlim) so the exponentials never run away.

Node index -1 is 0 V (ground).
"""
from __future__ import annotations

import math

VT = 0.025852          # thermal voltage at 300 K
GMIN = 1e-12           # tiny conductance across every junction (as SPICE)
R_ON, R_OFF = 0.01, 1e12      # an open switch leaks only a few picoamps

# ------------------------------------------------------------------------------------------- model data
DIODES = {  # Is, n, Rs, max current (A)
    "1N4001": (14.11e-9, 1.984, 0.0339, 1.0),
    "1N4007": (14.11e-9, 1.984, 0.0339, 1.0),
    "1N4148": (2.52e-9, 1.752, 0.568, 0.3),
    "1N5408": (1.4e-8, 1.9, 0.02, 3.0),
    "1N5819": (7.7e-7, 1.1, 0.05, 1.0),       # Schottky: about 0.4 V drop
}
LED_VF = {"Red": 1.95, "Orange": 2.0, "Yellow": 2.05, "Green": 2.15, "Blue": 3.1, "White": 3.1}
LED_N, LED_RS = 2.0, 4.0
BJTS = {  # polarity, Is, BF, BR, max Ic (A), max power (W)
    "BC548": (1, 1.8e-14, 290.0, 7.5, 0.1, 0.5),
    "2N3904": (1, 6.734e-15, 416.4, 0.737, 0.2, 0.625),
    "BD139": (1, 2e-13, 120.0, 5.0, 1.5, 1.25),
    "TIP31": (1, 1e-12, 50.0, 5.0, 3.0, 2.0),
    "BC558": (-1, 1e-14, 290.0, 7.0, 0.1, 0.5),
    "2N3906": (-1, 1.41e-15, 180.7, 4.977, 0.2, 0.625),
    "BD140": (-1, 2e-13, 120.0, 5.0, 1.5, 1.25),
    "BC547": (1, 1.8e-14, 290.0, 7.5, 0.1, 0.5),
    "BC337": (1, 4.1e-14, 300.0, 10.0, 0.8, 0.625),
    "2N2222": (1, 1.4e-14, 200.0, 6.0, 0.8, 0.5),
    "TIP120": (1, 1e-17, 1000.0, 5.0, 5.0, 2.0),       # Darlington (behaves like a very high-gain transistor)
    "BC557": (-1, 1e-14, 290.0, 7.0, 0.1, 0.5),
    "BC327": (-1, 4e-14, 300.0, 10.0, 0.8, 0.625),
    "2N2907": (-1, 1.1e-14, 200.0, 6.0, 0.6, 0.4),
    "TIP125": (-1, 1e-17, 1000.0, 5.0, 5.0, 2.0),
}
VCEO = {"BC548": 30, "BC547": 45, "BC337": 45, "2N3904": 40, "2N2222": 40, "BD139": 80, "TIP31": 40, "TIP120": 60,
        "BC558": 30, "BC557": 45, "BC327": 45, "2N3906": 40, "2N2907": 40, "BD140": 80, "TIP125": 60}
R_INT = {"cell": 0.2, "battery": 1.5, "dc_supply": 0.02, "ac_supply": 0.1, "rail_pos": 0.01}


def led_is(colour: str) -> float:
    """Saturation current chosen so the LED drops its typical voltage at 20 mA."""
    vf = LED_VF.get(colour, 2.0)
    vj = vf - 0.02 * LED_RS
    return 0.02 / math.exp(vj / (LED_N * VT))


def sexp(x: float) -> float:
    """exp() that carries on in a straight line above 80 instead of overflowing."""
    if x > 80.0:
        return math.exp(80.0) * (1.0 + x - 80.0)
    return math.exp(x)


def pnjlim(vnew: float, vold: float, vt: float, vcrit: float) -> float:
    """SPICE junction voltage limiting: stops Newton jumping far up the exponential in one go."""
    if vnew > vcrit and abs(vnew - vold) > 2 * vt:
        if vold > 0:
            arg = 1 + (vnew - vold) / vt
            vnew = vold + vt * math.log(arg) if arg > 0 else vcrit
        else:
            vnew = vt * math.log(max(vnew / vt, 1e-30))
    return vnew


class Stamper:
    """Collects the equations for one Newton iteration."""

    def __init__(self, A, b):
        self.A, self.b = A, b

    def g(self, a, c, G):
        """Conductance G between nodes a and c."""
        A = self.A
        if a >= 0:
            A[a, a] += G
        if c >= 0:
            A[c, c] += G
        if a >= 0 and c >= 0:
            A[a, c] -= G
            A[c, a] -= G

    def i(self, a, c, I):
        """Current I flowing out of node a, through the device, into node c."""
        if a >= 0:
            self.b[a] -= I
        if c >= 0:
            self.b[c] += I

    def nonlinear(self, nodes, I0, J, V0):
        """Terminal currents I_k (into the device) linearised: I_k ≈ I0_k + Σ J_kj (V_j − V0_j)."""
        A, b = self.A, self.b
        n = len(nodes)
        for k in range(n):
            a = nodes[k]
            if a < 0:
                continue
            rhs = -I0[k]
            for j in range(n):
                rhs += J[k][j] * V0[j]
                c = nodes[j]
                if c >= 0:
                    A[a, c] += J[k][j]
            b[a] += rhs


class Ctx:
    """What the devices need to know about the current step."""

    def __init__(self):
        self.t = 0.0
        self.h = 1e-6
        self.method = "be"      # "be" (backward Euler, after a jump) or "trap" (trapezoidal)
        self.dc = False         # True: capacitors are open circuits (DC operating point)
        self.source_scale = 1.0
        self.limited = False    # a junction voltage was limited in this iteration (not converged yet)


def v(x, n):
    return x[n] if n >= 0 else 0.0


# =========================================================================================== devices
class Device:
    """Base class. `nodes` are the external pins (in the part's pin order); extra internal nodes are added
    by the engine when `n_internal` > 0."""
    n_internal = 0
    nonlinear = False
    reactive = False

    def __init__(self, comp, nodes):
        self.comp = comp
        self.cid = comp.id if comp is not None else ""
        self.nodes = list(nodes)
        self.internal = []
        self.blown = False
        self.warn = None         # short text while something is wrong (e.g. "too much current")
        self.i_pins = [0.0] * len(nodes)   # current INTO the device at each pin, after the last step
        self.power = 0.0
        self._over = 0.0         # how long it has been overloaded (s)
        self.event = None        # message for the user when something happens (an LED pops …)
        self.update_params()

    def update_params(self):
        pass

    def prop(self, key):
        return self.comp.value(key)

    def stamp(self, S: Stamper, x, ctx: Ctx):
        raise NotImplementedError

    def accept(self, x, ctx: Ctx):
        """Called once a time step is accepted: update memory, readings and overload checks."""

    def begin_iter(self):
        pass

    def reading(self):
        """Text shown on meters during the simulation, or None."""
        return None

    def _overload(self, bad: bool, h: float, limit_s: float, instant: bool = False) -> bool:
        """True when a part has been overloaded long enough to fail."""
        if instant:
            return True
        self._over = self._over + h if bad else 0.0
        return self._over >= limit_s


class Resistive(Device):
    """Anything that behaves as a plain resistor between its two pins."""

    def resistance(self) -> float:
        return 1.0

    def stamp(self, S, x, ctx):
        R = R_OFF if self.blown else max(self.resistance(), 1e-6)
        S.g(self.nodes[0], self.nodes[1], 1.0 / R)

    def accept(self, x, ctx):
        R = R_OFF if self.blown else max(self.resistance(), 1e-6)
        vd = v(x, self.nodes[0]) - v(x, self.nodes[1])
        i = vd / R
        self.i_pins = [i, -i]
        self.power = vd * i
        self.vd = vd
        self.after(ctx)

    def after(self, ctx):
        pass


class Resistor(Resistive):
    def update_params(self):
        self.R = float(self.prop("resistance"))
        self.rating = float(self.prop("power") or 0.25)

    def resistance(self):
        return self.R

    def after(self, ctx):
        if self.blown:
            return
        hot = self.power > self.rating
        self.warn = "hot" if hot else None
        if self._overload(self.power > 2 * self.rating, ctx.h, 0.5, self.power > 8 * self.rating):
            self.blown = True
            self.event = (f"{self.comp.ref} burnt out — {self.power:.2f} W is far more than its "
                          f"{self.rating:g} W rating.")


class VarResistor(Resistive):
    def update_params(self):
        self.R = max(1.0, float(self.prop("resistance")) * float(self.prop("setting")) / 100.0)

    def resistance(self):
        return self.R


class LDR(Resistive):
    def update_params(self):
        lux = max(0.0, float(self.prop("light")))
        r = 15e3 * (max(lux, 1e-3) / 10.0) ** -0.7 if lux > 0 else 2e6
        self.R = min(2e6, max(100.0, r))

    def resistance(self):
        return self.R


class Moisture(Resistive):
    """Two probes in soil: 1 MΩ when dry down to 1 kΩ when soaking (evenly on a log scale)."""

    def update_params(self):
        m = min(100.0, max(0.0, float(self.prop("moisture"))))
        self.R = 1e6 * 10 ** (-3 * m / 100.0)

    def resistance(self):
        return self.R


class Thermistor(Resistive):
    B = 3950.0

    def update_params(self):
        t = float(self.prop("temperature")) + 273.15
        self.R = float(self.prop("r25")) * math.exp(self.B * (1.0 / t - 1.0 / 298.15))

    def resistance(self):
        return self.R


class Fuse(Resistive):
    def update_params(self):
        self.rating = float(self.prop("rating"))

    def resistance(self):
        return 0.05

    def after(self, ctx):
        i = abs(self.i_pins[0])
        if not self.blown and self._overload(i > self.rating, ctx.h, 0.02, i > 3 * self.rating):
            self.blown = True
            self.event = f"{self.comp.ref} blew — {i:.2f} A is more than its {self.rating:g} A rating."


class Switch(Resistive):
    """On/off switch, push switches, reed and tilt switches. `closed()` decides."""

    def closed(self):
        k = self.comp.kind
        if k == "switch":
            return bool(self.prop("closed"))
        if k == "reed_switch":
            return bool(self.prop("magnet"))
        if k == "tilt_switch":
            return bool(self.prop("tilted"))
        if k == "push_make":
            return bool(self.prop("pressed"))
        if k == "push_break":
            return not bool(self.prop("pressed"))
        return False

    def resistance(self):
        return R_ON if self.closed() else R_OFF


class SPDT(Device):
    """Changeover switch: common to A or to B."""

    def stamp(self, S, x, ctx):
        com, a, b = self.nodes
        to_a = self.prop("position") == "A"
        S.g(com, a, 1 / (R_ON if to_a else R_OFF))
        S.g(com, b, 1 / (R_OFF if to_a else R_ON))

    def accept(self, x, ctx):
        com, a, b = self.nodes
        to_a = self.prop("position") == "A"
        ia = (v(x, com) - v(x, a)) / (R_ON if to_a else R_OFF)
        ib = (v(x, com) - v(x, b)) / (R_OFF if to_a else R_ON)
        self.i_pins = [ia + ib, -ia, -ib]


class Potentiometer(Device):
    def update_params(self):
        R = float(self.prop("resistance"))
        s = min(1.0, max(0.0, float(self.prop("setting")) / 100.0))
        self.R1 = max(0.5, R * s)           # pin 1 to wiper
        self.R2 = max(0.5, R * (1 - s))     # wiper to pin 2

    def stamp(self, S, x, ctx):
        n1, n2, w = self.nodes
        S.g(n1, w, 1 / self.R1)
        S.g(w, n2, 1 / self.R2)

    def accept(self, x, ctx):
        n1, n2, w = self.nodes
        i1 = (v(x, n1) - v(x, w)) / self.R1
        i2 = (v(x, w) - v(x, n2)) / self.R2
        self.i_pins = [i1, -i2, i2 - i1]
        self.power = i1 * i1 * self.R1 + i2 * i2 * self.R2


class Source(Device):
    """A voltage source with a little internal resistance (Norton form): batteries, supplies, rails.
    Pins: + then − (a rail's − is 0 V)."""

    def update_params(self):
        self.V = float(self.prop("voltage"))
        self.Rint = R_INT.get(self.comp.kind, 0.05)
        self.freq = float(self.prop("frequency")) if self.comp.kind == "ac_supply" else 0.0

    def emf(self, t):
        if self.freq > 0:
            return self.V * math.sin(2 * math.pi * self.freq * t)
        return self.V

    def stamp(self, S, x, ctx):
        p, n = self.nodes
        G = 1.0 / self.Rint
        S.g(p, n, G)
        S.i(n, p, self.emf(ctx.t) * ctx.source_scale * G)     # pushes current out of + into the circuit

    def accept(self, x, ctx):
        p, n = self.nodes
        G = 1.0 / self.Rint
        i_out = (self.emf(ctx.t) - (v(x, p) - v(x, n))) * G     # current leaving + into the circuit
        self.i_pins = [-i_out, i_out]
        self.power = -(v(x, p) - v(x, n)) * i_out               # negative: it delivers power
        short = abs(i_out) > 0.5 * abs(self.V) / self.Rint and abs(self.V) > 0
        self.warn = "short" if short else None
        if short and not getattr(self, "_short_told", False):
            self._short_told = True
            self.event = (f"{self.comp.ref} is short-circuited — current is flowing straight from + to − "
                          f"({abs(i_out):.1f} A).")


class Capacitor(Device):
    reactive = True

    def update_params(self):
        self.C = float(self.prop("capacitance"))
        self.vmax = float(self.prop("max_voltage")) if self.comp.kind == "electrolytic" else None

    def reset(self):
        self.v_prev = 0.0
        self.i_prev = 0.0

    def __init__(self, comp, nodes):
        super().__init__(comp, nodes)
        self.reset()

    def _geq(self, ctx):
        return (2.0 if ctx.method == "trap" else 1.0) * self.C / ctx.h

    def stamp(self, S, x, ctx):
        a, c = self.nodes
        if self.blown or ctx.dc:
            S.g(a, c, GMIN)
            return
        G = self._geq(ctx)
        Ieq = G * self.v_prev + (self.i_prev if ctx.method == "trap" else 0.0)
        S.g(a, c, G)
        S.i(c, a, Ieq)          # i = G·v − Ieq, from a to c

    def accept(self, x, ctx):
        a, c = self.nodes
        vd = v(x, a) - v(x, c)
        if self.blown or ctx.dc:
            i = 0.0
        else:
            G = self._geq(ctx)
            i = G * vd - (G * self.v_prev + (self.i_prev if ctx.method == "trap" else 0.0))
        self.v_prev, self.i_prev = vd, i
        self.i_pins = [i, -i]
        self.vd = vd
        if self.vmax is not None and not self.blown:
            bad = vd < -1.0 or vd > 1.2 * self.vmax
            if self._overload(bad, ctx.h, 0.1):
                self.blown = True
                why = "it's connected the wrong way round" if vd < 0 else f"{vd:.1f} V is over its rating"
                self.event = f"{self.comp.ref} popped — {why}."


class Diode(Device):
    """Shockley diode with series resistance (via an internal node) and, for Zeners, reverse breakdown."""
    n_internal = 1
    nonlinear = True

    def update_params(self):
        k = self.comp.kind
        self.bv = None
        if k == "led":
            self.Is, self.n, self.Rs = led_is(self.prop("colour")), LED_N, LED_RS
            self.imax = float(self.prop("max_current"))
        elif k == "zener":
            self.Is, self.n, self.Rs = 1e-14, 1.0, 2.0
            self.bv = float(self.prop("voltage"))
            self.imax = 0.5
        else:
            Is, n, Rs, imax = DIODES.get(self.prop("model"), DIODES["1N4001"])
            self.Is, self.n, self.Rs, self.imax = Is, n, Rs, imax
        self.nvt = self.n * VT
        self.vcrit = self.nvt * math.log(self.nvt / (math.sqrt(2) * self.Is))
        self.vd_last = self.vd_acc = 0.0

    def begin_iter(self):
        self.vd_last = self.vd_acc

    def junction(self, vd):
        """Current and conductance of the junction at voltage vd."""
        e = sexp(vd / self.nvt)
        i = self.Is * (e - 1.0)
        g = self.Is * e / self.nvt
        if self.bv is not None and vd < -self.bv + 10 * VT * 5:
            # reverse breakdown: 1 mA at −BV, rising steeply
            u = -(vd + self.bv) / VT
            eb = sexp(u)
            i -= 1e-3 * eb
            g += 1e-3 * eb / VT
        return i + GMIN * vd, g + GMIN

    def stamp(self, S, x, ctx):
        a, c = self.nodes
        k = self.internal[0]
        if self.blown:
            S.g(a, c, 1 / R_OFF)
            S.g(a, k, 1.0)
            return
        S.g(a, k, 1.0 / self.Rs)
        vd = v(x, k) - v(x, c)
        vl = pnjlim(vd, self.vd_last, self.nvt, self.vcrit)
        if self.bv is not None and vd < -self.bv:      # limit in the breakdown direction too
            vl = -self.bv - pnjlim(-vd - self.bv, -self.vd_last - self.bv, VT, 0.6)
        if abs(vl - vd) > 1e-9:
            ctx.limited = True
        self.vd_last = vl
        i, g = self.junction(vl)
        S.g(k, c, g)
        S.i(k, c, i - g * vl)

    def accept(self, x, ctx):
        a, c = self.nodes
        k = self.internal[0]
        if self.blown:
            i = (v(x, a) - v(x, c)) / R_OFF
        else:
            vd = v(x, k) - v(x, c)
            i, _g = self.junction(vd)
            self.vd_last = self.vd_acc = vd
        self.i_pins = [i, -i]
        self.vd = v(x, a) - v(x, c)
        self.power = self.vd * i
        self.current = i
        if self.blown:
            return
        over = abs(i) > self.imax
        self.warn = "over" if over else None
        if self._overload(over, ctx.h, 0.03, abs(i) > 3 * self.imax):
            self.blown = True
            what = "LED" if self.comp.kind == "led" else "diode"
            hint = " Add a resistor in series to limit the current." if self.comp.kind == "led" else ""
            self.event = (f"{self.comp.ref} popped! {abs(i) * 1000:.0f} mA is too much for this {what} "
                          f"(max {self.imax * 1000:.0f} mA).{hint}")

    def glow(self):
        if self.blown or self.comp.kind != "led":
            return 0.0
        # LEDs give no visible light below about 0.1 mA, and look fully lit from about 15 mA
        return max(0.0, min(1.0, (self.current - 1e-4) / 0.015)) ** 0.6


class BJT(Device):
    """Ebers–Moll transistor. Pins B, C, E. PNP handled by flipping all polarities."""
    nonlinear = True

    def update_params(self):
        pol, Is, bf, br, icmax, pmax = BJTS.get(self.prop("model"), BJTS["BC548"])
        if (self.comp.kind == "pnp") != (pol < 0):     # model list mixes types: follow the symbol
            pol = -1 if self.comp.kind == "pnp" else 1
        self.pol, self.Is, self.bf, self.br, self.icmax, self.pmax = pol, Is, bf, br, icmax, pmax
        self.vcrit = VT * math.log(VT / (math.sqrt(2) * Is))
        self.vbe_last = self.vbc_last = 0.0
        self.vbe_acc = self.vbc_acc = 0.0
        self.ic = self.ib = 0.0

    def begin_iter(self):
        self.vbe_last, self.vbc_last = self.vbe_acc, self.vbc_acc

    def currents(self, vbe, vbc):
        """Currents into C and B (for an NPN) and their derivatives against vbe and vbc."""
        ef, er = sexp(vbe / VT), sexp(vbc / VT)
        If, Ir = self.Is * (ef - 1), self.Is * (er - 1)
        gf, gr = self.Is * ef / VT, self.Is * er / VT
        ic = If - Ir * (1 + 1 / self.br)
        ib = If / self.bf + Ir / self.br
        dic = (gf, -gr * (1 + 1 / self.br))
        dib = (gf / self.bf, gr / self.br)
        # tiny conductances across the junctions keep things solvable
        ib += GMIN * (vbe + vbc)
        dib = (dib[0] + GMIN, dib[1] + GMIN)
        ic -= GMIN * vbc
        dic = (dic[0], dic[1] - GMIN)
        return ic, ib, dic, dib

    def stamp(self, S, x, ctx):
        b, c, e = self._bce()
        if self.blown:
            for a1, a2 in ((b, e), (b, c), (c, e)):
                S.g(a1, a2, 1 / R_OFF)
            return
        p = self.pol
        vb, vc, ve = v(x, b), v(x, c), v(x, e)
        vbe, vbc = p * (vb - ve), p * (vb - vc)
        vbe_l = pnjlim(vbe, self.vbe_last, VT, self.vcrit)
        vbc_l = pnjlim(vbc, self.vbc_last, VT, self.vcrit)
        if abs(vbe_l - vbe) > 1e-9 or abs(vbc_l - vbc) > 1e-9:
            ctx.limited = True
        self.vbe_last, self.vbc_last = vbe_l, vbc_l
        ic, ib, dic, dib = self.currents(vbe_l, vbc_l)
        ie = -(ic + ib)
        # node voltages that correspond to the limited junction voltages (keep vb, move c and e)
        vc0, ve0 = vb - p * vbc_l, vb - p * vbe_l
        # derivatives of terminal currents (into the device) w.r.t. node voltages [B, C, E]
        def row(d):
            dbe, dbc = d
            return [dbe + dbc, -dbc, -dbe]
        Jc, Jb = row(dic), row(dib)
        Je = [-(Jc[i] + Jb[i]) for i in range(3)]
        S.nonlinear([b, c, e], [p * ib, p * ic, p * ie], [Jb, Jc, Je], [vb, vc0, ve0])

    def _bce(self):
        return self.nodes

    def accept(self, x, ctx):
        b, c, e = self._bce()
        p = self.pol
        vb, vc, ve = v(x, b), v(x, c), v(x, e)
        if self.blown:
            self.ic = self.ib = 0.0
        else:
            ic, ib, _d1, _d2 = self.currents(p * (vb - ve), p * (vb - vc))
            self.ic, self.ib = p * ic, p * ib
            self.vbe_acc, self.vbc_acc = p * (vb - ve), p * (vb - vc)
        self.i_pins = [self.ib, self.ic, -(self.ib + self.ic)]
        self.power = self.ic * (vc - ve) + self.ib * (vb - ve)
        if self.blown:
            return
        vmax = VCEO.get(self.prop("model"), 40) if self.comp.kind in ("npn", "pnp") else 30
        if abs(vc - ve) > 1.5 * vmax:
            self.blown = True
            self.event = spike_message(self.comp.ref, abs(vc - ve), vmax)
            return
        bad = abs(self.ic) > 1.5 * self.icmax or self.power > 1.5 * self.pmax
        self.warn = "over" if (abs(self.ic) > self.icmax or self.power > self.pmax) else None
        if self._overload(bad, ctx.h, 0.2, abs(self.ic) > 5 * self.icmax):
            self.blown = True
            self.event = (f"{self.comp.ref} burnt out — {abs(self.ic) * 1000:.0f} mA / {self.power:.2f} W is "
                          f"too much for a {self.prop('model')} (max {self.icmax * 1000:.0f} mA). "
                          "Add a resistor to its base or load.")


def spike_message(ref, volts, vmax):
    return (f"{ref} was destroyed by a {volts:.0f} V spike — more than its {vmax:.0f} V limit. If it switches a "
            "relay coil, motor or inductor, put a diode across the coil (pointing towards +) to catch the spike.")


class Lamp(Resistive):
    def update_params(self):
        V, P = float(self.prop("voltage")), float(self.prop("power"))
        self.Prated = P
        self.R = V * V / P if P > 0 else 100.0

    def resistance(self):
        return self.R

    def after(self, ctx):
        if self.blown:
            return
        if self._overload(self.power > 1.6 * self.Prated, ctx.h, 0.2, self.power > 4 * self.Prated):
            self.blown = True
            self.event = f"{self.comp.ref} blew — its filament can't take {self.power:.1f} W."

    def glow(self):
        if self.blown or self.Prated <= 0:
            return 0.0
        f = (self.power / self.Prated - 0.02) / 0.98       # a filament shows nothing below ~2 % power
        return max(0.0, min(1.0, f)) ** 0.5


class Buzzer(Resistive):
    def update_params(self):
        self.V = float(self.prop("voltage"))
        self.R = max(1.0, self.V / 0.015)

    def resistance(self):
        return self.R

    def level(self):
        """0..1 loudness (only when connected the right way round)."""
        vd = getattr(self, "vd", 0.0)
        return 0.0 if vd < 0.3 * self.V else min(1.0, vd / self.V)


class Speaker(Resistive):
    def update_params(self):
        self.R = float(self.prop("impedance"))

    def resistance(self):
        return self.R


class Motor(Device):
    """DC motor: winding resistance R in series with a back-EMF k·ω. The rotor speeds up until the back-EMF
    nearly balances the supply, so it takes a big current when starting and much less once running.
    Load (friction plus what it drives) slows it down and makes it take more current."""
    I_STALL = 1.0              # A at rated voltage, stopped
    W0 = 2 * math.pi * 100     # rad/s with no load at rated voltage (6000 rpm)
    LOADS = {"None": 0.0, "Light": 0.2, "Medium": 0.45, "Heavy": 0.8}

    def update_params(self):
        self.V = max(0.1, float(self.prop("voltage")))
        self.R = self.V / self.I_STALL
        self.k = self.V / self.W0
        self.b = 0.1 * self.k * self.I_STALL / self.W0           # no-load current about 10 % of stall
        self.J = 0.1 * self.k * self.k / self.R                    # spins up in about 0.1 s
        self.TL = self.LOADS.get(self.prop("load"), 0.0) * self.k * self.I_STALL
        if not hasattr(self, "w"):
            self.w = 0.0
            self.speed = 0.0
            self.current = 0.0

    def stamp(self, S, x, ctx):
        a, c = self.nodes
        G = 1.0 / self.R
        S.g(a, c, G)
        S.i(c, a, G * self.k * self.w)          # the back-EMF pushes against the supply

    def accept(self, x, ctx):
        a, c = self.nodes
        vd = v(x, a) - v(x, c)
        h = 0.0 if ctx.dc else ctx.h
        # rotor: J dω/dt = k·i − b·ω − load, with i = (v − kω)/R (solved implicitly: always stable)
        drive = self.k * vd / self.R
        if abs(self.w) < 1e-3 and abs(drive) <= self.TL:
            self.w = 0.0                         # not enough torque to get going against the load
        elif h > 0:
            sgn = 1.0 if (self.w if abs(self.w) > 1e-3 else drive) > 0 else -1.0
            self.w = (self.w + h / self.J * (drive - self.TL * sgn)) / \
                (1 + h * (self.b + self.k * self.k / self.R) / self.J)
        i = (vd - self.k * self.w) / self.R
        self.current = i
        self.vd = vd
        self.i_pins = [i, -i]
        self.power = vd * i
        self.speed = self.w / self.W0
        self.rpm = self.w * 60 / (2 * math.pi)
        self.warn = "fast" if abs(self.speed) > 1.5 else ("stalled" if self.TL > 0 and self.w == 0 and
                                                           abs(i) > 0.5 * self.I_STALL else None)


class Voltmeter(Resistive):
    def resistance(self):
        return 10e6

    def reading(self):
        return getattr(self, "vd", 0.0), "V"


class Ammeter(Resistive):
    def resistance(self):
        return 1e-3

    def reading(self):
        return self.i_pins[0], "A"


class Nothing(Device):
    """Parts with no electrical effect (0 V symbol)."""

    def stamp(self, S, x, ctx):
        pass


FACTORY = {
    "resistor": Resistor, "var_resistor": VarResistor, "ldr": LDR, "thermistor": Thermistor, "fuse": Fuse,
    "switch": Switch, "push_make": Switch, "push_break": Switch, "reed_switch": Switch, "tilt_switch": Switch,
    "moisture": Moisture, "spdt": SPDT, "potentiometer": Potentiometer,
    "cell": Source, "battery": Source, "dc_supply": Source, "ac_supply": Source, "rail_pos": Source,
    "capacitor": Capacitor, "electrolytic": Capacitor,
    "diode": Diode, "led": Diode, "zener": Diode, "npn": BJT, "pnp": BJT,
    "lamp": Lamp, "buzzer": Buzzer, "speaker": Speaker, "motor": Motor,
    "voltmeter": Voltmeter, "ammeter": Ammeter, "ground": Nothing,
}
