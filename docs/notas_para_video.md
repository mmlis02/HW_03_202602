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
