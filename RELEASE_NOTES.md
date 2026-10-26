**Wirely 1.5.2: US symbols, PWM dims LEDs and bulbs like it does in real life, and Wirely uses much less CPU and runs fast-switching circuits faster.** (Includes everything from 1.5.1.)

## Use it in your browser — nothing to install

**https://wirely-app.github.io/** — works on Chromebooks, and in Chrome, Edge, Firefox and Safari on any computer. It updates by itself.

## Downloads (desktop app)

- **Windows (64-bit):** `Wirely-Setup-1.5.2.exe` — run it; it updates an existing Wirely. If SmartScreen warns you (the installer isn't code-signed yet), click **More info → Run anyway**.
- **Mac (Apple Silicon):** `Wirely-1.5.2-mac-arm64.dmg` — open it and drag Wirely into Applications, replacing the old one. The first time, right-click Wirely → **Open** → **Open**.
- **Linux (x86_64):** `Wirely-1.5.2-x86_64.AppImage` — run `chmod +x Wirely-1.5.2-x86_64.AppImage`, then run it.

## New

- **Wirely has a new home: [wirely-app.github.io](https://wirely-app.github.io/)**. The old address forwards there automatically, old shared circuit links still work, and any unsaved work your browser kept comes with you.
- **US symbols:** turn on **View → US symbols** to draw parts the American way: zigzag resistors (and variable resistors, potentiometers, thermistors and LDRs), an S-shaped fuse, a curved minus plate on electrolytic capacitors and a filament in bulbs. Wirely remembers your choice.
- **PWM dims LEDs and bulbs:** LEDs, bulbs and displays now look as bright as your eye would see them. Switch one fully on and off faster than you can see (PWM) and it looks steadily dimmer, instead of flickering at random. This holds even when a busy circuit runs slower than real time. Choose a slow-motion speed and you can watch it flick on and off.
- It works for **RGB LEDs** too: PWM one colour to change the mix. Multiplexed 7-segment displays look steady as well.
- **New example: *PWM dimmer (555)*.** Turn the knob while it runs to dim an LED and a bulb.
- **The website shows its version number** next to the logo.
- **The website updates itself:** when a new version comes out, it switches over straight away (or asks first if you have unsaved work), instead of showing the old one until your next visit.

## Fixed

- The resistor's description no longer mentions a "realistic view" that doesn't exist.

## Faster

- **Uses much less CPU while a circuit runs**, so laptops stay cooler and quieter. Wirely no longer redraws things that haven't changed: the grid, parts and wires are only drawn again when they actually change. For example, the *Night light* went from about 60% of a CPU core to under 10%. Everything looks exactly the same. The browser version is lighter too.
- **Fast-switching circuits simulate faster:** 555 timers, PWM and the buck converter. The *PWM dimmer* runs about 40% faster and the *555 doorbell* nearly twice as fast, with the same accuracy.

425 automatic tests check Wirely against hand calculations, datasheets and ngspice, and the browser version is tested in a real browser before it goes live.

Free and open source under the **GNU GPL v3**. Bug reports, ideas and part requests are welcome on the **Issues** tab.
