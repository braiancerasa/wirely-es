# Changes

## 1.0.0 — first official release
Everything below, together: the circuit editor (r1), live simulation (r2), chips, logic and the graph (r3),
sound, relays, motors and sensors (r4), and the Wirely name, icons and downloads (r5).

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
