"""The parts library: what every component is called, where its pins are and which values it has.

Coordinates are in "sheet units" with the part's centre at (0, 0) and y pointing down. One grid square is
GRID units, and every pin sits exactly on a grid point so wires always meet them.

The drawings themselves live in ui/symbols.py; this file is plain data so the model and the simulator
can use it without Qt.
"""
from __future__ import annotations

from dataclasses import dataclass

GRID = 10


@dataclass(frozen=True)
class Prop:
    key: str
    label: str
    default: object
    unit: str = ""
    kind: str = "number"            # number | choice | bool | text
    choices: tuple = ()
    on_label: bool = False          # shown next to the part on the diagram
    min: float | None = None
    max: float | None = None
    help: str = ""


@dataclass(frozen=True)
class PartDef:
    key: str
    name: str
    category: str
    prefix: str                     # reference letter(s): R1, C1, LED1 …
    pins: tuple                     # ((name, x, y), …)
    props: tuple = ()
    box: tuple = (-30, -15, 60, 30)  # x, y, w, h: the clickable body (local)
    description: str = ""
    keywords: str = ""
    short: str = ""                 # shorter name for the gallery tile

    @property
    def tile_name(self):
        return self.short or self.name

    def prop(self, key):
        for p in self.props:
            if p.key == key:
                return p
        return None

    def defaults(self) -> dict:
        return {p.key: p.default for p in self.props}


CATEGORIES = [
    "Power supplies",
    "Resistors",
    "Capacitors & inductors",
    "Switches",
    "Input sensors",
    "Diodes & LEDs",
    "Transistors",
    "Logic gates",
    "Integrated circuits",
    "Output devices",
    "Meters & probes",
    "Labels",
]

LED_COLOURS = ("Red", "Green", "Yellow", "Blue", "White", "Orange")

TWO = (("1", -30, 0), ("2", 30, 0))           # standard two-pin part, 60 units long
TWO_POL = (("+", -30, 0), ("-", 30, 0))       # polarised: + on the left


def _p(*a, **k):
    return Prop(*a, **k)


_PARTS = [
    # ---------------------------------------------------------------- power supplies
    PartDef("cell", "Cell", "Power supplies", "B", TWO_POL,
            (_p("voltage", "Voltage", 1.5, "V", on_label=True, min=0, max=1000),),
            (-30, -20, 60, 40), "A single cell, e.g. an AA (1.5 V). The long plate is +.", "battery aa"),
    PartDef("battery", "Battery", "Power supplies", "B", TWO_POL,
            (_p("voltage", "Voltage", 9.0, "V", on_label=True, min=0, max=1000),),
            (-30, -20, 60, 40), "A battery of cells, e.g. 9 V PP3. The long plate is +.", "pp3 cell"),
    PartDef("dc_supply", "DC power supply", "Power supplies", "PSU", TWO_POL,
            (_p("voltage", "Voltage", 5.0, "V", on_label=True, min=0, max=1000),),
            (-30, -20, 60, 40), "A bench power supply giving a steady DC voltage.", "psu bench", short="DC supply"),
    PartDef("ac_supply", "AC power supply", "Power supplies", "AC", TWO,
            (_p("voltage", "Voltage (peak)", 6.0, "V", on_label=True, min=0, max=1000),
             _p("frequency", "Frequency", 50.0, "Hz", on_label=True, min=0)),
            (-30, -20, 60, 40), "An alternating supply (sine wave).", "sine mains", short="AC supply"),
    PartDef("rail_pos", "Supply rail (+V)", "Power supplies", "V", (("1", 0, 0),),
            (_p("voltage", "Voltage", 9.0, "V", on_label=True, min=-1000, max=1000),),
            (-15, -30, 30, 32), "A connection to the positive supply, measured from 0 V.", "vcc vdd terminal", short="+V rail"),
    PartDef("ground", "0 V (ground)", "Power supplies", "GND", (("1", 0, 0),), (),
            (-15, -2, 30, 22), "The 0 V reference that all voltages are measured from.", "earth gnd 0v", short="0 V"),

    # ---------------------------------------------------------------- resistors
    PartDef("resistor", "Resistor", "Resistors", "R", TWO,
            (_p("resistance", "Resistance", 1000.0, "Ω", on_label=True, min=1e-3),
             _p("power", "Power rating", 0.25, "W", min=0.0)),
            (-30, -10, 60, 20), "A fixed resistor. Colour bands come in the realistic view.", "ohm"),
    PartDef("var_resistor", "Variable resistor", "Resistors", "VR", TWO,
            (_p("resistance", "Maximum resistance", 10000.0, "Ω", on_label=True, min=1e-3),
             _p("setting", "Setting", 50.0, "%", min=0, max=100)),
            (-30, -15, 60, 30), "A resistor you can adjust while the circuit runs.", "rheostat preset", short="Variable resistor"),
    PartDef("potentiometer", "Potentiometer", "Resistors", "VR",
            (("1", -30, 0), ("2", 30, 0), ("wiper", 0, -30)),
            (_p("resistance", "Resistance", 10000.0, "Ω", on_label=True, min=1e-3),
             _p("setting", "Wiper position", 50.0, "%", min=0, max=100)),
            (-30, -30, 60, 40), "Three-terminal variable resistor (volume knob).", "pot wiper"),
    PartDef("fuse", "Fuse", "Resistors", "F", TWO,
            (_p("rating", "Rating", 1.0, "A", on_label=True, min=0),),
            (-30, -8, 60, 16), "Melts and breaks the circuit if the current is too high.", "protection"),

    # ---------------------------------------------------------------- capacitors
    PartDef("capacitor", "Capacitor", "Capacitors & inductors", "C", (("1", -20, 0), ("2", 20, 0)),
            (_p("capacitance", "Capacitance", 100e-9, "F", on_label=True, min=1e-15),),
            (-20, -15, 40, 30), "A non-polarised capacitor (ceramic / film).", "ceramic film"),
    PartDef("electrolytic", "Electrolytic capacitor", "Capacitors & inductors", "C", (("+", -20, 0), ("-", 20, 0)),
            (_p("capacitance", "Capacitance", 100e-6, "F", on_label=True, min=1e-15),
             _p("max_voltage", "Voltage rating", 25.0, "V", min=0)),
            (-20, -15, 40, 30), "A polarised capacitor for large values. Mind the + side!", "polarised", short="Electrolytic"),

    # ---------------------------------------------------------------- switches
    PartDef("switch", "On/off switch", "Switches", "S", TWO,
            (_p("closed", "Switched on", False, kind="bool"),),
            (-30, -15, 60, 25), "Toggle switch (SPST). Click it during the simulation.", "spst toggle"),
    PartDef("push_make", "Push switch (push to make)", "Switches", "S", TWO,
            (_p("pressed", "Pressed", False, kind="bool"),),
            (-30, -20, 60, 28), "Connects only while you hold it down.", "button ptm", short="Push to make"),
    PartDef("push_break", "Push switch (push to break)", "Switches", "S", TWO,
            (_p("pressed", "Pressed", False, kind="bool"),),
            (-30, -20, 60, 28), "Disconnects while you hold it down.", "button ptb", short="Push to break"),
    PartDef("spdt", "Changeover switch (SPDT)", "Switches", "S",
            (("com", -30, 0), ("a", 30, -10), ("b", 30, 10)),
            (_p("position", "Position", "A", kind="choice", choices=("A", "B")),),
            (-30, -18, 60, 36), "Connects the common terminal to A or to B.", "two way", short="Changeover"),

    # ---------------------------------------------------------------- input sensors
    PartDef("ldr", "Light dependent resistor (LDR)", "Input sensors", "LDR", TWO,
            (_p("light", "Light level", 500.0, "lux", min=0, max=100000,
                help="Bright room ≈ 500 lux, dark ≈ 1 lux"),),
            (-30, -24, 60, 48), "Resistance falls as the light gets brighter.", "light sensor", short="LDR"),
    PartDef("thermistor", "Thermistor (NTC)", "Input sensors", "TH", TWO,
            (_p("r25", "Resistance at 25°C", 10000.0, "Ω", on_label=True, min=1e-3),
             _p("temperature", "Temperature", 25.0, "°C", min=-50, max=200)),
            (-30, -16, 60, 32), "Resistance falls as it gets hotter.", "temperature sensor ntc", short="Thermistor"),

    # ---------------------------------------------------------------- diodes
    PartDef("diode", "Diode", "Diodes & LEDs", "D", (("A", -30, 0), ("K", 30, 0)),
            (_p("model", "Type", "1N4001", kind="choice", choices=("1N4001", "1N4007", "1N4148", "1N5408", "1N5819")),),
            (-30, -12, 60, 24), "Lets current flow one way only (anode → cathode).", "rectifier"),
    PartDef("led", "LED", "Diodes & LEDs", "LED", (("A", -30, 0), ("K", 30, 0)),
            (_p("colour", "Colour", "Red", kind="choice", choices=LED_COLOURS, on_label=True),
             _p("max_current", "Maximum current", 0.03, "A", min=0)),
            (-30, -24, 60, 36), "Light-emitting diode. Needs a series resistor or it will pop!", "light emitting"),
    PartDef("zener", "Zener diode", "Diodes & LEDs", "D", (("A", -30, 0), ("K", 30, 0)),
            (_p("voltage", "Zener voltage", 5.1, "V", on_label=True, min=0.5),),
            (-30, -12, 60, 24), "Conducts backwards at a set voltage — used as a voltage reference.", "regulator"),

    # ---------------------------------------------------------------- transistors
    PartDef("npn", "NPN transistor", "Transistors", "Q",
            (("B", -30, 0), ("C", 10, -30), ("E", 10, 30)),
            (_p("model", "Type", "BC548", kind="choice", choices=("BC548", "BC547", "BC337", "2N3904", "2N2222", "BD139", "TIP31", "TIP120")),),
            (-30, -30, 50, 60), "A small current into the base switches a bigger current.", "bjt bc548", short="NPN"),
    PartDef("pnp", "PNP transistor", "Transistors", "Q",
            (("B", -30, 0), ("C", 10, 30), ("E", 10, -30)),
            (_p("model", "Type", "BC558", kind="choice", choices=("BC558", "BC557", "BC327", "2N3906", "2N2907", "BD140", "TIP125")),),
            (-30, -30, 50, 60), "Like NPN but turns on when the base is pulled low.", "bjt bc558", short="PNP"),

    # ---------------------------------------------------------------- outputs
    PartDef("lamp", "Lamp", "Output devices", "L", TWO,
            (_p("voltage", "Rated voltage", 6.0, "V", on_label=True, min=0),
             _p("power", "Rated power", 0.36, "W", min=0)),
            (-30, -15, 60, 30), "A filament bulb.", "bulb light"),
    PartDef("buzzer", "Buzzer", "Output devices", "BZ", TWO_POL,
            (_p("voltage", "Rated voltage", 6.0, "V", on_label=True, min=0),),
            (-30, -20, 60, 32), "Beeps when current flows.", "sounder beeper"),
    PartDef("speaker", "Loudspeaker", "Output devices", "LS", TWO,
            (_p("impedance", "Impedance", 8.0, "Ω", on_label=True, min=0.1),),
            (-30, -20, 60, 32), "Plays the signal as sound — try a 555 or a signal generator at 100 Hz–5 kHz.",
            "loudspeaker sound"),
    PartDef("motor", "Motor", "Output devices", "M", TWO,
            (_p("voltage", "Rated voltage", 6.0, "V", on_label=True, min=0),
             _p("load", "Load", "None", kind="choice", choices=("None", "Light", "Medium", "Heavy"),
                help="How hard the motor has to work: more load, slower and more current")),
            (-30, -15, 60, 30), "A DC motor: draws a big current when starting, less once up to speed. "
            "Its speed depends on the voltage and how much load it drives.", "dc"),

    # ---------------------------------------------------------------- meters
    PartDef("voltmeter", "Voltmeter", "Meters & probes", "VM", TWO_POL, (),
            (-30, -15, 60, 30), "Measures the voltage across two points. Connect it in parallel.", "meter volts"),
    PartDef("ammeter", "Ammeter", "Meters & probes", "AM", TWO_POL, (),
            (-30, -15, 60, 30), "Measures the current through it. Connect it in series.", "meter amps current"),
]

# ------------------------------------------------------------------------------------------------ r3 parts
GATE2 = (("A", -40, -10), ("B", -40, 10), ("Y", 40, 0))
GATE1 = (("A", -40, 0), ("Y", 40, 0))
LOGIC_NOTE = " Logic chips are powered automatically from the circuit's supply."

_PARTS += [
    PartDef("signal_gen", "Signal generator", "Power supplies", "SG", TWO_POL,
            (_p("waveform", "Waveform", "Square", kind="choice", choices=("Square", "Sine", "Triangle"),
                on_label=True),
             _p("frequency", "Frequency", 1.0, "Hz", on_label=True, min=1e-3, max=1e6),
             _p("amplitude", "Amplitude (peak)", 5.0, "V", min=0, max=1000),
             _p("offset", "Offset", 0.0, "V", min=-1000, max=1000),
             _p("duty", "Duty cycle (square)", 50.0, "%", min=1, max=99,
                help="How much of each cycle a square wave spends high — for PWM")),
            (-30, -20, 60, 40), "Makes square, sine or triangle waves — great with the graph.",
            "function generator clock pulse square wave", short="Signal generator"),

    PartDef("nmos", "N-channel MOSFET", "Transistors", "Q", (("G", -30, 0), ("D", 10, -30), ("S", 10, 30)),
            (_p("model", "Type", "2N7000", kind="choice", choices=("2N7000", "BS170", "IRLZ44N", "IRF530", "IRF540", "IRF3205", "AO3400")),),
            (-30, -30, 50, 60), "Switched on by voltage at the gate — almost no gate current.",
            "mosfet fet 2n7000 irf540", short="N-MOSFET"),
    PartDef("pmos", "P-channel MOSFET", "Transistors", "Q", (("G", -30, 0), ("D", 10, 30), ("S", 10, -30)),
            (_p("model", "Type", "BS250", kind="choice", choices=("BS250", "IRF9530", "IRF9540", "FQP27P06", "IRLML6402")),),
            (-30, -30, 50, 60), "Like N-channel, but turns on when the gate is pulled low.",
            "mosfet fet bs250", short="P-MOSFET"),

    PartDef("not", "NOT gate", "Logic gates", "U", GATE1, (), (-30, -15, 70, 30),
            "Output is the opposite of the input." + LOGIC_NOTE, "inverter", short="NOT"),
    PartDef("and", "AND gate", "Logic gates", "U", GATE2, (), (-30, -20, 70, 40),
            "Output high only when A and B are both high." + LOGIC_NOTE, short="AND"),
    PartDef("or", "OR gate", "Logic gates", "U", GATE2, (), (-30, -20, 70, 40),
            "Output high when A or B (or both) is high." + LOGIC_NOTE, short="OR"),
    PartDef("nand", "NAND gate", "Logic gates", "U", GATE2, (), (-30, -20, 70, 40),
            "AND followed by NOT." + LOGIC_NOTE, short="NAND"),
    PartDef("nor", "NOR gate", "Logic gates", "U", GATE2, (), (-30, -20, 70, 40),
            "OR followed by NOT." + LOGIC_NOTE, short="NOR"),
    PartDef("xor", "XOR gate", "Logic gates", "U", GATE2, (), (-30, -20, 70, 40),
            "Output high when A and B are different." + LOGIC_NOTE, "exclusive", short="XOR"),
    PartDef("schmitt_not", "Schmitt NOT gate", "Logic gates", "U", GATE1, (), (-30, -15, 70, 30),
            "Inverter with hysteresis: switches cleanly even on slow signals (40106)." + LOGIC_NOTE,
            "40106 schmitt trigger", short="Schmitt NOT"),
    PartDef("dff", "D-type flip-flop", "Logic gates", "U",
            (("D", -50, -20), ("CLK", -50, 0), ("R", -50, 20), ("Q", 50, -20), ("Qn", 50, 20)), (),
            (-30, -40, 60, 80), "Copies D to Q on each rising clock edge. R resets Q to 0." + LOGIC_NOTE,
            "4013 latch memory clock", short="D flip-flop"),

    PartDef("timer555", "555 timer", "Integrated circuits", "IC",
            (("GND", -20, 60), ("TRIG", -60, 20), ("OUT", 60, 0), ("RESET", -20, -60), ("CTRL", 20, 60),
             ("THR", -60, 0), ("DIS", -60, -20), ("VCC", 20, -60)), (),
            (-40, -40, 80, 80), "The classic timer chip: flashers (astable) and one-shot timers (monostable).",
            "ne555 astable monostable timer clock", short="555 timer"),
    PartDef("opamp", "Op-amp", "Integrated circuits", "IC",
            (("-", -40, -10), ("+", -40, 10), ("out", 40, 0), ("V+", 0, -30), ("V-", 0, 30)),
            (_p("model", "Type", "741", kind="choice", choices=("741", "LM358", "TL071", "Rail-to-rail")),),
            (-30, -30, 60, 60), "Amplifier / comparator. If its supply pins are left unconnected it is "
            "powered automatically from the circuit's supply.", "741 lm358 comparator amplifier",
            short="Op-amp"),
    PartDef("counter4017", "Decade counter (4017)", "Integrated circuits", "IC",
            (("CLK", -60, -20), ("RST", -60, 0)) + tuple((f"Q{i}", 60, -50 + 10 * i) for i in range(10))
            + (("CO", 60, 50),), (),
            (-40, -60, 80, 120), "Each rising clock pulse moves the high output along: Q0, Q1 … Q9." + LOGIC_NOTE,
            "4017 johnson chaser sequencer", short="4017 counter"),
    PartDef("decoder4511", "7-segment decoder (4511)", "Integrated circuits", "IC",
            (("A", -60, -30), ("B", -60, -10), ("C", -60, 10), ("D", -60, 30))
            + tuple((s_, 60, -30 + 10 * i) for i, s_ in enumerate("abcdefg")), (),
            (-40, -40, 80, 80), "Turns a binary number (D C B A) into the segments for 0–9." + LOGIC_NOTE,
            "4511 bcd seven segment driver", short="4511 decoder"),

    PartDef("sevenseg", "7-segment display", "Output devices", "DS",
            tuple((s_, -50, -30 + 10 * i) for i, s_ in enumerate("abcdefg")) + (("COM", 0, 60),),
            (_p("colour", "Colour", "Red", kind="choice", choices=LED_COLOURS, on_label=False),),
            (-30, -50, 60, 100), "Common-cathode display with built-in resistors: a segment lights when "
            "its pin is high.", "seven segment led digit", short="7-segment"),

    PartDef("scope_probe", "Graph probe", "Meters & probes", "P", (("1", 0, 0),),
            (_p("channel", "Channel", "A", kind="choice", choices=("A", "B", "C", "D"), on_label=True),),
            (-12, -32, 24, 34), "Put it on a wire to plot that wire's voltage on the graph while running.",
            "oscilloscope scope graph trace plot", short="Graph probe"),
    PartDef("logic_probe", "Logic probe", "Meters & probes", "LP", (("1", 0, 0),), (),
            (-14, -40, 28, 42), "Shows H (high), L (low) or ? on whatever it touches.",
            "high low tester", short="Logic probe"),
]


# ------------------------------------------------------------------------------------------------ r4 parts
_PARTS += [
    PartDef("inductor", "Inductor", "Capacitors & inductors", "L", TWO,
            (_p("inductance", "Inductance", 10e-3, "H", on_label=True, min=1e-9),),
            (-30, -10, 60, 18), "A coil: resists changes in current (stores energy in a magnetic field).",
            "coil choke"),
    PartDef("relay", "Relay", "Switches", "RL",
            (("C1", -20, -30), ("C2", -20, 30), ("COM", 20, 30), ("NC", 10, -30), ("NO", 30, -30)),
            (_p("voltage", "Coil voltage", 6.0, "V", on_label=True, min=0.5),),
            (-30, -30, 70, 60), "A switch worked by an electromagnet. Current in the coil (C1–C2) flips COM from "
            "NC to NO. Put a diode across the coil!", "electromagnet switch coil spdt"),
    PartDef("reed_switch", "Reed switch", "Input sensors", "S", TWO,
            (_p("magnet", "Magnet nearby", False, kind="bool"),),
            (-30, -12, 60, 24), "Closes when a magnet is near. Click it while running to bring the magnet close.",
            "magnet door alarm", short="Reed switch"),
    PartDef("tilt_switch", "Tilt switch", "Input sensors", "S", TWO,
            (_p("tilted", "Tilted", False, kind="bool"),),
            (-30, -14, 60, 28), "A ball inside connects the contacts when it's tilted. Click it while running.",
            "ball mercury", short="Tilt switch"),
    PartDef("moisture", "Moisture sensor", "Input sensors", "MS", TWO,
            (_p("moisture", "Moisture", 0.0, "%", min=0, max=100, help="0 % = dry, 100 % = soaking wet"),),
            (-30, -20, 60, 34), "Two probes: the wetter the soil, the lower the resistance.",
            "water rain soil probe", short="Moisture"),
    PartDef("phototransistor", "Phototransistor", "Input sensors", "Q", (("C", 10, -30), ("E", 10, 30)),
            (_p("light", "Light level", 500.0, "lux", min=0, max=100000),),
            (-25, -30, 45, 60), "A transistor turned on by light instead of a base current. Collector at the top.",
            "light sensor photo", short="Phototransistor"),
    PartDef("note", "Text note", "Labels", "T", (),
            (_p("text", "Text", "Note", kind="text"),),
            (-40, -10, 80, 20), "A note on the diagram — for reports, documentation or worksheets. Double-click to change the text.",
            "label annotation text comment", short="Text note"),
]

PARTS: dict[str, PartDef] = {p.key: p for p in _PARTS}


def by_category() -> list[tuple[str, list[PartDef]]]:
    return [(c, [p for p in _PARTS if p.category == c]) for c in CATEGORIES
            if any(p.category == c for p in _PARTS)]


def get(key: str) -> PartDef:
    try:
        return PARTS[key]
    except KeyError:
        raise KeyError(f"Unknown part type '{key}'") from None
