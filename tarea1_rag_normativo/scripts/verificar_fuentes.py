"""Verificación de fuentes (Fase 1): se corre ANTES de construir el resto.

Para cada PDF mide:
- número de páginas
- caracteres por página (mínimo, mediana, máximo)
- páginas sin texto extraíble (posible escaneo, necesitaría OCR)
- orden de lectura: si los "Artículo N." aparecen en orden creciente, las columnas
  se están leyendo en el orden correcto
- encabezados de El Peruano y ligaduras rotas (ruido que habrá que limpiar)

Escribe data/processed/verificacion_fuentes.md y .csv

Uso (desde la carpeta tarea1_rag_normativo):
    python scripts/verificar_fuentes.py
"""
import csv
import re
import statistics
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import cargar_config, ruta  # noqa: E402
from src.extraccion import extraer_paginas  # noqa: E402

PATRON_ARTICULO = re.compile(r"Art[íi]culo\s+(\d+)\.")
PATRON_ENCABEZADO_EP = re.compile(r"NORMAS\s+LEGALES")
PATRON_LIGADURA = re.compile(r"[ﬁﬂﬀﬃﬄ]")


def verificar(doc_cfg: dict, carpeta_raw: Path, vcfg: dict) -> dict:
    min_chars = vcfg["min_caracteres_pagina"]
    min_articulos = vcfg["min_articulos_para_medir_orden"]
    umbral_orden = vcfg["umbral_orden_lectura"]
    ruta_pdf = carpeta_raw / doc_cfg["archivo"]
    pdf = pymupdf.open(ruta_pdf)
    textos = [p.get_text() for p in pdf]
    chars = [len(t.strip()) for t in textos]
    vacias = [i + 1 for i, c in enumerate(chars) if c < min_chars]

    # Solo el texto que pertenece a esta norma (sin las normas vecinas de El Peruano)
    paginas_norma = extraer_paginas(ruta_pdf, doc_cfg.get("recorte"))
    texto_norma = "\n".join(p["texto"] for p in paginas_norma)
    chars_ajenos = sum(p["chars_ajenos"] for p in paginas_norma)

    def orden_articulos(texto: str):
        # Proporción de pasos crecientes en la secuencia de "Artículo N."
        numeros = [int(n) for n in PATRON_ARTICULO.findall(texto)]
        pasos = list(zip(numeros, numeros[1:]))
        return (sum(1 for a, b in pasos if b >= a) / len(pasos)) if pasos else None, len(numeros)

    orden_bruto, _ = orden_articulos("\n".join(textos))
    orden, n_articulos = orden_articulos(texto_norma)

    paginas_con_encabezado = sum(1 for t in textos if PATRON_ENCABEZADO_EP.search(t[:200]))
    ligaduras = sum(len(PATRON_LIGADURA.findall(t)) for t in textos)

    # Orden aceptable = al menos 90% de pasos crecientes. Las referencias cruzadas
    # ("conforme al artículo 2...") explican los pocos saltos hacia atrás.
    # Con muy pocos artículos la medida no dice nada (un artículo citado ya la rompe):
    # en ese caso se revisa a mano y se anota en el README.
    muestra_suficiente = n_articulos >= min_articulos
    if not muestra_suficiente:
        orden = None
    legible = not vacias and (orden is None or orden >= umbral_orden)
    if not legible:
        veredicto = "NO"
    elif chars_ajenos:
        veredicto = "SÍ, recortando otras normas"
    else:
        veredicto = "SÍ"

    def pct(x):
        return f"{x:.0%}" if x is not None else "n/a"

    return {
        "id": doc_cfg["id"],
        "paginas_pdf": len(pdf),
        "paginas_con_texto_de_la_norma": len(paginas_norma),
        "chars_pagina_min": min(chars),
        "chars_pagina_mediana": int(statistics.median(chars)),
        "chars_pagina_max": max(chars),
        "paginas_sin_texto": ",".join(map(str, vacias)) or "ninguna",
        "chars_de_otras_normas": chars_ajenos,
        "articulos_detectados": n_articulos,
        "orden_pdf_completo": pct(orden_bruto),
        "orden_solo_la_norma": pct(orden) if muestra_suficiente else "revisión manual (pocos artículos)",
        "paginas_con_encabezado_elperuano": paginas_con_encabezado,
        "ligaduras_rotas": ligaduras,
        "usable": veredicto,
    }


def main():
    cfg = cargar_config()
    carpeta_raw = ruta(cfg, "raw")
    salida = ruta(cfg, "processed")
    salida.mkdir(parents=True, exist_ok=True)
    min_chars = cfg["verificacion"]["min_caracteres_pagina"]

    filas = [verificar(d, carpeta_raw, cfg["verificacion"]) for d in cfg["documentos"]]

    with open(salida / "verificacion_fuentes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)

    columnas = list(filas[0])
    lineas = ["| " + " | ".join(columnas) + " |", "|" + "---|" * len(columnas)]
    lineas += ["| " + " | ".join(str(f[c]) for c in columnas) + " |" for f in filas]
    tabla = "\n".join(lineas)
    (salida / "verificacion_fuentes.md").write_text(
        "# Verificación de fuentes (Tarea 1, Fase 1)\n\n"
        f"Página sin texto = menos de {min_chars} caracteres extraíbles.\n"
        "orden_* = % de veces que el número de 'Artículo N.' siguiente es mayor o igual al anterior "
        "(en todo el PDF y solo en el texto de la norma, tras recortar las normas vecinas).\n\n"
        + tabla + "\n",
        encoding="utf-8",
    )
    print(tabla)


if __name__ == "__main__":
    main()
