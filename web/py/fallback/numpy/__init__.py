"""A very small pure-Python stand-in for the bits of numpy the Wirely solver uses.

The browser version normally loads the real numpy. This is only a fallback, used if numpy can't be loaded
(for example a school network that blocks the download), so the app still works, just more slowly.
It covers: zeros, array, eye, linspace, abs, all, any, max, isfinite, linalg.solve / lstsq, and 1-D / 2-D
arrays with +, -, *, comparisons, slicing and [i, j] indexing.
"""
from __future__ import annotations

import builtins as _b
import math as _m

pi = _m.pi
inf = float("inf")
float64 = float
int16 = int
__version__ = "0-lite"


class ndarray(list):
    """1-D: a list of floats. 2-D: a list of rows (each an ndarray)."""

    @property
    def ndim(self):
        return 2 if self and isinstance(list.__getitem__(self, 0), list) else 1

    @property
    def shape(self):
        if self.ndim == 2:
            return (len(self), len(list.__getitem__(self, 0)))
        return (len(self),)

    @property
    def size(self):
        s = self.shape
        return s[0] * (s[1] if len(s) > 1 else 1)

    def __getitem__(self, k):
        if isinstance(k, tuple):
            i, j = k
            return list.__getitem__(list.__getitem__(self, i), j)
        r = list.__getitem__(self, k)
        if isinstance(k, slice):
            return ndarray(r)
        return r

    def __setitem__(self, k, v):
        if isinstance(k, tuple):
            i, j = k
            list.__getitem__(self, i)[j] = v
        else:
            list.__setitem__(self, k, v)

    def copy(self):
        if self.ndim == 2:
            return ndarray(ndarray(r) for r in self)
        return ndarray(self)

    def tolist(self):
        if self.ndim == 2:
            return [list(r) for r in self]
        return list(self)

    # ---- elementwise maths
    def _op(self, o, f):
        if isinstance(o, list):
            if self.ndim == 2:
                return ndarray(ndarray(f(a, b) for a, b in zip(ra, rb)) for ra, rb in zip(self, o))
            return ndarray(f(a, b) for a, b in zip(self, o))
        if self.ndim == 2:
            return ndarray(ndarray(f(a, o) for a in r) for r in self)
        return ndarray(f(a, o) for a in self)

    def __add__(self, o):
        return self._op(o, lambda a, b: a + b)

    __radd__ = __add__

    def __sub__(self, o):
        return self._op(o, lambda a, b: a - b)

    def __rsub__(self, o):
        return self._op(o, lambda a, b: b - a)

    def __mul__(self, o):
        return self._op(o, lambda a, b: a * b)

    __rmul__ = __mul__

    def __truediv__(self, o):
        return self._op(o, lambda a, b: a / b)

    def __neg__(self):
        return self._op(0.0, lambda a, b: -a)

    def __abs__(self):
        return abs_(self)

    def __le__(self, o):
        return self._op(o, lambda a, b: a <= b)

    def __lt__(self, o):
        return self._op(o, lambda a, b: a < b)

    def __ge__(self, o):
        return self._op(o, lambda a, b: a >= b)

    def __gt__(self, o):
        return self._op(o, lambda a, b: a > b)

    def __iadd__(self, o):
        return self.__add__(o)

    def __isub__(self, o):
        return self.__sub__(o)

    def sum(self):
        return sum_(self)

    def max(self):
        return max_(self)

    def astype(self, t):
        return ndarray(t(v) for v in self)


def _flat(a):
    if isinstance(a, list) and a and isinstance(a[0], list):
        return [v for r in a for v in r]
    if isinstance(a, list):
        return list(a)
    return [a]


def zeros(shape, dtype=float):
    if isinstance(shape, tuple):
        if len(shape) == 2:
            return ndarray(ndarray([0.0] * shape[1]) for _ in range(shape[0]))
        shape = shape[0]
    return ndarray([0.0] * int(shape))


def ones(n):
    return ndarray([1.0] * int(n))


def eye(n):
    out = zeros((n, n))
    for i in range(n):
        out[i][i] = 1.0
    return out


def array(a, dtype=None):
    if isinstance(a, list) and a and isinstance(a[0], list):
        return ndarray(ndarray(float(v) for v in r) for r in a)
    return ndarray(float(v) for v in a)


asarray = array


def arange(n):
    return ndarray(float(i) for i in range(int(n)))


def linspace(a, b, n):
    if n == 1:
        return ndarray([float(a)])
    return ndarray(a + (b - a) * i / (n - 1) for i in range(n))


def abs_(a):
    if isinstance(a, list):
        if a and isinstance(a[0], list):
            return ndarray(ndarray(_b.abs(v) for v in r) for r in a)
        return ndarray(_b.abs(v) for v in a)
    return _b.abs(a)


def all(a):         # noqa: A001 - same name as numpy's
    return _b.all(_flat(a))


def any(a):         # noqa: A001
    return _b.any(_flat(a))


def max_(a):
    return _b.max(_flat(a))


def sum_(a):
    return _b.sum(_flat(a))


def minimum(a, b):
    if isinstance(a, list):
        return ndarray(_b.min(x, b) for x in a)
    return _b.min(a, b)


def isfinite(a):
    if isinstance(a, list):
        return ndarray(_m.isfinite(v) for v in _flat(a))
    return _m.isfinite(a)


def sin(a):
    return ndarray(_m.sin(v) for v in a) if isinstance(a, list) else _m.sin(a)


def sign(a):
    f = lambda v: (v > 0) - (v < 0)       # noqa: E731
    return ndarray(float(f(v)) for v in a) if isinstance(a, list) else float(f(a))


abs = abs_          # noqa: A001
max = max_          # noqa: A001
sum = sum_          # noqa: A001
absolute = abs_


class _LinAlg:
    class LinAlgError(ValueError):
        pass

    @staticmethod
    def solve(A, b):
        n = len(A)
        M = [list(map(float, row)) + [float(b[i])] for i, row in enumerate(A)]
        scale = 0.0
        for row in M:
            for v in row[:n]:
                if v < 0:
                    v = -v
                if v > scale:
                    scale = v
        tiny = (scale or 1.0) * 1e-300
        for c in range(n):
            # partial pivoting
            p, best = c, -1.0
            for r in range(c, n):
                v = M[r][c]
                if v < 0:
                    v = -v
                if v > best:
                    p, best = r, v
            if best <= tiny:
                raise _LinAlg.LinAlgError("Singular matrix")
            if p != c:
                M[c], M[p] = M[p], M[c]
            pr = M[c]
            inv = 1.0 / pr[c]
            for r in range(c + 1, n):
                row = M[r]
                f = row[c]
                if f != 0.0:
                    f *= inv
                    for k in range(c, n + 1):
                        row[k] -= f * pr[k]
        x = [0.0] * n
        for i in range(n - 1, -1, -1):
            row = M[i]
            s = row[n]
            for k in range(i + 1, n):
                s -= row[k] * x[k]
            x[i] = s / row[i]
        return ndarray(x)

    @staticmethod
    def lstsq(A, b, rcond=None):
        """Least-squares answer via the regularised normal equations (good enough for the solver's fallback)."""
        n = len(A)
        m = len(A[0]) if n else 0
        AtA = [[0.0] * m for _ in range(m)]
        Atb = [0.0] * m
        for r in range(n):
            row = A[r]
            br = b[r]
            for i in range(m):
                ai = row[i]
                if ai != 0.0:
                    Atb[i] += ai * br
                    Ai = AtA[i]
                    for j in range(m):
                        Ai[j] += ai * row[j]
        tr = _b.sum(AtA[i][i] for i in range(m)) or 1.0
        lam = tr * 1e-14 / (m or 1)
        for i in range(m):
            AtA[i][i] += lam
        try:
            x = _LinAlg.solve(AtA, Atb)
        except _LinAlg.LinAlgError:
            x = ndarray([0.0] * m)
        return x, None, None, None


linalg = _LinAlg()


class _Random:
    class _Gen:
        def __init__(self, seed=None):
            import random
            self.r = random.Random(seed)

        def uniform(self, a, b, n=None):
            if n is None:
                return self.r.uniform(a, b)
            return ndarray(self.r.uniform(a, b) for _ in range(n))

    def default_rng(self, seed=None):
        return self._Gen(seed)


random = _Random()


def isscalar(x):
    return isinstance(x, (int, float, complex, bool))


bool_ = bool


def tanh(a):
    return ndarray(_m.tanh(v) for v in a) if isinstance(a, list) else _m.tanh(a)


def exp(a):
    return ndarray(_m.exp(v) for v in a) if isinstance(a, list) else _m.exp(a)
