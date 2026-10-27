---
name: Actualizar Wirely
description: Actualiza la traducción al español (Argentina) de Wirely a una versión nueva del proyecto original. Úselo cuando el usuario pida actualizar Wirely, traer una versión nueva, resolver conflictos de la traducción o generar el instalador de Windows.
---

# Actualizar la traducción de Wirely

Wirely es un simulador de circuitos ajeno (GPLv3, de Richard Willmott) que está traducido al
español de Argentina en este repositorio. La traducción es una rama de Git colgada del código
original, así que una versión nueva se fusiona con `git merge` y solo se traduce lo que llega
en inglés.

- `upstream` → repositorio original (solo lectura).
- `base` → la versión original sobre la que está hecha la traducción.
- `es` → la traducción (es la rama de trabajo).
- `tools/actualizar/` → las herramientas. No las traduzcas ni las edites salvo que el usuario lo pida.

## Reglas de la traducción (no negociables)

- Español de Argentina, trato de **usted** («haga clic», «presione», «arrastre», «elija»). Nada de voseo ni de «tú».
- Términos fijos: **AC/DC** (nunca CA/CC), **voltaje** (nunca tensión), **parlante** (nunca altavoz),
  **interruptor magnético** (nunca lengüeta), **optoacoplador** (nunca optoaislador).
- Vocabulario ya usado en el proyecto: condensador, resistencia, bobina/inductor, compuerta, drenador,
  fuente, colector, emisor, base, patilla, cable, componente, hoja, galería, zumbador, lámpara.
- **No traduzcas**: nombres de variables y funciones, claves de diccionarios y de propiedades
  (`"voltage"`, `"resistance"`, `"model"`), las `keywords` en inglés de `wirely/model/parts.py`,
  números de modelo (PC817, 2N7002), rutas, URL, `LICENSE` ni `THIRD-PARTY-NOTICES.txt`.
- **No cambies la lógica.** Solo texto visible (etiquetas, mensajes, tooltips, docstrings, comentarios,
  documentación, notas de los ejemplos).
- Los **títulos de los ejemplos son nombres de archivo**: si traduces uno, renombra el `.wirely`,
  actualiza `tools/make_examples.py` y las tablas del `README.md`.
- Mantén el ancho de línea y el estilo de alrededor (unas 120 columnas, mismas comillas y sangría).
- Si una cadena nueva es solo técnica (por ejemplo `"V"`, `"Hz"`, `"PC817"`), déjala igual.

## Flujo completo

Todos los comandos se ejecutan desde la raíz del proyecto. En Windows, si `python` no está en el
PATH, usa `.venv\Scripts\python.exe`.

### 1. Ver dónde estamos

```bash
python tools/actualizar/actualizar.py estado
```

Muestra la rama, si el árbol está limpio, la versión base, la última versión publicada y cuántas
cadenas quedan pendientes. Si el árbol tiene cambios sin guardar, no sigas: primero hay que
cerrarlos o descartarlos (pregunta al usuario).

### 2. Ver si hay versiones nuevas

```bash
python tools/actualizar/actualizar.py buscar
```

Hace `git fetch upstream --tags` y lista las versiones posteriores a la base. Si no hay ninguna,
informa al usuario y termina.

### 3. Fusionar

```bash
python tools/actualizar/actualizar.py actualizar v1.5.3
```

- Si sale bien: aplica el glosario automáticamente y lista las cadenas nuevas. Pasa al paso 5.
- Si hay conflictos (código de salida 3): sigue con el paso 4.

### 4. Resolver conflictos

Los conflictos aparecen donde el autor cambió una línea que nosotros habíamos traducido.
**Nunca** uses `git checkout --theirs` (dejaría inglés) ni `--ours` a ciegas (perdería lo nuevo).

Para cada archivo en conflicto:

1. Mira qué cambió el autor en esa versión:
   ```bash
   git diff v1.5.2 v1.5.3 -- ruta/del/archivo
   ```
   (usa la versión base anterior y la nueva, que son los dos extremos del merge).
2. Abre el archivo y reemplaza el bloque `<<<<<<<` … `=======` … `>>>>>>>` por el texto final:
   - quédate con la traducción;
   - incorpora traducido lo que el autor agregó o cambió;
   - toma del original los números de versión, URL y nombres de archivo (`Wirely-Setup-1.5.3.exe`).
3. Borra las tres líneas de marca. **No hace falta `git add`**: `cerrar` se encarga.
4. Cuando termines, comprueba que no queden marcas:
   ```bash
   git grep -n -E "^(<<<<<<< |>>>>>>> )"
   ```

Casos típicos:

- **Solo cambió una URL o un número de versión** dentro de una frase traducida: deja la frase en
  español con el dato nuevo.
- **El autor agregó un párrafo o una viñeta**: consérvala, traducida, en el mismo lugar.
- **El autor reescribió una sección entera** (por ejemplo `RELEASE_NOTES.md`): reemplaza la sección
  vieja por la nueva traducida, sin mezclar restos de la anterior.

### 5. Traducir lo nuevo

```bash
python tools/actualizar/actualizar.py pendientes
```

Lista dos grupos:

- **Pendientes de traducir**: cadenas que no estaban en el catálogo. Son las nuevas (o las que
  cambiaron). Traducilas en el archivo que indica.
- **Sospechosas de inglés**: cadenas que parecen inglés aunque ya estén en el catálogo. Es la red de
  seguridad para texto que se coló sin traducir.

Traduce en el lugar, sin tocar nada más. Después vuelve a ejecutar `pendientes` hasta que no quede
nada (las «sospechosas» pueden incluir falsos positivos: si es una sigla, un nombre de tecla o una
clave interna, déjala y avísale al usuario).

### 6. Verificar

```bash
python tools/actualizar/actualizar.py verificar
```

Corre siete comprobaciones: sintaxis de Python, sintaxis de JavaScript, autoprueba de la app, carga
de los ejemplos, que el generador reproduzca los ejemplos, la versión web y el glosario. Si algo
falla, corrígelo y repite. No cierres con comprobaciones en rojo.

### 7. Cerrar

```bash
python tools/actualizar/actualizar.py cerrar
```

Vuelve a verificar, actualiza `datos/version.json` y el catálogo de cadenas, hace el commit y crea
la etiqueta `es-v1.5.3`. Si el usuario tiene prisa, `cerrar --rapido` saltea la prueba web y el
generador (no lo hagas si tocaste ejemplos o la web).

## Después de actualizar

- Cuéntale al usuario: versión nueva, cuántos conflictos hubo, qué se tradujo y el resultado de las
  comprobaciones.
- Recuérdale que puede rehacer el instalador con:
  ```bash
  python tools/actualizar/actualizar.py compilar
  ```
  (necesita Inno Setup 6 instalado; deja `dist\Wirely-Setup-<versión>.exe`).

## Si algo sale mal

- **`actualizar` dice que hay un merge en curso**: termínalo con `cerrar` o cancélalo con
  `git merge --abort`.
- **`cerrar` se niega por marcas de conflicto**: quedan líneas `<<<<<<<` o `>>>>>>>` en esos archivos.
- **El glosario marca cambios**: ejecuta `python tools/actualizar/actualizar.py glosario` y vuelve a
  verificar. Es idempotente.
- **Quieres volver atrás**: `git reset --hard es-v1.5.2` (o la etiqueta anterior) devuelve la
  traducción a como estaba. Pregunta antes de descartar trabajo.
- **Un archivo quedó en inglés**: búscalo con `git diff <versión-vieja> -- ruta` y con
  `python tools/actualizar/cadenas.py --ingles`.

## Nunca

- Nunca publiques, hagas push ni crees releases: el repositorio es local.
- Nunca borres `.git` ni cambies de rama sin pedirlo.
- Nunca traduzcas `LICENSE` ni `THIRD-PARTY-NOTICES.txt`.
- Nunca edites `tools/actualizar/datos/cadenas.json` a mano: se regenera con `cerrar`.
