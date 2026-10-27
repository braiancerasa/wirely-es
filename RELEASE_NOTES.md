**Wirely 1.5.3: lecturas con sentido para condensadores, inductores y transistores.** (Incluye todo lo de la 1.5.2.)

## Úselo en su navegador — no hay nada que instalar

**https://wirely-app.github.io/** — funciona en Chromebooks y en Chrome, Edge, Firefox y Safari de cualquier computadora. Se actualiza solo.

## Descargas (app de escritorio)

- **Windows (64 bits):** `Wirely-Setup-1.5.3.exe` — ejecútelo; actualiza un Wirely existente. Si SmartScreen le advierte (el instalador aún no está firmado digitalmente), haga clic en **Más información → Ejecutar de todos modos**.
- **Mac (Apple Silicon):** `Wirely-1.5.3-mac-arm64.dmg` — ábralo y arrastre Wirely a Aplicaciones, reemplazando la versión anterior. La primera vez, haga clic derecho en Wirely → **Abrir** → **Abrir**.
- **Linux (x86_64):** `Wirely-1.5.3-x86_64.AppImage` — ejecute `chmod +x Wirely-1.5.3-x86_64.AppImage` y luego ejecútelo.

## Corregido

- **Los condensadores ya no muestran potencia.** Un condensador que se carga almacena energía en lugar de convertirla en calor, así que la cifra en «mW» que tenía al lado inducía a error. Ahora muestra solo el voltaje y la corriente.
- **Los inductores** muestran solo la pequeña pérdida de la bobina, no la energía que entra y sale de su campo magnético.
- **Los MOSFET muestran la corriente que circula por ellos.** La lectura era la de la compuerta (siempre unos 0 A), así que un MOSFET que conmutaba un motor parecía no dejar pasar nada. Ahora muestra el voltaje entre drenador y fuente y la corriente de drenador.
- **Los transistores NPN y PNP** ahora muestran el voltaje entre colector y emisor y la corriente de colector, no los de la base.
