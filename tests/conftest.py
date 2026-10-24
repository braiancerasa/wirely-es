"""Settings for the tests: no sound, no real screen."""
import os

os.environ.setdefault("WIRELY_NO_SOUND", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
