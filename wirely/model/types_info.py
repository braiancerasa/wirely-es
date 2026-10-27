"""What each part type (model number) is good for: shown under the Type box when you double-click a part,
so you can tell, say, why you'd pick an AO3400 over a 2N7002. Figures are typical datasheet values."""

TYPE_INFO = {
    # ---------------------------------------------------------------- diodes
    "1N4001": "Rectificador de uso general: 1 A, 50 V. Para fuentes de alimentación y protección contra "
              "polaridad inversa.",
    "1N4007": "Igual que el 1N4001 pero para 1000 V — la elección habitual en rectificadores de red.",
    "1N4148": "Diodo de señal pequeño y rápido: 0,3 A, 100 V. Para lógica, señales y para absorber los picos "
              "de las bobinas de relés pequeños.",
    "1N5408": "Rectificador grande: 3 A, 1000 V. Para fuentes de alimentación de más corriente.",
    "1N5819": "Schottky: solo unos 0,4 V de caída y muy rápido. Para fuentes conmutadas y protección de "
              "bajo voltaje.",

    # ---------------------------------------------------------------- NPN
    "BC548": "NPN de pequeña señal: 100 mA, 30 V, ganancia de unos 290. El clásico para conmutar LEDs y "
             "relés pequeños.",
    "BC547": "Como el BC548 pero para 45 V.",
    "BC337": "NPN de corriente media: hasta 800 mA, 45 V. Para relés, motores pequeños y zumbadores.",
    "2N3904": "NPN de pequeña señal: 200 mA, 40 V. El equivalente estadounidense habitual del BC548.",
    "2N2222": "NPN de corriente media: hasta 800 mA, 40 V. Un interruptor de uso general muy común.",
    "BD139": "NPN de potencia: 1,5 A, 80 V, en un encapsulado que se puede atornillar a un disipador. Para "
             "motores y audio.",
    "TIP31": "NPN de potencia: 3 A, 40 V. Para motores, lámparas y solenoides.",
    "TIP120": "NPN Darlington: ganancia de unos 1000 y 5 A, así que una corriente de base mínima conmuta una "
              "carga grande — pero cae unos 1 V incluso del todo encendido, así que se calienta.",

    # ---------------------------------------------------------------- PNP
    "BC558": "PNP de pequeña señal: 100 mA, 30 V. Se enciende cuando se lleva la base a nivel bajo; el "
             "complementario del BC548.",
    "BC557": "Como el BC558 pero para 45 V; el complementario del BC547.",
    "BC327": "PNP de corriente media: hasta 800 mA, 45 V; el complementario del BC337.",
    "2N3906": "PNP de pequeña señal: 200 mA, 40 V; el complementario del 2N3904.",
    "2N2907": "PNP de corriente media: hasta 600 mA, 40 V; el complementario del 2N2222.",
    "BD140": "PNP de potencia: 1,5 A, 80 V; el complementario del BD139.",
    "TIP125": "PNP Darlington: ganancia de unos 1000, 5 A; el complementario del TIP120.",

    # ---------------------------------------------------------------- N-channel MOSFETs
    "2N7000": "MOSFET N pequeño (de inserción): 200 mA, 60 V, unos 1,2 Ω encendido con 10 V en la puerta. "
              "Bien para LEDs y relés pequeños; con 3,3 V de lógica solo conduce en parte.",
    "2N7002": "La versión de montaje superficial (SOT-23) del 2N7000: unos 0,3 A, 60 V, aproximadamente 1 Ω. "
              "Para cargas pequeñas y adaptación de niveles lógicos, no para motores.",
    "BS170": "MOSFET N pequeño (de inserción): 500 mA, 60 V, unos 1,2 Ω. Como un 2N7000 con un poco más de "
             "corriente.",
    "AO3400": "MOSFET de montaje superficial pequeño que conduce del todo con solo 2,5 V en la puerta: 5,7 A, "
              "30 V, unos 20 mΩ. Elíjalo en lugar de un 2N7002 para conmutar cargas reales (motores, tiras de "
              "LED) directamente desde un microcontrolador de 3,3 V: tiene unas 50 veces menos resistencia.",
    "IRLZ44N": "MOSFET de potencia de nivel lógico (TO-220): conduce del todo desde unos 5 V, 47 A, 55 V, "
               "unos 20 mΩ. El habitual para conmutar motores y tiras de LED desde un Arduino de 5 V.",
    "IRF530": "MOSFET de potencia: 14 A, 100 V, unos 0,12 Ω — pero necesita unos 10 V en la puerta para "
              "conducir del todo.",
    "IRF540": "MOSFET de potencia: 28 A, 100 V, unos 60 mΩ — necesita unos 10 V en la puerta (no es de "
              "nivel lógico: con 5 V solo conduce en parte).",
    "IRF3205": "MOSFET de potencia de muy baja resistencia: 110 A, 55 V, unos 6,5 mΩ. Para motores grandes y "
               "conmutación de mucha corriente; necesita unos 10 V en la puerta.",

    # ---------------------------------------------------------------- P-channel MOSFETs
    "BS250": "MOSFET P pequeño: 230 mA, 45 V, unos 10 Ω. Para conmutar cargas pequeñas en el lado positivo.",
    "IRF9530": "MOSFET P de potencia: 12 A, 100 V, unos 0,2 Ω. Conmuta el lado positivo de una carga; "
               "necesita unos −10 V de puerta a fuente.",
    "IRF9540": "MOSFET P de potencia: 19 A, 100 V, unos 0,15 Ω. El complementario del IRF540.",
    "FQP27P06": "MOSFET P de potencia: 27 A, 60 V, unos 55 mΩ. Un interruptor de lado alto muy usado en "
                "sistemas de 12 V.",
    "IRLML6402": "MOSFET P de montaje superficial minúsculo, que conduce del todo desde −2,5 V: 3,7 A, 20 V, "
                 "unos 50 mΩ. Para conmutar baterías y proteger contra polaridad inversa en circuitos de "
                 "3,3–5 V.",

    # ---------------------------------------------------------------- op-amps
    "741": "El amplificador operacional clásico: necesita una alimentación simétrica (±) de al menos ±5 V y su "
           "salida se queda unos 1 V por debajo de cada riel. Bien para aprender; lento (0,5 V/µs).",
    "LM358": "Operacional doble y económico que funciona con una sola alimentación (3–32 V) y cuyas entradas "
             "y salida llegan a 0 V — pero no al riel superior. Ideal para circuitos de sensores de 5–12 V.",
    "TL071": "Operacional de entrada JFET: casi sin corriente de entrada (30 pA) y rápido (13 V/µs). Para "
             "audio y circuitos de muy alta resistencia; mejor con ±5 V o más.",
    "Rail-to-rail": "Un operacional CMOS moderno cuya salida llega a ambos rieles de alimentación. Ideal con "
                    "alimentaciones de 3,3–5 V.",

    # ---------------------------------------------------------------- optoisolators and relays
    "PC817": "El optoacoplador habitual: ganancia de corriente (CTR) de unos 130 %, salida de 35 V. Para "
             "aislar un microcontrolador de otro circuito.",
    "4N25": "Optoacoplador antiguo con menos ganancia (unos 50 %): dé más corriente a su LED.",
    "4N35": "Como el 4N25 pero con más ganancia (unos 100 %).",
    "TLP521": "Optoacoplador con salida de 55 V: ganancia de unos 100 %.",
    "6N139": "Optoacoplador con salida Darlington: ganancia muy alta, así que una pequeña corriente de LED "
             "conmuta una carga mayor.",
    "TLP3122A": "Relé de estado sólido de fotomosfet: unos 1 mA por su LED conmuta hasta 1,4 A a 60 V, en AC "
                "o DC, sin chasquidos ni contactos que se desgasten. Unos 0,25 Ω encendido.",

    # ---------------------------------------------------------------- shunt regulators
    "TL431": "Referencia de precisión ajustable: mantiene su pin REF a 2,495 V absorbiendo corriente por su "
             "cátodo. Dos resistencias fijan cualquier voltaje de 2,5 a 36 V; hasta 100 mA.",
    "TLV431": "Versión de bajo voltaje del TL431: referencia de 1,24 V, así que funciona en circuitos de "
              "1,24–6 V (rieles de 3,3 V); hasta 15 mA.",

    # ---------------------------------------------------------------- analogue multiplexers
    "CD4051B": "Conmutador analógico de 8 canales (serie 4000): funciona de 3 a 18 V, unos 470 Ω encendido a "
               "5 V y 125 Ω a 15 V.",
    "74HC4051": "Conmutador analógico de 8 canales (74HC): más rápido y de menor resistencia (unos 100 Ω a "
                "5 V) pero solo para alimentaciones de 2–10 V.",

    # ---------------------------------------------------------------- thyristors (1.4.0)
    "C106D": "Tiristor pequeño y sensible: 4 A, 400 V, se dispara con unos 0,2 mA de corriente de puerta. La "
             "elección habitual para alarmas que se enclavan y proyectos escolares.",
    "2N5060": "Tiristor sensible minúsculo (TO-92): 0,8 A, 30 V, se dispara con 0,2 mA. Para enclavamientos "
              "de baja potencia.",
    "TIC106D": "Como el C106D en un encapsulado mayor: 5 A, 400 V, puerta sensible.",
    "BT151": "Tiristor de potencia: 12 A, 500 V, pero necesita unos pocos mA en la puerta y más corriente "
             "para mantenerse encendido.",

    # ---------------------------------------------------------------- regulators
    "7805": "Regulador fijo de 5 V, hasta 1,5 A. Necesita al menos unos 7 V de entrada. El clásico para "
            "alimentar lógica y microcontroladores desde una fuente de 9–12 V.",
    "7809": "Regulador fijo de 9 V, hasta 1,5 A. Necesita al menos unos 11 V de entrada.",
    "7812": "Regulador fijo de 12 V, hasta 1,5 A. Necesita al menos unos 14 V de entrada.",
    "LM1117-3.3": "Regulador de 3,3 V de baja caída, hasta 0,8 A: funciona desde solo unos 4,4 V de entrada "
                  "— para microcontroladores de 3,3 V alimentados desde 5 V. Máximo 15 V de entrada.",

    # ---------------------------------------------------------------- comparators
    "LM393": "Comparador doble para alimentación única (2–36 V): las entradas funcionan hasta 0 V y la salida "
             "es de colector abierto, capaz de absorber unos 16 mA.",
    "LM311": "Comparador más rápido y con salida más potente: absorbe hasta 50 mA, suficiente para un relé o "
             "una lámpara pequeña.",
}


def describe(model: str) -> str:
    return TYPE_INFO.get(str(model), "")
