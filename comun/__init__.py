"""Piezas del motor RAG compartidas por la Tarea 1 y la Tarea 2.

- embeddings.py : interfaz común Embedder + implementaciones local (e5-small) y OpenAI
- costos.py     : precio según la hora de cada llamada (franjas) y log de costos
- llm.py        : llamada al LLM con esquema JSON estricto, costo, log y manejo de errores

Ninguno importa librerías de interfaz (Streamlit, etc.).
"""
