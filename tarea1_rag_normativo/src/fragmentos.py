"""División del texto limpio en fragmentos con metadatos.

Decisiones:
- Un fragmento NUNCA cruza de una página a otra: así su `pagina` es exacta.
- Se arman juntando párrafos completos hasta `tamano` caracteres; un párrafo más largo
  que eso se corta por palabras. Entre fragmentos consecutivos de la misma página se
  repiten los últimos `solape` caracteres para no partir una idea por la mitad.
- ID estable y único entre documentos: "<documento>:p<página>:c<n.º>". Si el texto
  procesado y la configuración no cambian, los IDs salen idénticos en cada corrida.
"""
import hashlib
import json
import re
from pathlib import Path

ORDINAL = r"(?:PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA|SEXTA|SÉPTIMA|OCTAVA|NOVENA|DÉCIMA|UNDÉCIMA|DUODÉCIMA|VIGÉSIMA|ÚNICA)"
# "Artículo 85." o encabezado de disposición: "PRIMERA.", "VIGÉSIMA NOVENA.", "DECIMOTERCERA." (D.S.)
ENCABEZADO_ARTICULO = re.compile(
    rf"^[“\"]?\s*(Artículo\s+\d+|{ORDINAL}(?:\s+[A-ZÁÉÍÓÚ]+)?|DECIMO[A-ZÁÉÍÓÚ]+|VIGESIMO[A-ZÁÉÍÓÚ]+)\.")
ETIQUETA_VIGENTE = re.compile(r"\[Texto vigente — [^\]]*? por (?P<norma>.+?), publicada el (?P<fecha>[^\]]+)\]")


def _etiqueta_unidad(encabezado: str) -> str:
    return encabezado if encabezado.startswith("Artículo") else f"Disposición {encabezado}"


def _cortar_parrafo_largo(parrafo: str, tamano: int) -> list[str]:
    palabras, partes, actual = parrafo.split(" "), [], ""
    for p in palabras:
        if actual and len(actual) + 1 + len(p) > tamano:
            partes.append(actual)
            actual = p
        else:
            actual = f"{actual} {p}".strip()
    if actual:
        partes.append(actual)
    return partes


def _cola(texto: str, solape: int) -> str:
    """Últimos `solape` caracteres, empezando en un límite de palabra."""
    if solape <= 0 or len(texto) <= solape:
        return ""
    cola = texto[-solape:]
    return cola[cola.find(" ") + 1:] if " " in cola else cola


def fragmentar_pagina(texto: str, tamano: int, solape: int) -> list[str]:
    unidades = []
    for par in texto.split("\n\n"):
        par = par.strip()
        if par:
            unidades.extend(_cortar_parrafo_largo(par, tamano) if len(par) > tamano else [par])

    fragmentos, actual = [], ""
    for u in unidades:
        if actual and len(actual) + 2 + len(u) > tamano:
            fragmentos.append(actual)
            cola = _cola(actual, solape)
            actual = f"{cola} {u}".strip() if cola else u
        else:
            actual = f"{actual}\n\n{u}" if actual else u
    if actual:
        fragmentos.append(actual)
    return fragmentos


def fragmentar_documento(doc_cfg: dict, carpeta_processed: Path, tamano: int, solape: int) -> list[dict]:
    """Lee data/processed/<id>.jsonl (nunca el PDF) y devuelve fragmentos con metadatos."""
    registros = [json.loads(l) for l in open(carpeta_processed / f"{doc_cfg['id']}.jsonl", encoding="utf-8")]
    salida = []
    articulo_vigente = ""  # último "Artículo N" visto; se arrastra a la página siguiente
    for reg in registros:
        for n, texto in enumerate(fragmentar_pagina(reg["texto"], tamano, solape)):
            encontrados = [_etiqueta_unidad(m.group(1)) for par in texto.split("\n\n")
                           if (m := ENCABEZADO_ARTICULO.match(par))]
            empieza_con_articulo = bool(ENCABEZADO_ARTICULO.match(texto))
            articulo_inicio = encontrados[0] if empieza_con_articulo else articulo_vigente
            if encontrados:
                articulo_vigente = encontrados[-1]
            mods = ETIQUETA_VIGENTE.findall(texto)
            salida.append({
                "id": f"{doc_cfg['id']}:p{reg['pagina']}:c{n}",
                "texto": texto,
                "metadatos": {
                    "documento": doc_cfg["id"],
                    "titulo": doc_cfg["titulo"],
                    "tipo": doc_cfg["tipo"],
                    "version": doc_cfg["version"],
                    "fecha_version": doc_cfg["fecha_version"],
                    "pagina": reg["pagina"],
                    "modifica": doc_cfg["modifica"] or "",
                    # artículo en el que empieza el fragmento y los que se abren dentro de él
                    "articulo": articulo_inicio,
                    "articulos_en_fragmento": ", ".join(encontrados),
                    # capa 2 de versiones: qué norma cambió el texto que contiene este fragmento
                    "modificado_por": "; ".join(dict.fromkeys(m[0] for m in mods)),
                    "fecha_modificacion": "; ".join(dict.fromkeys(m[1] for m in mods)),
                    "chars": len(texto),
                    "hash": hashlib.sha1(texto.encode("utf-8")).hexdigest()[:12],
                },
            })
    return salida
