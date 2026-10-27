**Wirely 1.5.3: readings that make sense for capacitors, inductors and transistors.** (Includes everything from 1.5.2.)

## Use it in your browser — nothing to install

**https://wirely-app.github.io/** — works on Chromebooks, and in Chrome, Edge, Firefox and Safari on any computer. It updates by itself.

## Downloads (desktop app)

- **Windows (64-bit):** `Wirely-Setup-1.5.3.exe` — run it; it updates an existing Wirely. If SmartScreen warns you (the installer isn't code-signed yet), click **More info → Run anyway**.
- **Mac (Apple Silicon):** `Wirely-1.5.3-mac-arm64.dmg` — open it and drag Wirely into Applications, replacing the old one. The first time, right-click Wirely → **Open** → **Open**.
- **Linux (x86_64):** `Wirely-1.5.3-x86_64.AppImage` — run `chmod +x Wirely-1.5.3-x86_64.AppImage`, then run it.

## Fixed

- **Capacitors no longer show power.** A capacitor charging up stores energy rather than turning it into heat, so the "mW" figure next to it was misleading. It now shows just voltage and current.
- **Inductors** show only the small loss in the coil, not the energy going in and out of their magnetic field.
- **MOSFETs show the current that flows through them.** The reading used to be the gate's (always about 0 A), so a MOSFET switching a motor looked like it was passing nothing. It now shows drain-to-source voltage and the drain current.
- **NPN and PNP transistors** now show collector-to-emitter voltage and the collector current, not the base's.
