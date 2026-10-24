**Wirely 1.1.0: more accurate MOSFETs and op-amps.**

## Downloads

- **Windows (64-bit):** `Wirely-Setup-1.1.0.exe` — run it; it updates an existing Wirely. If SmartScreen warns you (the installer isn't code-signed yet), click **More info → Run anyway**.
- **Mac (Apple Silicon):** `Wirely-1.1.0-mac-arm64.dmg` — open it and drag Wirely into Applications, replacing the old one. The first time, right-click Wirely → **Open** → **Open**.
- **Linux (x86_64):** `Wirely-1.1.0-x86_64.AppImage` — run `chmod +x Wirely-1.1.0-x86_64.AppImage`, then run it.

## What's new

- **MOSFETs fitted to their datasheets.** Every type's threshold voltage and on-resistance match its datasheet, and each now has its body diode, internal gate resistance and voltage-dependent gate and drain capacitances. Switching takes real time and the gate shows the Miller plateau. Gate charge matches the datasheets (AO3400: 6.1 nC vs 6 nC; FQP27P06: 32.3 nC vs 33 nC) and switching delays match ngspice to within a few nanoseconds.
- **Op-amps fitted to their datasheets.** Open-loop gain, input bias current, supply current, output swing that depends on the load (a 741 on ±15 V gives ±14 V into 10 kΩ and ±13 V into 2 kΩ), and the LM358 reaching 0 V but not its top rail. Output current is drawn through the supply pins, and too high a supply voltage destroys the chip.
- **Diodes survive short surges** as real ones do, instead of popping on a nanosecond spike.
- **About twice as fast** on every circuit, and much faster with MOSFETs.
- **Updating is cleaner:** the Windows installer removes the old version's library files first.
- **Linux:** tested on Wayland as well as X11.

233 automatic tests now check Wirely against hand calculations, datasheets and ngspice.

Free and open source under the **GNU GPL v3**. Bug reports, ideas and part requests are welcome on the **Issues** tab.
