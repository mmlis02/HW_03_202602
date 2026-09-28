"""Fase 1: extrae y limpia los documentos del corpus, y escribe el reporte de calidad.

Salidas en data/processed/:
  <id>.jsonl                       una línea por página: documento, página y texto limpio
  versiones_<id>.json              cada nota "(*)" resuelta (qué se borró y qué quedó vigente)
  reporte_calidad_extraccion.md    reporte legible (también lo muestra la app)
  reporte_calidad_extraccion.json  lo mismo en formato para programas
  ejemplos_limpieza.md             ejemplos antes/después de cada regla

Uso (desde la carpeta tarea1_rag_normativo):
    python scripts/procesar_documentos.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import cargar_config, ruta  # noqa: E402
from src.extraccion import extraer_paginas  # noqa: E402
from src.limpieza import limpiar_documento, limpiar_ruido_pagina  # noqa: E402

DESCRIPCION_REGLAS = {
    "R1_encabezado_elperuano": "Encabezado de página de El Peruano eliminado",
    "R2_sello_firma": "Sello 'Firmado por: Editora Peru' eliminado",
    "R3_codigo_publicacion": "Código de publicación de cierre eliminado",
    "R4_ligaduras": "Ligaduras rotas corregidas",
    "R5_concordancias": "Párrafos de concordancias SPIJ eliminados",
    "R7_nota_partida_entre_paginas_unida": "Notas (*) partidas entre páginas unidas",
    "R7_modificacion_texto_antiguo_eliminado": "Modificaciones: texto antiguo eliminado, texto vigente etiquetado",
    "R7_modificacion_sin_texto_antiguo_ubicado": "Modificaciones SIN ubicar texto antiguo (revisar)",
    "R7_incorporacion": "Incorporaciones etiquetadas",
    "R7_derogacion": "Derogaciones: texto derogado eliminado",
    "R7_aviso_vigencia": "Avisos de vigencia conservados",
    "R7_fe_de_erratas": "Fe de erratas aplicada",
    "R7_nota_no_reconocida": "Notas (*) no reconocidas (revisar)",
}


def recorte(texto: str, n: int, desde_el_final: bool = False) -> str:
    return (texto[-n:] if desde_el_final else texto[:n]).strip()


def main():
    cfg = cargar_config()
    raw, processed = ruta(cfg, "raw"), ruta(cfg, "processed")
    processed.mkdir(parents=True, exist_ok=True)
    reglas = cfg["limpieza"]

    reporte, crudos, limpios_por_doc = [], {}, {}
    for doc in (d for d in cfg["documentos"] if d["incluir"]):
        pdf = pymupdf.open(raw / doc["archivo"])
        texto_pdf = [p.get_text() for p in pdf]
        paginas = extraer_paginas(raw / doc["archivo"], doc.get("recorte"))
        limpias, contador, registro = limpiar_documento(paginas, doc["id"], reglas)
        crudos[doc["id"]] = {p["pagina"]: p["texto"] for p in paginas}
        limpios_por_doc[doc["id"]] = {p["pagina"]: p["texto"] for p in limpias}

        # Salida principal: una línea JSON por página, con su número de página del PDF
        with open(processed / f"{doc['id']}.jsonl", "w", encoding="utf-8") as f:
            for p in limpias:
                f.write(json.dumps({"documento": doc["id"], "pagina": p["pagina"], "texto": p["texto"],
                                    "chars": len(p["texto"])}, ensure_ascii=False) + "\n")
        if registro:
            (processed / f"versiones_{doc['id']}.json").write_text(
                json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")

        # Páginas descartadas: en el PDF pero sin texto de la norma después de recortar/limpiar
        conservadas = {p["pagina"] for p in limpias}
        con_texto_norma = {p["pagina"] for p in paginas}
        descartadas = []
        for n in range(1, len(pdf) + 1):
            if n not in con_texto_norma:
                descartadas.append({"pagina": n, "motivo": "pertenece solo a otra norma (recorte El Peruano)"})
            elif n not in conservadas:
                descartadas.append({"pagina": n, "motivo": "quedó vacía tras la limpieza (solo ruido)"})

        # Conteo de marcas "(*)": cada NOTA empieza una línea con "(*)"; además, el texto al que
        # se refiere suele terminar con otra marca "(*)" de llamada. Por eso hay más marcas que notas.
        texto_norma = "\n".join(p["texto"] for p in paginas)
        marcas = texto_norma.count("(*)")
        notas = len(re.findall(r"^\s*\(\*\)", texto_norma, flags=re.M))
        tipos = Counter(r["accion"].split(" (")[0].replace("Numeral 1", "Numeral") for r in registro)

        medio = limpias[len(limpias) // 2]
        reporte.append({
            "documento": doc["id"],
            "titulo": doc["titulo"],
            "paginas_pdf": len(pdf),
            "paginas_conservadas": len(limpias),
            "paginas_descartadas": descartadas,
            "chars_pdf_completo": sum(len(t) for t in texto_pdf),
            "chars_de_la_norma_tras_recorte": sum(len(p["texto"]) for p in paginas),
            "chars_limpios": sum(len(p["texto"]) for p in limpias),
            "reglas_aplicadas": {k: v for k, v in contador.items() if v},
            "marcas_asterisco_en_pdf": marcas,
            "notas_de_version": notas,
            "marcas_de_llamada": marcas - notas,
            "notas_por_tipo": dict(tipos),
            "muestra_pagina": medio["pagina"],
            "muestra_texto": recorte(medio["texto"], 700),
        })

    # --- Reporte legible ----------------------------------------------------------
    lineas = ["# Reporte de calidad de extracción (Tarea 1, Fase 1)", "",
              "Generado por `scripts/procesar_documentos.py`. 'chars' = caracteres.", "",
              "| Documento | Págs. PDF | Págs. conservadas | Págs. descartadas | chars PDF completo | chars de la norma (tras recorte) | chars limpios |",
              "|---|---|---|---|---|---|---|"]
    for r in reporte:
        lineas.append(f"| {r['documento']} | {r['paginas_pdf']} | {r['paginas_conservadas']} | {len(r['paginas_descartadas'])} | "
                      f"{r['chars_pdf_completo']:,} | {r['chars_de_la_norma_tras_recorte']:,} | {r['chars_limpios']:,} |")
    for r in reporte:
        lineas += ["", f"## {r['documento']} — {r['titulo']}", ""]
        if r["paginas_descartadas"]:
            lineas += [f"- Página {d['pagina']} descartada: {d['motivo']}" for d in r["paginas_descartadas"]]
        else:
            lineas.append("- Páginas descartadas: ninguna (todas tienen texto de la norma).")
        if r["notas_de_version"]:
            lineas += ["", f"Notas de versión \"(*)\": el PDF tiene **{r['marcas_asterisco_en_pdf']} marcas \"(*)\"**, que corresponden a "
                       f"**{r['notas_de_version']} notas** (líneas que empiezan con \"(*)\") más **{r['marcas_de_llamada']} marcas de llamada** "
                       "(el \"(*)\" pegado al final del texto al que se refiere cada nota; los avisos de la primera página no tienen llamada).", "",
                       "| Tipo de nota | Cantidad |", "|---|---|"]
            lineas += [f"| {k} | {v} |" for k, v in sorted(r["notas_por_tipo"].items(), key=lambda x: -x[1])]
        lineas += ["", "Reglas de limpieza aplicadas:", ""]
        lineas += [f"- {DESCRIPCION_REGLAS.get(k, k)}: **{v}**" for k, v in r["reglas_aplicadas"].items()] or ["- ninguna"]
        lineas += ["", f"Muestra del texto limpio (página {r['muestra_pagina']}, mitad del documento):", "",
                   "```text", r["muestra_texto"], "```"]
    (processed / "reporte_calidad_extraccion.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    (processed / "reporte_calidad_extraccion.json").write_text(json.dumps(reporte, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- Ejemplos antes / después ------------------------------------------------
    def bloque(titulo, antes, despues):
        return [f"## {titulo}", "", "**Antes (texto crudo del PDF):**", "", "```text", antes, "```", "",
                "**Después (texto limpio):**", "", "```text", despues, "```", ""]

    ej = ["# Ejemplos de limpieza: antes y después", ""]
    ds_c, ds_l = crudos["ds001_2026_ef"], limpios_por_doc["ds001_2026_ef"]
    ej += bloque("R1 + R6 — Encabezado de El Peruano pegado al texto y líneas cortadas (D.S. 001-2026-EF, pág. 4)",
                 recorte(ds_c[4], 420), recorte(ds_l[4], 330))
    ej += bloque("Recorte + R3 — Fin de la norma y otra norma en la misma página (D.S. 001-2026-EF, pág. 16)",
                 recorte(pymupdf.open(raw / "ds001_2026_ef.pdf")[15].get_text().split("Dado en", 1)[1][:700], 700),
                 recorte(ds_l[16], 300, desde_el_final=True))
    dl_c, dl_l = crudos["dl1715"], limpios_por_doc["dl1715"]
    ej += bloque("R2 — Sello de firma digital (D.Leg. 1715, pág. 1)",
                 dl_c[1][dl_c[1].rfind("(…)"):].strip(), dl_l[1][dl_l[1].rfind("(…)"):].strip())
    ley_c, ley_l = crudos["ley32069"], limpios_por_doc["ley32069"]
    i = ley_c[43].find("(*) Literal modificado por el Artículo 3")
    j = ley_l[43].find("[Texto vigente")
    ej += bloque("R7 — Versión: texto antiguo + nota '(*) modificado por' (Ley 32069 actualizada, pág. 43, art. 85.1.e)",
                 ley_c[43][max(0, i - 330):i + 560].strip(), ley_l[43][j:j + 420].strip())
    # R4 no aparece en el corpus final, pero sí en el texto original de la ley (descartado); se muestra la regla.
    original = next(d for d in cfg["documentos"] if d["id"] == "ley32069_original")
    pag = pymupdf.open(raw / original["archivo"])[10].get_text()
    k = pag.find("Caliﬁ")
    ej += bloque("R4 — Ligaduras rotas (texto original de la ley, pág. 11; no aparece en el corpus final)",
                 pag[k - 60:k + 60].strip(), limpiar_ruido_pagina(pag[k - 60:k + 60], reglas, Counter()).strip())
    (processed / "ejemplos_limpieza.md").write_text("\n".join(ej), encoding="utf-8")

    print("\n".join(lineas[:4 + len(reporte) + 2]))
    print(f"\nArchivos escritos en {processed}")


if __name__ == "__main__":
    main()
