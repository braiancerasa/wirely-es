**Wirely ES 1.5.3:** Lecturas que tienen sentido para capacitores, inductores y transistores.

_Esta es una traducción no oficial al español de Wirely, basada en el proyecto original [Wirely](https://github.com/wirely-app) creado por su autor. Todo el crédito del desarrollo corresponde al autor original; aquí solo se tradujo la interfaz al español. El resto del funcionamiento es idéntico al original._

**_Distribuido bajo la misma licencia que el proyecto original._**

Usalo en tu navegador — no es necesario instalar

[wirely-es-web](https://braiancerasa.github.io/wirely-es/) — funciona en Chromebooks, y en Chrome, Edge, Firefox y Safari en cualquier computadora. Se actualiza solo.

Descargas (aplicación de escritorio)

- Windows (64 bits): Wirely-Setup-1.5.3.exe — ejecutalo; actualiza una instalación existente de Wirely. Si SmartScreen te advierte (el instalador todavía no está firmado digitalmente), hacé clic en Más información → Ejecutar de todas formas.

- Linux (x86_64): Wirely-1.5.3-x86_64.AppImage — ejecutá chmod +x Wirely-1.5.3-x86_64.AppImage, y después ejecutalo.

Corregido

- Los capacitores ya no muestran potencia. Un capacitor que se carga almacena energía en lugar de convertirla en calor, así que la cifra en "mW" a su lado era engañosa. Ahora muestra solo voltaje y corriente.

- Los inductores muestran solo la pequeña pérdida en la bobina, no la energía que entra y sale de su campo magnético.

- Los MOSFET muestran la corriente que fluye a través de ellos. Antes la lectura era la de la compuerta (siempre alrededor de 0 A), así que un MOSFET conmutando un motor parecía no estar pasando nada. Ahora muestra el voltaje drenaje-fuente y la corriente de drenaje.

- Los transistores NPN y PNP ahora muestran el voltaje colector-emisor y la corriente de colector, no la de la base.