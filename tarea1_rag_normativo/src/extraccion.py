"""Extracción de texto PÁGINA POR PÁGINA.

Desde el primer paso, cada texto va pegado a su número de página: nunca se une
el documento entero en un solo string. Así cualquier fragmento posterior sabe
de qué página viene y se puede citar.
"""
import re
from pathlib import Path

import pymupdf


def _linea_marcador(codigo: str) -> re.Pattern:
    # El Peruano cierra cada norma con su código en una línea sola, p. ej. "2474920-3"
    return re.compile(rf"^\s*{re.escape(codigo)}\s*$", flags=re.M)


def extraer_paginas(ruta_pdf: Path, recorte: dict | None = None) -> list[dict]:
    """Devuelve [{'pagina': n, 'texto': ..., 'chars_ajenos': k}, ...] solo con el texto de la norma.

    recorte = {'despues_de': código o None, 'hasta': código o None}
      - despues_de: se descarta todo lo anterior a ese código (final de la norma previa).
      - hasta: se descarta todo lo posterior a ese código (el propio código se conserva
        como cierre). Lo que viene después pertenece a otra norma.
    Las páginas que quedan sin texto de la norma se omiten, pero las demás
    conservan su número de página ORIGINAL del PDF.
    """
    recorte = recorte or {}
    pdf = pymupdf.open(ruta_pdf)
    textos = [p.get_text() for p in pdf]

    dentro = recorte.get("despues_de") is None  # ¿ya empezó la norma?
    terminado = False
    paginas = []
    for n, texto in enumerate(textos, start=1):
        original = len(texto)
        if terminado:
            continue
        if not dentro:
            m = _linea_marcador(recorte["despues_de"]).search(texto)
            if not m:
                continue
            texto = texto[m.end():]
            dentro = True
        if recorte.get("hasta"):
            m = _linea_marcador(recorte["hasta"]).search(texto)
            if m:
                texto = texto[: m.end()]
                terminado = True
        paginas.append({"pagina": n, "texto": texto, "chars_ajenos": original - len(texto)})
    return paginas
