"""Plays the simulation's sounds through the computer's speakers.

Some computers' sound systems can crash a program that opens them (we've seen it on Linux with no sound
server), so the first time sound is needed Wirely tries it in a separate little process. Only if that
works does it open the sound device itself; otherwise sound stays off and nothing else is affected.
The answer is remembered, and WIRELY_NO_SOUND=1 turns sound off completely.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading

from PySide6.QtCore import QObject, QSettings, QTimer, Signal

from ..sim.audio import RATE, Synth

PROBE_CODE = r"""
import sys
from PySide6.QtCore import QCoreApplication
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices
app = QCoreApplication([])
dev = QMediaDevices.defaultAudioOutput()
if dev.isNull():
    sys.exit(3)
fmt = QAudioFormat()
fmt.setSampleRate(44100)
fmt.setChannelCount(1)
fmt.setSampleFormat(QAudioFormat.Int16)
sink = QAudioSink(dev, fmt)
io = sink.start()
print("SOUND-OK" if io is not None else "SOUND-FAIL")
sink.stop()
"""


def probe_command():
    if getattr(sys, "frozen", False):           # a built app: ask the app itself to run the check
        return [sys.executable, "--audio-probe"]
    return [sys.executable, "-c", PROBE_CODE]


def run_probe() -> bool:
    try:
        r = subprocess.run(probe_command(), capture_output=True, text=True, timeout=20,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0 and "SOUND-OK" in r.stdout


class SoundPlayer(QObject):
    availabilityChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.synth = Synth()
        self.enabled = True
        self.sink = None
        self.io = None
        self._settings = QSettings("Wirely", "Wirely")
        if os.environ.get("WIRELY_NO_SOUND") == "1":
            self.state = "none"
        else:
            known = self._settings.value("sound_ok")
            self.state = {"true": "ok", "false": "none"}.get(str(known).lower(), "unknown")
        self._probe_thread = None
        self._probe_result = None
        self._timer = QTimer(self)
        self._timer.setInterval(15)
        self._timer.timeout.connect(self._pump)
        self._wanted = False

    def available(self):
        return self.state != "none"

    def start(self):
        """Simulation started: get sound going (checking the device first, once, in the background)."""
        self._wanted = True
        if not self.enabled or self.state == "none":
            return
        if self.state == "unknown":
            if self._probe_thread is None:
                def work():
                    self._probe_result = run_probe()
                self._probe_thread = threading.Thread(target=work, daemon=True)
                self._probe_thread.start()
                QTimer.singleShot(200, self._check_probe)
            return
        self._open()

    def _check_probe(self):
        if self._probe_thread is not None and self._probe_thread.is_alive():
            QTimer.singleShot(200, self._check_probe)
            return
        ok = bool(self._probe_result)
        self.state = "ok" if ok else "none"
        self._settings.setValue("sound_ok", "true" if ok else "false")
        self.availabilityChanged.emit(ok)
        if ok and self._wanted and self.enabled:
            self._open()

    def _open(self):
        if self.sink is not None:
            return
        try:
            from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices
            dev = QMediaDevices.defaultAudioOutput()
            if dev.isNull():
                self.state = "none"
                return
            fmt = QAudioFormat()
            fmt.setSampleRate(RATE)
            fmt.setChannelCount(1)
            fmt.setSampleFormat(QAudioFormat.Int16)
            self.sink = QAudioSink(dev, fmt, self)
            self.sink.setBufferSize(int(RATE * 2 * 0.12))
            self.io = self.sink.start()
            if self.io is None:
                self.sink = None
                return
            self._timer.start()
        except Exception:       # noqa: BLE001 - sound is a nice extra; never let it break anything
            self.sink = self.io = None
            self.state = "none"

    def _pump(self):
        if self.sink is None or self.io is None:
            return
        try:
            free = self.sink.bytesFree()
            n = min(free // 2, int(RATE * 0.06))
            if n > 0:
                self.io.write(self.synth.render(n).tobytes())
        except Exception:       # noqa: BLE001
            self.stop()

    def stop(self):
        self._wanted = False
        self.synth.silence_all()
        self.synth.voices.clear()
        self._timer.stop()
        if self.sink is not None:
            try:
                self.sink.stop()
            except Exception:   # noqa: BLE001
                pass
        self.sink = self.io = None

    def set_enabled(self, on: bool):
        self.enabled = on
        if not on:
            was = self._wanted
            self.stop()
            self._wanted = was
        elif self._wanted:
            self.start()
