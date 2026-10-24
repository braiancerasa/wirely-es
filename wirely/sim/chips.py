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
# Every type is described by its datasheet figures, and the model is fitted to them when Wirely starts.
# Typical values are used where the datasheet gives them; where it only gives a maximum, about 75–80 % of it.
#   polarity, Vgs(th) (V) at its test current (A), on-resistance points ((Vgs, Rds(on) Ω), …),
#   Ciss, Coss, Crss (F) at the datasheet's test Vds (V), max Vds (V), max Id (A), max power without a heatsink (W)
MOSFET_DATA = {
    "2N7000":    (1, 2.1, 1e-3, ((10, 1.2), (4.5, 1.8)), 20e-12, 11e-12, 4e-12, 25, 60, 0.2, 0.4),
    "BS170":     (1, 2.1, 1e-3, ((10, 1.2),), 24e-12, 17e-12, 5e-12, 10, 60, 0.5, 0.83),
    "IRF540":    (1, 3.0, 250e-6, ((10, 0.060),), 1700e-12, 560e-12, 120e-12, 25, 100, 28.0, 2.0),
    "IRF530":    (1, 3.0, 250e-6, ((10, 0.12),), 670e-12, 250e-12, 60e-12, 25, 100, 14.0, 2.0),
    "IRLZ44N":   (1, 1.5, 250e-6, ((10, 0.018), (5, 0.020), (4, 0.028)), 1700e-12, 400e-12, 150e-12, 25, 55,
                  47.0, 2.0),
    "IRF3205":   (1, 3.0, 250e-6, ((10, 0.0065),), 3247e-12, 781e-12, 211e-12, 25, 55, 110.0, 2.0),
    "AO3400":    (1, 1.05, 250e-6, ((10, 0.018), (4.5, 0.019), (2.5, 0.024)), 630e-12, 75e-12, 50e-12, 15, 30,
                  5.7, 1.4),
    "BS250":     (-1, 2.25, 1e-3, ((10, 10.0),), 60e-12, 25e-12, 8e-12, 10, 45, 0.23, 0.7),
    "IRF9540":   (-1, 3.0, 250e-6, ((10, 0.15),), 1400e-12, 590e-12, 140e-12, 25, 100, 19.0, 2.0),
    "IRF9530":   (-1, 3.0, 250e-6, ((10, 0.22),), 860e-12, 340e-12, 93e-12, 25, 100, 12.0, 2.0),
    "FQP27P06":  (-1, 3.0, 250e-6, ((10, 0.055),), 1100e-12, 510e-12, 120e-12, 25, 60, 27.0, 2.0),
    "IRLML6402": (-1, 0.55, 250e-6, ((4.5, 0.050), (2.5, 0.080)), 633e-12, 145e-12, 110e-12, 10, 20, 3.7, 1.3),
}
SUB_S = 2 * 1.5 * VT        # how softly a MOSFET turns on below threshold: about 90 mV per decade of current
CAP_VJ, CAP_M, CAP_FC = 2.0, 0.8, 0.5   # shape of Cgd and Cds against voltage (fitted to datasheet gate charges)


class MosParams:
    def __init__(self, name):
        (self.pol, self.vth, self.ith, self.rds, self.ciss, self.coss, self.crss, self.vcap, self.vdss,
         self.idmax, self.pmax) = MOSFET_DATA[name]
        self.lam = 0.01 if self.idmax < 1 else 0.003
        self.vto, self.kp, self.theta, self.rser = fit_mosfet(self.vth, self.ith, self.rds, self.vdss)
        # body diode: about 0.72 V at a sixth of the rated current
        self.bd_n = 1.2
        self.bd_is = (self.idmax / 6) / math.exp(0.72 / (self.bd_n * VT))
        k = (1 + self.vcap / CAP_VJ) ** CAP_M          # datasheet capacitances are measured at vcap
        self.rg = 2.0 if self.idmax >= 1 else 10.0      # internal gate resistance (typical datasheet values)
        self.cgs = self.ciss - self.crss
        self.cgd0 = self.crss * k
        self.cds0 = max(self.coss - self.crss, 0.0) * k


def fit_mosfet(vth, ith, rds_pts, vdss):
    """Threshold (VTO), transconductance (KP), mobility reduction (THETA) and drain series resistance that
    reproduce the datasheet's Vgs(th) at its test current and its Rds(on) at each gate voltage given.
    The part of Rds(on) that doesn't fall with gate voltage is split between the drift region (in series; a
    bigger share in higher-voltage parts) and the channel's mobility falling at high gate voltage (THETA)."""
    drift = 0.5 if vdss >= 100 else 0.25 if vdss >= 45 else 0.15
    vto = vth - 0.3
    kp, theta, rd = 1.0, 0.0, 0.0
    r_top = max(rds_pts)[1]                     # Rds(on) at the highest gate voltage
    for _ in range(200):
        vovs = [softplus(vg - vto, SUB_S) for vg, _r in rds_pts]
        rs = [r for _vg, r in rds_pts]
        if len(rds_pts) >= 2:                    # least squares in relative error: R = a / vov + const
            xs = [1 / vv for vv in vovs]
            ws = [1 / (r * r) for r in rs]
            sw = sum(ws)
            mx = sum(w * x for w, x in zip(ws, xs)) / sw
            my = sum(w * y for w, y in zip(ws, rs)) / sw
            sxx = sum(w * (x - mx) ** 2 for w, x in zip(ws, xs))
            a = (sum(w * (x - mx) * (y - my) for w, x, y in zip(ws, xs, rs)) / sxx) if sxx > 0 else rs[0] * vovs[0]
            const = my - a * mx
            if a <= 0 or const < drift * r_top:
                const = drift * r_top
                a = sum(x * (y - const) for x, y in zip(xs, rs)) / sum(x * x for x in xs)
        else:
            const = drift * rs[0]
            a = (rs[0] - const) * vovs[0]
        kp = 1.0 / a
        rd = min(const, drift * r_top)
        theta = (const - rd) * kp
        vov_th = math.sqrt(2 * ith / kp)
        new = vth - SUB_S * math.log(math.expm1(vov_th / SUB_S))
        if abs(new - vto) < 1e-10:
            vto = new
            break
        vto = new
    return vto, kp, theta, rd


MOSFETS = {name: MosParams(name) for name in MOSFET_DATA}
VDS_MAX = {name: p.vdss for name, p in MOSFETS.items()}


class QCap:
    """A charge-based capacitor (keeps charge exactly, as SPICE does). With M > 0 it's a junction-style
    capacitance: C = C0·(1 − vf/VJ)^−M while reverse biased (vf < 0 widens the depletion layer, so C falls),
    levelling off once it's forward biased past FC·VJ. vf is measured from the "a" node to the "c" node."""

    def __init__(self, C0, M=0.0):
        self.C0, self.M = C0, M
        self.vf_lim = CAP_FC * CAP_VJ
        if M:
            self.c_lim = C0 * (1 - self.vf_lim / CAP_VJ) ** -M
            self.q_lim = self._qj(self.vf_lim)
        self.q_prev = self.i_prev = 0.0

    def _qj(self, vf):
        return self.C0 * CAP_VJ / (1 - self.M) * (1 - (1 - vf / CAP_VJ) ** (1 - self.M))

    def c(self, vf):
        if not self.M:
            return self.C0
        return self.c_lim if vf >= self.vf_lim else self.C0 * (1 - vf / CAP_VJ) ** -self.M

    def q(self, vf):
        if not self.M:
            return self.C0 * vf
        return self.q_lim + self.c_lim * (vf - self.vf_lim) if vf >= self.vf_lim else self._qj(vf)

    # Always backward Euler: these small device capacitances sit right next to stiff, fast parts (a diode
    # clamping a node, a gate driver), where the trapezoidal rule rings from step to step. Backward Euler damps
    # that, at no real cost in accuracy for capacitances this small (the op-amp's pole capacitor does the same).
    def current(self, vf, ctx):
        return (self.q(vf) - self.q_prev) / ctx.h

    def stamp(self, S, a, c, vf, ctx):
        if ctx.dc or self.C0 <= 0:
            return
        G = self.c(vf) / ctx.h
        S.g(a, c, G)
        S.i(a, c, self.current(vf, ctx) - G * vf)

    def accept(self, vf, ctx):
        i = 0.0 if (ctx.dc or self.C0 <= 0) else self.current(vf, ctx)
        self.q_prev, self.i_prev = self.q(vf), i
        return i

    def settle(self, vf):
        self.q_prev, self.i_prev = self.q(vf), 0.0


class MOSFET(Device):
    """Power / small-signal MOSFET fitted to its datasheet. Pins G, D, S.
    Inside: the channel (square law, softened below threshold as real MOSFETs are), the drain's series
    resistance (internal node), the body diode from source to drain, the gate–source capacitance, and
    voltage-dependent gate–drain (Miller) and drain–source capacitances — so switching takes real time and
    shows the Miller plateau."""
    nonlinear = True
    reactive = True
    n_internal = 2              # [0] the drain inside its series resistance, [1] the gate inside its resistance

    def update_params(self):
        default = "2N7000" if self.comp.kind == "nmos" else "BS250"
        self.P = MOSFETS.get(self.prop("model"), MOSFETS[default])
        self.pol = -1 if self.comp.kind == "pmos" else 1
        P = self.P
        self.vt, self.kp, self.lam, self.idmax, self.pmax = P.vto, P.kp, P.lam, P.idmax, P.pmax
        self.theta = P.theta
        self.rser = P.rser
        self.rg = P.rg
        self.cgs, self.cgd, self.cds = QCap(P.cgs), QCap(P.cgd0, CAP_M), QCap(P.cds0, CAP_M)
        self.bd_nvt = P.bd_n * VT
        self.bd_vcrit = self.bd_nvt * math.log(self.bd_nvt / (math.sqrt(2) * P.bd_is))
        self.vgs_acc = self.vds_acc = self.vbd_acc = 0.0
        self.vgs_last = self.vds_last = self.vbd_last = 0.0
        self.id = 0.0

    def begin_iter(self):
        self.vgs_last, self.vds_last, self.vbd_last = self.vgs_acc, self.vds_acc, self.vbd_acc

    def ids(self, vgs, vds):
        """Channel current for an N-channel device (vgs, vds may be anything)."""
        if vds < 0:                       # source and drain swap roles
            return -self.ids(vgs - vds, -vds)
        vov = softplus(vgs - self.vt, SUB_S)
        kp = self.kp / (1 + self.theta * vov)       # mobility falls at high gate voltage
        if vds < vov:
            i = kp * (vov * vds - 0.5 * vds * vds)
        else:
            i = 0.5 * kp * vov * vov
        return i * (1 + self.lam * vds)

    def ids_g(self, vgs, vds):
        """Channel current and its slopes (gm = dI/dVgs, gds = dI/dVds), N-channel convention."""
        if vds < 0:                       # source and drain swap roles
            i, gm, gds = self.ids_g(vgs - vds, -vds)
            return -i, -gm, gm + gds
        z = (vgs - self.vt) / SUB_S
        vov = softplus(vgs - self.vt, SUB_S)
        dvov = 1.0 / (1.0 + math.exp(-z)) if z > -40 else 0.0          # d vov / d vgs
        den = 1 + self.theta * vov
        kp = self.kp / den
        dkp = -self.kp * self.theta / (den * den)                       # d kp / d vov
        lam = 1 + self.lam * vds
        if vds < vov:
            core = vov * vds - 0.5 * vds * vds
            i0 = kp * core
            di_dvov = dkp * core + kp * vds
            di_dvds = kp * (vov - vds)
        else:
            core = 0.5 * vov * vov
            i0 = kp * core
            di_dvov = dkp * core + kp * vov
            di_dvds = 0.0
        return i0 * lam, di_dvov * dvov * lam, di_dvds * lam + i0 * self.lam

    def _bd(self, vf):
        e = sexp(vf / self.bd_nvt)
        return self.P.bd_is * (e - 1.0) + GMIN * vf, self.P.bd_is * e / self.bd_nvt + GMIN

    def _cap_nodes(self):
        """(capacitor, anode node, cathode node) — anode/cathode as for its junction."""
        _g, d, s = self.nodes
        g = self.internal[1]
        if self.pol > 0:
            return ((self.cgs, g, s), (self.cgd, g, d), (self.cds, s, d))
        return ((self.cgs, g, s), (self.cgd, d, g), (self.cds, d, s))

    def stamp(self, S, x, ctx):
        gx, d, s = self.nodes
        dp, g = self.internal
        S.g(gx, g, 1.0 / self.rg)
        S.g(gx, s, G_GATE)          # a 1 GΩ leak: a gate left unconnected settles at the source voltage (off)
        if self.blown:
            S.g(d, s, 1 / R_OFF)
            S.g(g, s, 1 / R_OFF)
            S.g(d, dp, 1.0)
            return
        p = self.pol
        S.g(d, dp, 1.0 / self.rser)
        vg, vdp, vs = v(x, g), v(x, dp), v(x, s)
        vgs, vds = p * (vg - vs), p * (vdp - vs)
        # limit how far one Newton step may move the gate and drain voltages
        lv = [vgs, vds]
        for i, (now, last, lim) in enumerate(((vgs, self.vgs_last, 1.0), (vds, self.vds_last, 4.0))):
            if abs(now - last) > lim:
                lv[i] = last + math.copysign(lim, now - last)
                ctx.limited = True
        self.vgs_last, self.vds_last = lv
        V0 = [vs + p * lv[0], vs + p * lv[1], vs]
        i, gm, gds = self.ids_g(lv[0], lv[1])
        # currents into [gate, drain, source]: the drain takes p·i; slopes against [vg, vd, vs]
        jd = [gm, gds, -(gm + gds)]
        S.nonlinear([g, dp, s], [0.0, p * i, -p * i], [[0.0, 0.0, 0.0], jd, [-jd[0], -jd[1], -jd[2]]], V0)
        # body diode: source → drain for N-channel, drain → source for P-channel
        an, ca = (s, dp) if p > 0 else (dp, s)
        vf = v(x, an) - v(x, ca)
        vl = pnjlim(vf, self.vbd_last, self.bd_nvt, self.bd_vcrit)
        if abs(vl - vf) > 1e-9:
            ctx.limited = True
        self.vbd_last = vl
        i, gd = self._bd(vl)
        S.g(an, ca, gd)
        S.i(an, ca, i - gd * vl)
        for cap, a, c in self._cap_nodes():
            cap.stamp(S, a, c, v(x, a) - v(x, c), ctx)

    def accept(self, x, ctx):
        gx, d, s = self.nodes
        dp, g = self.internal
        p = self.pol
        vgx, vg, vd, vs, vdp = v(x, gx), v(x, g), v(x, d), v(x, s), v(x, dp)
        ip = [(vgx - vg) / self.rg + G_GATE * (vgx - vs), (vd - vdp) / self.rser, 0.0]
        if self.blown:
            ip[1] = (vd - vs) / R_OFF
            for cap, a, c in self._cap_nodes():
                cap.settle(v(x, a) - v(x, c))
        else:
            self.vgs_acc, self.vds_acc = p * (vg - vs), p * (vdp - vs)
            an, ca = (s, dp) if p > 0 else (dp, s)
            self.vbd_acc = v(x, an) - v(x, ca)
            # the gate pin's current goes through rg and the channel's through rser; Cgd and Cds connect to
            # the drain pin itself, so their currents add to it
            for cap, a, c in self._cap_nodes():
                ic = cap.accept(v(x, a) - v(x, c), ctx)
                if a == d:
                    ip[1] += ic
                elif c == d:
                    ip[1] -= ic
        ip[2] = -(ip[0] + ip[1])
        self.id = ip[1]
        self.i_pins = ip
        self.power = vgx * ip[0] + vd * ip[1] + vs * ip[2]
        if self.blown:
            return
        vmax = self.P.vdss
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

    def after_dc(self):
        """After the DC answer: the capacitors start charged to the voltages they're at."""
        for cap, _a, _c in self._cap_nodes():
            cap.i_prev = 0.0


# ============================================================================================== op-amp
class OpAmpData:
    """One op-amp type's datasheet figures (typical values)."""

    def __init__(self, a0, gbw, sr, ib, rin, iq, hd_hi, hd_lo, r_src, r_sink, i_src, i_sink, vs_max):
        self.a0, self.gbw, self.sr = a0, gbw, sr            # open-loop gain, gain-bandwidth (Hz), slew rate (V/s)
        self.ib, self.rin = ib, rin          # input bias current (A, + = into the pins) and input resistance (Ω)
        self.iq = iq                         # supply current with no load (A)
        self.hd_hi, self.hd_lo = hd_hi, hd_lo      # how close the output gets to V+ / V− with a light load (V)
        self.r_src, self.r_sink = r_src, r_sink    # how much closer it falls short per amp of load current (Ω)
        self.i_src, self.i_sink = i_src, i_sink    # short-circuit output current, sourcing / sinking (A)
        self.vs_max = vs_max                 # maximum total supply voltage (V)


OPAMPS = {
    # 741: ±14 V into 10 kΩ and ±13 V into 2 kΩ on ±15 V; 80 nA bias current; 2 MΩ input; 1.7 mA supply
    "741": OpAmpData(2e5, 1e6, 0.5e6, 80e-9, 2e6, 1.7e-3, 0.75, 0.75, 200.0, 200.0, 0.025, 0.025, 36.0),
    # LM358 (one of the two): output reaches 0 V but only V+ − 1.5 V; PNP inputs, so 20 nA flows OUT of them
    "LM358": OpAmpData(1e5, 0.7e6, 0.3e6, -20e-9, 10e6, 0.35e-3, 1.4, 0.005, 50.0, 100.0, 0.04, 0.02, 32.0),
    # TL071: JFET inputs (30 pA); ±13.5 V into 10 kΩ, ±12 V into 2 kΩ on ±15 V
    "TL071": OpAmpData(2e5, 3e6, 13e6, 30e-12, 1e12, 1.4e-3, 1.05, 1.05, 320.0, 320.0, 0.04, 0.04, 36.0),
    # a typical CMOS rail-to-rail op-amp
    "Rail-to-rail": OpAmpData(1e5, 10e6, 10e6, 1e-12, 1e13, 1e-3, 0.01, 0.01, 25.0, 25.0, 0.05, 0.05, 40.0),
}


class OpAmp(Device):
    """Macro-model fitted to each type's datasheet: a transconductance input stage with one dominant pole
    (open-loop gain, gain-bandwidth and slew rate as the real chip), input bias current and input resistance,
    then an output stage that stops short of the supply rails — further the more current it delivers — and
    limits its current. The supply pins carry the chip's own supply current plus whatever the output delivers,
    as in the real chip. Pins: −, +, out, V+, V−."""
    n_internal = 1
    nonlinear = True
    GM = 1e-3

    def update_params(self):
        self.D = D = OPAMPS.get(self.prop("model"), OPAMPS["741"])
        self.C1 = self.GM / (2 * math.pi * D.gbw)
        self.Imax = D.sr * self.C1
        self.G1 = self.GM / D.a0
        self.vm_prev = 0.0
        self.auto_pos = self.auto_neg = False       # set by the engine when V+ / V− are left unconnected
        self.vlogic = 9.0
        self._dc = False

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
        D = self.D
        if self._dc:            # slew rate only limits how fast things change: not in a steady DC answer
            i1 = self.GM * (vpos - vneg)
        else:
            i1 = self.Imax * math.tanh(self.GM * (vpos - vneg) / self.Imax)
        u = (vp + vn) / 2 + vm
        lo, hi = vn + D.hd_lo, vp - D.hd_hi
        if hi < lo:
            hi = lo = (vp + vn) / 2
        # once the output is saturated, hold the internal node just past it (as the real chip's internal
        # stages saturate too) — this also keeps the solver from wandering
        iclamp = 1e-3 * (softplus(u - (hi + 0.3), 0.05) - softplus((lo - 0.3) - u, 0.05))
        vt = lo + softplus(u - lo, 0.05) - softplus(u - hi, 0.05)
        # sourcing current to the load (vt > vout) or sinking it, blended smoothly so the solver sees no kink
        w = 0.5 * (1 + math.tanh((vt - vout) / 0.01))
        isrc = D.i_src * math.tanh((vt - vout) / D.r_src / D.i_src)
        isnk = D.i_sink * math.tanh((vt - vout) / D.r_sink / D.i_sink)
        iout = w * isrc + (1 - w) * isnk
        powered = math.tanh(max(vp - vn, 0.0))         # the chip only draws its supply current when powered
        iq = D.iq * powered
        ib = D.ib * powered
        i_in = (vneg - vpos) / D.rin
        i_neg = ib + GMIN * vneg + i_in
        i_pos = ib + GMIN * vpos - i_in
        # what flows out of the output comes in at V+ (sourcing) or leaves at V− (sinking); the input bias
        # currents return through V− (or come from V+ for a PNP input stage, which has ib < 0)
        pos_part = 0.5 * (iout + math.sqrt(iout * iout + 1e-12))      # smooth max(iout, 0)
        i_vp = iq + pos_part - (min(ib, 0.0) * 2)
        i_vn = -iq + (iout - pos_part) - (max(ib, 0.0) * 2)
        return [i_neg, i_pos, -iout, i_vp, i_vn, self.G1 * vm + iclamp - i1]

    def stamp(self, S, x, ctx):
        neg, pos, out, vpn, vnn = self.nodes
        m = self.internal[0]
        if self.blown:
            S.g(neg, pos, GMIN)
            S.g(out, -1, GMIN)
            S.g(m, -1, 1.0)
            return
        if not ctx.dc:      # the dominant-pole capacitor (always backward Euler: no ringing)
            G = self.C1 / ctx.h
            S.g(m, -1, G)
            S.i(-1, m, G * self.vm_prev)
        self._dc = ctx.dc
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
        self._dc = ctx.dc
        if self.blown:
            self.i_pins = [0.0] * 5
            self.vout = V[2]
            return
        I = self._f(V)
        self.vm_prev = V[5]
        self.i_pins = [I[0], I[1], I[2], 0.0 if self.auto_pos else I[3], 0.0 if self.auto_neg else I[4]]
        self.vout = V[2]
        vp, vn = self.rails(x)
        self.power = sum(V[k] * self.i_pins[k] for k in range(5))
        over = (vp - vn) > self.D.vs_max
        self.warn = "over" if over else None
        if self._overload(over, ctx.h, 0.05, (vp - vn) > 1.3 * self.D.vs_max):
            self.blown = True
            self.event = (f"{self.comp.ref} was destroyed — {vp - vn:.0f} V across its supply pins is more than "
                          f"a {self.prop('model')} can take ({self.D.vs_max:.0f} V maximum).")


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
    pin_groups = ((0, 1), (2, 3, 4))      # the coil and the contacts are separate circuits
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


# ------------------------------------------------------------------------------------------- optoisolator
# type: (typical current transfer ratio CTR = Ic / If, max LED current, max collector current, max Vce)
OPTOS = {
    "PC817": (1.3, 0.05, 0.05, 35.0),
    "4N25": (0.5, 0.06, 0.05, 30.0),
    "4N35": (1.0, 0.06, 0.1, 30.0),
    "TLP521": (1.0, 0.05, 0.05, 55.0),
    "6N139": (5.0, 0.02, 0.06, 18.0),      # Darlington output: very high gain, lower voltage
}
OPTO_IS, OPTO_N, OPTO_RS = 1.7e-12, 2.0, 2.0     # infrared LED: about 1.2 V at 20 mA


class Optocoupler(BJT):
    """Optoisolator (optocoupler): an infrared LED (A, K) shining on an NPN phototransistor (C, E) in one
    package, with no electrical connection between the two sides. The light makes a base current inside the
    transistor, so the collector current is about CTR × the LED current until the transistor saturates.
    Internal nodes: [0] the LED junction (behind its series resistance), [1] the transistor's base."""
    n_internal = 2
    pin_groups = ((0, 1), (2, 3))         # A–K and C–E are separate circuits

    def update_params(self):
        ctr, self.if_max, self.icmax, self.vceo = OPTOS.get(self.prop("model"), OPTOS["PC817"])
        self.pol, self.Is, self.bf, self.br = 1, 1e-14, 400.0, 5.0
        self.k = ctr / self.bf                     # base current per amp of LED current
        self.pmax = 0.15
        self.vcrit = VT * math.log(VT / (math.sqrt(2) * self.Is))
        self.nvt = OPTO_N * VT
        self.vcrit_led = self.nvt * math.log(self.nvt / (math.sqrt(2) * OPTO_IS))
        self.vbe_last = self.vbc_last = self.vbe_acc = self.vbc_acc = 0.0
        self.vd_last = self.vd_acc = 0.0
        self.ic = self.ib = self.i_led = 0.0

    def _bce(self):
        return (self.internal[1], self.nodes[2], self.nodes[3])

    def begin_iter(self):
        super().begin_iter()
        self.vd_last = self.vd_acc

    @staticmethod
    def led(vd):
        e = sexp(vd / (OPTO_N * VT))
        return OPTO_IS * (e - 1.0) + GMIN * vd, OPTO_IS * e / (OPTO_N * VT) + GMIN

    def stamp(self, S, x, ctx):
        a, k_, c, e = self.nodes
        j, b = self.internal
        if self.blown:
            S.g(a, k_, 1 / R_OFF)
            S.g(a, j, 1.0)
            S.g(c, e, 1 / R_OFF)
            S.g(b, e, 1.0)
            return
        # the infrared LED, with its series resistance
        S.g(a, j, 1.0 / OPTO_RS)
        vd = v(x, j) - v(x, k_)
        vl = pnjlim(vd, self.vd_last, self.nvt, self.vcrit_led)
        if abs(vl - vd) > 1e-9:
            ctx.limited = True
        self.vd_last = vl
        i, g = self.led(vl)
        S.g(j, k_, g)
        S.i(j, k_, i - g * vl)
        # its light: a current from the collector into the base, k × the LED current
        iph = self.k * max(0.0, i)
        gph = self.k * g if i > 0 else 0.0
        vk = v(x, k_)
        S.nonlinear([c, b, j, k_], [iph, -iph, 0.0, 0.0],
                    [[0, 0, gph, -gph], [0, 0, -gph, gph], [0, 0, 0, 0], [0, 0, 0, 0]],
                    [v(x, c), v(x, b), vk + vl, vk])
        # the phototransistor
        super().stamp(S, x, ctx)

    def accept(self, x, ctx):
        a, k_, c, e = self.nodes
        j, b = self.internal
        vb, vc, ve = v(x, b), v(x, c), v(x, e)
        if self.blown:
            self.i_led = (v(x, a) - v(x, k_)) / R_OFF
            self.ic = self.ib = 0.0
            iph = 0.0
        else:
            vd = v(x, j) - v(x, k_)
            self.i_led, _g = self.led(vd)
            self.vd_last = self.vd_acc = vd
            ic, ib, _d1, _d2 = self.currents(vb - ve, vb - vc)
            self.ic, self.ib = ic, ib
            self.vbe_acc, self.vbc_acc = vb - ve, vb - vc
            iph = self.k * max(0.0, self.i_led)
        i_c = self.ic + iph                      # what flows in at the collector pin
        self.i_pins = [self.i_led, -self.i_led, i_c, -i_c]
        self.vd = v(x, a) - v(x, k_)
        self.power = self.vd * self.i_led + i_c * (vc - ve)
        self.current = self.i_led
        if self.blown:
            return
        ref, model = self.comp.ref, self.prop("model")
        if abs(vc - ve) > 1.5 * self.vceo:
            self.blown = True
            self.event = spike_message(ref, abs(vc - ve), self.vceo)
            return
        led_bad = self.i_led > self.if_max
        out_bad = abs(i_c) > self.icmax
        self.warn = "over" if (led_bad or out_bad) else None
        if self._overload(led_bad or out_bad, ctx.h, 0.05,
                          self.i_led > 3 * self.if_max or abs(i_c) > 4 * self.icmax):
            self.blown = True
            if led_bad:
                self.event = (f"{ref} popped! {self.i_led * 1000:.0f} mA is too much for the LED inside a {model} "
                              f"(max {self.if_max * 1000:.0f} mA). Add a resistor in series with pins A–K.")
            else:
                self.event = (f"{ref} burnt out — {abs(i_c) * 1000:.0f} mA through its output is too much for a "
                              f"{model} (max {self.icmax * 1000:.0f} mA). Add a resistor to the load.")

    def glow(self):
        """0..1: how hard the (invisible, infrared) LED inside is shining."""
        if self.blown:
            return 0.0
        return max(0.0, min(1.0, (self.i_led - 1e-4) / 0.01)) ** 0.6


FACTORY = {
    "inductor": Inductor, "relay": Relay, "phototransistor": PhotoTransistor, "optocoupler": Optocoupler,
    "nmos": MOSFET, "pmos": MOSFET, "opamp": OpAmp, "timer555": Timer555,
    "not": Gate, "and": Gate, "or": Gate, "nand": Gate, "nor": Gate, "xor": Gate, "schmitt_not": Gate,
    "dff": DFF, "counter4017": Counter4017, "decoder4511": Decoder4511,
    "sevenseg": SevenSeg, "signal_gen": SignalGen, "scope_probe": Probe, "logic_probe": Probe,
}
