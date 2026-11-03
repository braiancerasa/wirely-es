**Wirely ES 1.5.4.4:** el generador de señal entrega siempre por el polo positivo.

_Wirely es un simulador de circuitos creado por Richard Willmott. Esta es una versión no oficial en español (Argentina) y un fork del proyecto original: además de la traducción, agrega funciones y correcciones propias. No está afiliada al autor ni es una versión oficial. Todo el crédito del programa, el diseño y el código original corresponde a su autor._

_Distribuido bajo la misma licencia que el proyecto original (GNU GPL v3)._

Úselo en su navegador — no hace falta instalar nada

[wirely-es-web](https://braiancerasa.github.io/wirely-es/) — funciona en Chromebooks y en Chrome, Edge, Firefox y Safari en cualquier computadora. Se actualiza solo.

Descargas (aplicación de escritorio)

- Windows (64 bits): Wirely-Setup-1.5.4.4.exe — ejecútelo; actualiza una instalación existente. Si SmartScreen le advierte (el instalador todavía no está firmado digitalmente), haga clic en Más información → Ejecutar de todas formas.

- macOS (Apple Silicon e Intel): Wirely-1.5.4.4-mac-arm64.dmg para Mac con chip Apple (M1 o posterior) y Wirely-1.5.4.4-mac-intel.dmg para Mac con procesador Intel. Abra el .dmg y arrastre Wirely a la carpeta Aplicaciones. La primera vez, si macOS lo bloquea porque la app todavía no está firmada, vaya a Ajustes del Sistema → Privacidad y seguridad y elija Abrir igualmente. Requiere macOS 14 o posterior.

- Linux (x86_64): Wirely-1.5.4.4-x86_64.AppImage — ejecute chmod +x Wirely-1.5.4.4-x86_64.AppImage y después ejecútelo.

Corregido

- **Generador de señal.** En un circuito sin ningún símbolo de 0 V, el generador tomaba como referencia un cable cualquiera en lugar de su propia pata negativa. Por eso el voltaje aparecía siempre en el mismo cable, aunque fuera el negativo, y al voltear la pieza no cambiaba de lado. Ahora la pata negativa es la referencia y el voltaje sale siempre por el polo +, esté arriba, abajo, a la izquierda o a la derecha. La descripción de la pieza ahora lo aclara.

Todo lo de la 1.5.4.3 sigue incluido

- **Sonda de corriente (I1–I4)** con la corriente instantánea de su rama y el desfasaje real: la corriente adelanta en un circuito capacitivo y se atrasa en uno inductivo, como en un osciloscopio.

- **Simulación destructiva**, con la opción en el menú Simular y la tilde recordada entre sesiones. Sin la tilde nada se rompe, y al desactivarla se reparan las piezas quemadas.

- **Gráfico que se mueve a mano** al pausar, con las vistas Separados y Superpuestos, el selector de amperes y la planilla CSV con la unidad correcta.

- **Nombres más claros:** «sonda de tensión» e «inductor», y la categoría «Condensadores e inductores».

Cómo usarlo

- El **generador de señal** entrega la onda por su polo +, marcado con un signo + en el símbolo. Su pata negativa es la referencia de 0 V cuando el circuito no tiene un símbolo de 0 V.

- Si quiere fijar la referencia en otro punto, agregue un símbolo **0 V (tierra)**: el generador sigue entregando por el polo +.

- Para ver si una corriente se adelanta o se atrasa, coloque una sonda de tensión y una de corriente y elija **Vista → Superpuestos**.

Pruebas

- Se agregaron nueve pruebas para el generador de señal: las ocho orientaciones posibles y un caso volteado con el polo + abajo. En todas, el polo + entrega el voltaje y el − queda en 0 V. La suite completa pasa, incluidas las comparaciones con ngspice en la compilación automática.

Notas

- La numeración es propia de este fork: el cuarto número es nuestra revisión, así que las versiones nunca se confunden con las del proyecto original (que usa tres números).

- La sonda de corriente, las vistas del gráfico, el selector de amperes, el desplazamiento manual del gráfico, la simulación destructiva, los nombres «sonda de tensión» e «inductor», las flechas y las correcciones de la fase de la sonda de corriente y del generador de señal son mejoras de este fork; no están en el proyecto original.

- El simulador, las piezas y el funcionamiento siguen siendo los de Wirely 1.5.3. La versión 1.5.4 del proyecto original agrega un menú de idiomas (inglés, español, alemán y japonés); este fork no lo incluye porque ya está en español.
