"""La biblioteca de componentes: cómo se llama cada componente, dónde están sus pines y qué valores tiene.

Las coordenadas están en "unidades de hoja" con el centro del componente en (0, 0) y la y apuntando hacia abajo. Un cuadrado de la cuadrícula es
GRID unidades, y cada pin se sitúa exactamente en un punto de la cuadrícula para que los cables siempre los encuentren.

Los dibujos en sí están en ui/symbols.py; este archivo son datos planos para que el modelo y el simulador
puedan usarlo sin Qt.
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
    on_label: bool = False          # se muestra junto al componente en el diagrama
    min: float | None = None
    max: float | None = None
    help: str = ""


@dataclass(frozen=True)
class PartDef:
    key: str
    name: str
    category: str
    prefix: str                     # letra(s) de referencia: R1, C1, LED1 …
    pins: tuple                     # ((nombre, x, y), …)
    props: tuple = ()
    box: tuple = (-30, -15, 60, 30)  # x, y, w, h: el cuerpo clicable (local)
    description: str = ""
    keywords: str = ""
    short: str = ""                 # nombre más corto para la tarjeta de la galería

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
    "Fuentes de alimentación",
    "Resistencias",
    "Condensadores y bobinas",
    "Interruptores",
    "Sensores de entrada",
    "Diodos y LEDs",
    "Transistores",
    "Puertas lógicas",
    "Circuitos integrados",
    "Dispositivos de salida",
    "Medidores y sondas",
    "Etiquetas",
]

LED_COLOURS = ("Rojo", "Verde", "Amarillo", "Azul", "Blanco", "Naranja")

TWO = (("1", -30, 0), ("2", 30, 0))           # componente estándar de dos pines, 60 unidades de largo
TWO_POL = (("+", -30, 0), ("-", 30, 0))       # polarizado: + a la izquierda


def _p(*a, **k):
    return Prop(*a, **k)


_PARTS = [
    # ---------------------------------------------------------------- fuentes de alimentación
    PartDef("cell", "Pila", "Fuentes de alimentación", "B", TWO_POL,
            (_p("voltage", "Voltaje", 1.5, "V", on_label=True, min=0, max=1000),),
            (-30, -20, 60, 40), "Una sola pila, p. ej. una AA (1,5 V). La placa larga es +.", "battery aa"),
    PartDef("battery", "Batería", "Fuentes de alimentación", "B", TWO_POL,
            (_p("voltage", "Voltaje", 9.0, "V", on_label=True, min=0, max=1000),),
            (-30, -20, 60, 40), "Una batería de pilas, p. ej. 9 V PP3. La placa larga es +.", "pp3 cell"),
    PartDef("dc_supply", "Fuente de alimentación DC", "Fuentes de alimentación", "PSU", TWO_POL,
            (_p("voltage", "Voltaje", 5.0, "V", on_label=True, min=0, max=1000),),
            (-30, -20, 60, 40), "Una fuente de laboratorio que da un voltaje DC constante.", "psu bench", short="Fuente DC"),
    PartDef("ac_supply", "Fuente de alimentación AC", "Fuentes de alimentación", "AC", TWO,
            (_p("voltage", "Voltaje (pico)", 6.0, "V", on_label=True, min=0, max=1000),
             _p("frequency", "Frecuencia", 50.0, "Hz", on_label=True, min=0)),
            (-30, -20, 60, 40), "Una fuente alterna (onda senoidal).", "sine mains", short="Fuente AC"),
    PartDef("rail_pos", "Riel de alimentación (+V)", "Fuentes de alimentación", "V", (("1", 0, 0),),
            (_p("voltage", "Voltaje", 9.0, "V", on_label=True, min=-1000, max=1000),),
            (-15, -30, 30, 32), "Una conexión a la alimentación positiva, medida desde 0 V.", "vcc vdd terminal", short="Riel +V"),
    PartDef("ground", "0 V (tierra)", "Fuentes de alimentación", "GND", (("1", 0, 0),), (),
            (-15, -2, 30, 22), "La referencia de 0 V desde la que se miden todos los voltajes.", "earth gnd 0v", short="0 V"),

    # ---------------------------------------------------------------- resistencias
    PartDef("resistor", "Resistencia", "Resistencias", "R", TWO,
            (_p("resistance", "Resistencia", 1000.0, "Ω", on_label=True, min=1e-3),
             _p("power", "Potencia nominal", 0.25, "W", min=0.0)),
            (-30, -10, 60, 20), "Una resistencia fija.", "ohm"),
    PartDef("var_resistor", "Resistencia variable", "Resistencias", "VR", TWO,
            (_p("resistance", "Resistencia máxima", 10000.0, "Ω", on_label=True, min=1e-3),
             _p("setting", "Ajuste", 50.0, "%", min=0, max=100)),
            (-30, -15, 60, 30), "Una resistencia que puede ajustar mientras el circuito se ejecuta.", "rheostat preset", short="Resistencia variable"),
    PartDef("potentiometer", "Potenciómetro", "Resistencias", "VR",
            (("1", -30, 0), ("2", 30, 0), ("wiper", 0, -30)),
            (_p("resistance", "Resistencia", 10000.0, "Ω", on_label=True, min=1e-3),
             _p("setting", "Posición del cursor", 50.0, "%", min=0, max=100)),
            (-30, -30, 60, 40), "Resistencia variable de tres terminales (control de volumen).", "pot wiper"),
    PartDef("fuse", "Fusible", "Resistencias", "F", TWO,
            (_p("rating", "Corriente nominal", 1.0, "A", on_label=True, min=0),),
            (-30, -8, 60, 16), "Se funde y abre el circuito si la corriente es demasiado alta.", "protection"),

    # ---------------------------------------------------------------- condensadores
    PartDef("capacitor", "Condensador", "Condensadores y bobinas", "C", (("1", -20, 0), ("2", 20, 0)),
            (_p("capacitance", "Capacitancia", 100e-9, "F", on_label=True, min=1e-15),),
            (-20, -15, 40, 30), "Un condensador no polarizado (cerámico / de película).", "ceramic film"),
    PartDef("electrolytic", "Condensador electrolítico", "Condensadores y bobinas", "C", (("+", -20, 0), ("-", 20, 0)),
            (_p("capacitance", "Capacitancia", 100e-6, "F", on_label=True, min=1e-15),
             _p("max_voltage", "Voltaje nominal", 25.0, "V", min=0)),
            (-20, -15, 40, 30), "Un condensador polarizado para valores grandes. ¡Cuidado con el lado +!", "polarised", short="Electrolítico"),

    # ---------------------------------------------------------------- interruptores
    PartDef("switch", "Interruptor de encendido/apagado", "Interruptores", "S", TWO,
            (_p("closed", "Encendido", False, kind="bool"),),
            (-30, -15, 60, 25), "Interruptor de conmutación (SPST). Haga clic en él durante la simulación.", "spst toggle"),
    PartDef("push_make", "Pulsador (normalmente abierto)", "Interruptores", "S", TWO,
            (_p("pressed", "Presionado", False, kind="bool"),),
            (-30, -20, 60, 28), "Conecta solo mientras lo mantiene presionado.", "button ptm", short="Pulsador NA"),
    PartDef("push_break", "Pulsador (normalmente cerrado)", "Interruptores", "S", TWO,
            (_p("pressed", "Presionado", False, kind="bool"),),
            (-30, -20, 60, 28), "Desconecta mientras lo mantiene presionado.", "button ptb", short="Pulsador NC"),
    PartDef("spdt", "Conmutador (SPDT)", "Interruptores", "S",
            (("com", -30, 0), ("a", 30, -10), ("b", 30, 10)),
            (_p("position", "Posición", "A", kind="choice", choices=("A", "B")),),
            (-30, -18, 60, 36), "Conecta el terminal común a A o a B.", "two way", short="Conmutador"),

    # ---------------------------------------------------------------- sensores de entrada
    PartDef("ldr", "Fotorresistencia (LDR)", "Sensores de entrada", "LDR", TWO,
            (_p("light", "Nivel de luz", 500.0, "lux", min=0, max=100000,
                help="Habitación bien iluminada ≈ 500 lux, oscuridad ≈ 1 lux"),),
            (-30, -24, 60, 48), "La resistencia cae a medida que la luz se hace más brillante.", "light sensor", short="LDR"),
    PartDef("thermistor", "Termistor (NTC)", "Sensores de entrada", "TH", TWO,
            (_p("r25", "Resistencia a 25 °C", 10000.0, "Ω", on_label=True, min=1e-3),
             _p("temperature", "Temperatura", 25.0, "°C", min=-50, max=200)),
            (-30, -16, 60, 32), "La resistencia cae a medida que se calienta.", "temperature sensor ntc", short="Termistor"),

    # ---------------------------------------------------------------- diodos
    PartDef("diode", "Diodo", "Diodos y LEDs", "D", (("A", -30, 0), ("K", 30, 0)),
            (_p("model", "Tipo", "1N4001", kind="choice", choices=("1N4001", "1N4007", "1N4148", "1N5408", "1N5819")),),
            (-30, -12, 60, 24), "Deja pasar la corriente en un solo sentido (ánodo → cátodo).", "rectifier"),
    PartDef("led", "LED", "Diodos y LEDs", "LED", (("A", -30, 0), ("K", 30, 0)),
            (_p("colour", "Color", "Rojo", kind="choice", choices=LED_COLOURS, on_label=True),
             _p("max_current", "Corriente máxima", 0.03, "A", min=0)),
            (-30, -24, 60, 36), "Diodo emisor de luz. ¡Necesita una resistencia en serie o se quemará!", "light emitting"),
    PartDef("zener", "Diodo Zener", "Diodos y LEDs", "D", (("A", -30, 0), ("K", 30, 0)),
            (_p("voltage", "Voltaje Zener", 5.1, "V", on_label=True, min=0.5),),
            (-30, -12, 60, 24), "Conduce en inversa a un voltaje fijo — se usa como referencia de voltaje.", "regulator"),

    # ---------------------------------------------------------------- transistores
    PartDef("npn", "Transistor NPN", "Transistores", "Q",
            (("B", -30, 0), ("C", 10, -30), ("E", 10, 30)),
            (_p("model", "Tipo", "BC548", kind="choice", choices=("BC548", "BC547", "BC337", "2N3904", "2N2222", "BD139", "TIP31", "TIP120")),),
            (-30, -30, 50, 60), "Una pequeña corriente en la base conmuta una corriente mayor.", "bjt bc548", short="NPN"),
    PartDef("pnp", "Transistor PNP", "Transistores", "Q",
            (("B", -30, 0), ("C", 10, 30), ("E", 10, -30)),
            (_p("model", "Tipo", "BC558", kind="choice", choices=("BC558", "BC557", "BC327", "2N3906", "2N2907", "BD140", "TIP125")),),
            (-30, -30, 50, 60), "Como el NPN pero se enciende cuando la base se lleva a nivel bajo.", "bjt bc558", short="PNP"),

    # ---------------------------------------------------------------- salidas
    PartDef("lamp", "Lámpara", "Dispositivos de salida", "L", TWO,
            (_p("voltage", "Voltaje nominal", 6.0, "V", on_label=True, min=0),
             _p("power", "Potencia nominal", 0.36, "W", min=0)),
            (-30, -15, 60, 30), "Una lámpara de filamento.", "bulb light"),
    PartDef("buzzer", "Zumbador", "Dispositivos de salida", "BZ", TWO_POL,
            (_p("voltage", "Voltaje nominal", 6.0, "V", on_label=True, min=0),),
            (-30, -20, 60, 32), "Emite un pitido cuando circula corriente.", "sounder beeper"),
    PartDef("speaker", "Parlante", "Dispositivos de salida", "LS", TWO,
            (_p("impedance", "Impedancia", 8.0, "Ω", on_label=True, min=0.1),),
            (-30, -20, 60, 32), "Reproduce la señal como sonido — pruebe un 555 o un generador de señal a 100 Hz–5 kHz.",
            "loudspeaker sound"),
    PartDef("motor", "Motor", "Dispositivos de salida", "M", TWO,
            (_p("voltage", "Voltaje nominal", 6.0, "V", on_label=True, min=0),
             _p("load", "Carga", "Ninguna", kind="choice", choices=("Ninguna", "Ligera", "Media", "Pesada"),
                help="Cuánto esfuerzo tiene que hacer el motor: más carga, más lento y más corriente")),
            (-30, -15, 60, 30), "Un motor DC: consume mucha corriente al arrancar, menos una vez alcanza la velocidad. "
            "Su velocidad depende del voltaje y de la carga que arrastre.", "dc"),

    # ---------------------------------------------------------------- medidores
    PartDef("voltmeter", "Voltímetro", "Medidores y sondas", "VM", TWO_POL, (),
            (-30, -15, 60, 30), "Mide el voltaje entre dos puntos. Conéctelo en paralelo.", "meter volts"),
    PartDef("ammeter", "Amperímetro", "Medidores y sondas", "AM", TWO_POL, (),
            (-30, -15, 60, 30), "Mide la corriente que lo atraviesa. Conéctelo en serie.", "meter amps current"),
]

# ------------------------------------------------------------------------------------------------ componentes r3
GATE2 = (("A", -40, -10), ("B", -40, 10), ("Y", 40, 0))
GATE1 = (("A", -40, 0), ("Y", 40, 0))
LOGIC_NOTE = " Los chips lógicos se alimentan automáticamente desde la alimentación del circuito."
SR_NOTE = " Los pines de control activos en bajo sin conectar (MR, OE, PL, CE) cuentan como no activos."

_PARTS += [
    PartDef("signal_gen", "Generador de señal", "Fuentes de alimentación", "SG", TWO_POL,
            (_p("waveform", "Forma de onda", "Cuadrada", kind="choice", choices=("Cuadrada", "Senoidal", "Triangular"),
                on_label=True),
             _p("frequency", "Frecuencia", 1.0, "Hz", on_label=True, min=1e-3, max=1e6),
             _p("amplitude", "Amplitud (pico)", 5.0, "V", min=0, max=1000),
             _p("offset", "Desplazamiento", 0.0, "V", min=-1000, max=1000),
             _p("duty", "Ciclo de trabajo (cuadrada)", 50.0, "%", min=1, max=99,
                help="Qué parte de cada ciclo pasa en alto una onda cuadrada — para PWM")),
            (-30, -20, 60, 40), "Genera ondas cuadradas, senoidales o triangulares — ideal con el gráfico.",
            "function generator clock pulse square wave", short="Generador de señal"),

    PartDef("xtal_clock", "Reloj de cristal", "Fuentes de alimentación", "X", (("OUT", 40, 0),),
            (_p("frequency", "Frecuencia", 1.0, "Hz", on_label=True, min=0.01, max=1e6),),
            (-30, -18, 60, 36), "Un reloj estable y preciso para lógica: un oscilador de cristal de cuarzo (con un divisor "
            "interno), así que mantiene el tiempo exacto — a diferencia de un 555. OUT conmuta entre 0 V y la alimentación."
            + LOGIC_NOTE, "crystal quartz oscillator clock pulse 32768 timer", short="Reloj de cristal"),
    PartDef("nmos", "MOSFET de canal N", "Transistores", "Q", (("G", -30, 0), ("D", 10, -30), ("S", 10, 30)),
            (_p("model", "Tipo", "2N7000", kind="choice", choices=("2N7000", "2N7002", "BS170", "AO3400", "IRLZ44N", "IRF530", "IRF540", "IRF3205")),),
            (-30, -30, 50, 60), "Se enciende por voltaje en la puerta — casi sin corriente de puerta.",
            "mosfet fet 2n7000 irf540", short="N-MOSFET"),
    PartDef("pmos", "MOSFET de canal P", "Transistores", "Q", (("G", -30, 0), ("D", 10, 30), ("S", 10, -30)),
            (_p("model", "Tipo", "BS250", kind="choice", choices=("BS250", "IRF9530", "IRF9540", "FQP27P06", "IRLML6402")),),
            (-30, -30, 50, 60), "Como el de canal N, pero se enciende cuando la puerta se lleva a nivel bajo.",
            "mosfet fet bs250", short="P-MOSFET"),

    PartDef("not", "Puerta NOT", "Puertas lógicas", "U", GATE1, (), (-30, -15, 70, 30),
            "La salida es lo contrario de la entrada." + LOGIC_NOTE, "inverter", short="NOT"),
    PartDef("and", "Puerta AND", "Puertas lógicas", "U", GATE2, (), (-30, -20, 70, 40),
            "Salida en alto solo cuando A y B están ambas en alto." + LOGIC_NOTE, short="AND"),
    PartDef("or", "Puerta OR", "Puertas lógicas", "U", GATE2, (), (-30, -20, 70, 40),
            "Salida en alto cuando A o B (o ambas) están en alto." + LOGIC_NOTE, short="OR"),
    PartDef("nand", "Puerta NAND", "Puertas lógicas", "U", GATE2, (), (-30, -20, 70, 40),
            "AND seguida de NOT." + LOGIC_NOTE, short="NAND"),
    PartDef("nor", "Puerta NOR", "Puertas lógicas", "U", GATE2, (), (-30, -20, 70, 40),
            "OR seguida de NOT." + LOGIC_NOTE, short="NOR"),
    PartDef("xor", "Puerta XOR", "Puertas lógicas", "U", GATE2, (), (-30, -20, 70, 40),
            "Salida en alto cuando A y B son diferentes." + LOGIC_NOTE, "exclusive", short="XOR"),
    PartDef("schmitt_not", "Puerta NOT Schmitt", "Puertas lógicas", "U", GATE1, (), (-30, -15, 70, 30),
            "Inversor con histéresis: conmuta limpiamente incluso con señales lentas (40106)." + LOGIC_NOTE,
            "40106 schmitt trigger", short="NOT Schmitt"),
    PartDef("dff", "Biestable tipo D", "Puertas lógicas", "U",
            (("D", -50, -20), ("CLK", -50, 0), ("R", -50, 20), ("Q", 50, -20), ("Qn", 50, 20)), (),
            (-30, -40, 60, 80), "Copia D a Q en cada flanco de subida del reloj. R pone Q a 0." + LOGIC_NOTE,
            "4013 latch memory clock", short="Biestable D"),
    PartDef("schmitt_nand", "Puerta NAND Schmitt", "Puertas lógicas", "U", GATE2, (), (-30, -20, 70, 40),
            "Puerta NAND con histéresis (4093): conmuta limpiamente incluso con señales lentas, así que con una resistencia y "
            "un condensador forma un oscilador que puede encender y apagar." + LOGIC_NOTE,
            "4093 schmitt trigger nand oscillator", short="NAND Schmitt"),
    PartDef("jkff", "Biestable JK", "Puertas lógicas", "U",
            (("J", -50, -20), ("CLK", -50, 0), ("K", -50, 20), ("S", 0, -60), ("R", 0, 60),
             ("Q", 50, -20), ("Qn", 50, 20)), (),
            (-30, -40, 60, 80), "En cada flanco de subida del reloj: J=1 pone Q a 1, K=1 lo pone a 0, ambos 1 lo conmutan "
            "(así divide el reloj por 2), ambos 0 lo mantienen. S y R lo ponen o lo resetean de inmediato (4027)."
            + LOGIC_NOTE, "4027 jk flip flop toggle divide counter", short="Biestable JK"),

    PartDef("timer555", "Temporizador 555", "Circuitos integrados", "IC",
            (("GND", -20, 60), ("TRIG", -60, 20), ("OUT", 60, 0), ("RESET", -20, -60), ("CTRL", 20, 60),
             ("THR", -60, 0), ("DIS", -60, -20), ("VCC", 20, -60)), (),
            (-40, -40, 80, 80), "El chip temporizador clásico: intermitentes (astable) y temporizadores de un disparo (monostable).",
            "ne555 astable monostable timer clock", short="Temporizador 555"),
    PartDef("opamp", "Amplificador operacional", "Circuitos integrados", "IC",
            (("-", -40, -10), ("+", -40, 10), ("out", 40, 0), ("V+", 0, -30), ("V-", 0, 30)),
            (_p("model", "Tipo", "741", kind="choice", choices=("741", "LM358", "TL071", "Rail-to-rail")),),
            (-30, -30, 60, 60), "Amplificador / comparador. Si sus pines de alimentación se dejan sin conectar, se "
            "alimenta automáticamente desde la alimentación del circuito.", "741 lm358 comparator amplifier",
            short="Amp. operacional"),
    PartDef("counter4017", "Contador de décadas (4017)", "Circuitos integrados", "IC",
            (("CLK", -60, -20), ("RST", -60, 0)) + tuple((f"Q{i}", 60, -50 + 10 * i) for i in range(10))
            + (("CO", 60, 50),), (),
            (-40, -60, 80, 120), "Cada pulso de reloj en subida mueve la salida en alto: Q0, Q1 … Q9." + LOGIC_NOTE,
            "4017 johnson chaser sequencer", short="Contador 4017"),
    PartDef("decoder4511", "Decodificador de 7 segmentos (4511)", "Circuitos integrados", "IC",
            (("A", -60, -30), ("B", -60, -10), ("C", -60, 10), ("D", -60, 30))
            + tuple((s_, 60, -30 + 10 * i) for i, s_ in enumerate("abcdefg")), (),
            (-40, -40, 80, 80), "Convierte un número binario (D C B A) en los segmentos para 0–9." + LOGIC_NOTE,
            "4511 bcd seven segment driver", short="Decodificador 4511"),

    PartDef("sevenseg", "Pantalla de 7 segmentos", "Dispositivos de salida", "DS",
            tuple((s_, -50, -30 + 10 * i) for i, s_ in enumerate("abcdefg")) + (("COM", 0, 60),),
            (_p("colour", "Color", "Rojo", kind="choice", choices=LED_COLOURS, on_label=False),),
            (-30, -50, 60, 100), "Pantalla de cátodo común con resistencias incorporadas: un segmento se enciende cuando "
            "su pin está en alto.", "seven segment led digit", short="7 segmentos"),

    PartDef("scope_probe", "Sonda de gráfico", "Medidores y sondas", "P", (("1", 0, 0),),
            (_p("channel", "Canal", "A", kind="choice", choices=("A", "B", "C", "D"), on_label=True),),
            (-12, -32, 24, 34), "Póngala en un cable para representar el voltaje de ese cable en el gráfico durante la ejecución.",
            "oscilloscope scope graph trace plot", short="Sonda de gráfico"),
    PartDef("logic_probe", "Sonda lógica", "Medidores y sondas", "LP", (("1", 0, 0),), (),
            (-14, -40, 28, 42), "Muestra H (alto), L (bajo) o ? en lo que toque.",
            "high low tester", short="Sonda lógica"),
]


# ------------------------------------------------------------------------------------------------ componentes r4
_PARTS += [
    PartDef("inductor", "Bobina", "Condensadores y bobinas", "L", TWO,
            (_p("inductance", "Inductancia", 10e-3, "H", on_label=True, min=1e-9),),
            (-30, -10, 60, 18), "Una bobina: se opone a los cambios de corriente (almacena energía en un campo magnético).",
            "coil choke"),
    PartDef("relay", "Relé", "Interruptores", "RL",
            (("C1", -20, -30), ("C2", -20, 30), ("COM", 20, 30), ("NC", 10, -30), ("NO", 30, -30)),
            (_p("voltage", "Voltaje de bobina", 6.0, "V", on_label=True, min=0.5),),
            (-30, -30, 70, 60), "Un interruptor accionado por un electroimán. La corriente en la bobina (C1–C2) conmuta COM de "
            "NC a NO. ¡Ponga un diodo en paralelo con la bobina!", "electromagnet switch coil spdt"),
    PartDef("reed_switch", "Interruptor magnético", "Sensores de entrada", "S", TWO,
            (_p("magnet", "Imán cerca", False, kind="bool"),),
            (-30, -12, 60, 24), "Se cierra cuando un imán está cerca. Haga clic en él durante la ejecución para acercar el imán.",
            "magnet door alarm", short="Interruptor magnético"),
    PartDef("tilt_switch", "Interruptor de inclinación", "Sensores de entrada", "S", TWO,
            (_p("tilted", "Inclinado", False, kind="bool"),),
            (-30, -14, 60, 28), "Una bola en el interior conecta los contactos cuando se inclina. Haga clic en él durante la ejecución.",
            "ball mercury", short="Interruptor inclinación"),
    PartDef("moisture", "Sensor de humedad", "Sensores de entrada", "MS", TWO,
            (_p("moisture", "Humedad", 0.0, "%", min=0, max=100, help="0 % = seco, 100 % = empapado"),),
            (-30, -20, 60, 34), "Dos sondas: cuanto más húmedo el suelo, menor la resistencia.",
            "water rain soil probe", short="Humedad"),
    PartDef("phototransistor", "Fototransistor", "Sensores de entrada", "Q", (("C", 10, -30), ("E", 10, 30)),
            (_p("light", "Nivel de luz", 500.0, "lux", min=0, max=100000),),
            (-25, -30, 45, 60), "Un transistor encendido por luz en lugar de por corriente de base. Colector arriba.",
            "light sensor photo", short="Fototransistor"),
    PartDef("optocoupler", "Optoacoplador", "Transistores", "U",
            (("A", -40, -20), ("K", -40, 20), ("C", 40, -20), ("E", 40, 20)),
            (_p("model", "Tipo", "PC817", kind="choice", choices=("PC817", "4N25", "4N35", "TLP521", "6N139"),
                on_label=True),),
            (-40, -32, 80, 64), "Un LED que ilumina un fototransistor dentro de un mismo encapsulado: la corriente por A–K "
            "enciende C–E, sin conexión eléctrica entre ambos lados. Necesita una resistencia en serie "
            "con el LED.", "optocoupler opto isolator coupler pc817 4n25 4n35 tlp521 6n139 isolation",
            short="Optoacoplador"),
    # ---------------------------------------------------------------- solicitados por usuarios (1.3.0)
    PartDef("shunt_ref", "Regulador shunt (TL431)", "Diodos y LEDs", "U",
            (("K", 0, -30), ("A", 0, 30), ("REF", -30, 0)),
            (_p("model", "Tipo", "TL431", kind="choice", choices=("TL431", "TLV431"), on_label=True),),
            (-30, -30, 50, 60), "Una referencia de precisión ajustable: absorbe corriente en su cátodo (K) para mantener "
            "su pin REF a 2,495 V (TL431) o 1,24 V (TLV431). Aliméntelo a través de una resistencia, fije la salida con "
            "dos resistencias: Vout = Vref × (1 + R1 / R2).",
            "tl431 tlv431 reference zener regulator shunt adjustable", short="TL431"),
    PartDef("ssr", "Relé de estado sólido", "Interruptores", "K",
            (("A", -40, -20), ("K", -40, 20), ("O1", 40, -20), ("O2", 40, 20)),
            (_p("model", "Tipo", "TLP3122A", kind="choice", choices=("TLP3122A",), on_label=True),),
            (-40, -32, 80, 64), "Un relé sin partes móviles: una pequeña corriente por su LED (A–K) enciende "
            "MOSFETs entre O1 y O2 — AC o DC, silencioso y aislado del lado del LED. Necesita una resistencia en "
            "serie con el LED.", "ssr photomos photorelay tlp3122a solid state relay", short="SSR"),
    PartDef("mux4051", "Conmutador analógico de 8 canales (4051)", "Circuitos integrados", "IC",
            (("COM", -60, -40), ("A", -60, 0), ("B", -60, 10), ("C", -60, 20), ("INH", -60, 30))
            + tuple((f"Y{i}", 60, -40 + 10 * i) for i in range(8)),
            (_p("model", "Tipo", "CD4051B", kind="choice", choices=("CD4051B", "74HC4051"), on_label=True),),
            (-40, -50, 80, 90), "Conecta COM a una de Y0–Y7, elegida por el número binario en C B A — un "
            "conmutador analógico, así que las señales pueden ir en ambos sentidos. INH en alto apaga todos los conmutadores."
            + LOGIC_NOTE, "mux multiplexer demultiplexer 4051 cd4051 74hc4051 analog switch", short="Mux 4051"),
    PartDef("sr164", "Registro de desplazamiento (74HC164)", "Circuitos integrados", "IC",
            (("DSA", -60, -30), ("DSB", -60, -10), ("CP", -60, 10), ("MR", -60, 30))
            + tuple((f"Q{i}", 60, -40 + 10 * i) for i in range(8)), (),
            (-40, -50, 80, 90), "Entrada serie, salida paralelo: en cada flanco de subida del reloj (CP) los bits se desplazan Q0 → Q7 "
            "y Q0 toma DSA AND DSB. MR en bajo lo borra. 74HC: para circuitos de 2–6 V." + LOGIC_NOTE
            + SR_NOTE, "74hc164 164 shift register sipo serial", short="74HC164"),
    PartDef("sr595", "Registro de desplazamiento con latch (74HC595)", "Circuitos integrados", "IC",
            (("DS", -60, -40), ("SHCP", -60, -20), ("STCP", -60, 0), ("MR", -60, 20), ("OE", -60, 40))
            + tuple((f"Q{i}", 60, -40 + 10 * i) for i in range(8)) + (("Q7S", 60, 40),), (),
            (-40, -50, 80, 100), "Entrada serie, salida paralelo, con latch: introduzca bits con SHCP, luego un flanco de subida de "
            "STCP los copia a Q0–Q7 todos a la vez. Q7S pasa los datos al siguiente chip. OE en alto apaga "
            "las salidas; MR en bajo borra el registro de desplazamiento. 74HC: para circuitos de 2–6 V."
            + LOGIC_NOTE + SR_NOTE, "74hc595 595 shift register latch sipo", short="74HC595"),
    PartDef("sr165", "Registro de desplazamiento (74HC165)", "Circuitos integrados", "IC",
            tuple((f"D{i}", -60, -60 + 10 * i) for i in range(8))
            + (("DS", -60, 20), ("CP", -60, 30), ("CE", -60, 40), ("PL", -60, 50))
            + (("Q7", 60, -10), ("Q7N", 60, 10)), (),
            (-40, -70, 80, 130), "Entrada paralelo, salida serie: PL en bajo carga D0–D7, luego cada flanco de subida del reloj (CP, con "
            "CE en bajo) desplaza los bits fuera de Q7, con DS entrando por detrás. Para leer muchos botones con pocos "
            "pines. 74HC: para circuitos de 2–6 V." + LOGIC_NOTE + SR_NOTE,
            "74hc165 165 shift register piso parallel load", short="74HC165"),
    PartDef("sr597", "Registro de desplazamiento con latch de entrada (74HC597)", "Circuitos integrados", "IC",
            tuple((f"D{i}", -60, -60 + 10 * i) for i in range(8))
            + (("DS", -60, 20), ("SHCP", -60, 30), ("STCP", -60, 40), ("PL", -60, 50), ("MR", -60, 60))
            + (("Q7", 60, 0),), (),
            (-40, -70, 80, 140), "Entrada paralelo, salida serie, con latch de entrada: un flanco de subida de STCP captura D0–D7, "
            "PL en bajo los copia al registro de desplazamiento, y cada flanco de subida de SHCP los desplaza fuera de Q7. MR en bajo "
            "borra el registro de desplazamiento. 74HC: para circuitos de 2–6 V." + LOGIC_NOTE + SR_NOTE,
            "74hc597 597 shift register piso latch", short="74HC597"),
    # ---------------------------------------------------------------- 1.4.0
    PartDef("led_bi2", "LED bicolor (2 patas)", "Diodos y LEDs", "LED", (("A", -30, 0), ("B", 30, 0)),
            (_p("max_current", "Corriente máxima", 0.03, "A", min=0),),
            (-30, -28, 60, 48), "Un LED rojo y otro verde espalda con espalda en un mismo encapsulado: la corriente de A a B lo enciende "
            "en rojo, de B a A en verde. Invierta la dirección rápidamente (o use AC) y se ve amarillo. Necesita una "
            "resistencia en serie.", "bicolour bicolor two colour dual red green led", short="LED bicolor"),
    PartDef("led_bi3", "LED bicolor (3 patas)", "Diodos y LEDs", "LED",
            (("R", -30, -10), ("G", -30, 10), ("K", 30, 0)),
            (_p("max_current", "Corriente máxima", 0.03, "A", min=0),),
            (-30, -30, 60, 54), "Un LED rojo y otro verde que comparten cátodo (K): R enciende rojo, G enciende verde, "
            "ambos juntos se ven amarillos. Cada ánodo necesita su propia resistencia.",
            "bicolour bicolor dual three leg common cathode red green led", short="LED bicolor (3)"),
    PartDef("led_rgb", "LED RGB", "Diodos y LEDs", "LED",
            (("R", -30, -20), ("G", -30, 0), ("B", -30, 20), ("K", 30, 0)),
            (_p("max_current", "Corriente máxima", 0.03, "A", min=0),),
            (-30, -40, 60, 68), "LEDs rojo, verde y azul que comparten cátodo (K). Mézclelos para obtener otros "
            "colores: rojo + verde = amarillo, los tres = blanco. Cada ánodo necesita su propia resistencia; use PWM "
            "(un generador de señal) para brillos intermedios.", "rgb colour mixing common cathode led",
            short="LED RGB"),
    PartDef("bridge", "Puente rectificador", "Diodos y LEDs", "BR",
            (("AC1", 0, -40), ("AC2", 0, 40), ("+", 40, 0), ("-", -40, 0)),
            (_p("rating", "Corriente nominal", 1.0, "A", on_label=True, min=0.01),),
            (-30, -30, 60, 60), "Cuatro diodos en un encapsulado: convierte AC en DC (onda completa), así que + siempre es "
            "positivo, sin importar cómo esté conectada la AC. Agregue un condensador grande entre + y − para alisarlo.",
            "rectifier diode bridge full wave ac dc w01 db107", short="Puente rectificador"),
    PartDef("scr", "Tiristor (SCR)", "Transistores", "SCR", (("A", -30, 0), ("K", 30, 0), ("G", 10, 30)),
            (_p("model", "Tipo", "C106D", kind="choice", choices=("C106D", "2N5060", "TIC106D", "BT151")),),
            (-30, -20, 60, 50), "Un interruptor que se enclava: una pequeña corriente en la puerta (G) lo enciende, y "
            "sigue encendido — incluso cuando la corriente de puerta se detiene — hasta que la corriente que lo atraviesa (A → K) se detiene. La "
            "alarma clásica que sigue sonando después de que el disparo ha desaparecido: resetéelo cortando el circuito.",
            "thyristor scr latch c106 2n5060 tic106 bt151 alarm", short="Tiristor"),
    PartDef("reg_fixed", "Regulador de voltaje (78xx)", "Fuentes de alimentación", "IC",
            (("IN", -50, 0), ("GND", 0, 30), ("OUT", 50, 0)),
            (_p("model", "Tipo", "7805", kind="choice", choices=("7805", "7809", "7812", "LM1117-3.3"),
                on_label=True),
             _p("heatsink", "Con disipador", False, kind="bool",
                help="Sin disipador solo puede disipar unos 1,5 W antes de sobrecalentarse")),
            (-40, -20, 80, 40), "Da un voltaje de salida estable (5 V para un 7805) a partir de una entrada más alta y sucia. "
            "La entrada debe estar unos 2 V por encima de la salida. El voltaje extra se convierte en calor, así que se "
            "apaga si se calienta demasiado.", "regulator 7805 7809 7812 lm7805 1117 ldo 5v power supply",
            short="Regulador 78xx"),
    PartDef("reg_adj", "Regulador ajustable (LM317)", "Fuentes de alimentación", "IC",
            (("IN", -50, 0), ("ADJ", 0, 30), ("OUT", 50, 0)),
            (_p("heatsink", "Con disipador", False, kind="bool",
                help="Sin disipador solo puede disipar unos 1,5 W antes de sobrecalentarse"),),
            (-40, -20, 80, 40), "Un regulador que se ajusta con dos resistencias: mantiene OUT 1,25 V por encima de ADJ, así que con "
            "R1 de OUT a ADJ y R2 de ADJ a 0 V, Vout = 1,25 V × (1 + R2 / R1). Normalmente R1 = 240 Ω.",
            "regulator lm317 adjustable variable power supply", short="LM317"),
    PartDef("transformer", "Transformador", "Fuentes de alimentación", "T",
            (("P1", -40, -30), ("P2", -40, 30), ("S1", 40, -30), ("S2", 40, 30)),
            (_p("ratio", "Relación de vueltas (primario ÷ secundario)", 10.0, "", on_label=True, min=0.01, max=1000,
                help="10 significa que el secundario da una décima parte del voltaje del primario"),
             _p("rating", "Potencia nominal", 5.0, "W", min=0.01)),
            (-30, -30, 60, 60), "Dos bobinas en un mismo núcleo: la AC en el primario (P1–P2) genera AC en el secundario "
            "(S1–S2), reducida (o elevada) por la relación de vueltas. Ambos lados no están conectados. Solo funciona con AC.",
            "transformer step down step up mains coil isolation", short="Transformador"),
    PartDef("dpdt", "Conmutador doble (DPDT)", "Interruptores", "S",
            (("com1", -30, -20), ("a1", 30, -30), ("b1", 30, -10),
             ("com2", -30, 20), ("a2", 30, 10), ("b2", 30, 30)),
            (_p("position", "Posición", "A", kind="choice", choices=("A", "B")),),
            (-30, -38, 60, 76), "Dos conmutadores que funcionan juntos: ambos comunes van a A, o ambos a B. "
            "Se usa para invertir un motor. Haga clic en él durante la ejecución.", "dpdt double pole reversing motor two way",
            short="Conmutador DPDT"),
    PartDef("rotary", "Conmutador rotatorio", "Interruptores", "S",
            (("COM", -30, 0), ("1", 30, -30), ("2", 30, -10), ("3", 30, 10), ("4", 30, 30)),
            (_p("position", "Posición", "1", kind="choice", choices=("1", "2", "3", "4")),),
            (-30, -38, 60, 76), "Conecta COM a uno de cuatro contactos. Haga clic en él durante la ejecución para girarlo a la "
            "siguiente posición.", "rotary selector switch way position knob", short="Conmutador rotatorio"),
    PartDef("keypad", "Teclado (12 teclas)", "Interruptores", "KP",
            tuple((f"R{i + 1}", -30 + 10 * i, 70) for i in range(4)) + tuple((f"C{i + 1}", 10 + 10 * i, 70)
                                                                             for i in range(3)), (),
            (-40, -55, 80, 110), "Como el teclado de un teléfono o una cerradura: cada tecla une su fila (R1–R4) con su columna "
            "(C1–C3) mientras se presiona. Haga clic y mantenga presionada una tecla durante la ejecución.",
            "keypad keyboard matrix buttons door lock code", short="Teclado"),
    PartDef("relay_dpdt", "Relé DPDT", "Interruptores", "RL",
            (("C1", -40, -30), ("C2", -40, 30), ("COM1", 0, -20), ("NC1", 40, -30), ("NO1", 40, -10),
             ("COM2", 0, 20), ("NC2", 40, 10), ("NO2", 40, 30)),
            (_p("voltage", "Voltaje de bobina", 6.0, "V", on_label=True, min=0.5),),
            (-50, -38, 100, 76), "Un relé con dos conmutadores: la corriente en la bobina (C1–C2) conmuta ambos "
            "COM de NC a NO a la vez. Se usa para invertir un motor o conmutar dos circuitos a la vez. ¡Ponga un diodo "
            "en paralelo con la bobina!", "relay double pole dpdt reversing motor electromagnet two changeover",
            short="Relé DPDT"),
    PartDef("hall", "Sensor de efecto Hall", "Sensores de entrada", "U",
            (("VCC", 0, -30), ("GND", 0, 30), ("OUT", 30, 0)),
            (_p("magnet", "Imán cerca", False, kind="bool"),),
            (-25, -30, 55, 60), "Detecta un imán (tipo A3144). Su salida es de colector abierto: lleva OUT a 0 V cuando un imán está cerca, "
            "así que use una resistencia pull-up de OUT a +. Necesita 4,5–24 V en VCC. Haga clic "
            "en él durante la ejecución para acercar el imán.", "hall effect magnet sensor a3144 switch",
            short="Sensor Hall"),
    PartDef("stepper", "Motor paso a paso", "Dispositivos de salida", "M",
            (("A1", -40, -10), ("A2", -40, 10), ("B1", 40, -10), ("B2", 40, 10)),
            (_p("voltage", "Voltaje nominal", 12.0, "V", on_label=True, min=1),
             _p("steps", "Pasos por vuelta", "48", kind="choice", choices=("48", "200"))),
            (-28, -28, 56, 56), "Gira en pasos exactos: la corriente por una bobina (A1–A2 o B1–B2) lleva el eje "
            "a la siguiente posición. Active A, B, luego A y B al revés (p. ej. con un L293D) y girará "
            "paso a paso. 48 pasos son 7,5° por paso; 200 son 1,8°.", "stepper motor step bipolar l293d",
            short="Motor paso a paso"),
    PartDef("solenoid", "Solenoide", "Dispositivos de salida", "SOL", TWO,
            (_p("voltage", "Voltaje nominal", 12.0, "V", on_label=True, min=0.5),),
            (-30, -16, 60, 32), "Un electroimán que atrae un émbolo metálico — para cerraduras y válvulas. "
            "Como la bobina de un relé, genera un gran pico de voltaje al apagarse: ponga un diodo en paralelo.",
            "solenoid plunger actuator lock valve coil electromagnet"),
    PartDef("comparator", "Comparador", "Circuitos integrados", "IC",
            (("+", -40, -10), ("-", -40, 10), ("OUT", 40, 0)),
            (_p("model", "Tipo", "LM393", kind="choice", choices=("LM393", "LM311"), on_label=True),),
            (-30, -30, 70, 60), "Compara dos voltajes: cuando + es menor que −, OUT se lleva a 0 V; cuando + es "
            "mayor, OUT se apaga (colector abierto), así que agregue una resistencia pull-up de OUT a +. Conmuta más "
            "limpiamente que un amplificador operacional." + LOGIC_NOTE, "comparator lm393 lm311 lm339 compare threshold",
            short="Comparador"),
    PartDef("ic4026", "Contador y controlador de pantalla (4026)", "Circuitos integrados", "IC",
            (("CLK", -60, -30), ("INH", -60, -10), ("RST", -60, 10))
            + tuple((s_, 60, -30 + 10 * i) for i, s_ in enumerate("abcdefg")) + (("CO", 60, 50),), (),
            (-40, -40, 80, 100), "Cuenta pulsos de reloj en subida 0–9 y controla directamente una pantalla de 7 segmentos. CO "
            "pasa a alto después del 9, para dar reloj al siguiente 4026 de las decenas. RST en alto lo resetea a 0; INH en alto lo pausa."
            + LOGIC_NOTE, "4026 counter decade seven segment display driver", short="Contador 4026"),
    PartDef("l293d", "Controlador de motor (L293D)", "Circuitos integrados", "IC",
            (("EN12", -60, -40), ("1A", -60, -30), ("2A", -60, -20), ("EN34", -60, 10), ("3A", -60, 20),
             ("4A", -60, 30), ("1Y", 60, -30), ("2Y", 60, -20), ("3Y", 60, 20), ("4Y", 60, 30),
             ("VCC1", -20, -80), ("VCC2", 20, -80), ("GND", 0, 70)), (),
            (-40, -60, 80, 110), "Cuatro semipuentes en H: cada salida Y sigue a su entrada A mientras su enable (EN) esté "
            "en alto, así que 1Y y 2Y juntos controlan un motor hacia delante, hacia atrás o parado. VCC1 es la alimentación lógica "
            "(5 V); VCC2 alimenta el motor (hasta 36 V). Unos 0,6 A por salida, con diodos "
            "incorporados para absorber picos.", "l293d l293 h bridge h-bridge motor driver reverse stepper", short="L293D"),
    PartDef("ic4060", "Contador y oscilador (4060)", "Circuitos integrados", "IC",
            (("PI", -60, -40), ("PO", -60, -20), ("POn", -60, 0), ("MR", -60, 30))
            + tuple((f"Q{n}", 60, -50 + 10 * i) for i, n in enumerate((4, 5, 6, 7, 8, 9, 10, 12, 13, 14))), (),
            (-40, -60, 80, 110), "Un contador de 14 etapas con su propio oscilador — para temporizadores largos y precisos. Conecte "
            "un condensador C de CTC a un punto X, una resistencia R de RTC a X, y unos 10 × R de X a RS: "
            "oscila a aproximadamente 1 ÷ (2,3 R C), y Q4 … Q14 dividen eso entre 16 … 16384. MR en alto lo resetea."
            + LOGIC_NOTE, "4060 counter oscillator timer divider binary", short="Contador 4060"),
    PartDef("note", "Nota de texto", "Etiquetas", "T", (),
            (_p("text", "Texto", "Nota", kind="text"),),
            (-40, -10, 80, 20), "Una nota en el diagrama — para informes, documentación u hojas de trabajo. Doble clic para cambiar el texto.",
            "label annotation text comment", short="Nota de texto"),
]

PARTS: dict[str, PartDef] = {p.key: p for p in _PARTS}


def by_category() -> list[tuple[str, list[PartDef]]]:
    return [(c, [p for p in _PARTS if p.category == c]) for c in CATEGORIES
            if any(p.category == c for p in _PARTS)]


def get(key: str) -> PartDef:
    try:
        return PARTS[key]
    except KeyError:
        raise KeyError(f"Tipo de componente desconocido: '{key}'") from None