"""Wirely's device models written out as ngspice subcircuits, so tests can run the very same circuit in
ngspice and compare. Each is built from the same fitted parameters Wirely uses."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wirely.sim import chips as CH  # noqa: E402


def _ids(vgs, vds, P):
    """ngspice expression for the N-channel channel current with vds ≥ 0 (same formula as MOSFET.ids)."""
    s = CH.SUB_S
    vov = f"({s}*ln(1+exp(({vgs}-({P.vto}))/{s})))"
    kp = f"({P.kp}/(1+{P.theta}*{vov}))"
    lin = f"{kp}*({vov}*{vds}-0.5*{vds}*{vds})"
    sat = f"0.5*{kp}*{vov}*{vov}"
    return f"(({vds}<{vov}) ? ({lin}) : ({sat}))*(1+{P.lam}*{vds})"


def _qcap(a, c, C0, M):
    """Charge expression matching QCap (junction-style, levelling off past FC·VJ forward)."""
    VJ, FC = CH.CAP_VJ, CH.CAP_FC
    lim = FC * VJ
    clim = C0 * (1 - lim / VJ) ** -M
    vf = f"v({a},{c})"
    return (f"Q='{C0}*{VJ}/{1 - M}*(1-pow(1-min({vf},{lim})/{VJ},{1 - M}))"
            f" + {clim}*max({vf}-{lim},0)'")


def mosfet_subckt(model, pol, name=None):
    """.subckt <name> d g s for a Wirely MOSFET type (pol = +1 N-channel, −1 P-channel)."""
    P = CH.MOSFETS[model]
    name = name or f"W{model}"
    p = pol
    vgs, vds = f"({p}*v(gi,s))", f"({p}*v(dp,s))"
    fwd = _ids(vgs, vds, P)
    # source and drain swap roles when vds < 0
    rev = "-(" + _ids(f"({vgs}-{vds})", f"(-{vds})", P) + ")"
    chan = f"{p}*(({vds}>=0) ? ({fwd}) : ({rev}))"
    an, ca = ("s", "dp") if p > 0 else ("dp", "s")
    cgd = ("gi", "d") if p > 0 else ("d", "gi")
    cds = ("s", "d") if p > 0 else ("d", "s")
    lines = [f".subckt {name} d g s",
             f"RG g gi {P.rg}",
             "RLEAK g s 1G",
             f"RD d dp {P.rser}",
             f"BCH dp s I={chan}",
             f"DBODY {an} {ca} DB{name}",
             f".model DB{name} D(IS={P.bd_is:.6e} N={P.bd_n})",
             f"CGS gi s {P.cgs:.6e}",
             f"CGD {cgd[0]} {cgd[1]} {_qcap(cgd[0], cgd[1], P.cgd0, CH.CAP_M)}",
             f"CDS {cds[0]} {cds[1]} {_qcap(cds[0], cds[1], P.cds0, CH.CAP_M)}",
             f".ends {name}"]
    return "\n".join(lines) + "\n"
