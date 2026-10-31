**Wirely ES 1.5.4.2:** cámara lenta para la corriente — vea cómo fluyen los electrones.

_Esta es una traducción no oficial al español de Wirely, basada en el proyecto original [Wirely](https://github.com/wirely-app) creado por su autor. Todo el crédito del desarrollo corresponde al autor original; aquí solo se tradujo la interfaz al español. El resto del funcionamiento es idéntico al original._

**_Distribuido bajo la misma licencia que el proyecto original._**

Usalo en tu navegador — no es necesario instalar

[wirely-es-web](https://braiancerasa.github.io/wirely-es/) — funciona en Chromebooks, y en Chrome, Edge, Firefox y Safari en cualquier computadora. Se actualiza solo.

Descargas (aplicación de escritorio)

- Windows (64 bits): Wirely-Setup-1.5.4.2.exe — ejecutalo; actualiza una instalación existente de Wirely. Si SmartScreen te advierte (el instalador todavía no está firmado digitalmente), hacé clic en Más información → Ejecutar de todas formas.

- macOS (Apple Silicon e Intel): Wirely-1.5.4.2-mac-arm64.dmg para Mac con chip Apple (M1 o posterior) y Wirely-1.5.4.2-mac-intel.dmg para Mac con procesador Intel. Abrí el .dmg y arrastrá Wirely a la carpeta Aplicaciones. La primera vez, si macOS lo bloquea porque la app todavía no está firmada, andá a Ajustes del Sistema → Privacidad y seguridad y elegí Abrir igualmente. Requiere macOS 14 o posterior.

- Linux (x86_64): Wirely-1.5.4.2-x86_64.AppImage — ejecutá chmod +x Wirely-1.5.4.2-x86_64.AppImage, y después ejecutalo.

Novedades

- **Velocidad del flujo de corriente.** Al lado del control de velocidad de simulación hay uno nuevo: ×¼, ×½, ×1, ×2 y ×4. Frena o acelera solo los puntos que recorren los cables, para ver en cámara lenta cómo circula la corriente. No cambia el circuito, ni el voltaje, ni la simulación.

- **El flujo puede seguir la velocidad de simulación.** En el menú **Simular**, la opción «El flujo sigue la velocidad de simulación» hace que los puntos se frenen junto con la cámara lenta, en la misma proporción. Queda guardada para la próxima vez.

- **La velocidad de los puntos ahora depende más de la corriente.** Entre 1 mA y 1 A la velocidad cambia unas cuatro veces (antes cambiaba menos del doble), así que una rama con poca corriente se distingue a simple vista de una con mucha. Las corrientes habituales, como los 15 mA de un LED, se mueven igual que antes.

Cómo usarlo

- Para ver el flujo despacio, ponga el flujo en **×¼** y, si quiere que todo vaya junto, active **El flujo sigue la velocidad de simulación** y baje la velocidad de simulación (por ejemplo, a 1/10).

- El control del flujo es solo para mirar: el circuito sigue funcionando igual, con las mismas corrientes y los mismos voltajes.

Una aclaración sobre las resistencias

- En un circuito serie la corriente es la misma en todos los puntos: los electrones no se frenan al atravesar una resistencia (si lo hicieran, se acumularía carga). Lo que cambia de un lado al otro es la energía por carga, es decir, el voltaje, y eso se ve en el color del cable y en las lecturas.

- Donde sí hay velocidades distintas es en las ramas en paralelo: la rama con más resistencia lleva menos corriente y ahí los puntos van más despacio.

Notas

- La numeración es propia de esta traducción: el cuarto número es nuestra revisión, así que las versiones nunca se confunden con las del proyecto original (que usa tres números).

- El control de velocidad del flujo es una mejora de esta traducción; no está en el proyecto original.

- El simulador, las piezas y el funcionamiento son los mismos que en Wirely 1.5.3. La versión 1.5.4 del proyecto original agrega un menú de idiomas (inglés, español, alemán y japonés); esta traducción no lo incluye porque ya está en español.
