# Wirely 1.0.0

**A free, open-source circuit design and simulation app — draw a circuit, press play, watch it work.**
For the workplace, the classroom and the workbench.

## Downloads

| | File | How to install |
|---|---|---|
| **Windows** | `Wirely-Setup-1.0.0.exe` | Run it and follow the installer. `.wirely` files then open in Wirely. If SmartScreen warns (the installer isn't code-signed yet): **More info → Run anyway**. |
| **Mac** (Apple Silicon) | `Wirely-1.0.0-mac-arm64.dmg` | Open it and drag Wirely into Applications. The first time: right-click Wirely → **Open** → **Open** (it isn't signed by Apple yet). |
| **Linux** | `Wirely-1.0.0-x86_64.AppImage` | `chmod +x Wirely-1.0.0-x86_64.AppImage` and run it. |

## What it does

- **Draw circuits** with UK-style symbols: drag parts from the gallery, drag from pin to pin to wire them, double-click to change values (type `10k`, `4k7`, `100n` …). Undo, copy and paste, notes, PNG / SVG / PDF export, bill of materials, light and dark themes.
- **Press Play** and it runs: LEDs glow, lamps light, motors spin up and slow under load, relays click, buzzers and speakers make real sound, meters read. Wires are coloured by voltage and current flows along them. Click switches and drag sliders (light, temperature, moisture …) while it runs; hover over any wire for its voltage and current.
- **Parts that pop:** an LED without a resistor, an overloaded resistor, a transistor hit by a relay's voltage spike — each with a message saying what happened and how to fix it.
- **Graph (oscilloscope)** and **logic probe**.
- **Chips and more:** 555 timer, op-amps, logic gates, D flip-flop, 4017 counter, 4511 decoder, 7-segment display, optoisolators, MOSFETs and transistors (many types), relays, inductors, sensors, signal generator with PWM.
- **20 example circuits**, from an LED and resistor to a 555 doorbell, LED chaser, optoisolator and buck converter.

## Accuracy

Wirely has its own circuit solver (the same method as SPICE). 184 automatic tests check it against textbook formulas — LED current, transistor gain, RC and RL curves, 555 timing, op-amp gain, buck converter output — and against ngspice.
