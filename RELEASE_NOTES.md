**Wirely 1.2.0: real filament lamps.**

## Downloads

- **Windows (64-bit):** `Wirely-Setup-1.2.0.exe` — run it; it updates an existing Wirely. If SmartScreen warns you (the installer isn't code-signed yet), click **More info → Run anyway**.
- **Mac (Apple Silicon):** `Wirely-1.2.0-mac-arm64.dmg` — open it and drag Wirely into Applications, replacing the old one. The first time, right-click Wirely → **Open** → **Open**.
- **Linux (x86_64):** `Wirely-1.2.0-x86_64.AppImage` — run `chmod +x Wirely-1.2.0-x86_64.AppImage`, then run it.

## What's new

- **Filament lamps behave like real ones.** The filament's resistance rises as it heats up, so a lamp's current–voltage graph curves over — just like the GCSE/A-level required practical (current goes as V^0.6, as real lamps measure). Hover over a lamp at different voltages and work out R = V ÷ I: it changes.
- **Switch-on surge:** a cold filament has about a twelfth of its hot resistance, so a lamp takes a surge of about 11× its running current when switched on, then settles in a fraction of a second. Lamps brighten and fade over a moment instead of instantly, and lamps on reduced power look properly dim (two lamps in series are clearly dimmer than one).
- **Resistors ride out short surges:** they now heat up over about a second before burning out, as real ones do, so a brief surge is fine but a lasting overload still burns them out.

243 automatic tests check Wirely against hand calculations, datasheets and ngspice.

Free and open source under the **GNU GPL v3**. Bug reports, ideas and part requests are welcome on the **Issues** tab.
