"""Builds the example circuits in examples/.  Run:  python tools/make_examples.py"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from wirely.model.circuit import Circuit, route  # noqa: E402

OUT = os.path.join(ROOT, "examples")


def pin(c, part, name):
    return part.pin_positions()[name]


def wire(c, *pts):
    c.add_wire(list(pts))


def led_and_resistor():
    c = Circuit()
    c.title = "LED and resistor"
    b = c.add("battery", 0, 80, rot=1, props={"voltage": 9})            # + top (0,50), - bottom (0,110)
    s = c.add("switch", 70, 0)                                           # (40,0) - (100,0)
    r = c.add("resistor", 170, 0, props={"resistance": 470})             # (140,0) - (200,0)
    d = c.add("led", 240, 80, rot=1, props={"colour": "Red"})           # A (240,50), K (240,110)
    wire(c, pin(c, b, "+"), (0, 0), pin(c, s, "1"))
    wire(c, pin(c, s, "2"), pin(c, r, "1"))
    wire(c, pin(c, r, "2"), (240, 0), pin(c, d, "A"))
    wire(c, pin(c, d, "K"), (240, 160), (0, 160), pin(c, b, "-"))
    return c


def voltage_divider():
    c = Circuit()
    c.title = "Voltage divider"
    b = c.add("battery", 0, 100, rot=1, props={"voltage": 9})            # + (0,70) - (0,130)
    r1 = c.add("resistor", 120, 40, rot=1, props={"resistance": 10e3})   # (120,10)-(120,70)
    r2 = c.add("resistor", 120, 160, rot=1, props={"resistance": 4.7e3})  # (120,130)-(120,190)
    vm = c.add("voltmeter", 220, 160, rot=1)                             # + (220,130) - (220,190)
    g = c.add("ground", 120, 240)
    wire(c, pin(c, b, "+"), (0, 0), (120, 0), pin(c, r1, "1"))
    wire(c, pin(c, r1, "2"), pin(c, r2, "1"))
    wire(c, (120, 100), (220, 100), pin(c, vm, "+"))
    wire(c, pin(c, r2, "2"), (120, 240))
    wire(c, pin(c, vm, "-"), (220, 220), (120, 220))
    wire(c, pin(c, b, "-"), (0, 220), (120, 220))
    del g
    return c


def night_light():
    """LED comes on when it gets dark: variable resistor on top, LDR below, transistor switch."""
    c = Circuit()
    c.title = "Night light"
    top, bot = -60, 260
    v = c.add("rail_pos", 0, top, props={"voltage": 9})
    vr = c.add("var_resistor", 0, 60, rot=1, props={"resistance": 47e3})   # (0,30)-(0,90)
    ldr = c.add("ldr", 0, 180, rot=1)                                      # (0,150)-(0,210)
    rb = c.add("resistor", 90, 120, props={"resistance": 4.7e3})           # (60,120)-(120,120)
    q = c.add("npn", 150, 120)                                             # B (120,120) C (160,90) E (160,150)
    rl = c.add("resistor", 160, -20, rot=1, props={"resistance": 470})     # (160,-50)-(160,10)
    led = c.add("led", 160, 60, rot=1, props={"colour": "Yellow"})       # A (160,30) K (160,90)
    c.add("ground", 0, bot)
    wire(c, pin(c, v, "1"), pin(c, vr, "1"))
    wire(c, pin(c, v, "1"), (160, top), pin(c, rl, "1"))
    wire(c, pin(c, rl, "2"), pin(c, led, "A"))
    wire(c, pin(c, vr, "2"), pin(c, ldr, "1"))
    wire(c, (0, 120), pin(c, rb, "1"))
    wire(c, pin(c, ldr, "2"), (0, bot), (160, bot), pin(c, q, "E"))
    assert pin(c, led, "K") == pin(c, q, "C") and pin(c, rb, "2") == pin(c, q, "B")
    return c


def two_way_switch():
    c = Circuit()
    c.title = "Two-way light switch"
    b = c.add("battery", 0, 120, rot=1, props={"voltage": 6})            # + (0,90) - (0,150)
    s1 = c.add("spdt", 90, 40)                                           # com (60,40) a (120,30) b (120,50)
    s2 = c.add("spdt", 230, 40, flip=True)                               # com (260,40) a (200,30) b (200,50)
    lamp = c.add("lamp", 320, 120, rot=1)                                # (320,90)-(320,150)
    wire(c, pin(c, b, "+"), (0, 40), pin(c, s1, "com"))
    wire(c, pin(c, s1, "a"), pin(c, s2, "a"))
    wire(c, pin(c, s1, "b"), pin(c, s2, "b"))
    wire(c, pin(c, s2, "com"), (320, 40), pin(c, lamp, "1"))
    wire(c, pin(c, lamp, "2"), (320, 200), (0, 200), pin(c, b, "-"))
    return c


def capacitor_charging():
    """Switch at A: the capacitor charges through 10 kΩ (watch the voltmeter climb over a few seconds).
    Switch to B: it discharges through 1 kΩ and the LED, which fades out."""
    c = Circuit()
    c.title = "Capacitor charging"
    b = c.add("battery", 0, 100, rot=1, props={"voltage": 9})               # + (0,70) - (0,130)
    r = c.add("resistor", 60, 0, props={"resistance": 10e3})               # (30,0)-(90,0)
    s = c.add("spdt", 150, 10, flip=True, props={"position": "A"})         # com (180,10) a (120,0) b (120,20)
    cap = c.add("electrolytic", 260, 100, rot=1, props={"capacitance": 470e-6})  # + (260,80) - (260,120)
    vm = c.add("voltmeter", 340, 100, rot=1)                               # + (340,70) - (340,130)
    rl = c.add("resistor", 120, 60, rot=1, props={"resistance": 1000})     # (120,30)-(120,90)
    led = c.add("led", 120, 150, rot=1, props={"colour": "Green"})        # A (120,120) K (120,180)
    assert pin(c, s, "com") == (180, 10) and pin(c, s, "a") == (120, 0) and pin(c, s, "b") == (120, 20)
    wire(c, pin(c, b, "+"), (0, 0), pin(c, r, "1"))
    wire(c, pin(c, r, "2"), pin(c, s, "a"))
    wire(c, pin(c, s, "com"), (260, 10), pin(c, cap, "+"))
    wire(c, (260, 10), (340, 10), pin(c, vm, "+"))
    wire(c, pin(c, s, "b"), pin(c, rl, "1"))
    wire(c, pin(c, rl, "2"), pin(c, led, "A"))
    wire(c, pin(c, b, "-"), (0, 220), (340, 220), pin(c, vm, "-"))
    wire(c, pin(c, cap, "-"), (260, 220))
    wire(c, pin(c, led, "K"), (120, 220))
    return c


def buzzer_and_motor():
    c = Circuit()
    c.title = "Buzzer and motor"
    b = c.add("battery", 0, 100, rot=1, props={"voltage": 6})               # + (0,70) - (0,130)
    pb = c.add("push_make", 90, 0)                                          # (60,0)-(120,0)
    bz = c.add("buzzer", 200, 100, rot=1)                                   # + (200,70) - (200,130)
    sw = c.add("switch", 90, -80)                                           # (60,-80)-(120,-80)
    m = c.add("motor", 300, 100, rot=1)                                     # (300,70)-(300,130)
    wire(c, pin(c, b, "+"), (0, -80), pin(c, sw, "1"))
    wire(c, (0, 0), pin(c, pb, "1"))
    wire(c, pin(c, pb, "2"), (200, 0), pin(c, bz, "+"))
    wire(c, pin(c, sw, "2"), (300, -80), pin(c, m, "1"))
    wire(c, pin(c, b, "-"), (0, 180), (300, 180), pin(c, m, "2"))
    wire(c, pin(c, bz, "-"), (200, 180))
    return c


def timer_555(c, x=300, y=200, R1=10e3, R2=47e3, C=10e-6, top=60, bot=360, cap_kind="electrolytic"):
    """A 555 astable at (x, y) wired to rails at y=top and y=bot. Returns the 555 and its output pin."""
    ic = c.add("timer555", x, y)
    r1 = c.add("resistor", x - 140, y - 100, rot=1, props={"resistance": R1})      # (x-140, y-130) … (y-70)
    r2 = c.add("resistor", x - 140, y + 10, rot=1, props={"resistance": R2})       # (x-140, y-20) … (y+40)
    cap = c.add(cap_kind, x - 100, y + 100, rot=1, props={"capacitance": C})      # + (x-100, y+80)
    cp, cm = ("+", "-") if cap_kind == "electrolytic" else ("1", "2")
    cc = c.add("capacitor", x + 20, y + 100, rot=1, props={"capacitance": 10e-9})  # (x+20, y+80)…(y+120)
    P = lambda part, n: pin(c, part, n)
    wire(c, P(ic, "VCC"), (x + 20, top))
    wire(c, P(ic, "RESET"), (x - 20, top))
    wire(c, P(r1, "1"), (x - 140, top))
    wire(c, P(r1, "2"), P(r2, "1"))
    wire(c, P(ic, "DIS"), (x - 140, y - 20))
    wire(c, P(ic, "THR"), (x - 100, y), P(cap, cp))
    wire(c, P(ic, "TRIG"), (x - 100, y + 20))
    wire(c, P(r2, "2"), (x - 100, y + 40))
    wire(c, P(ic, "CTRL"), P(cc, "1"))
    wire(c, P(cc, "2"), (x + 20, bot))
    wire(c, P(ic, "GND"), (x - 20, bot))
    wire(c, P(cap, cm), (x - 100, bot))
    return ic


def flasher_555():
    c = Circuit()
    c.title = "555 LED flasher"
    b = c.add("battery", 0, 200, rot=1, props={"voltage": 9})                 # + (0,170) - (0,230)
    ic = timer_555(c)
    r3 = c.add("resistor", 420, 200, props={"resistance": 470})              # (390,200)-(450,200)
    led = c.add("led", 480, 280, rot=1, props={"colour": "Red"})            # A (480,250) K (480,310)
    wire(c, pin(c, b, "+"), (0, 60), (320, 60))
    wire(c, pin(c, ic, "OUT"), pin(c, r3, "1"))
    wire(c, pin(c, r3, "2"), (480, 200), pin(c, led, "A"))
    wire(c, pin(c, b, "-"), (0, 360), (480, 360), pin(c, led, "K"))
    c.add("ground", 0, 360)
    c.add("scope_probe", 370, 200, props={"channel": "A"})
    c.add("scope_probe", 200, 270, props={"channel": "B"})
    return c


def led_chaser():
    c = Circuit()
    c.title = "LED chaser (555 + 4017)"
    b = c.add("battery", 0, 200, rot=1, props={"voltage": 9})
    ic = timer_555(c, R1=10e3, R2=68e3, C=4.7e-6)
    cnt = c.add("counter4017", 700, 200)
    wire(c, pin(c, b, "+"), (0, 60), (320, 60))
    wire(c, pin(c, ic, "OUT"), (560, 200), (560, 180), pin(c, cnt, "CLK"))
    # count 0-4 then reset: Q5 back to RST
    wire(c, pin(c, cnt, "Q5"), (790, 200), (790, 280), (620, 280), (620, 200), pin(c, cnt, "RST"))
    colours = ["Red", "Orange", "Yellow", "Green", "Blue"]
    for i in range(5):
        x = 830 + 70 * i
        led = c.add("led", x, 320, rot=1, props={"colour": colours[i]})        # A (x,290) K (x,350)
        wire(c, pin(c, cnt, f"Q{i}"), (x, 150 + 10 * i), pin(c, led, "A"))
        wire(c, pin(c, led, "K"), (x, 360))
    wire(c, pin(c, b, "-"), (0, 360), (1110, 360))
    c.add("ground", 0, 360)
    return c


def opamp_light_sensor():
    c = Circuit()
    c.title = "Op-amp dark sensor"
    b = c.add("battery", 0, 150, rot=1, props={"voltage": 9})                  # + (0,120) - (0,180)
    ldr = c.add("ldr", 100, 80, rot=1)                                         # (100,50)-(100,110)
    r = c.add("resistor", 100, 190, rot=1, props={"resistance": 10e3})       # (100,160)-(100,220)
    pot = c.add("potentiometer", 220, 150, rot=1, props={"resistance": 10e3})  # 1 (220,120) 2 (220,180) w (250,150)
    oa = c.add("opamp", 360, 150, props={"model": "LM358"})                    # - (320,140) + (320,160) out (400,150)
    rl = c.add("resistor", 450, 150, props={"resistance": 470})               # (420,150)-(480,150)
    led = c.add("led", 510, 220, rot=1, props={"colour": "Green"})           # A (510,190) K (510,250)
    assert pin(c, pot, "wiper") == (250, 150)
    wire(c, pin(c, b, "+"), (0, 0), (360, 0), pin(c, oa, "V+"))
    wire(c, pin(c, ldr, "1"), (100, 0))
    wire(c, pin(c, pot, "1"), (220, 0))
    wire(c, pin(c, ldr, "2"), pin(c, r, "1"))
    wire(c, (100, 130), (160, 130), (160, 90), (300, 90), (300, 140), pin(c, oa, "-"))
    wire(c, pin(c, pot, "wiper"), (280, 150), (280, 160), pin(c, oa, "+"))
    wire(c, pin(c, oa, "out"), pin(c, rl, "1"))
    wire(c, pin(c, rl, "2"), (510, 150), pin(c, led, "A"))
    wire(c, pin(c, b, "-"), (0, 300), (510, 300), pin(c, led, "K"))
    wire(c, pin(c, r, "2"), (100, 300))
    wire(c, pin(c, pot, "2"), (220, 300))
    wire(c, pin(c, oa, "V-"), (360, 300))
    c.add("ground", 0, 300)
    return c


def logic_gates():
    c = Circuit()
    c.title = "Logic gates"
    b = c.add("battery", 0, 150, rot=1, props={"voltage": 9})
    sa = c.add("switch", 100, 70, rot=1)                                       # (100,40)-(100,100)
    sb = c.add("switch", 180, 70, rot=1)
    ra = c.add("resistor", 100, 190, rot=1, props={"resistance": 10e3})       # (100,160)-(100,220)
    rb = c.add("resistor", 180, 190, rot=1, props={"resistance": 10e3})
    g = c.add("and", 320, 150)                                                 # A (280,140) B (280,160) Y (360,150)
    led = c.add("led", 420, 220, rot=1, props={"colour": "Red"})             # A (420,190) K (420,250)
    wire(c, pin(c, b, "+"), (0, 0), (180, 0), pin(c, sb, "1"))
    wire(c, pin(c, sa, "1"), (100, 0))
    wire(c, pin(c, sa, "2"), pin(c, ra, "1"))
    wire(c, pin(c, sb, "2"), pin(c, rb, "1"))
    wire(c, (100, 130), (260, 130), (260, 140), pin(c, g, "A"))
    wire(c, (180, 150), (240, 150), (240, 160), pin(c, g, "B"))
    wire(c, pin(c, g, "Y"), (420, 150), pin(c, led, "A"))
    wire(c, pin(c, b, "-"), (0, 300), (420, 300), pin(c, led, "K"))
    wire(c, pin(c, ra, "2"), (100, 300))
    wire(c, pin(c, rb, "2"), (180, 300))
    c.add("logic_probe", 140, 130)
    c.add("logic_probe", 220, 150)
    c.add("logic_probe", 390, 150)
    c.add("ground", 0, 300)
    return c


def mosfet_motor():
    c = Circuit()
    c.title = "MOSFET motor switch"
    b = c.add("battery", 0, 150, rot=1, props={"voltage": 9})                  # + (0,120) - (0,180)
    m = c.add("motor", 300, 80, rot=1, props={"voltage": 9})                   # (300,50)-(300,110)
    d = c.add("diode", 370, 80, rot=3)                                         # A (370,110) K (370,50)
    q = c.add("nmos", 290, 190, props={"model": "IRF540"})                     # G (260,190) D (300,160) S (300,220)
    sw = c.add("switch", 170, 190)                                             # (140,190)-(200,190)
    rg = c.add("resistor", 230, 250, rot=1, props={"resistance": 100e3})      # (230,220)-(230,280)
    assert pin(c, d, "A") == (370, 110) and pin(c, d, "K") == (370, 50)
    wire(c, pin(c, b, "+"), (0, 0), (370, 0), pin(c, d, "K"))
    wire(c, pin(c, m, "1"), (300, 0))
    wire(c, pin(c, m, "2"), pin(c, q, "D"))
    wire(c, pin(c, d, "A"), (370, 140), (300, 140))
    wire(c, pin(c, sw, "1"), (140, 0))
    wire(c, pin(c, sw, "2"), pin(c, q, "G"))
    wire(c, pin(c, rg, "1"), (230, 190))
    wire(c, pin(c, b, "-"), (0, 300), (300, 300), pin(c, q, "S"))
    wire(c, pin(c, rg, "2"), (230, 300))
    c.add("ground", 0, 300)
    return c


def rc_filter_graph():
    c = Circuit()
    c.title = "RC filter on the graph"
    g = c.add("signal_gen", 0, 150, rot=1, props={"waveform": "Square", "frequency": 5, "amplitude": 2.5,
                                                   "offset": 2.5})              # + (0,120) - (0,180)
    r = c.add("resistor", 130, 60, props={"resistance": 10e3})                # (100,60)-(160,60)
    cap = c.add("capacitor", 220, 150, rot=1, props={"capacitance": 4.7e-6})  # (220,130)-(220,170)
    wire(c, pin(c, g, "+"), (0, 60), pin(c, r, "1"))
    wire(c, pin(c, r, "2"), (220, 60), pin(c, cap, "1"))
    wire(c, pin(c, g, "-"), (0, 240), (220, 240), pin(c, cap, "2"))
    c.add("ground", 0, 240)
    c.add("scope_probe", 50, 60, props={"channel": "A"})
    c.add("scope_probe", 220, 100, props={"channel": "B"})
    return c


def binary_display():
    c = Circuit()
    c.title = "Binary to 7-segment"
    b = c.add("battery", 0, 200, rot=1, props={"voltage": 9})                  # + (0,170) - (0,230)
    dec = c.add("decoder4511", 480, 200)
    disp = c.add("sevenseg", 660, 200)
    for i, (name, x) in enumerate(zip("ABCD", (80, 140, 200, 260))):
        sw = c.add("switch", x, 70, rot=1, props={"closed": name != "D"})     # (x,40)-(x,100)
        pd = c.add("resistor", x, 330, rot=1, props={"resistance": 10e3})     # (x,300)-(x,360)
        wire(c, pin(c, sw, "1"), (x, 0))
        wire(c, pin(c, sw, "2"), pin(c, pd, "1"))
        wire(c, pin(c, pd, "2"), (x, 400))
        wire(c, (x, 170 + 20 * i), pin(c, dec, name))
    for s_ in "abcdefg":
        wire(c, pin(c, dec, s_), pin(c, disp, s_))
    wire(c, pin(c, b, "+"), (0, 0), (260, 0))
    wire(c, pin(c, b, "-"), (0, 400), (660, 400), pin(c, disp, "COM"))
    c.add("ground", 0, 400)
    return c


def relay_lamp():
    c = Circuit()
    c.title = "Relay switching a lamp"
    b = c.add("battery", 0, 150, rot=1, props={"voltage": 9})                  # + (0,120) - (0,180)
    s1 = c.add("switch", 100, 70, rot=1)                                       # (100,40)-(100,100)
    rb = c.add("resistor", 150, 150, props={"resistance": 4.7e3})            # (120,150)-(180,150)
    rp = c.add("resistor", 100, 230, rot=1, props={"resistance": 47e3})      # (100,200)-(100,260)
    q = c.add("npn", 210, 150)                                                 # B (180,150) C (220,120) E (220,180)
    rl = c.add("relay", 240, 60, props={"voltage": 9})                       # C1 (220,30) C2 (220,90) COM (260,90) NO (270,30)
    d = c.add("diode", 180, 60, rot=3, props={"model": "1N4148"})            # A (180,90) K (180,30)
    lamp = c.add("lamp", 400, 180, rot=1, props={"voltage": 9, "power": 0.5})  # (400,150)-(400,210)
    assert pin(c, rl, "NO") == (270, 30) and pin(c, d, "K") == (180, 30)
    wire(c, pin(c, b, "+"), (0, 0), (330, 0))
    wire(c, pin(c, s1, "1"), (100, 0))
    wire(c, pin(c, s1, "2"), (100, 150), pin(c, rb, "1"))
    wire(c, (100, 150), pin(c, rp, "1"))
    wire(c, pin(c, rl, "C1"), (220, 0))
    wire(c, pin(c, d, "K"), (180, 0))
    wire(c, pin(c, d, "A"), pin(c, rl, "C2"))
    wire(c, pin(c, rl, "C2"), pin(c, q, "C"))
    wire(c, pin(c, rl, "COM"), (260, 100), (330, 100), (330, 0))
    wire(c, pin(c, rl, "NO"), (270, 20), (400, 20), pin(c, lamp, "1"))
    wire(c, pin(c, b, "-"), (0, 300), (400, 300), pin(c, lamp, "2"))
    wire(c, pin(c, rp, "2"), (100, 300))
    wire(c, pin(c, q, "E"), (220, 300))
    c.add("ground", 0, 300)
    c.add("note", 330, -40, props={"text": "The diode across the relay coil protects Q1.\nDelete it and see what happens!"})
    return c


def motor_load():
    c = Circuit()
    c.title = "Motor and load"
    b = c.add("battery", 0, 150, rot=1, props={"voltage": 6})
    s1 = c.add("switch", 90, 0)                                                # (60,0)-(120,0)
    am = c.add("ammeter", 190, 0)                                              # + (160,0) - (220,0)
    m = c.add("motor", 280, 150, rot=1, props={"voltage": 6, "load": "None"})  # (280,120)-(280,180)
    wire(c, pin(c, b, "+"), (0, 0), pin(c, s1, "1"))
    wire(c, pin(c, s1, "2"), pin(c, am, "+"))
    wire(c, pin(c, am, "-"), (280, 0), pin(c, m, "1"))
    wire(c, pin(c, m, "2"), (280, 300), (0, 300), pin(c, b, "-"))
    c.add("note", 140, 350, props={"text": "Switch on: the motor takes a big current to start,\nthen less. "
                                           "Double-click M1 to change its load."})
    return c


def doorbell_555():
    c = Circuit()
    c.title = "555 doorbell"
    b = c.add("battery", -80, 200, rot=1, props={"voltage": 9})                # + (-80,170) - (-80,230)
    pb = c.add("push_make", -80, 100, rot=1)                                   # (-80,70)-(-80,130)
    ic = timer_555(c, R1=1e3, R2=10e3, C=100e-9, cap_kind="capacitor")
    ck = c.add("electrolytic", 410, 200, props={"capacitance": 10e-6})        # + (390,200) - (430,200)
    sp = c.add("speaker", 480, 280, rot=1)                                     # (480,250)-(480,310)
    wire(c, pin(c, pb, "1"), (-80, 60), (320, 60))
    wire(c, pin(c, pb, "2"), pin(c, b, "+"))
    wire(c, pin(c, ic, "OUT"), pin(c, ck, "+"))
    wire(c, pin(c, ck, "-"), (480, 200), pin(c, sp, "1"))
    wire(c, pin(c, b, "-"), (-80, 360), (480, 360), pin(c, sp, "2"))
    c.add("ground", -80, 360)
    c.add("note", 200, -10, props={"text": "Press the button (and turn your sound up) — about 690 Hz."})
    return c


def transistor_alarm(title, sensor, sensor_props, top_r, bottom_is_sensor, note):
    c = Circuit()
    c.title = title
    b = c.add("battery", 0, 150, rot=1, props={"voltage": 9})
    if bottom_is_sensor:
        r1 = c.add("resistor", 120, 70, rot=1, props={"resistance": top_r})     # (120,40)-(120,100)
        sn = c.add(sensor, 120, 230, rot=1, props=sensor_props)                  # (120,200)-(120,260)
        top, bot = r1, sn
    else:
        sn = c.add(sensor, 120, 70, rot=1, props=sensor_props)
        r1 = c.add("resistor", 120, 230, rot=1, props={"resistance": top_r})
        top, bot = sn, r1
    rb = c.add("resistor", 180, 150, props={"resistance": 4.7e3})            # (150,150)-(210,150)
    q = c.add("npn", 240, 150)                                                 # B (210,150) C (250,120) E (250,180)
    bz = c.add("buzzer", 250, 60, rot=1)                                       # + (250,30) - (250,90)
    wire(c, pin(c, b, "+"), (0, 0), (250, 0), pin(c, bz, "+"))
    wire(c, pin(c, top, "1"), (120, 0))
    wire(c, pin(c, top, "2"), pin(c, bot, "1"))
    wire(c, (120, 150), pin(c, rb, "1"))
    wire(c, pin(c, bz, "-"), pin(c, q, "C"))
    wire(c, pin(c, b, "-"), (0, 300), (250, 300), pin(c, q, "E"))
    wire(c, pin(c, bot, "2"), (120, 300))
    c.add("ground", 0, 300)
    c.add("note", 130, 350, props={"text": note})
    return c


def burglar_alarm():
    return transistor_alarm("Burglar alarm (reed switch)", "reed_switch", {"magnet": True}, 10e3, True,
                            "Door shut: magnet near, reed switch closed, silent.\nClick the reed switch to open "
                            "the door…")


def rain_alarm():
    return transistor_alarm("Rain alarm (moisture sensor)", "moisture", {"moisture": 0.0}, 47e3, False,
                            "Drag the moisture slider: when the probes get wet the buzzer sounds.")


def buck_converter():
    """12 V → about 6 V with a P-MOSFET switching 1000 times a second, a Schottky diode, inductor and capacitor."""
    c = Circuit()
    c.title = "Buck converter"
    b = c.add("dc_supply", 0, 150, rot=1, props={"voltage": 12})                # + (0,120) - (0,180)
    g = c.add("signal_gen", 60, 150, rot=1, props={"waveform": "Square", "frequency": 1000, "amplitude": 6,
                                                    "offset": 6, "duty": 50})   # + (60,120) - (60,180)
    inv = c.add("not", 130, 40)                                                  # A (90,40) Y (170,40)
    q = c.add("pmos", 220, 40, props={"model": "IRF9540"})                       # G (190,40) D (230,70) S (230,10)
    d = c.add("diode", 230, 170, rot=3, props={"model": "1N5819"})              # A (230,200) K (230,140)
    ind = c.add("inductor", 300, 100, props={"inductance": 10e-3})              # (270,100)-(330,100)
    cap = c.add("electrolytic", 370, 180, rot=1, props={"capacitance": 100e-6})  # + (370,160) - (370,200)
    r = c.add("resistor", 450, 180, rot=1, props={"resistance": 10, "power": 5})  # (450,150)-(450,210)
    vm = c.add("voltmeter", 530, 180, rot=1)                                     # + (530,150) - (530,210)
    assert pin(c, q, "S") == (230, 10) and pin(c, d, "K") == (230, 140)
    wire(c, pin(c, b, "+"), (0, 0), (230, 0), pin(c, q, "S"))
    wire(c, pin(c, g, "+"), (60, 40), pin(c, inv, "A"))
    wire(c, pin(c, inv, "Y"), pin(c, q, "G"))
    wire(c, pin(c, q, "D"), pin(c, d, "K"))
    wire(c, (230, 100), pin(c, ind, "1"))
    wire(c, pin(c, ind, "2"), (370, 100), pin(c, cap, "+"))
    wire(c, (370, 100), (450, 100), pin(c, r, "1"))
    wire(c, (450, 100), (530, 100), pin(c, vm, "+"))
    wire(c, pin(c, b, "-"), (0, 300), (530, 300), pin(c, vm, "-"))
    wire(c, pin(c, g, "-"), (60, 300))
    wire(c, pin(c, d, "A"), (230, 300))
    wire(c, pin(c, cap, "-"), (370, 300))
    wire(c, pin(c, r, "2"), (450, 300))
    c.add("ground", 0, 300)
    c.add("scope_probe", 410, 100, props={"channel": "A"})
    c.add("scope_probe", 230, 90, props={"channel": "B"})
    c.add("note", 270, -60, props={"text": "Buck converter: Q1 switches 12 V on and off 1000 times a second.\n"
                                           "L1 and C1 smooth the pulses, so about 12 V × duty cycle comes out.\n"
                                           "Double-click SG1 and change its duty cycle — watch the output follow."})
    return c


def optoisolator():
    c = Circuit()
    c.title = "Optoisolator"
    b1 = c.add("battery", 0, 150, rot=1, props={"voltage": 9})                 # + (0,120) - (0,180)
    s1 = c.add("switch", 90, 0)                                                 # (60,0)-(120,0)
    r1 = c.add("resistor", 190, 0, props={"resistance": 1e3})                 # (160,0)-(220,0)
    u1 = c.add("optocoupler", 300, 150, props={"model": "PC817"})             # A (260,130) K (260,170) C (340,130) E (340,170)
    b2 = c.add("battery", 600, 150, rot=1, props={"voltage": 9})               # + (600,120) - (600,180)
    r2 = c.add("resistor", 470, 0, props={"resistance": 1e3})                 # (440,0)-(500,0)
    led = c.add("led", 400, 60, rot=1, props={"colour": "Green"})             # A (400,30) K (400,90)
    assert pin(c, u1, "A") == (260, 130) and pin(c, u1, "E") == (340, 170) and pin(c, led, "K") == (400, 90)
    # input side
    wire(c, pin(c, b1, "+"), (0, 0), pin(c, s1, "1"))
    wire(c, pin(c, s1, "2"), pin(c, r1, "1"))
    wire(c, pin(c, r1, "2"), (260, 0), pin(c, u1, "A"))
    wire(c, pin(c, u1, "K"), (260, 300), (0, 300), pin(c, b1, "-"))
    c.add("ground", 0, 300)
    # output side: its own battery, not joined to the input side anywhere
    wire(c, pin(c, b2, "+"), (600, 0), pin(c, r2, "2"))
    wire(c, pin(c, r2, "1"), (400, 0), pin(c, led, "A"))
    wire(c, pin(c, led, "K"), (400, 130), pin(c, u1, "C"))
    wire(c, pin(c, u1, "E"), (340, 300), (600, 300), pin(c, b2, "-"))
    c.add("note", 300, -60, props={"text": "Two separate circuits: switch S1 on the left lights LED1 on the right\n"
                                           "through the light inside U1 only — no wire joins the two sides."})
    return c


def tl431_reference():
    c = Circuit()
    c.title = "TL431 adjustable reference"
    b = c.add("dc_supply", 0, 150, rot=1, props={"voltage": 12})           # + (0,120) - (0,180)
    rs = c.add("resistor", 110, 0, props={"resistance": 470})              # (80,0)-(140,0)
    u = c.add("shunt_ref", 220, 150, props={"model": "TL431"})             # K (220,120) A (220,180) REF (190,150)
    r1 = c.add("resistor", 140, 90, rot=1, props={"resistance": 10e3})     # (140,60)-(140,120)
    r2 = c.add("resistor", 140, 210, rot=1, props={"resistance": 10e3})    # (140,180)-(140,240)
    vm = c.add("voltmeter", 330, 150, rot=1)                               # + (330,120) - (330,180)
    assert pin(c, u, "REF") == (190, 150) and pin(c, r1, "1") == (140, 60)
    wire(c, pin(c, b, "+"), (0, 0), pin(c, rs, "1"))
    wire(c, pin(c, rs, "2"), (220, 0), pin(c, u, "K"))
    wire(c, (140, 0), pin(c, r1, "1"))
    wire(c, pin(c, r1, "2"), (140, 150), pin(c, u, "REF"))
    wire(c, (140, 150), pin(c, r2, "1"))
    wire(c, (220, 0), (330, 0), pin(c, vm, "+"))
    wire(c, pin(c, b, "-"), (0, 300), (330, 300), pin(c, vm, "-"))
    wire(c, pin(c, u, "A"), (220, 300))
    wire(c, pin(c, r2, "2"), (140, 300))
    c.add("ground", 0, 300)
    c.add("note", 170, -60, props={"text": "The TL431 sinks just enough current to hold REF at 2.495 V,\n"
                                           "so Vout = 2.495 × (1 + R1 / R2) = 5 V here. Change R1 or R2!"})
    return c


def shift_register_595():
    c = Circuit()
    c.title = "Shift register (74HC595)"
    b = c.add("dc_supply", 0, 150, rot=1, props={"voltage": 5})            # + (0,120) - (0,180)
    u = c.add("sr595", 300, 150)        # DS (240,110) SHCP (240,130) STCP (240,150) MR (240,170) OE (240,190)
    assert pin(c, u, "DS") == (240, 110) and pin(c, u, "Q0") == (360, 110) and pin(c, u, "Q7S") == (360, 190)
    s_data = c.add("switch", 210, 80, rot=1)                               # (210,50)-(210,110)
    s_clk = c.add("push_make", 170, 80, rot=1)                             # (170,50)-(170,110)
    s_lat = c.add("push_make", 130, 80, rot=1)                             # (130,50)-(130,110)
    for sw in (s_data, s_clk, s_lat):
        wire(c, pin(c, sw, "1"), (sw.x, 40))
    wire(c, pin(c, b, "+"), (0, 40), (210, 40))
    wire(c, pin(c, s_data, "2"), pin(c, u, "DS"))
    wire(c, pin(c, s_clk, "2"), (170, 130), pin(c, u, "SHCP"))
    wire(c, pin(c, s_lat, "2"), (130, 150), pin(c, u, "STCP"))
    wire(c, pin(c, u, "MR"), (110, 170), (110, 40))          # MR to + (not clearing)
    wire(c, pin(c, u, "OE"), (230, 190), (230, 400))         # OE to 0 V (outputs on)
    xmax = 420 + 70 * 7
    wire(c, pin(c, b, "-"), (0, 400), (xmax, 400))
    for i in range(8):
        x = 420 + 70 * (7 - i)              # Q7 on the left … Q0 on the right: read it as a binary number
        led = c.add("led", x, 260, rot=1, props={"colour": "Red"})        # A (x,230) K (x,290)
        r = c.add("resistor", x, 330, rot=1, props={"resistance": 330})   # (x,300)-(x,360)
        wire(c, pin(c, u, f"Q{i}"), (x, 110 + 10 * i), pin(c, led, "A"))
        wire(c, pin(c, led, "K"), pin(c, r, "1"))
        wire(c, pin(c, r, "2"), (x, 400))
    c.add("logic_probe", 380, 260)
    wire(c, pin(c, u, "Q7S"), (380, 190), (380, 260))
    c.add("ground", 0, 400)
    c.add("note", 660, 30, props={"text": "Set DATA (S1), press CLOCK (S2) to shift it in — eight times.\n"
                                           "Then press LATCH (S3): the LEDs show the byte all at once."})
    s_data.ref, s_clk.ref, s_lat.ref = "S1", "S2", "S3"
    return c


# ------------------------------------------------------------------------------------------- 1.4.0 examples
def thyristor_alarm():
    """A latching alarm: press the trigger and it keeps sounding until you press reset."""
    c = Circuit()
    c.title = "Thyristor alarm (latching)"
    b = c.add("battery", 0, 150, rot=1, props={"voltage": 9})                 # + (0,120) - (0,180)
    reset = c.add("push_break", 100, 0)                                       # (70,0)-(130,0)
    bz = c.add("buzzer", 400, 80, rot=1, props={"voltage": 9})                # + (400,50) - (400,110)
    scr = c.add("scr", 400, 170, rot=1, props={"model": "C106D"})             # A (400,140) K (400,200) G (370,180)
    trig = c.add("push_make", 200, 90, rot=1)                                 # (200,60)-(200,120)
    rg = c.add("resistor", 285, 180, props={"resistance": 4700})              # (255,180)-(315,180)
    assert pin(c, scr, "G") == (370, 180) and pin(c, bz, "+") == (400, 50)
    wire(c, pin(c, b, "+"), (0, 0), pin(c, reset, "1"))
    wire(c, pin(c, reset, "2"), (400, 0), pin(c, bz, "+"))
    wire(c, pin(c, bz, "-"), pin(c, scr, "A"))
    wire(c, pin(c, trig, "1"), (200, 0))
    wire(c, pin(c, trig, "2"), (200, 180), pin(c, rg, "1"))
    wire(c, pin(c, rg, "2"), pin(c, scr, "G"))
    wire(c, pin(c, scr, "K"), (400, 300))
    wire(c, pin(c, b, "-"), (0, 300), (400, 300))
    c.add("ground", 0, 300)
    reset.ref, trig.ref = "S1", "S2"
    c.add("note", 230, -60, props={"text": "Press S2 (the trigger, like a door switch): the alarm keeps sounding\n"
                                            "after you let go — the thyristor latches. Press S1 to reset it."})
    return c


def power_supply_5v():
    """Mains to 5 V: transformer, bridge rectifier, smoothing capacitor and a 7805 regulator."""
    c = Circuit()
    c.title = "5 V power supply (7805)"
    ac = c.add("ac_supply", 0, 150, rot=1, props={"voltage": 325, "frequency": 50})   # 1 (0,120) 2 (0,180)
    t = c.add("transformer", 120, 150, props={"ratio": 20, "rating": 5})              # P1 (80,120) P2 (80,180) S1 (160,120) S2 (160,180)
    br = c.add("bridge", 260, 160)                                                     # AC1 (260,120) AC2 (260,200) + (300,160) - (220,160)
    c1 = c.add("electrolytic", 340, 230, rot=1, props={"capacitance": 1000e-6, "max_voltage": 25})  # + (340,210) - (340,250)
    reg = c.add("reg_fixed", 450, 160, props={"model": "7805"})                       # IN (400,160) GND (450,190) OUT (500,160)
    r = c.add("resistor", 570, 160, props={"resistance": 220})                        # (540,160)-(600,160)
    led = c.add("led", 640, 230, rot=1, props={"colour": "Green"})                    # A (640,200) K (640,260)
    vm = c.add("voltmeter", 720, 230, rot=1)                                           # + (720,200) - (720,260)
    assert pin(c, ac, "1") == (0, 120) and pin(c, t, "S2") == (160, 180) and pin(c, br, "AC2") == (260, 200)
    assert pin(c, reg, "IN") == (400, 160) and pin(c, reg, "GND") == (450, 190)
    wire(c, pin(c, ac, "1"), pin(c, t, "P1"))
    wire(c, pin(c, ac, "2"), pin(c, t, "P2"))
    wire(c, pin(c, t, "S1"), pin(c, br, "AC1"))
    wire(c, pin(c, t, "S2"), (160, 220), (260, 220), pin(c, br, "AC2"))
    wire(c, pin(c, br, "+"), (340, 160), pin(c, c1, "+"))
    wire(c, (340, 160), pin(c, reg, "IN"))
    wire(c, pin(c, reg, "OUT"), pin(c, r, "1"))
    wire(c, pin(c, r, "2"), (640, 160), pin(c, led, "A"))
    wire(c, (640, 160), (720, 160), pin(c, vm, "+"))
    for p_ in (pin(c, br, "-"), pin(c, c1, "-"), pin(c, reg, "GND"), pin(c, led, "K"), pin(c, vm, "-")):
        wire(c, p_, (p_[0], 300))
    wire(c, (220, 300), (720, 300))
    c.add("ground", 220, 300)
    c.add("scope_probe", 320, 160, props={"channel": "A"})
    c.add("scope_probe", 520, 160, props={"channel": "B"})
    c.add("note", 360, 40, props={"text": "Mains (simulated!) → the transformer steps it down → the bridge rectifies it →\n"
                                           "C1 smooths it → the 7805 gives a steady 5 V. The graph shows A and B."})
    return c


def rgb_mixer():
    c = Circuit()
    c.title = "RGB colour mixer"
    b = c.add("battery", 0, 150, rot=1, props={"voltage": 9})                  # + (0,120) - (0,180)
    led = c.add("led_rgb", 400, 260)                                            # R (370,240) G (370,260) B (370,280) K (430,260)
    sws = []
    for x, ya, colour in ((100, 240, "R"), (170, 260, "G"), (240, 280, "B")):
        sw = c.add("switch", x, 70, rot=1, props={"closed": colour != "B"})    # (x,40)-(x,100)
        r = c.add("resistor", x, 160, rot=1, props={"resistance": 470})       # (x,130)-(x,190)
        wire(c, pin(c, sw, "1"), (x, 0))
        wire(c, pin(c, sw, "2"), pin(c, r, "1"))
        wire(c, pin(c, r, "2"), (x, ya), pin(c, led, colour))
        sws.append(sw)
    wire(c, pin(c, b, "+"), (0, 0), (240, 0))
    wire(c, pin(c, led, "K"), (430, 340))
    wire(c, pin(c, b, "-"), (0, 340), (430, 340))
    c.add("ground", 0, 340)
    for sw, ref in zip(sws, ("S1", "S2", "S3")):
        sw.ref = ref
    c.add("note", 620, 140, props={"text": "Click S1 (red), S2 (green) and S3 (blue) while it runs\n"
                                            "to mix colours: red + green = yellow, all three = white."})
    return c


def counter_4026():
    c = Circuit()
    c.title = "Counter (555 + 4026)"
    b = c.add("battery", 0, 200, rot=1, props={"voltage": 9})                 # + (0,170) - (0,230)
    ic = timer_555(c, R1=10e3, R2=68e3, C=4.7e-6)                              # OUT (360,200)
    cnt = c.add("ic4026", 520, 200)                                            # CLK (460,170) INH (460,190) RST (460,210)
    disp = c.add("sevenseg", 700, 200)
    wire(c, pin(c, b, "+"), (0, 60), (320, 60))
    wire(c, pin(c, ic, "OUT"), (420, 200), (420, 170), pin(c, cnt, "CLK"))
    wire(c, pin(c, cnt, "INH"), (440, 190), (440, 360))
    wire(c, pin(c, cnt, "RST"), (450, 210), (450, 360))
    for s_ in "abcdefg":
        wire(c, pin(c, cnt, s_), pin(c, disp, s_))
    wire(c, pin(c, disp, "COM"), (700, 360))
    wire(c, pin(c, b, "-"), (0, 360), (700, 360))
    c.add("ground", 0, 360)
    c.add("note", 560, 60, props={"text": "The 555 makes clock pulses; the 4026 counts them\n"
                                           "and drives the display directly — no decoder needed."})
    return c


def motor_reversing():
    c = Circuit()
    c.title = "Reversing a motor (DPDT)"
    b = c.add("battery", 0, 100, rot=1, props={"voltage": 6})                  # + (0,70) - (0,130)
    sw = c.add("dpdt", 150, 100)              # com1 (120,80) a1 (180,70) b1 (180,90) com2 (120,120) a2 (180,110) b2 (180,130)
    m = c.add("motor", 400, 100, rot=1, props={"voltage": 6})                  # 1 (400,70) 2 (400,130)
    assert pin(c, sw, "b2") == (180, 130) and pin(c, m, "1") == (400, 70)
    wire(c, pin(c, b, "+"), (0, 40), (100, 40), (100, 80), pin(c, sw, "com1"))
    wire(c, pin(c, b, "-"), (0, 160), (100, 160), (100, 120), pin(c, sw, "com2"))
    wire(c, pin(c, sw, "a1"), pin(c, m, "1"))
    wire(c, pin(c, sw, "b2"), (240, 130), (240, 30), (400, 30), pin(c, m, "1"))
    wire(c, pin(c, sw, "b1"), (300, 90), (300, 130), pin(c, m, "2"))
    wire(c, pin(c, sw, "a2"), (320, 110), (320, 150), (400, 150), pin(c, m, "2"))
    c.add("ground", 0, 160)
    c.add("note", 200, 210, props={"text": "Click S1 while it runs: the switch swaps the motor's\n"
                                            "connections over, so it spins the other way."})
    return c


def l293d_motor():
    """An L293D drives a motor forwards or backwards from two logic inputs; a 7805 makes its 5 V logic supply."""
    c = Circuit()
    c.title = "Motor driver (L293D)"
    b = c.add("battery", 0, 200, rot=1, props={"voltage": 9})                  # + (0,170) - (0,230)
    reg = c.add("reg_fixed", 150, 60, props={"model": "7805"})                 # IN (100,60) GND (150,90) OUT (200,60)
    ic = c.add("l293d", 400, 220)
    s1 = c.add("switch", 290, 130, rot=1)                                      # (290,100)-(290,160)
    s2 = c.add("switch", 250, 130, rot=1)                                      # (250,100)-(250,160)
    m = c.add("motor", 540, 200, rot=1, props={"voltage": 6})                  # 1 (540,170) 2 (540,230)
    assert pin(c, ic, "EN12") == (340, 180) and pin(c, ic, "VCC2") == (420, 140) and pin(c, ic, "GND") == (400, 290)
    assert pin(c, s1, "1") == (290, 100) and pin(c, m, "1") == (540, 170)
    wire(c, pin(c, b, "+"), (0, 0), (420, 0), pin(c, ic, "VCC2"))
    wire(c, (100, 0), pin(c, reg, "IN"))
    wire(c, pin(c, reg, "OUT"), (380, 60), pin(c, ic, "VCC1"))
    wire(c, pin(c, ic, "EN12"), (320, 180), (320, 60))
    wire(c, pin(c, s1, "1"), (290, 60))
    wire(c, pin(c, s2, "1"), (250, 60))
    wire(c, pin(c, s1, "2"), (290, 190), pin(c, ic, "1A"))
    wire(c, pin(c, s2, "2"), (250, 200), pin(c, ic, "2A"))
    wire(c, pin(c, ic, "1Y"), (500, 190), (500, 140), (540, 140), pin(c, m, "1"))
    wire(c, pin(c, ic, "2Y"), (480, 200), (480, 260), (540, 260), pin(c, m, "2"))
    wire(c, pin(c, ic, "EN34"), (330, 230), (330, 330))
    wire(c, pin(c, ic, "GND"), (400, 330))
    wire(c, pin(c, reg, "GND"), (150, 330))
    wire(c, pin(c, b, "-"), (0, 330), (400, 330))
    c.add("ground", 0, 330)
    s1.ref, s2.ref = "S1", "S2"
    c.add("note", 260, 400, props={"text": "Close S1 and the motor turns one way; close S2 instead and it turns the other way.\n"
                                            "Both or neither: it stops. The 7805 makes the 5 V the chip's logic needs."})
    return c


def relay_reversing():
    """A DPDT relay swaps a motor's connections over when its coil is switched on."""
    c = Circuit()
    c.title = "Relay reversing a motor (DPDT)"
    b = c.add("battery", 0, 150, rot=1, props={"voltage": 9})                  # + (0,120) - (0,180)
    s1 = c.add("switch", 100, 50, rot=1)                                       # (100,20)-(100,80)
    rl = c.add("relay_dpdt", 200, 150, props={"voltage": 9})
    d = c.add("diode", 130, 150, rot=3, props={"model": "1N4001"})
    m = c.add("motor", 460, 150, rot=1, props={"voltage": 9})                  # 1 (460,120) 2 (460,180)
    assert pin(c, rl, "C1") == (160, 120) and pin(c, rl, "COM1") == (200, 130) and pin(c, rl, "NO2") == (240, 180)
    assert pin(c, d, "K")[1] < pin(c, d, "A")[1], (pin(c, d, "K"), pin(c, d, "A"))
    dk, da = pin(c, d, "K"), pin(c, d, "A")
    wire(c, pin(c, b, "+"), (0, 0), (380, 0))
    wire(c, pin(c, s1, "1"), (100, 0))
    wire(c, pin(c, s1, "2"), (100, 90), (160, 90), pin(c, rl, "C1"))
    wire(c, dk, (dk[0], 90))
    wire(c, da, (da[0], 300))
    wire(c, pin(c, rl, "C2"), (160, 300))
    wire(c, pin(c, rl, "NO2"), (380, 180), (380, 0))
    wire(c, pin(c, rl, "NC1"), (380, 120))
    wire(c, pin(c, rl, "NO1"), (320, 140), (320, 300))
    wire(c, pin(c, rl, "NC2"), (320, 160))
    wire(c, pin(c, rl, "COM1"), (200, 60), (460, 60), pin(c, m, "1"))
    wire(c, pin(c, rl, "COM2"), (200, 240), (460, 240), pin(c, m, "2"))
    wire(c, pin(c, b, "-"), (0, 300), (320, 300))
    c.add("ground", 0, 300)
    s1.ref = "S1"
    c.add("note", 240, 370, props={"text": "Click S1 while it runs: the relay clicks over and both of its switches swap\n"
                                            "the motor's connections, so it spins the other way. D1 catches the coil's spike."})
    return c


NEW_14 = (thyristor_alarm, power_supply_5v, rgb_mixer, counter_4026, motor_reversing, l293d_motor, relay_reversing)


def main(only=None):
    os.makedirs(OUT, exist_ok=True)
    for fn in (led_and_resistor, voltage_divider, night_light, two_way_switch, capacitor_charging,
               buzzer_and_motor, flasher_555, led_chaser, opamp_light_sensor, logic_gates, mosfet_motor,
               rc_filter_graph, binary_display, relay_lamp, motor_load, doorbell_555, burglar_alarm,
               rain_alarm, buck_converter, optoisolator, tl431_reference,
               shift_register_595) + NEW_14:
        if only and fn not in only:
            continue
        c = fn()
        path = os.path.join(OUT, c.title + ".wirely")
        c.save(path)
        open_pins = c.unconnected_pins()
        print(f"{path}: {len(c.components)} parts, {len(c.wires)} wires, {len(c.nets())} nets,"
              f" unconnected pins: {len(open_pins)}")


if __name__ == "__main__":
    main()
