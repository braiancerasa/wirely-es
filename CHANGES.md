# Cambios

## 1.5.3 — Lecturas con sentido para condensadores, inductores y transistores
- **Los condensadores ya no muestran potencia.** Un condensador que se carga o se descarga toma o devuelve
  energía, pero no convierte nada de eso en calor, así que la lectura en «mW» que tenía al lado (voltaje ×
  corriente) inducía a error. Un condensador ideal ahora muestra solo su voltaje y su corriente.
- **Los inductores muestran solo lo que realmente disipan** (la pequeña pérdida de la bobina), no la energía que
  entra y sale de su campo magnético.
- **Los MOSFET muestran su corriente de drenador.** La lectura era la del voltaje y la corriente de la compuerta,
  que siempre es de unos 0 A, así que un MOSFET que conmutaba un motor parecía no dejar pasar nada. Ahora muestra
  el voltaje entre drenador y fuente y la corriente que circula por él (la corriente de drenador).
- **Los transistores NPN y PNP** muestran de la misma manera el voltaje entre colector y emisor y la corriente de
  colector, en lugar de los de la base.
- Nueva prueba que cubre todo lo anterior.

## 1.5.2 — Símbolos de EE. UU., el PWM se ve estable incluso cuando la simulación no da abasto, y la conmutación veloz corre más rápido
- **Nueva dirección: https://wirely-app.github.io/** (código: github.com/wirely-app/wirely-app.github.io). La
  dirección anterior redirige allí, mantiene funcionando los enlaces compartidos y traslada el trabajo sin guardar
  que el navegador conservaba.
- **Símbolos de EE. UU.:** Ver → Símbolos EE. UU. dibuja los componentes al estilo estadounidense: resistencias en
  zigzag (y resistencias variables, potenciómetros, termistores y LDR), un fusible en forma de S, una placa − curva
  en los condensadores electrolíticos y un filamento en las lámparas. Solo cambia el aspecto; se recuerda para la
  próxima vez.
- La descripción de la resistencia ya no menciona una «vista realista» que no existe.
- **El sitio web cambia a una versión nueva de inmediato** (o pregunta si hay trabajo sin guardar) en lugar de
  hacerlo solo en la próxima visita.
- **Los LEDs con PWM ya no parpadean cuando un circuito cargado se ejecuta más lento que el tiempo real:** el
  promedio que hace el ojo ahora abarca el tramo correcto de tiempo simulado según la velocidad elegida, y no según
  lo rápido que logre seguir la computadora. Con una velocidad de cámara lenta todavía se los ve encenderse y
  apagarse.
- **Simulación más rápida de la conmutación veloz** (555, PWM, el convertidor reductor): después de un cambio
  repentino, el simulador recupera la velocidad antes y da pasos más grandes cuando poco está cambiando. El
  *Regulador de brillo PWM* se ejecuta un 40 % más rápido y el *Timbre con 555* casi al doble de velocidad, con la
  misma precisión (las frecuencias del 555 no cambian).

## 1.5.1 — El PWM atenúa LEDs y lámparas
- **Los LEDs, las lámparas y las pantallas se ven tan brillantes como los vería su ojo:** su luz se promedia en cada
  momento en pantalla, así que el PWM (encender y apagar por completo más rápido de lo que puede ver) los hace ver
  con un brillo estable y más tenue, como en la vida real, en lugar de parpadear al azar. Baje la velocidad de la
  simulación y podrá verlos encenderse y apagarse. Esto funciona también con LEDs RGB (aplique PWM a un color para
  cambiar la mezcla) y con pantallas de 7 segmentos multiplexadas.
- Nuevo ejemplo: *Regulador de brillo PWM (555)* — gire la perilla para atenuar un LED y una lámpara.
- El sitio web muestra su número de versión junto al logotipo.
- **Mucha menos CPU mientras se ejecuta:** la cuadrícula de puntos se mantiene ya dibujada en lugar de dibujarse
  punto por punto en cada cuadro, los componentes y los cables solo se vuelven a dibujar cuando cambian, un cuadro
  en el que nada se ve distinto no se dibuja en absoluto, y los puntos del flujo de corriente y el gráfico hacen
  menos trabajo. Por ejemplo, la Luz nocturna pasó de cerca del 60 % de un núcleo de CPU a menos del 10 % en la app
  de escritorio. Se ve exactamente igual. La versión para navegador también gana.

## 1.5.0 — componentes nuevos, un cuadro de unidades para los valores, lecturas móviles y muchas correcciones
- **Un cuadro de unidades junto a los valores:** en las propiedades de un componente, la resistencia tiene
  Ω / kΩ / MΩ junto al número, la capacidad pF / nF / µF / mF / F, la inductancia µH / mH / H y la frecuencia
  Hz / kHz / MHz. Escribir el valor completo (4k7, 100n) sigue funcionando — se ordena en el número y su escala.
- **Reloj de cuarzo:** un reloj de onda cuadrada exacto para lógica (ajuste su frecuencia).
- **Motor paso a paso** (48 o 200 pasos por vuelta): su eje gira un paso cada vez que cambian las bobinas —
  acciónelo con un L293D. Se puede ver girar el eje.
- **Conmutador rotatorio** (1 polo, 4 posiciones: haga clic para girarlo) y un **teclado de 12 teclas** (filas ×
  columnas, como el de una cerradura: mantenga presionada una tecla).
- **Biestable JK** (4027) y **compuerta NAND Schmitt** (4093).
- Nuevos ejemplos: *Motor paso a paso (reloj de cuarzo + L293D)*, *Teclado (qué tecla se presiona)*, *Contador
  binario (flip-flops JK)*, *Intermitente con NAND Schmitt (4093)* y *Conmutador rotatorio (elegir un LED)*.
- **Lógica al encender:** una entrada que simplemente está en alto desde el principio ya no cuenta como flanco de
  reloj, así que los contadores y los biestables arrancan en 0.
- **Arrastre una lectura** (fijada, o con Lecturas activado) para apartarla del camino; una línea de puntos muestra
  a qué pertenece.

Errores encontrados al revisar cada ejemplo paso a paso y probar cada componente en miles de circuitos aleatorios:
- **Las corrientes de los cables junto a los símbolos de 0 V** (al pasar el mouse, en Lecturas y en los puntos de
  flujo) podían ser incorrectas — p. ej. 7,3 mA en lugar de 14,8 mA en la Luz nocturna, o en el ejemplo del
  registro de desplazamiento. Las lecturas y los voltajes de los componentes siempre fueron correctos.
- **Lecturas en el momento en que algo conmuta:** los reguladores, los 555, los chips lógicos, los relés y los
  motores mostraban durante un paso la corriente del estado al que estaban conmutando *hacia* (un 7805 mostraba
  137 A al encender). El 555 además omitía la corriente de su pin CTRL.
- **Los chips y las pantallas muestran su potencia** en Lecturas (mostraban 0 W).
- **Los componentes mal conectados ya no congelan la simulación:** un regulador de voltaje con la entrada y la
  salida invertidas (o conectado de cualquier otra forma incorrecta), un TL431 al revés o con REF en la
  alimentación, un amplificador operacional cuya salida queda fuera de su alimentación, y un tiristor quemado.
- **Los reguladores de voltaje** dejan pasar corriente de OUT a IN cuando se los conecta al revés, como los reales.
- **Los amplificadores operacionales** se destruyen por una alimentación invertida, o porque su salida se fuerza
  muy por fuera de su alimentación.
- **Los tiristores** ahora encienden bobinas de relé (y otras bobinas): antes se soltaban mientras la corriente de la
  bobina todavía estaba creciendo, incluso con la compuerta excitada.
- **Tiristores:** demasiada corriente de compuerta (compuerta conectada directamente a la alimentación) los quema,
  con un mensaje que indica agregar una resistencia de compuerta.
- **Etiquetas:** los nombres de los componentes ya no se superponen a los pines cuando los chips y los reguladores
  están girados, la etiqueta del puente rectificador queda despejada de sus pines, el nombre del LED RGB ya no tiene
  sus flechas de luz atravesándolo, y los nombres de los pines de un chip girado de costado corren a lo largo de sus
  pines en lugar de superponerse.

## 1.4.1 — corrección del LED RGB, LEDs más brillantes
- **LEDs RGB:** el verde ahora es el mismo tipo de chip que el azul (unos 3,1 V, como los LEDs RGB reales), así que
  el verde y el azul en una misma resistencia comparten la corriente y se mezclan. (El rojo, de unos 2 V, todavía se
  lleva casi toda la corriente si comparte una resistencia con ellos — como en uno real; dé a cada color su propia
  resistencia para mezclar cualquier color.)
- **Los LEDs se ven más brillantes cuando están encendidos:** un color más intenso y un brillo más grande y luminoso.

## 1.4.0 — Lecturas y 16 componentes nuevos
- **Lecturas:** un botón nuevo en la barra de herramientas muestra el voltaje y la corriente en cada cable, y el
  voltaje, la corriente y la potencia de cada componente mientras el circuito se ejecuta. Haga clic en cualquier
  cable o componente mientras se ejecuta para fijar solo su lectura. **Simular → Copiar lecturas** copia las
  lecturas de cada componente como una tabla para pegarla en una planilla de cálculo.
- **LEDs bicolor** (de 2 y de 3 patas) y un **LED RGB** que mezcla sus colores.
- **Puente rectificador** y un **transformador** (ajuste su relación de vueltas; advierte si le aplica DC).
- **Tiristor (SCR):** C106D, 2N5060, TIC106D y BT151 — se enclavan con un pulso de compuerta y permanecen
  encendidos hasta que la corriente cae por debajo de su corriente de mantenimiento.
- **Reguladores de voltaje:** 7805, 7809, 7812, LM1117-3.3 y el LM317 ajustable, con caída de voltaje, límite de
  corriente y apagado térmico (coloque un disipador en sus propiedades).
- **Comparadores:** LM393 y LM311 (salidas de colector abierto).
- **Controlador de motor L293D:** cuatro semipuentes H con diodos de pico incorporados — accione un motor en ambos
  sentidos desde pines de lógica, o ajuste su velocidad con PWM en el pin de habilitación. Se apaga si se calienta
  demasiado.
- **4026** contador de décadas con salidas de 7 segmentos, y el **4060** contador con su propio oscilador.
- **Interruptor DPDT**, **relé DPDT** (dos contactos conmutados), **sensor de efecto Hall** (haga clic para acercar
  el imán) y un **solenoide** que hace clic.
- Nuevos ejemplos: *Alarma con tiristor (enclavada)*, *Fuente de 5 V (7805)*, *Mezclador de color RGB*,
  *Contador (555 + 4026)*, *Inversión de motor (DPDT)*, *Controlador de motor (L293D)* e *Inversión de motor con
  relé (DPDT)*.
- Los reguladores de voltaje ahora tienen una caída de voltaje adecuada (unos 1,2 V con carga liviana y 2 V a 1 A
  para un 78xx), y ya no se quedan trabados cuando una batería baja bajo carga.
- El sitio web cuenta las visitas con GoatCounter (sin cookies ni datos personales).

## 1.3.0 — componentes pedidos por usuarios y Wirely en su navegador web
- **Wirely Web:** toda la app se ejecuta en un navegador web, así que funciona en **Chromebooks** y en computadoras
  de la escuela sin nada que instalar — en https://wirely-app.github.io/. Es el propio código Python de la app de
  escritorio (la hoja, los símbolos y el simulador) ejecutándose en el navegador con Pyodide, así que se ve y se
  comporta igual.
- En el navegador: abra y guarde archivos `.wirely` (funcionan en ambas versiones), todos los ejemplos, el gráfico,
  el sonido, las imágenes PNG, la lista de materiales, **enlaces que llevan un circuito** (para Google Classroom /
  Teams), funciona **sin conexión** después de la primera visita, se instala como app, y admite gestos de pantalla
  táctil y touchpad.
- En el gráfico, una traza curva ya no oculta las líneas de la cuadrícula ni las demás trazas que hay debajo.
- **Registros de desplazamiento:** 74HC164 (entrada serie, salida paralelo), 74HC595 (con registro de salida y
  habilitación de salida), 74HC165 (entrada paralelo, salida serie) y 74HC597 (con registro de entrada). Advierten
  si se los usa por encima de su límite de 6 V.
- **Conmutador analógico 4051** (CD4051B y 74HC4051), con la resistencia de encendido de la hoja de datos de cada
  tipo según su voltaje de alimentación.
- **Referencias ajustables en derivación TL431 / TLV431:** Vout = Vref × (1 + R1/R2), con sus límites de corriente
  y voltaje.
- **Relé de estado sólido (TLP3122A):** salida de foto-MOSFET que conmuta AC o DC, y se enciende en alrededor de un
  milisegundo.
- MOSFET **2N7002**.
- **Cada tipo de componente está explicado:** elija un tipo en las propiedades de un componente y una línea debajo
  indica para qué sirve.
- Nuevos ejemplos: *Referencia ajustable TL431* y *Registro de desplazamiento (74HC595)*.
- Las etiquetas de los chips quedan encima del chip en lugar de sobre sus pines.

## 1.2.0 — lámparas de filamento reales
- **Las lámparas de filamento se comportan como las reales:** la resistencia del filamento aumenta a medida que se
  calienta, así que la curva corriente–voltaje se dobla (I ∝ V^0.6, como se mide en lámparas reales — el trabajo
  práctico obligatorio de secundaria), una lámpara fría recibe una corriente de irrupción de unas 11 veces su
  corriente de régimen al encenderse, y tarda un momento en iluminarse y en apagarse.
- **Las resistencias se calientan durante alrededor de un segundo** antes de quemarse, así que un pico breve (como
  el encendido de una lámpara) está bien, pero una sobrecarga sostenida igual las quema.

## 1.1.0 — MOSFET y amplificadores operacionales más precisos
- **MOSFET ajustados a sus hojas de datos:** voltaje de umbral y resistencia de encendido a los voltajes de
  compuerta de la hoja de datos, movilidad que cae con un voltaje de compuerta alto, el diodo de cuerpo, resistencia
  interna de compuerta y capacitancias de compuerta y drenador que dependen del voltaje. La conmutación ahora lleva
  tiempo real y muestra la meseta de Miller; la carga de compuerta coincide con las hojas de datos (AO3400 6,1 nC
  contra 6 nC, FQP27P06 32,3 nC contra 33 nC) y los retardos de conmutación coinciden con ngspice.
- **Amplificadores operacionales ajustados a sus hojas de datos:** ganancia en lazo abierto, corriente y resistencia
  de polarización de entrada, corriente de alimentación, excursión de salida que depende de la carga, límites
  separados de fuente y sumidero, y el LM358 que llega a 0 V pero no al riel superior. La corriente de salida se
  toma realmente de los pines de alimentación, y un exceso de voltaje de alimentación destruye el chip.
- Los diodos resisten picos breves de corriente (como los reales) en lugar de reventar ante un pico de un
  nanosegundo.
- **Los MOSFET se perforan por encima de su voltaje nominal** (avalancha, a alrededor del 15 % por encima): un pico
  breve se absorbe hasta la energía de avalancha nominal del componente (los MOSFET de potencia sobreviven al pico
  de una bobina de relé; un 2N7000 no), pero una alimentación por encima de la nominal lo destruye, con un mensaje
  que explica por qué.
- **Los motores se queman** con mucho más que su voltaje nominal (un motor de 9 V con 150 V gira demasiado rápido y
  se sobrecalienta).
- El simulador es unas dos veces más rápido en todos los circuitos (y mucho más rápido con MOSFET).
- El instalador limpia los archivos de biblioteca de la versión anterior al actualizar.
- Linux: prefiere X11/XWayland y recurre a Wayland; la compilación automática ahora prueba ambos.

## 1.0.0 — primera versión oficial
Todo lo siguiente, junto: el editor de circuitos (r1), la simulación en vivo (r2), los chips, la lógica y el
gráfico (r3), el sonido, los relés, los motores y los sensores (r4), y el nombre Wirely, los iconos y las descargas
(r5).

- Componente nuevo: **optoacoplador** — PC817, 4N25, 4N35, TLP521 y 6N139 (Darlington), con un
  circuito de ejemplo. Sus dos lados son circuitos verdaderamente separados, cada uno con su propia alimentación.
- Corregido: un circuito unido a otro solo a través de los contactos de un relé o de un optoacoplador ahora obtiene
  su propia referencia de 0 V, así que su propia alimentación puede ser cualquiera (antes, una fuente de DC separada
  allí podía no resolverse).
- El ajuste de tiempo Automático del gráfico ahora sigue la señal repetitiva más rápida de cualquier sonda (antes,
  solo miraba la sonda A — así que un convertidor reductor, donde A es DC suave, mostraba un barrido de 5 segundos
  de una señal de 1 kHz).

## r5 — Wirely (se convirtió en 1.0.0)
- **Nombre nuevo: Wirely** (antes Sparkbench). Los circuitos ahora son archivos `.wirely`; los antiguos `.spark`
  todavía se abren.
- **Logotipo nuevo** (una W dibujada como un cable, con corriente que circula por él) y un **icono de archivo** para
  los circuitos `.wirely`.
- **Pantalla de inicio** con la versión y la revisión mientras Wirely arranca.
- **Descargas compiladas automáticamente en GitHub**: instalador de Windows (con asociación de archivos `.wirely`),
  `.dmg` de Mac (con icono de documento) y AppImage de Linux (más un script para agregarlo al menú de aplicaciones y
  asociar `.wirely`). Cada push ejecuta las pruebas.
- Hacer doble clic en un archivo `.wirely` en el Finder lo abre en Mac; el propio icono de Wirely en la barra de
  tareas de Windows.
- **Ciclo de trabajo del generador de señales** (PWM) para ondas cuadradas.
- Ejemplo nuevo: **convertidor reductor** (12 V → unos 6 V). Su voltaje de salida, su rizado y la corriente del
  inductor se prueban contra las fórmulas de los libros y contra ngspice (dentro del 0,5 %).

## r4 — sonido, relés, motores y sensores
- **Sonido:** los zumbadores zumban, los parlantes reproducen la señal simulada a su tono real, los motores zumban,
  los relés hacen clic. Botón de sonido para apagarlo. Wirely verifica el sonido de la computadora de forma segura
  primero, así que una configuración de audio rota nunca puede hacerlo fallar.
- **Relé** (bobina + contactos conmutados, activación al 75 %, desactivación al 30 %) e **inductor**. Conmutar una
  bobina sin diodo de rueda libre produce un pico de voltaje real que destruye el transistor — con un mensaje que
  explica la solución.
- **Los motores** ahora tienen fuerza contraelectromotriz: gran corriente de arranque y luego menos; un ajuste de
  *Carga* los frena y hace que consuman más corriente; pase el mouse para ver su velocidad en rpm.
- Sensores nuevos: **interruptor magnético** (haga clic para acercar el imán), **interruptor de inclinación**,
  **sensor de humedad** (deslizador), **fototransistor** (deslizador de luz).
- Muchos tipos más: MOSFET BS170, IRLZ44N (nivel lógico), IRF530, IRF3205, AO3400, IRF9530, FQP27P06, IRLML6402;
  transistores BC547, BC337, 2N2222, TIP120, BC557, BC327, 2N2907, TIP125; diodos 1N4007, 1N5408, 1N5819
  (Schottky); amplificador operacional TL071.
- **Lecturas al pasar el mouse:** mientras se ejecuta, pase el mouse sobre un cable para ver su voltaje y su
  corriente (con sentido).
- **Notas de texto** para hojas de trabajo, **menús contextuales**, **guardado automático** cada minuto con
  recuperación tras un bloqueo.
- Corregido: un MOSFET con la compuerta desconectada se encendía solo; el brillo del LED ahora está centrado en el
  LED.
- Cinco ejemplos nuevos: relé que enciende una lámpara, motor y carga, timbre con 555, alarma antirrobo, alarma de
  lluvia.

## r3 — chips, lógica y el gráfico
- **Gráfico (osciloscopio):** coloque sondas de gráfico A–D sobre los cables y presione Ejecutar. Tiempo y voltios
  por cuadro automáticos o fijos, lecturas en vivo con frecuencia, pase el mouse para leer valores, guarde el
  gráfico como imagen.
- **Sonda lógica:** muestra H / L / ? sobre lo que toca.
- Componentes nuevos: **temporizador 555**, **amplificador operacional** (741, LM358, rail-to-rail), **compuertas
  NOT / AND / OR / NAND / NOR / XOR / NOT Schmitt**, **biestable tipo D**, **contador de décadas 4017**,
  **decodificador 4511**, **display de 7 segmentos**, **MOSFET de canal N y P** (2N7000, IRF540, BS250, IRF9540),
  **generador de señales** (cuadrada / senoidal / triangular).
- El solucionador cae exactamente en los momentos de conmutación, así que la temporización del 555 coincide con las
  fórmulas de los libros (dentro del 1 %).
- Los chips lógicos y los amplificadores operacionales con pines de alimentación desconectados se alimentan
  automáticamente de la fuente del circuito.
- Siete ejemplos nuevos: intermitente LED con 555, luces secuenciales (555 + 4017), sensor de oscuridad con
  amplificador operacional, compuertas lógicas, conmutación de motor con MOSFET, filtro RC en el gráfico, binario a
  7 segmentos.
- Los deslizadores encuentran un lugar libre junto a su componente.

## r2 — simulación en vivo
- **Ejecutar / Pausar / Detener** (F5 / F6 / Shift+F5) y un control de velocidad (desde 10× más rápido hasta 1/1000
  de la velocidad).
- El propio solucionador de circuitos de Wirely: Newton–Raphson para diodos, LEDs y transistores; condensadores en el
  tiempo con control automático del paso. Verificado contra respuestas calculadas a mano y ngspice en las pruebas.
- Los LEDs brillan con su color, las lámparas se encienden, los motores giran, los zumbadores muestran ondas de
  sonido, los medidores muestran una lectura.
- Cables coloreados por voltaje (con una referencia de colores) y flujo de corriente animado — ambos se pueden
  desactivar.
- Haga clic en interruptores y conmutadores, mantenga presionados los pulsadores, arrastre los deslizadores de los
  LDR (nivel de luz), termistores (temperatura) y resistencias variables mientras se ejecuta. Haga doble clic en un
  componente para cambiar su valor en vivo.
- Los componentes sobrecargados lo muestran: LEDs, diodos, transistores y electrolíticos revientan, las lámparas y
  los fusibles se queman, las resistencias se queman — con un mensaje que dice qué pasó y cómo solucionarlo. Las
  baterías en cortocircuito se señalan. Detener repara todo.
- Pase el mouse sobre un cable o componente mientras se ejecuta para leer voltaje, corriente y potencia.
- Dos ejemplos nuevos: *Carga de un condensador* y *Zumbador y motor*.
- Corregido: «Diodos y LEDs» perdía su «&» en Windows; los botones deshabilitados ahora se ven deshabilitados.

## r1 — editor de circuitos (primera versión)
- Galería de componentes con 29 componentes en 9 grupos, símbolos estilo británico/IEC, cuadro de búsqueda.
- Coloque componentes haciendo clic o arrastrando; rote (R / Shift+R), voltee (F), mueva, elimine.
- Cables: arrastre de pin a pin, o haga clic en las esquinas; los cables se mantienen rectos, eligen la esquina que
  no pasa por un componente y siguen a los componentes cuando los mueve o los rota; derive de un cable (W) con un
  punto de unión; arrastre un cable hacia un lado o mueva su extremo suelto.
- Haga doble clic en un componente para cambiar sus valores — escríbalos de la forma habitual (10k, 4k7, 100n,
  4.7µ).
- Deshacer / rehacer para todo, copiar / cortar / pegar / duplicar.
- Guarde y abra circuitos (archivos .wirely), archivos recientes, cuatro circuitos de ejemplo.
- Exporte el diagrama como PNG, SVG o PDF (siempre negro sobre blanco), cópielo como imagen, lista de materiales.
- Temas claro y oscuro, cuadrícula de puntos, ajuste de zoom suave.
