**Wirely ES 1.5.4.5:** el gráfico acerca el voltaje y la corriente con la rueda, y las escalas se escriben con su unidad.

_Wirely es un simulador de circuitos creado por Richard Willmott. Esta es una versión no oficial en español (Argentina) y un fork del proyecto original: además de la traducción, agrega funciones y correcciones propias. No está afiliada al autor ni es una versión oficial. Todo el crédito del programa, el diseño y el código original corresponde a su autor._

_Distribuido bajo la misma licencia que el proyecto original (GNU GPL v3)._

Úselo en su navegador — no hace falta instalar nada

[wirely-es-web](https://braiancerasa.github.io/wirely-es/) — funciona en Chromebooks y en Chrome, Edge, Firefox y Safari en cualquier computadora. Se actualiza solo.

Descargas (aplicación de escritorio)

- Windows (64 bits): Wirely-Setup-1.5.4.5.exe — ejecútelo; actualiza una instalación existente. Si SmartScreen le advierte (el instalador todavía no está firmado digitalmente), haga clic en Más información → Ejecutar de todas formas.

- macOS (Apple Silicon e Intel): Wirely-1.5.4.5-mac-arm64.dmg para Mac con chip Apple (M1 o posterior) y Wirely-1.5.4.5-mac-intel.dmg para Mac con procesador Intel. Abra el .dmg y arrastre Wirely a la carpeta Aplicaciones. La primera vez, si macOS lo bloquea porque la app todavía no está firmada, vaya a Ajustes del Sistema → Privacidad y seguridad y elija Abrir igualmente. Requiere macOS 14 o posterior.

- Linux (x86_64): Wirely-1.5.4.5-x86_64.AppImage — ejecute chmod +x Wirely-1.5.4.5-x86_64.AppImage y después ejecútelo.

Novedades

- **Zoom vertical con la rueda.** Sobre el gráfico, la rueda del mouse acerca o aleja el voltaje y la corriente a la vez, sin tocar el tiempo. Cada paso cambia el rango un 25 %; hacia arriba acerca y hacia abajo amplía el rango. Si una escala estaba en Automático, el zoom parte del valor que se estaba viendo, así el cambio es continuo.

- **Cero visible y desplazable.** Las escalas automáticas quedan simétricas respecto de 0 y el cero aparece centrado. Para correr el cero de un eje, arrastre su regla lateral hacia arriba o hacia abajo: cada eje se mueve por separado y el desplazamiento se conserva al cambiar la escala o hacer zoom. Un doble clic sobre la regla devuelve ese cero al centro.

- **Escalas con unidad a elección.** El tiempo, el voltaje y la corriente por división ahora se escriben en un cuadro de texto y la unidad se elige en un desplegable: s, ms o µs; V o mV; A, mA o µA. Se admiten valores intermedios, como 2,5 ms o 0,2 V. Un cuadro vacío equivale a Automático, y al cambiar la unidad se conserva la escala física.

- **Igual en el escritorio y en la web**, con las escalas, las unidades y el desplazamiento del cero recordados entre sesiones.

Todo lo de la 1.5.4.4 sigue incluido

- **Generador de señal.** La pata negativa es la referencia y el voltaje sale siempre por el polo +, esté arriba, abajo, a la izquierda o a la derecha. Antes, en un circuito sin ningún símbolo de 0 V, tomaba como referencia un cable cualquiera. La descripción de la pieza ahora lo aclara.

Todo lo de la 1.5.4.3 sigue incluido

- **Sonda de corriente (I1–I4)** con la corriente instantánea de su rama y el desfasaje real: la corriente adelanta en un circuito capacitivo y se atrasa en uno inductivo, como en un osciloscopio.

- **Simulación destructiva**, con la opción en el menú Simular y la tilde recordada entre sesiones. Sin la tilde nada se rompe, y al desactivarla se reparan las piezas quemadas.

- **Gráfico que se mueve a mano** al pausar, con las vistas Separados y Superpuestos, el selector de amperes y la planilla CSV con la unidad correcta.

- **Nombres más claros:** «sonda de tensión» e «inductor», y la categoría «Condensadores e inductores».

Cómo usarlo

- Coloque las sondas, presione **Ejecutar** y pase la rueda del mouse sobre el gráfico para ajustar el alto de las ondas. El tiempo no cambia.

- Escriba el valor por división que quiera y elija la unidad al lado. Si deja el cuadro vacío, el gráfico elige la escala solo (Automático).

- Arrastre la regla lateral de voltaje o de corriente para correr ese cero; haga doble clic para devolverlo al centro. Con el botón izquierdo y en pausa, arrastre el gráfico para moverse por el tiempo.

- Para ver si una corriente se adelanta o se atrasa, coloque una sonda de tensión y una de corriente y elija **Vista → Superpuestos**.

Pruebas

- Se agregaron seis pruebas para el gráfico: el zoom con rueda cambia las dos escalas verticales y conserva el tiempo; el valor escrito y su unidad fijan la escala y la conversión de unidad la conserva; la corriente admite valores intermedios y sus unidades; arrastrar una regla mueve solo ese cero; el cero llega al borde pero nunca sale de vista; y un cuadro vacío mantiene el Automático. La suite completa pasa, incluidas las comparaciones con ngspice en la compilación automática.

Notas

- La numeración es propia de este fork: el cuarto número es nuestra revisión, así que las versiones nunca se confunden con las del proyecto original (que usa tres números).

- La sonda de corriente, las vistas del gráfico, el selector de amperes, el desplazamiento manual del gráfico, el zoom vertical, el cero desplazable, las escalas con unidad, la simulación destructiva, los nombres «sonda de tensión» e «inductor», las flechas y las correcciones de la fase de la sonda de corriente y del generador de señal son mejoras de este fork; no están en el proyecto original.

- El simulador, las piezas y el funcionamiento siguen siendo los de Wirely 1.5.3. La versión 1.5.4 del proyecto original agrega un menú de idiomas (inglés, español, alemán y japonés); este fork no lo incluye porque ya está en español.
