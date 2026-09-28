# Notas para el video (en palabras simples)

Este archivo explica, paso a paso y sin tecnicismos, qué se hizo y por qué. Sirve como guion de apoyo para el video.

---

## Fase 0 — Preparar el proyecto

**Qué hice**
- Creé las carpetas que sugiere el enunciado: una para la Tarea 1 (`tarea1_rag_normativo`), otra para la Tarea 2 (`tarea2_radar`) y `docs` para los documentos de apoyo.
- Creé un **entorno virtual** (`.venv`): una "caja" aislada donde se instalan las librerías del proyecto sin tocar el resto de la computadora.
- Escribí `requirements.txt`, la lista de librerías con su versión exacta, para que cualquiera pueda instalar exactamente lo mismo.
- Creé `.env.example`. La clave de OpenAI va en un archivo `.env` que **nunca** se sube a GitHub; `.env.example` solo muestra el nombre de la variable, vacía.
- Creé `.gitignore`, la lista de cosas que git debe ignorar: la clave, el entorno virtual y los archivos de datos grandes. Los datos se vuelven a descargar con un script.

**Por qué**
- **Reproducible:** otra persona, por ejemplo el profesor en Windows, puede instalar todo con los pasos del README.
- **Seguro:** la clave de la API nunca queda en el historial de git.
- **Liviano:** el repositorio no se llena de archivos pesados que se pueden volver a bajar.

**Dato útil para el video**
- Probé que todas las librerías funcionan con Python 3.14 antes de empezar. El entorno ocupa unos 1.9 GB, casi todo por PyTorch, el motor que usa el modelo de embeddings.
- Elegí `pyshp` para leer el mapa de departamentos en lugar de `geopandas`: es mucho más liviana y no necesita instalar programas extra en Windows.

---

## Tarea 1 · Fase 1 · Paso 1 — Descargar y verificar las fuentes (antes de programar lo demás)

**Qué hice**
- Busqué los PDFs **solo en fuentes oficiales**: gob.pe (MEF y OECE) y El Peruano. Un script (`scripts/descargar_fuentes.py`) los baja a `data/raw/`, no repite descargas y anota la fecha de descarga y una "huella" (sha256) de cada archivo en `data/manifiesto_descargas.json`.
- Otro script (`scripts/verificar_fuentes.py`) revisa cada PDF: cuántas páginas tiene, cuántas letras hay por página, si alguna página no tiene texto (sería una imagen escaneada) y si el texto sale en el orden correcto.
- Para comprobar el orden usé un truco simple: si los "Artículo 1, 2, 3…" aparecen en orden creciente, las columnas se están leyendo bien. En la ley sale 99 %; los pocos saltos son citas a otros artículos.

**Qué encontré (esto sirve para el video)**
- **El Peruano imprime varias normas en la misma página.** El PDF del D.S. 001-2026-EF trae en su última página otra norma completa, una resolución sobre índices de corrección monetaria. Si no se recorta, el asistente podría "citar" algo que no es del decreto.
- **Cómo lo resolví:** El Peruano cierra cada norma con un código (por ejemplo `2474920-3`), así que recorto el texto exactamente en ese código. Esa regla está escrita en `config.yaml`.
- **La versión actualizada de la ley** (compilada por OECE) conserva el texto antiguo y, al lado, una nota "(*) Literal modificado por…" con el texto nuevo. Eso ayuda con las versiones, pero es una trampa: si el asistente lee solo el texto antiguo, respondería algo que ya no rige.
- Hay letras "rotas" (ﬁ, ﬂ) en la ley publicada en El Peruano, por ejemplo "Caliﬁ cación". Se limpiarán en el siguiente paso.

**Decisión: qué versión de la ley usar (opción B)**
- Revisé dos versiones de la Ley 32069: el texto original de 2024 y la versión actualizada al 19/07/2026 que publica OECE en gob.pe. Las dos se pueden leer bien.
- Elegí la **actualizada** porque desde 2024 varias leyes cambiaron artículos. Con el texto original, el asistente podría responder algo que ya no rige, y para una MYPE eso es peor que no responder.
- La del texto original queda en la tabla como prueba de que también la revisé.
- Agregué el **D.Leg. 1715** como documento opcional. Es la norma que cambió un literal de la ley (agregó la "infraestructura hidráulica" a las obras que no se pueden paralizar con medidas cautelares). Sirve para mostrar en el video cómo el asistente explica qué norma cambió qué y cuándo.

---

## Tarea 1 · Fase 1 · Paso 2 — Limpiar el texto y medir su calidad

**Qué hice**
- **La página va pegada al texto desde el primer momento.** Leo cada PDF página por página, y cada pedazo de texto sale con su número de página. Nunca junto todo el documento en un solo texto.
  - *Para el video:* si juntara todo y lo cortara después, tendría que adivinar de qué página viene cada pedazo contando letras. Al limpiar se borran letras (encabezados, notas), así que esa cuenta se descuadra y las citas saldrían con páginas equivocadas.
- **Limpié el ruido con reglas escritas y contadas:**
  - borré el encabezado de El Peruano en cada página (número, "NORMAS LEGALES", fecha);
  - borré el sello de firma digital y el código de cierre de la norma;
  - uní las líneas que el PDF cortaba por el ancho de la columna (a veces cortaba cada palabra en una línea);
  - quité las "concordancias" del SPIJ.
- **Resolví las versiones de la ley.** La versión actualizada trae el texto viejo y, al lado, la nota "(*) modificado por…" con el texto nuevo. Mi programa:
  - borra el texto viejo para que el buscador **no pueda encontrarlo**;
  - deja el texto nuevo con una etiqueta: "[Texto vigente — modificado por el D.Leg. 1715, publicada el 04 febrero 2026]".

  Eran 20 notas: 12 modificaciones, 2 incorporaciones, 1 derogación, 4 avisos y 1 fe de erratas. Las 12 modificaciones se resolvieron todas.
- Generé un **reporte de calidad** por documento (páginas, letras, páginas descartadas, reglas aplicadas y una muestra del medio del texto) y un archivo con **ejemplos de antes y después**.

**Por qué**
- Si el texto lleva basura (encabezados, otras normas), el buscador puede traer un pedazo que no dice nada útil, o que es de otra norma.
- Si el texto viejo sigue en el índice, el asistente podría responder algo que **ya no rige**. Borrarlo antes de indexar es la forma más segura: lo que no está en el índice no se puede citar.

**Números para decir en el video**
- De 112.601 letras del PDF del D.S. 001-2026-EF, 6.272 eran de otra norma y se recortaron.
- Ninguna página se descartó: todas tienen texto de su norma.
- Ejemplo estrella para el video: el art. 85.1.e) antes (sin "infraestructura hidráulica") y después (con la etiqueta del D.Leg. 1715).
