**Wirely 1.4.1: RGB LED fix and brighter LEDs.**

## Use it in your browser — nothing to install

**https://richiewillmott.github.io/Wirely/** — works on Chromebooks, and in Chrome, Edge, Firefox and Safari on any computer. It updates by itself.

## Downloads (desktop app)

- **Windows (64-bit):** `Wirely-Setup-1.4.1.exe` — run it; it updates an existing Wirely. If SmartScreen warns you (the installer isn't code-signed yet), click **More info → Run anyway**.
- **Mac (Apple Silicon):** `Wirely-1.4.1-mac-arm64.dmg` — open it and drag Wirely into Applications, replacing the old one. The first time, right-click Wirely → **Open** → **Open**.
- **Linux (x86_64):** `Wirely-1.4.1-x86_64.AppImage` — run `chmod +x Wirely-1.4.1-x86_64.AppImage`, then run it.

## What's changed

- **RGB LEDs mix properly:** green is now the same kind of chip as blue (about 3.1 V, like real RGB LEDs), so green and blue on one resistor share the current and make cyan. Red is only about 2 V, so if it shares a resistor with the others it takes nearly all the current — just like a real one. Give each colour its own resistor to mix any colours (see the *RGB colour mixer* example).
- **LEDs look brighter when they're on:** a stronger colour and a bigger, brighter glow.

New in 1.4: **Readings** (see every voltage, current and power at once), **Copy readings**, and 16 new parts including the L293D, 7805/LM317 regulators, thyristors, transformers and RGB LEDs.

329 automatic tests check Wirely against hand calculations, datasheets and ngspice.

Free and open source under the **GNU GPL v3**. Bug reports, ideas and part requests are welcome on the **Issues** tab.
