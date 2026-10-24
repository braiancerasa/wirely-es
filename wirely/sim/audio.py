"""Sound for the simulation (no Qt): work out what each buzzer, speaker, motor and relay should sound like,
and synthesise it as audio samples.

A loudspeaker plays the *simulated* signal: we measure the frequency, size and shape of the voltage across it
(so a 555 at 440 Hz sounds at 440 Hz even if the simulation has to run slower than real time).
"""
from __future__ import annotations

import math
from collections import deque

import numpy as np

RATE = 44100
BUZZER_HZ = 2700.0


def frequency(ts, vs):
    """Frequency from rising crossings of the mid level (median of the latest cycles), or None."""
    if len(vs) < 4:
        return None
    lo, hi = min(vs), max(vs)
    if hi - lo < 0.05:
        return None
    mid = (lo + hi) / 2
    hyst = (hi - lo) * 0.1
    ups = []
    armed = vs[0] < mid - hyst
    for i in range(1, len(vs)):
        if armed and vs[i - 1] < mid <= vs[i]:
            f = (mid - vs[i - 1]) / (vs[i] - vs[i - 1]) if vs[i] != vs[i - 1] else 0
            ups.append(ts[i - 1] + f * (ts[i] - ts[i - 1]))
            armed = False
        elif vs[i] < mid - hyst:
            armed = True
    if len(ups) < 3:
        return None
    recent = ups[-6:]
    gaps = sorted(b - a for a, b in zip(recent, recent[1:]))
    period = gaps[len(gaps) // 2]
    return 1.0 / period if period > 0 else None


def squareness(vs):
    """0 for a smooth wave, 1 for a square wave (how much of the time it sits near its top or bottom)."""
    if len(vs) < 4:
        return 0.0
    lo, hi = min(vs), max(vs)
    if hi - lo < 1e-9:
        return 0.0
    edge = 0.1 * (hi - lo)
    near = sum(1 for x in vs if x < lo + edge or x > hi - edge)
    return max(0.0, min(1.0, (near / len(vs) - 0.4) / 0.5))


class SpeakerWatch:
    """Keeps the recent voltage across one loudspeaker (in simulated time)."""

    def __init__(self, window=0.25):
        self.window = window
        self.t = deque()
        self.v = deque()

    def add(self, t, v):
        self.t.append(t)
        self.v.append(v)
        while self.t and self.t[0] < t - self.window:
            self.t.popleft()
            self.v.popleft()

    def voice(self, R):
        """(frequency, loudness 0..1, squareness) or None when there's nothing to hear."""
        ts, vs = list(self.t), list(self.v)
        f = frequency(ts, vs)
        if not f or not (20.0 <= f <= 16000.0):
            return None
        lo, hi = min(vs), max(vs)
        amp = (hi - lo) / 2
        power = amp * amp / 2 / max(R, 0.1)
        loud = max(0.0, min(1.0, math.sqrt(power / 0.25)))       # 0.25 W ≈ full volume
        return f, loud, squareness(vs)


class Voice:
    def __init__(self):
        self.freq = 440.0
        self.amp = 0.0
        self.target = 0.0
        self.shape = 0.0           # 0 sine … 1 square … 2 sawtooth (motor hum)
        self.phase = 0.0


class Synth:
    """Mixes all the voices into 16-bit mono samples, gliding volume changes so nothing clicks."""

    def __init__(self, master=0.5):
        self.voices: dict[str, Voice] = {}
        self.master = master
        self._clicks = []          # remaining samples of relay click bursts
        self._rng = np.random.default_rng(1)

    def set(self, key, freq, loud, shape=0.0):
        v = self.voices.setdefault(key, Voice())
        v.freq = float(freq)
        v.target = float(loud)
        v.shape = float(shape)

    def silence_all(self):
        for v in self.voices.values():
            v.target = 0.0

    def click(self):
        self._clicks.append(int(0.012 * RATE))

    def render(self, n: int) -> np.ndarray:
        out = np.zeros(n)
        k = np.arange(n)
        for key in list(self.voices):
            v = self.voices[key]
            if v.amp < 1e-4 and v.target < 1e-4:
                if v.target == 0:
                    del self.voices[key]
                continue
            amp = v.amp + (v.target - v.amp) * np.minimum(1.0, (k + 1) / (0.02 * RATE))
            ph = v.phase + 2 * np.pi * v.freq * (k + 1) / RATE
            if v.shape >= 1.5:          # sawtooth-ish hum
                wave = 2 * ((ph / (2 * np.pi)) % 1.0) - 1
                wave *= 0.6
            else:
                s = np.sin(ph)
                sq = np.sign(s) * 0.6     # squares sound much louder: tame them
                wave = (1 - v.shape) * s + v.shape * sq
            out += amp * wave
            v.amp = float(amp[-1])
            v.phase = float(ph[-1] % (2 * np.pi))
        if self._clicks:
            for i, left in enumerate(self._clicks):
                m = min(left, n)
                burst = self._rng.uniform(-1, 1, m) * np.exp(-np.arange(m) / (0.003 * RATE)) * 0.8
                out[:m] += burst
                self._clicks[i] = left - m
            self._clicks = [c for c in self._clicks if c > 0]
        out = np.tanh(out * self.master)          # soft limit when lots play at once
        return (out * 32000).astype(np.int16)


def update_from_sim(synth: Synth, sim, watches: dict, motor_hum=True):
    """Set the synth's voices from the running simulation (call once per frame)."""
    seen = set()
    for d in sim.devices:
        k = d.comp.kind
        key = d.cid
        if k == "buzzer" and not d.blown:
            lvl = d.level()
            if lvl > 0:
                synth.set(key, BUZZER_HZ, 0.35 * lvl, 1.0)
                seen.add(key)
        elif k == "speaker" and not d.blown:
            w = watches.get(key)
            voice = w.voice(d.R) if w else None
            if voice:
                f, loud, sq = voice
                synth.set(key, f, 0.8 * loud, sq)
                seen.add(key)
        elif k == "motor" and motor_hum and abs(getattr(d, "rpm", 0.0)) > 60:
            f = abs(d.rpm) / 60 * 2                # commutator buzz: two pulses per turn
            synth.set(key, max(30.0, f), 0.06 * min(1.0, abs(d.speed)), 2.0)
            seen.add(key)
        elif k == "relay":
            last = getattr(d, "_clicks_heard", 0)
            if d.clicks > last:
                for _ in range(min(3, d.clicks - last)):
                    synth.click()
                d._clicks_heard = d.clicks
    for key, v in synth.voices.items():
        if key not in seen:
            v.target = 0.0
