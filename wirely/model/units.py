"""Reading and writing component values the way people type them: 10k, 4k7, 2M2, 100n, 4.7µF, 0.5 …

parse("10k")  -> 10000.0      parse("4k7") -> 4700.0      parse("100nF", "F") -> 1e-07
fmt(4700, "Ω") -> "4.7kΩ"     fmt(1e-07, "F") -> "100nF"
"""
from __future__ import annotations

import math
import re

PREFIXES = {
    "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "μ": 1e-6, "m": 1e-3,
    "": 1.0, "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9,
}
# symbols people use for the unit itself; they are ignored when parsing
UNIT_WORDS = {
    "Ω": ["Ω", "ω", "ohms", "ohm", "R", "r"],
    "F": ["F", "f"], "V": ["V", "v"], "A": ["A", "a"], "W": ["W", "w"], "Hz": ["Hz", "hz", "HZ"],
    "s": ["s", "S", "sec"], "%": ["%"], "°C": ["°C", "C", "c"], "H": ["H", "h"], "lux": ["lux", "lx"],
}

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"




def parse(text, unit: str = "") -> float:
    """Turn what someone typed into a number. Raises ValueError if it makes no sense."""
    if isinstance(text, (int, float)):
        return float(text)
    s = str(text).strip().replace(" ", "").replace(",", ".")
    if not s:
        raise ValueError("Please type a value")
    if s.lower().endswith("meg"):           # SPICE style 1meg
        s = s[:-3] + "M"
    # strip a trailing unit word (longest first), e.g. "10kΩ", "4.7uF", "9V"
    for word in sorted(UNIT_WORDS.get(unit, []), key=len, reverse=True):
        if s.endswith(word) and len(s) > len(word):
            rest = s[: -len(word)]
            # "4R7"/"4k7" handled below, so only strip when what is left still parses as a value
            if re.fullmatch(_NUM + r"[pnuµμmkKMG]?", rest) or re.fullmatch(r"\d+[pnuµμmkKMG]\d+", rest):
                s = rest
                break
    # 4k7, 2M2, 4R7, 4n7 style (the letter acts as the decimal point)
    m = re.fullmatch(r"(\d+)([pnuµμmkKMGRr])(\d+)", s)
    if m:
        whole, p, frac = m.groups()
        mult = 1.0 if p in "Rr" else PREFIXES[p]
        return float(f"{whole}.{frac}") * mult
    m = re.fullmatch(r"(" + _NUM + r")([pnuµμmkKMG]?)", s)
    if not m:
        raise ValueError(f"'{text}' isn't a value I understand (try e.g. 10k, 4k7, 100n)")
    return float(m.group(1)) * PREFIXES[m.group(2)]


def fmt(value: float, unit: str = "", digits: int = 3) -> str:
    """Neat engineering text for a number: 4700 -> 4.7k, 1e-7 -> 100n (plus the unit)."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "–"
    if unit in ("%", "°C", "lux"):
        return f"{_trim(value, digits)}{unit}"
    if value == 0:
        return f"0{unit}"
    a = abs(value)
    for p, mult in (("G", 1e9), ("M", 1e6), ("k", 1e3), ("", 1.0), ("m", 1e-3), ("µ", 1e-6), ("n", 1e-9), ("p", 1e-12)):
        if a >= mult * 0.9995:
            return f"{_trim(value / mult, digits)}{p}{unit}"
    return f"{value:.3g}{unit}"


def _trim(x: float, digits: int) -> str:
    s = f"{x:.{digits}g}"
    if "e" in s:
        s = f"{x:.{digits}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s
