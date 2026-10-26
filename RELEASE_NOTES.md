**Wirely 1.5.1: PWM now dims LEDs and bulbs like it does in real life, and Wirely uses much less CPU.**

## Use it in your browser — nothing to install

**https://richiewillmott.github.io/Wirely/** — works on Chromebooks, and in Chrome, Edge, Firefox and Safari on any computer. It updates by itself.

## Downloads (desktop app)

- **Windows (64-bit):** `Wirely-Setup-1.5.1.exe` — run it; it updates an existing Wirely. If SmartScreen warns you (the installer isn't code-signed yet), click **More info → Run anyway**.
- **Mac (Apple Silicon):** `Wirely-1.5.1-mac-arm64.dmg` — open it and drag Wirely into Applications, replacing the old one. The first time, right-click Wirely → **Open** → **Open**.
- **Linux (x86_64):** `Wirely-1.5.1-x86_64.AppImage` — run `chmod +x Wirely-1.5.1-x86_64.AppImage`, then run it.

## New

- **PWM dims LEDs and bulbs:** LEDs, bulbs and displays now look as bright as your eye would see them. Switch one fully on and off faster than you can see (PWM) and it looks steadily dimmer, instead of flickering at random. Slow the simulation down and you can watch it flick on and off.
- It works for **RGB LEDs** too: PWM one colour to change the mix. Multiplexed 7-segment displays look steady as well.
- **New example: *PWM dimmer (555)*.** Turn the knob while it runs to dim an LED and a bulb.
- **The website shows its version number** next to the logo.

## Faster

- **Uses much less CPU while a circuit runs**, so laptops stay cooler and quieter. Wirely no longer redraws things that haven't changed: the grid, parts and wires are only drawn again when they actually change. For example, the *Night light* went from about 60% of a CPU core to under 10%. Everything looks exactly the same. The browser version is lighter too.

420 automatic tests check Wirely against hand calculations, datasheets and ngspice, and the browser version is tested in a real browser before it goes live.

Free and open source under the **GNU GPL v3**. Bug reports, ideas and part requests are welcome on the **Issues** tab.
