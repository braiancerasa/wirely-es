# Compilar Wirely

Esto es para quienes quieren ejecutar Wirely desde su código fuente, modificarlo o crear los instaladores por su
cuenta. Para simplemente **usar** Wirely, descárguelo desde la [última versión](https://github.com/wirely-app/wirely-app.github.io/releases/latest)
— consulte el [README](README.md).

## Ejecutar desde el código fuente

Necesita Python 3.10–3.13 (64 bits) desde https://www.python.org. En Windows, marque «Add python.exe to PATH».
Luego inícielo — **la primera ejecución instala todo automáticamente**:

- **Windows:** haga doble clic en `run_wirely.bat` (o en `start.py` si Smart App Control bloquea los archivos .bat)
- **Mac / Linux:** ejecute `./run_wirely.sh` (o `python3 start.py`)

El primer inicio crea una carpeta privada `.venv` y descarga Qt y numpy (unos 170 MB). Para reinstalar desde cero,
elimine la carpeta `.venv`. O adminístrelo usted mismo: `pip install -r requirements.txt` y luego `python -m wirely`.

## Compilaciones automáticas en GitHub (Windows, Mac y Linux)

`.github/workflows/build.yml` hace todo en las propias computadoras de GitHub:

- **Cada push** ejecuta las pruebas automáticas.
- **Publicar una versión** compila el instalador de Windows, los `.dmg` de Mac (Apple Silicon e Intel) y el AppImage
  de Linux, verifica que cada uno inicie (su autoprueba) y adjunta los cuatro a la versión publicada.
- **Actions → Build (Windows, Mac, Linux) → Run workflow** hace en cambio una compilación de prueba: los archivos,
  una captura de pantalla de Wirely ejecutándose en Mac y los registros van a un borrador de versión privado
  llamado *Test builds* (solo usted puede verlo).

Para publicar una versión: aumente `__version__` en `wirely/__init__.py` (y en `pyproject.toml`), haga push y luego
en GitHub vaya a **Releases → Draft a new release**, etiquétela (p. ej. `v1.0.1`) y presione **Publish**. Las
descargas aparecen en la versión unos 15 minutos después.

### Numeración de las versiones de esta traducción

Las versiones de esta traducción llevan un cuarto número propio: `1.5.4.1`, `1.5.4.2`, y así. Los tres primeros
números son la versión de la app y el cuarto es la revisión de la traducción, de modo que nunca coincida con una
versión del proyecto original (que usa tres números). Use solo números: el instalador de Windows y los datos del
`.exe` no aceptan sufijos como `-es.1`. En cada versión, las notas aclaran sobre qué versión de Wirely está basada.

## La versión para navegador (Wirely Web)

La versión web está en `web/`. Ejecuta el propio código Python de la app de escritorio — `wirely/model`, `wirely/sim`
y el código de la hoja y del dibujo de `wirely/ui` — en el navegador con [Pyodide](https://pyodide.org). En un
navegador no hay Qt, así que `web/py/qtshim.py` reemplaza las partes de Qt que usa ese código: su QPainter anota lo
que se le pidió dibujar, y `web/app.js` lo reproduce en un canvas de HTML. `web/py/wirely_web.py` es el pegamento
entre la página y Python, y `web/py/fallback/numpy` es un pequeño reemplazo de numpy en Python puro, que se usa solo
si no se puede descargar el numpy real.

**En GitHub** (`.github/workflows/web.yml`): cada push lo compila y lo prueba en un navegador real (Chromium); los
push a la rama principal (`main`) luego lo publican en GitHub Pages, en
<https://braiancerasa.github.io/wirely-es/>. Configuración por única vez:
**Settings → Pages → Build and deployment → Source: GitHub Actions**.

**Usted mismo:**

```
python tools/build_web.py                      # compila _site/ (luego Pyodide se carga desde el CDN de jsDelivr)
cd _site && python -m http.server 8000         # luego abra http://localhost:8000
```

Para incluir Pyodide mismo (así no se carga nada desde un CDN, como hace la compilación de GitHub):
`npm pack pyodide@314.0.7`, descomprímalo y pase `--pyodide <eso>/package` (más `--numpy <wheel>` para numpy).
`python tools/web_smoke.py _site` prueba el sitio compilado en Chromium sin interfaz (`pip install playwright` y
`playwright install chromium` primero). `tests/test_web.py` prueba el pegamento web en Python común.

## Crear un programa de Windows usted mismo

Haga doble clic en **`build_exe.bat`**. Empaqueta Wirely en **`dist\Wirely\Wirely.exe`** (se ejecuta en cualquier PC
con Windows de 64 bits sin Python) y, si está instalado [Inno Setup](https://jrsoftware.org/isdl.php) (gratuito),
también crea **`dist\Wirely-Setup-<version>.exe`** con accesos directos en el menú Inicio y en el escritorio, y con
los archivos `.wirely` abriéndose en Wirely.

## Mac y Linux usted mismo

- Mac: `python3 -m pip install -r requirements.txt pyinstaller` y luego `bash packaging/mac/build_mac.sh`
- Linux: `python3 -m pip install -r requirements.txt pyinstaller` y luego `bash packaging/linux/build_appimage.sh`
  (un AppImage se ejecuta en sistemas Linux al menos tan nuevos como aquel en el que se compiló).

## Iconos

El logotipo y el icono de archivo `.wirely` se dibujan en código (`wirely/ui/icons.py`). Después de cambiarlos,
ejecute `python tools/make_icons.py` (necesita Pillow) para reescribir los archivos PNG, ICO y SVG de `wirely/assets`.

## Dónde está cada cosa

```
wirely/
  model/       el circuito (biblioteca de componentes, cables, conexiones, archivos) — sin Qt
  sim/         el solucionador de circuitos, modelos de componentes, flujo de corriente, síntesis de sonido — sin Qt
  ui/          la ventana: hoja, galería, gráfico, diálogos, pantalla de inicio, salida de sonido
packaging/     receta de PyInstaller, instalador de Windows, scripts de compilación para Mac y Linux
tests/         pytest: modelo, solucionador (contra respuestas calculadas a mano y ngspice), editor y simulación en vivo
tools/         circuitos de ejemplo, iconos y capturas de pantalla
```
