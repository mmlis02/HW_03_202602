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
