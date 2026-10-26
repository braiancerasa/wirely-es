**Wirely 1.5.2: PWM looks steady even when the simulation is slowed, and fast-switching circuits run faster.**

## Use it in your browser — nothing to install

**https://richiewillmott.github.io/Wirely/** — works on Chromebooks, and in Chrome, Edge, Firefox and Safari on any computer. It updates by itself.

## Downloads (desktop app)

- **Windows (64-bit):** `Wirely-Setup-1.5.2.exe` — run it; it updates an existing Wirely. If SmartScreen warns you (the installer isn't code-signed yet), click **More info → Run anyway**.
- **Mac (Apple Silicon):** `Wirely-1.5.2-mac-arm64.dmg` — open it and drag Wirely into Applications, replacing the old one. The first time, right-click Wirely → **Open** → **Open**.
- **Linux (x86_64):** `Wirely-1.5.2-x86_64.AppImage` — run `chmod +x Wirely-1.5.2-x86_64.AppImage`, then run it.

## Fixed

- **LEDs on PWM no longer blink when a circuit is too busy to run in real time** (for example the *PWM dimmer* in the browser). They now look steady, as they would in real life. Choose a slow-motion speed and you can still watch them flick on and off.

## Faster

- **Fast-switching circuits simulate faster:** 555 timers, PWM and the buck converter. The *PWM dimmer* runs about 40% faster and the *555 doorbell* nearly twice as fast, with the same accuracy.

421 automatic tests check Wirely against hand calculations, datasheets and ngspice, and the browser version is tested in a real browser before it goes live.

Free and open source under the **GNU GPL v3**. Bug reports, ideas and part requests are welcome on the **Issues** tab.
