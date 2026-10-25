**Wirely 1.3.0: parts you asked for — and Wirely in your web browser.** Thanks to everyone who sent requests!

## Use it in your browser — nothing to install

**https://richiewillmott.github.io/Wirely/** — works on Chromebooks, and in Chrome, Edge, Firefox and Safari on any computer.

It's the same Wirely: the same parts, symbols, examples and simulator, running in the browser. Your circuits stay on your computer — nothing is uploaded.

- **Save** gives you a `.wirely` file that opens in the browser version and the desktop app alike.
- **File → Copy a link to this circuit** — paste it into Google Classroom or Teams and everyone gets their own copy.
- Works **offline** after the first visit, and Chrome can **install it as an app** for the Chromebook launcher.
- Touchpad and touch-screen friendly: two-finger scroll to move around, pinch to zoom.

## Downloads (desktop app)

- **Windows (64-bit):** `Wirely-Setup-1.3.0.exe` — run it; it updates an existing Wirely. If SmartScreen warns you (the installer isn't code-signed yet), click **More info → Run anyway**.
- **Mac (Apple Silicon):** `Wirely-1.3.0-mac-arm64.dmg` — open it and drag Wirely into Applications, replacing the old one. The first time, right-click Wirely → **Open** → **Open**.
- **Linux (x86_64):** `Wirely-1.3.0-x86_64.AppImage` — run `chmod +x Wirely-1.3.0-x86_64.AppImage`, then run it.

## New parts

- **Shift registers:** 74HC164, 74HC595 (with its output latch and output-enable), 74HC165 and 74HC597 (with its input latch). Try the new *Shift register (74HC595)* example: set the data switch, clock it in, then latch it onto eight LEDs.
- **4051 analogue switch** (CD4051B and 74HC4051): connects COM to one of eight channels, with each type's real on-resistance.
- **TL431 / TLV431 adjustable references:** set any voltage with two resistors — see the new *TL431 adjustable reference* example.
- **Solid-state relay (TLP3122A):** a small LED current silently switches up to 1.4 A, AC or DC, isolated.
- **2N7002** MOSFET added.
- **Every part type is explained:** double-click a transistor, MOSFET, diode, op-amp and more, choose a type, and a line underneath tells you what it's good for — like why you'd pick an AO3400 over a 2N7002.

## Also

- Chip labels no longer sit on top of the pins.
- On the graph, a curved trace no longer hides the grid lines and the other trace.

271 automatic tests check Wirely against hand calculations, datasheets and ngspice — and the browser version is tested in a real browser before it goes live.

Free and open source under the **GNU GPL v3**. Bug reports, ideas and part requests are welcome on the **Issues** tab.
