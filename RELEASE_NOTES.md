**Wirely 1.5.0: new parts, a unit box for values, and readings you can move.** Plus a big round of bug fixes, found by checking every example step by step and testing every part in thousands of random circuits.

## Use it in your browser — nothing to install

**https://richiewillmott.github.io/Wirely/** — works on Chromebooks, and in Chrome, Edge, Firefox and Safari on any computer. It updates by itself.

## Downloads (desktop app)

- **Windows (64-bit):** `Wirely-Setup-1.5.0.exe` — run it; it updates an existing Wirely. If SmartScreen warns you (the installer isn't code-signed yet), click **More info → Run anyway**.
- **Mac (Apple Silicon):** `Wirely-1.5.0-mac-arm64.dmg` — open it and drag Wirely into Applications, replacing the old one. The first time, right-click Wirely → **Open** → **Open**.
- **Linux (x86_64):** `Wirely-1.5.0-x86_64.AppImage` — run `chmod +x Wirely-1.5.0-x86_64.AppImage`, then run it.

## New

- **A unit box next to values:** double-click a resistor and there's **Ω / kΩ / MΩ** beside the number; capacitors have **pF / nF / µF**, inductors **µH / mH / H**, and frequencies **Hz / kHz / MHz**. Typing the whole value (4k7, 100n) still works.
- **Move a reading out of the way:** drag any reading label to wherever it's clearest. A dashed line shows which wire or part it belongs to.

## New parts

- **Crystal clock** — an exact clock for logic circuits, unlike a 555.
- **Stepper motor** — turns one step at a time; drive it with an L293D and watch the shaft turn.
- **Rotary switch** (click to turn it) and a **12-key keypad** (hold down a key), wired as rows and columns like a real one.
- **JK flip-flop** (4027) and **Schmitt NAND gate** (4093).

## New examples

*Stepper motor (crystal clock + L293D)*, *Keypad (which key is pressed)*, *Binary counter (JK flip-flops)*, *Schmitt NAND flasher (4093)* and *Rotary switch (pick an LED)*.

## Fixed

- **Wire currents next to 0 V symbols** — when you hover, in **Readings**, and in the flow dots — could be wrong (for example 7.3 mA instead of 14.8 mA in the *Night light* example). Part readings and voltages were always right.
- **Readings at the moment something switches:** regulators, 555s, logic chips, relays and motors showed the wrong current for an instant when they switched.
- **A thyristor now switches a relay on:** it used to let go while the coil's current was still building up.
- **Chips and displays now show their power** in Readings instead of 0 W.
- **Wiring mistakes no longer freeze the simulation:** a voltage regulator wired the wrong way round, a TL431 upside down, an op-amp with its output held outside its supply, or a burnt-out thyristor.
- **More realistic failures:** an op-amp on a reversed supply is destroyed, a thyristor with its gate wired straight to the supply burns out (and tells you to add a gate resistor), and a reversed regulator leaks back from OUT to IN like a real one.
- **Counters and flip-flops start from 0:** an input that's simply high at switch-on no longer counts as a clock pulse.
- **Tidier labels** when parts are turned round: names no longer sit on pins, and a chip on its side has its pin names running along the pins.

406 automatic tests check Wirely against hand calculations, datasheets and ngspice — and the browser version is tested in a real browser before it goes live.

Free and open source under the **GNU GPL v3**. Bug reports, ideas and part requests are welcome on the **Issues** tab.
