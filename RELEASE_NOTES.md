**Wirely ES 1.5.4.3:** sonda de corriente y gráfico con voltaje y corriente a la vez.

_Wirely es un simulador de circuitos creado por Richard Willmott. Esta es una versión no oficial en español (Argentina) y un fork del proyecto original: además de la traducción, agrega funciones y correcciones propias. No está afiliada al autor ni es una versión oficial. Todo el crédito del programa, el diseño y el código original corresponde a su autor._

_Distribuido bajo la misma licencia que el proyecto original (GNU GPL v3)._

Úselo en su navegador — no hace falta instalar nada

[wirely-es-web](https://braiancerasa.github.io/wirely-es/) — funciona en Chromebooks y en Chrome, Edge, Firefox y Safari en cualquier computadora. Se actualiza solo.

Descargas (aplicación de escritorio)

- Windows (64 bits): Wirely-Setup-1.5.4.3.exe — ejecútelo; actualiza una instalación existente. Si SmartScreen le advierte (el instalador todavía no está firmado digitalmente), haga clic en Más información → Ejecutar de todas formas.

- macOS (Apple Silicon e Intel): Wirely-1.5.4.3-mac-arm64.dmg para Mac con chip Apple (M1 o posterior) y Wirely-1.5.4.3-mac-intel.dmg para Mac con procesador Intel. Abra el .dmg y arrastre Wirely a la carpeta Aplicaciones. La primera vez, si macOS lo bloquea porque la app todavía no está firmada, vaya a Ajustes del Sistema → Privacidad y seguridad y elija Abrir igualmente. Requiere macOS 14 o posterior.

- Linux (x86_64): Wirely-1.5.4.3-x86_64.AppImage — ejecute chmod +x Wirely-1.5.4.3-x86_64.AppImage y después ejecútelo.

Novedades

- **Sonda de corriente (I1–I4).** En Medidores y sondas hay una pieza nueva para medir la corriente de un cable sin cortarlo ni modificar el circuito. Se apoya sobre el cable y se engancha al que tiene debajo; si el cable se mueve, se vuelve a enganchar sola, igual que la sonda de voltaje. Si no toca ningún cable, no mide nada. Es una sonda ideal, sin resistencia de derivación: el circuito funciona exactamente igual que sin ella.

- **Canales de corriente separados.** Las sondas de voltaje siguen siendo A–D y las de corriente son I1–I4, cada una con su color. Así se pueden mirar hasta ocho señales a la vez sin mezclar unidades.

- **Gráfico con voltaje y corriente.** El gráfico muestra el valor y la frecuencia de cada sonda, y el cursor da la lectura con su unidad: V o mV para el voltaje, A, mA o µA para la corriente. La planilla CSV y la imagen guardada también llevan la unidad correcta.

- **Dos formas de ver las señales.** El selector **Vista** permite **Separados** (voltaje arriba y corriente abajo, con la misma altura) o **Superpuestos** (las dos en un solo gráfico, con los voltios a la izquierda y los amperes a la derecha). Sirve para comparar si una onda se adelanta o se atrasa respecto de la otra.

- **Selector de amperes.** Al lado de «Voltios» hay un selector «Amperes» con escala automática o 1 mA, 10 mA, 100 mA y 1 A por división. La vista, el tiempo y las escalas se recuerdan entre sesiones. Si solo hay sondas de un tipo, el panel queda como antes.

- **La versión web también.** La sonda de corriente, los selectores y las dos vistas están en la versión del navegador, con el mismo comportamiento que en escritorio.

- **El proyecto se presenta como fork.** El README y el «Acerca de» de escritorio y de la web ahora aclaran que esta es una versión no oficial en español (Argentina) y un fork del original, con funciones y correcciones propias además de la traducción. Ya no figura como una simple traducción.

- **Flechas de los desplegables.** En Windows, los desplegables usan flechas propias, claras u oscuras según el tema, en lugar de la flecha nativa que se veía anticuada.

- **Pruebas.** Se agregaron ocho pruebas para la sonda de corriente y el gráfico. La suite completa pasa, incluidas las comparaciones con ngspice en la compilación automática.

Cómo usarlo

- Coloque una **sonda de corriente** sobre el cable que quiere medir, elija su canal (I1–I4) y presione Ejecutar. El gráfico se abre solo.

- Para ver las dos señales juntas, elija **Superpuestos**; para compararlas por separado, **Separados**.

- La sonda no corta el cable ni agrega una resistencia: el circuito funciona igual que sin ella.

Notas

- La numeración es propia de este fork: el cuarto número es nuestra revisión, así que las versiones nunca se confunden con las del proyecto original (que usa tres números).

- La sonda de corriente, las vistas del gráfico, el selector de amperes y las flechas son mejoras de este fork; no están en el proyecto original.

- El simulador, las piezas y el funcionamiento siguen siendo los de Wirely 1.5.3. La versión 1.5.4 del proyecto original agrega un menú de idiomas (inglés, español, alemán y japonés); este fork no lo incluye porque ya está en español.
