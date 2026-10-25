# Changes

## 1.4.1 — RGB LED fix, brighter LEDs
- **RGB LEDs:** green is now the same kind of chip as blue (about 3.1 V, like real RGB LEDs), so green and blue
  on one resistor share the current and mix. (Red, at about 2 V, still takes nearly all the current if it shares
  a resistor with them — as in a real one; give each colour its own resistor to mix any colours.)
- **LEDs look brighter when they're on:** a stronger colour and a bigger, brighter glow.

## 1.4.0 — Readings, and 16 new parts
- **Readings:** a new toolbar button shows the voltage and current on every wire, and the voltage, current and
  power of every part, while the circuit runs. Click any wire or part while it runs to pin just its reading.
  **Simulate → Copy readings** copies every part's readings as a table to paste into a spreadsheet.
- **Bi-colour LEDs** (2-leg and 3-leg) and an **RGB LED** that mixes its colours.
- **Bridge rectifier**, and a **transformer** (set its turns ratio; warns if you give it DC).
- **Thyristor (SCR):** C106D, 2N5060, TIC106D and BT151 — latches on from a gate pulse and stays on until the
  current drops below its holding current.
- **Voltage regulators:** 7805, 7809, 7812, LM1117-3.3 and the adjustable LM317, with dropout, current limit and
  thermal shutdown (fit a heatsink in its properties).
- **Comparators:** LM393 and LM311 (open-collector outputs).
- **L293D motor driver:** four half-H drivers with built-in spike diodes — drive a motor both ways from logic
  pins, or set its speed with PWM on the enable pin. It shuts down if it gets too hot.
- **4026** decade counter with 7-segment outputs, and the **4060** counter with its own oscillator.
- **DPDT switch**, **DPDT relay** (two changeover contacts), **Hall effect sensor** (click to bring the
  magnet near) and a **solenoid** that clicks.
- New examples: *Thyristor alarm (latching)*, *5 V power supply (7805)*, *RGB colour mixer*,
  *Counter (555 + 4026)*, *Reversing a motor (DPDT)*, *Motor driver (L293D)* and *Relay reversing a motor
  (DPDT)*.
- Voltage regulators now have a proper dropout (about 1.2 V at light load, 2 V at 1 A for a 78xx), and no
  longer get stuck when a battery sags under load.
- The website counts visits with GoatCounter (no cookies, no personal data).

## 1.3.0 — parts requested by users, and Wirely in your web browser
- **Wirely Web:** the whole app runs in a web browser, so it works on **Chromebooks** and school computers with
  nothing to install — at https://richiewillmott.github.io/Wirely/. It's the desktop app's own Python code
  (the sheet, the symbols and the simulator) running in the browser with Pyodide, so it looks and behaves the same.
- In the browser: open and save `.wirely` files (they work in both versions), all the examples, the graph,
  sound, PNG pictures, the parts list, **links that carry a circuit** (for Google Classroom / Teams), works
  **offline** after the first visit, installs as an app, and touch-screen and touchpad gestures.
- On the graph, a curved trace no longer hides the grid lines and the other traces under it.
- **Shift registers:** 74HC164 (serial in, parallel out), 74HC595 (with output latch and output enable),
  74HC165 (parallel in, serial out) and 74HC597 (with input latch). They warn if run above their 6 V limit.
- **4051 analogue switch** (CD4051B and 74HC4051), with each type's datasheet on-resistance at its supply voltage.
- **TL431 / TLV431 adjustable shunt references:** Vout = Vref × (1 + R1/R2), with their current and voltage limits.
- **Solid-state relay (TLP3122A):** photo-MOSFET output that switches AC or DC, turning on over about a millisecond.
- **2N7002** MOSFET.
- **Every part type is explained:** choose a type in a part's properties and a line underneath says what it's for.
- New examples: *TL431 adjustable reference* and *Shift register (74HC595)*.
- Chip labels sit above the chip instead of over its pins.

## 1.2.0 — real filament lamps
- **Filament lamps behave like real ones:** the filament's resistance rises as it heats up, so the current–voltage
  graph curves (I ∝ V^0.6, as measured on real lamps — the GCSE/A-level required practical), a cold lamp takes a
  surge of about 11× its running current at switch-on, and it takes a moment to brighten and to fade.
- **Resistors heat up over about a second** before burning out, so a brief surge (like a lamp's switch-on) is fine
  but a lasting overload still burns them out.

## 1.1.0 — more accurate MOSFETs and op-amps
- **MOSFETs fitted to their datasheets:** threshold voltage and on-resistance at the datasheet's gate voltages,
  mobility falling at high gate voltage, the body diode, internal gate resistance, and voltage-dependent gate and
  drain capacitances. Switching now takes real time and shows the Miller plateau; gate charge matches the
  datasheets (AO3400 6.1 nC vs 6 nC, FQP27P06 32.3 nC vs 33 nC) and switching delays match ngspice.
- **Op-amps fitted to their datasheets:** open-loop gain, input bias current and resistance, supply current,
  output swing that depends on the load, separate source/sink limits, and the LM358 swinging to 0 V but not to
  its top rail. Output current is drawn through the supply pins, and too much supply voltage destroys the chip.
- Diodes ride out short current surges (as real ones do) instead of popping on a nanosecond spike.
- **MOSFETs break down above their voltage rating** (avalanche, at about 15 % over): a short spike is absorbed up to
  the part's avalanche energy rating (power MOSFETs survive a relay coil's spike; a 2N7000 doesn't), but a supply
  above the rating destroys it, with a message saying why.
- **Motors burn out** on far more than their rated voltage (a 9 V motor on 150 V spins much too fast and overheats).
- The simulator is about twice as fast on every circuit (and much faster with MOSFETs).
- The installer clears out the old version's library files when updating.
- Linux: prefers X11/XWayland and falls back to Wayland; the automatic build now tests both.

## 1.0.0 — first official release
Everything below, together: the circuit editor (r1), live simulation (r2), chips, logic and the graph (r3),
sound, relays, motors and sensors (r4), and the Wirely name, icons and downloads (r5).

- New part: **optoisolator** (optocoupler) — PC817, 4N25, 4N35, TLP521 and 6N139 (Darlington), with an
  example circuit. Its two sides are truly separate circuits, each with its own supply.
- Fixed: a circuit joined to another only through a relay's contacts or an optoisolator now gets its own 0 V
  reference, so its own supply can be anything (before, a separate DC power supply there could fail to solve).
- The graph's Auto time setting now follows the fastest repeating signal on any probe (before, it only
  looked at probe A — so a buck converter, where A is smooth DC, showed a 5-second sweep of a 1 kHz signal).

## r5 — Wirely (became 1.0.0)
- **New name: Wirely** (was Sparkbench). Circuits are now `.wirely` files; old `.spark` files still open.
- **New logo** (a W drawn as a wire, with current flowing along it) and a **file icon** for `.wirely` circuits.
- **Splash screen** with the version and revision while Wirely starts.
- **Downloads built automatically on GitHub**: Windows installer (with `.wirely` file association), Mac `.dmg`
  (with document icon) and Linux AppImage (plus a script to add it to the app menu and associate `.wirely`).
  Every push runs the tests.
- Double-clicking a `.wirely` file in Finder opens it on the Mac; Wirely's own icon on the Windows taskbar.
- **Signal generator duty cycle** (PWM) for square waves.
- New example: **buck converter** (12 V → about 6 V). Its output voltage, ripple and inductor current are
  tested against the textbook formulas and against ngspice (within 0.5 %).

## r4 — sound, relays, motors and sensors
- **Sound:** buzzers buzz, loudspeakers play the simulated signal at its real pitch, motors hum, relays click.
  Sound button to switch it off. Wirely checks the computer's sound safely first, so a broken sound setup
  can never crash it.
- **Relay** (coil + changeover contacts, pull-in 75 %, drop-out 30 %) and **inductor**. Switching a coil with
  no flyback diode makes a real voltage spike that destroys the transistor — with a message explaining the fix.
- **Motors** now have back-EMF: big starting current, then less; a *Load* setting slows them and makes them
  take more current; hover to see their speed in rpm.
- New sensors: **reed switch** (click to bring the magnet near), **tilt switch**, **moisture sensor** (slider),
  **phototransistor** (light slider).
- Many more types: MOSFETs BS170, IRLZ44N (logic level), IRF530, IRF3205, AO3400, IRF9530, FQP27P06,
  IRLML6402; transistors BC547, BC337, 2N2222, TIP120, BC557, BC327, 2N2907, TIP125; diodes 1N4007, 1N5408,
  1N5819 (Schottky); op-amp TL071.
- **Hover readings:** while running, hover over a wire for its voltage and current (with direction).
- **Text notes** for worksheets, **right-click menus**, **autosave** every minute with recovery after a crash.
- Fixed: a MOSFET with an unconnected gate turned itself on; LED glow now centred on the LED.
- Five new examples: relay switching a lamp, motor and load, 555 doorbell, burglar alarm, rain alarm.

## r3 — chips, logic and the graph
- **Graph (oscilloscope):** put graph probes A–D on wires and press Play. Automatic or fixed time and volts
  per square, live readings with frequency, hover to read values, save the graph as a picture.
- **Logic probe:** shows H / L / ? on whatever it touches.
- New parts: **555 timer**, **op-amp** (741, LM358, rail-to-rail), **NOT / AND / OR / NAND / NOR / XOR /
  Schmitt NOT gates**, **D-type flip-flop**, **4017 decade counter**, **4511 decoder**, **7-segment display**,
  **N- and P-channel MOSFETs** (2N7000, IRF540, BS250, IRF9540), **signal generator** (square / sine / triangle).
- The solver lands exactly on switching moments, so 555 timing matches the textbook formulas (within 1 %).
- Logic chips and op-amps with unconnected supply pins are powered from the circuit's supply automatically.
- Seven new examples: 555 LED flasher, LED chaser (555 + 4017), op-amp dark sensor, logic gates, MOSFET motor
  switch, RC filter on the graph, binary to 7-segment.
- Sliders find a clear spot next to their part.

## r2 — live simulation
- **Play / Pause / Stop** (F5 / F6 / Shift+F5) and a speed control (10× faster down to 1/1000 speed).
- Wirely's own circuit solver: Newton–Raphson for diodes, LEDs and transistors; capacitors over time with
  automatic step control. Checked against hand-worked answers and ngspice in the tests.
- LEDs glow in their colour, lamps light up, motors spin, buzzers show sound waves, meters show a reading.
- Wires coloured by voltage (with a colour key) and animated current flow — both can be switched off.
- Click switches and changeover switches, hold push switches, drag sliders for LDRs (light level),
  thermistors (temperature) and variable resistors while it runs. Double-click a part to change its value
  live.
- Parts that are overloaded show it: LEDs, diodes, transistors and electrolytics pop, lamps and fuses blow,
  resistors burn out — with a message saying what happened and how to fix it. Short-circuited batteries are
  pointed out. Stop mends everything.
- Hover over a wire or part while running to read voltage, current and power.
- Two new examples: *Capacitor charging* and *Buzzer and motor*.
- Fixed: "Diodes & LEDs" lost its "&" on Windows; greyed-out buttons now look greyed out.

## r1 — circuit editor (first release)
- Parts gallery with 29 parts in 9 groups, UK/IEC-style symbols, search box.
- Place parts by clicking or dragging; rotate (R / Shift+R), flip (F), move, delete.
- Wires: drag from pin to pin, or click corners; wires stay square, pick the corner that doesn't run
  through a part, follow parts when you move or rotate them; branch off a wire (W) with a junction dot;
  drag a wire sideways or move its loose end.
- Double-click a part to change its values — type them the usual way (10k, 4k7, 100n, 4.7µ).
- Undo / redo for everything, copy / cut / paste / duplicate.
- Save and open circuits (.wirely files), recent files, four example circuits.
- Export the diagram as PNG, SVG or PDF (always black on white), copy it as a picture, bill of materials.
- Light and dark themes, dot grid, smooth zoom-to-fit.
