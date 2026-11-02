**Wirely ES 1.5.4.3:** sonda de corriente, gráfico con voltaje y corriente que se mueve a mano, y simulación destructiva.

_Wirely es un simulador de circuitos creado por Richard Willmott. Esta es una versión no oficial en español (Argentina) y un fork del proyecto original: además de la traducción, agrega funciones y correcciones propias. No está afiliada al autor ni es una versión oficial. Todo el crédito del programa, el diseño y el código original corresponde a su autor._

_Distribuido bajo la misma licencia que el proyecto original (GNU GPL v3)._

Úselo en su navegador — no hace falta instalar nada

[wirely-es-web](https://braiancerasa.github.io/wirely-es/) — funciona en Chromebooks y en Chrome, Edge, Firefox y Safari en cualquier computadora. Se actualiza solo.

Descargas (aplicación de escritorio)

- Windows (64 bits): Wirely-Setup-1.5.4.3.exe — ejecútelo; actualiza una instalación existente. Si SmartScreen le advierte (el instalador todavía no está firmado digitalmente), haga clic en Más información → Ejecutar de todas formas.

- macOS (Apple Silicon e Intel): Wirely-1.5.4.3-mac-arm64.dmg para Mac con chip Apple (M1 o posterior) y Wirely-1.5.4.3-mac-intel.dmg para Mac con procesador Intel. Abra el .dmg y arrastre Wirely a la carpeta Aplicaciones. La primera vez, si macOS lo bloquea porque la app todavía no está firmada, vaya a Ajustes del Sistema → Privacidad y seguridad y elija Abrir igualmente. Requiere macOS 14 o posterior.

- Linux (x86_64): Wirely-1.5.4.3-x86_64.AppImage — ejecute chmod +x Wirely-1.5.4.3-x86_64.AppImage y después ejecútelo.

Novedades

- **Simulación destructiva.** El menú **Simular** tiene una opción nueva, **Simulación destructiva**, marcada con tilde por defecto. Con la tilde, los componentes se calientan y se queman como siempre cuando los sobrecarga. Sin la tilde, todo es indestructible: nada se rompe, y sirve para mirar corrientes, flujos y gráficos sin que el circuito se corte. Las advertencias de calentamiento y sobrecarga siguen apareciendo, y las lecturas de potencia no cambian, así que también sirve para comprobar cálculos. La opción se recuerda entre sesiones, en escritorio y en la web. Al desmarcarla mientras ejecuta, lo que ya estaba roto se repara y la simulación sigue.

- **Sonda de corriente (I1–I4).** En Medidores y sondas hay una pieza nueva para medir la corriente de un cable sin cortarlo ni modificar el circuito. Se apoya sobre el cable y se engancha al que tiene debajo; si el cable se mueve, se vuelve a enganchar sola, igual que la sonda de tensión. Si no toca ningún cable, no mide nada. Es una sonda ideal, sin resistencia de derivación: el circuito funciona exactamente igual que sin ella.

- **Canales de corriente separados.** Las sondas de tensión siguen siendo A–D y las de corriente son I1–I4, cada una con su color. Así se pueden mirar hasta ocho señales a la vez sin mezclar unidades.

- **Gráfico con voltaje y corriente.** El gráfico muestra el valor y la frecuencia de cada sonda, y el cursor da la lectura con su unidad: V o mV para el voltaje, A, mA o µA para la corriente. La planilla CSV y la imagen guardada también llevan la unidad correcta.

- **Dos formas de ver las señales.** El selector **Vista** permite **Separados** (voltaje arriba y corriente abajo, con la misma altura) o **Superpuestos** (las dos en un solo gráfico, con los voltios a la izquierda y los amperes a la derecha). Sirve para comparar si una onda se adelanta o se atrasa respecto de la otra.

- **Selector de amperes.** Al lado de «Voltios» hay un selector «Amperes» con escala automática o 1 mA, 10 mA, 100 mA y 1 A por división. La vista, el tiempo y las escalas se recuerdan entre sesiones. Si solo hay sondas de un tipo, el panel queda como antes.

- **Gráfico que se mueve a mano.** Con la simulación en pausa, arrastre el gráfico hacia la izquierda o la derecha para recorrer el tiempo: hacia atrás llega hasta el inicio de la simulación y hacia adelante, solo hasta donde se pausó. Sirve para alinear una onda con otra y comparar mejor su forma. Al reanudar, el gráfico vuelve solo a seguir el trazo en vivo.

- **Fase de la corriente.** La sonda de corriente muestra la corriente instantánea de la rama donde está puesta, con su desfasaje real: en un circuito capacitivo la corriente adelanta al voltaje y en uno inductivo se atrasa, como en un osciloscopio. El desfasaje cambia al modificar la resistencia, el capacitor, el inductor o la frecuencia. El sentido de la sonda se fija solo con la primera corriente que circula, así que la misma rama se ve igual sin importar de qué lado se dibujó el cable.

- **La versión web también.** La sonda de corriente, los selectores, las dos vistas, la simulación destructiva y el desplazamiento manual del gráfico están en la versión del navegador, con el mismo comportamiento que en escritorio.

- **Sonda de tensión.** La pieza que antes se llamaba «sonda de gráfico» ahora es «sonda de tensión», para distinguirla de la sonda de corriente, que también dibuja en el gráfico. Su funcionamiento no cambia.

- **Inductor.** El componente «Bobina» ahora se llama «Inductor», y su categoría en el menú pasó de «Condensadores y bobinas» a «Condensadores e inductores», para usar el término que se emplea en la práctica.

- **El proyecto se presenta como fork.** El README y el «Acerca de» de escritorio y de la web ahora aclaran que esta es una versión no oficial en español (Argentina) y un fork del original, con funciones y correcciones propias además de la traducción. Ya no figura como una simple traducción.

- **Flechas de los desplegables.** En Windows, los desplegables usan flechas propias, claras u oscuras según el tema, en lugar de la flecha nativa que se veía anticuada.

- **Pruebas.** Se agregaron doce pruebas para la sonda de corriente (cuatro de ellas comparan el desfasaje con el voltaje), cinco para la simulación destructiva y cinco para el desplazamiento manual del gráfico. La suite completa pasa, incluidas las comparaciones con ngspice en la compilación automática.

Cómo usarlo

- Coloque una **sonda de corriente** sobre el cable que quiere medir, elija su canal (I1–I4) y presione Ejecutar. El gráfico se abre solo.

- Para ver las dos señales juntas, elija **Superpuestos**; para compararlas por separado, **Separados**.

- Para comparar dos ondas con más detalle, pause la simulación y arrastre el gráfico: se mueve por el tiempo hasta el inicio de la simulación. Al reanudar, vuelve solo a seguir el trazo en vivo.

- La sonda no corta el cable ni agrega una resistencia: el circuito funciona igual que sin ella.

- Para ver un circuito sin que nada se rompa, desmarque **Simulación destructiva** en el menú Simular: las piezas se siguen calentando y avisando, pero no se queman.

Notas

- La numeración es propia de este fork: el cuarto número es nuestra revisión, así que las versiones nunca se confunden con las del proyecto original (que usa tres números).

- La sonda de corriente, las vistas del gráfico, el selector de amperes, el desplazamiento manual del gráfico, la simulación destructiva, los nombres «sonda de tensión» e «inductor», las flechas y la corrección de la fase de la sonda de corriente son mejoras de este fork; no están en el proyecto original.

- El simulador, las piezas y el funcionamiento siguen siendo los de Wirely 1.5.3. La versión 1.5.4 del proyecto original agrega un menú de idiomas (inglés, español, alemán y japonés); este fork no lo incluye porque ya está en español.
