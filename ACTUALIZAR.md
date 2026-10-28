# Actualizar la traducción de Wirely

Wirely es un simulador de circuitos de Richard Willmott (GPLv3). Este proyecto es **una traducción
no oficial al español de Argentina**, publicada en <https://braiancerasa.github.io/wirely-es/>.
El programa, el diseño y el código son del autor original; acá solo está traducido el texto.

La traducción no es un archivo aparte: son cambios sobre el código original. Por eso el proyecto
está guardado como un repositorio Git con la versión original como base, y cada versión nueva se
**fusiona** en lugar de volver a traducirse.

```
v1.5.2 ──●──●──●──●──●  (rama «es»: la traducción)
         \           \
          ●───────────●  (v1.5.3, v1.5.4…: el original, rama «base»)
```

- **`es`** — la traducción. Es la rama en la que se trabaja.
- **`base`** — la última versión original sobre la que está hecha la traducción.
- **`upstream`** — el repositorio del autor, solo para leer. Nunca se sube nada.

## Lo más rápido: pedírselo a la IA

Abrí OpenCode en esta carpeta y escribí:

> Actualizá Wirely a la última versión.

La IA usa el *skill* `.opencode/skills/actualizar-wirely/SKILL.md`, que le indica el flujo completo:
buscar la versión nueva, fusionar, resolver los conflictos, traducir solo lo que llegó en inglés,
verificar y cerrar. Al final te cuenta qué cambió y cuántas cadenas se tradujeron.

Si preferís hacerlo a mano, son seis comandos.

## A mano, paso a paso

Todos los comandos van desde la carpeta del proyecto. Si `python` no está en el PATH, usá
`.venv\Scripts\python.exe`. En Windows también podés hacer doble clic en **`ACTUALIZAR.bat`** para
ver el estado, o arrastrarle un comando: `ACTUALIZAR.bat buscar`.

### 1. Ver dónde estamos

```bash
python tools/actualizar/actualizar.py estado
```

Dice la rama, si hay cambios sin guardar, la versión base y si hay versiones nuevas.

### 2. Buscar versiones nuevas

```bash
python tools/actualizar/actualizar.py buscar
```

Descarga las etiquetas del repositorio original y lista lo que hay después de la base.

### 3. Fusionar

```bash
python tools/actualizar/actualizar.py actualizar v1.5.3
```

- **Sin conflictos**: aplica el glosario solo y muestra las cadenas nuevas. Pasá al paso 5.
- **Con conflictos**: lista los archivos. Es normal: son las líneas que el autor tocó y que
  nosotros habíamos traducido. Seguí con el paso 4.

### 4. Resolver conflictos

Abrí cada archivo marcado y buscá los bloques así:

```
<<<<<<< HEAD
Lo que dice nuestra traducción.
=======
What the author wrote now.
>>>>>>> v1.5.3
```

Dejá el texto final en español: quédate con la traducción e incorporá traducido lo que el autor
agregó o cambió. Los números de versión, las URL y los nombres de archivo se toman del original.
Borrá las tres líneas de marca (`<<<<<<<`, `=======`, `>>>>>>>`). No hace falta `git add`.

Para ver exactamente qué cambió el autor en ese archivo:

```bash
git diff v1.5.2 v1.5.3 -- README.md
```

Y para comprobar que no quedó ninguna marca:

```bash
git grep -n -E "^(<<<<<<< |>>>>>>> )"
```

### 5. Traducir lo nuevo

```bash
python tools/actualizar/actualizar.py pendientes
```

Muestra dos listas:

- **Pendientes de traducir** — cadenas que no estaban en el catálogo: las nuevas o las que
  cambiaron. Traducilas donde indica.
- **Sospechosas de inglés** — texto que parece inglés aunque ya estuviera en el catálogo. Es la red
  de seguridad. Si es una sigla, una tecla o una clave interna, se deja.

Repetí hasta que no quede nada.

### 6. Verificar y cerrar

```bash
python tools/actualizar/actualizar.py verificar
python tools/actualizar/actualizar.py cerrar
```

`verificar` corre siete pruebas: sintaxis de Python, sintaxis del JavaScript, autoprueba de la app,
carga de los 35 ejemplos, que el generador reproduzca los ejemplos, la versión web y el glosario.
`cerrar` vuelve a verificar, guarda el catálogo de cadenas, hace el commit y crea la etiqueta
`es-v1.5.3`. Si algo falla, no cierra nada.

### 7. Publicar la web

El sitio se publica solo: GitHub Actions compila la versión web, la prueba en un navegador real y la sube
a <https://braiancerasa.github.io/wirely-es/>. Después de `cerrar`, alcanza con subir los cambios:

```bash
git push
```

Tarda unos 5–10 minutos. Los navegadores que ya lo tenían abierto se actualizan en la siguiente visita.

## Qué hace cada herramienta

| Archivo | Para qué sirve |
|---|---|
| `tools/actualizar/actualizar.py` | El menú principal: `estado`, `buscar`, `actualizar`, `pendientes`, `glosario`, `verificar`, `cerrar`, `compilar`. |
| `tools/actualizar/cadenas.py` | Extrae las cadenas visibles y las compara con el catálogo. `--guardar` actualiza el catálogo. |
| `tools/actualizar/glosario.py` | Aplica la terminología fija (AC/DC, voltaje, parlante, interruptor magnético, optoacoplador) y el dialecto. `--check` solo informa. |
| `tools/actualizar/verificar.py` | Las siete comprobaciones. `--rapido` saltea la web y el generador. |
| `tools/actualizar/glosario.json` | Las reglas de terminología, para agregar o cambiar términos. |
| `tools/actualizar/datos/cadenas.json` | El catálogo de cadenas ya traducidas. No se edita a mano. |
| `tools/actualizar/datos/version.json` | La versión base y la fecha de la última actualización. |

## El instalador de Windows

1. Instalá **Inno Setup 6** desde <https://jrsoftware.org/isdl.php> (gratuito, opciones por defecto).
2. Ejecutá:

   ```bash
   python tools/actualizar/actualizar.py compilar
   ```

   o hacé doble clic en `build_exe.bat`.

Quedan en `dist\`:

- `dist\Wirely\Wirely.exe` — la app portable, funciona sin Python.
- `dist\Wirely-Setup-1.5.3.exe` — el instalador en español, con accesos directos y asociación de
  archivos `.wirely`.

El instalador no está firmado digitalmente, así que SmartScreen va a advertir la primera vez:
**Más información → Ejecutar de todos modos**.

## Preguntas frecuentes

**¿Tengo que traducir todo de nuevo en cada versión?**
No. Git fusiona solo. Normalmente hay que traducir unas pocas decenas de cadenas: lo nuevo y lo que
el autor haya cambiado.

**¿Y si el autor reescribe media interfaz?**
Van a aparecer más conflictos, pero el método sigue siendo el mismo. Si algún día se vuelve
insostenible, la solución definitiva es sacar el español del código (archivos de traducción de Qt y
un diccionario JSON para la web), que es un trabajo aparte.

**¿Puedo publicar el instalador?**
Sí, con las condiciones de la GPLv3: al distribuir el instalador hay que ofrecer también el código
fuente modificado (este repositorio público ya lo hace), mantener los avisos de autoría y aclarar que
es una traducción no oficial. El instalador no está firmado, así que SmartScreen va a advertir.

**¿Mis circuitos guardados se pierden al actualizar?**
No. Los archivos `.wirely` viven fuera del proyecto. Solo se renombran los ejemplos que se
traducen; si tenías uno abierto desde **Archivo → Ejemplos**, abrilo de nuevo.

**¿Cómo vuelvo atrás si algo sale mal?**
```bash
git reset --hard es-v1.5.2
```
Eso devuelve la traducción a la versión anterior. Preguntá antes de descartar trabajo sin guardar.

**¿Qué archivos no hay que tocar?**
`LICENSE`, `THIRD-PARTY-NOTICES.txt` y `tools/actualizar/datos/cadenas.json` (se regenera solo).
Tampoco se traducen los nombres de variables, las claves internas ni las `keywords` de
`wirely/model/parts.py`.
