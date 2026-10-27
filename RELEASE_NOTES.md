**Wirely 1.5.2: símbolos de EE. UU., el PWM atenúa LEDs y lámparas como en la vida real, y Wirely usa mucha menos CPU y ejecuta más rápido los circuitos de conmutación veloz.** (Incluye todo lo de la 1.5.1.)

## Úselo en su navegador — no hay nada que instalar

**https://wirely-app.github.io/** — funciona en Chromebooks y en Chrome, Edge, Firefox y Safari de cualquier computadora. Se actualiza solo.

## Descargas (app de escritorio)

- **Windows (64 bits):** `Wirely-Setup-1.5.2.exe` — ejecútelo; actualiza un Wirely existente. Si SmartScreen le advierte (el instalador aún no está firmado digitalmente), haga clic en **Más información → Ejecutar de todos modos**.
- **Mac (Apple Silicon):** `Wirely-1.5.2-mac-arm64.dmg` — ábralo y arrastre Wirely a Aplicaciones, reemplazando la versión anterior. La primera vez, haga clic derecho en Wirely → **Abrir** → **Abrir**.
- **Linux (x86_64):** `Wirely-1.5.2-x86_64.AppImage` — ejecute `chmod +x Wirely-1.5.2-x86_64.AppImage` y luego ejecútelo.

## Novedades

- **Wirely tiene una nueva dirección: [wirely-app.github.io](https://wirely-app.github.io/)**. La dirección anterior redirige allí automáticamente, los enlaces de circuitos compartidos siguen funcionando y cualquier trabajo sin guardar que su navegador conservara se traslada con usted.
- **Símbolos de EE. UU.:** active **Ver → Símbolos EE. UU.** para dibujar los componentes al estilo estadounidense: resistencias en zigzag (y resistencias variables, potenciómetros, termistores y LDR), un fusible en forma de S, una placa − curva en los condensadores electrolíticos y un filamento en las lámparas. Wirely recuerda su elección.
- **El PWM atenúa LEDs y lámparas:** los LEDs, las lámparas y las pantallas ahora se ven tan brillantes como los vería su ojo. Encienda y apague uno por completo más rápido de lo que puede ver (PWM) y se ve con un brillo estable y más tenue, en lugar de parpadear al azar. Esto se mantiene incluso cuando un circuito muy cargado se ejecuta más lento que el tiempo real. Elija una velocidad de cámara lenta y podrá verlo encenderse y apagarse.
- También funciona con **LEDs RGB**: aplique PWM a un color para cambiar la mezcla. Las pantallas de 7 segmentos multiplexadas también se ven estables.
- **Nuevo ejemplo: *Regulador de brillo PWM (555)*.** Gire la perilla mientras ejecuta para atenuar un LED y una lámpara.
- **El sitio web muestra su número de versión** junto al logotipo.
- **El sitio web se actualiza solo:** cuando sale una versión nueva, cambia de inmediato (o pregunta primero si hay trabajo sin guardar), en lugar de mostrar la anterior hasta su próxima visita.

## Corregido

- La descripción de la resistencia ya no menciona una «vista realista» que no existe.

## Más rápido

- **Usa mucha menos CPU mientras un circuito se ejecuta**, así que las laptops se mantienen más frías y silenciosas. Wirely ya no vuelve a dibujar lo que no cambió: la cuadrícula, los componentes y los cables solo se vuelven a dibujar cuando realmente cambian. Por ejemplo, la *Luz nocturna* pasó de cerca del 60 % de un núcleo de CPU a menos del 10 %. Todo se ve exactamente igual. La versión para navegador también es más liviana.
- **Los circuitos de conmutación veloz se simulan más rápido:** temporizadores 555, PWM y el convertidor reductor. El *Regulador de brillo PWM* se ejecuta un 40 % más rápido y el *Timbre con 555* casi al doble de velocidad, con la misma precisión.

425 pruebas automáticas verifican Wirely contra cálculos a mano, hojas de datos y ngspice, y la versión para navegador se prueba en un navegador real antes de publicarse.

Gratuito y de código abierto bajo la **GNU GPL v3**. Los informes de errores, las ideas y los pedidos de componentes son bienvenidos en la pestaña **Issues**.
