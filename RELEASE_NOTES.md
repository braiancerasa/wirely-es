**Wirely 1.4.0: Readings, and 16 new parts.** Thanks to everyone who sent ideas!

## Use it in your browser — nothing to install

**https://richiewillmott.github.io/Wirely/** — works on Chromebooks, and in Chrome, Edge, Firefox and Safari on any computer. It updates by itself.

## Downloads (desktop app)

- **Windows (64-bit):** `Wirely-Setup-1.4.0.exe` — run it; it updates an existing Wirely. If SmartScreen warns you (the installer isn't code-signed yet), click **More info → Run anyway**.
- **Mac (Apple Silicon):** `Wirely-1.4.0-mac-arm64.dmg` — open it and drag Wirely into Applications, replacing the old one. The first time, right-click Wirely → **Open** → **Open**.
- **Linux (x86_64):** `Wirely-1.4.0-x86_64.AppImage` — run `chmod +x Wirely-1.4.0-x86_64.AppImage`, then run it.

## Readings

Press the new **Readings** button while a circuit runs and every wire shows its voltage and current, and every part its voltage, current and power. Or leave it off and **click** any wire or part to pin just that reading — click again to remove it. **Simulate → Copy readings** copies them all as a table, ready to paste into a spreadsheet or your write-up.

## New parts

- **Bi-colour LEDs** (2-leg and 3-leg) and an **RGB LED** — the colours mix.
- **Bridge rectifier** and **transformer** — build a real mains-style power supply.
- **Thyristor (SCR):** C106D, 2N5060, TIC106D, BT151 — a gate pulse latches it on until the current stops.
- **Voltage regulators:** 7805, 7809, 7812, LM1117-3.3 and the adjustable LM317. They drop out, current-limit, and get too hot without a heatsink.
- **Comparators:** LM393 and LM311.
- **L293D motor driver:** drive a motor forwards and backwards from logic pins, with PWM speed control.
- **4026** counter (drives a 7-segment display directly) and **4060** counter with built-in oscillator.
- **DPDT switch**, **DPDT relay** (two changeover contacts), **Hall effect sensor** and **solenoid**.

## New examples

*Thyristor alarm (latching)*, *5 V power supply (7805)*, *RGB colour mixer*, *Counter (555 + 4026)*, *Reversing a motor (DPDT)*, *Motor driver (L293D)* and *Relay reversing a motor (DPDT)*.

328 automatic tests check Wirely against hand calculations, datasheets and ngspice — and the browser version is tested in a real browser before it goes live.

Free and open source under the **GNU GPL v3**. Bug reports, ideas and part requests are welcome on the **Issues** tab.
