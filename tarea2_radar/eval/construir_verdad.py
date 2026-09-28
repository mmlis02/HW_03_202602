"""Construye los procesos relevantes de cada pregunta a partir de eval/definiciones.yaml,
FILTRANDO la tabla validada y buscando palabras clave (sin usar el buscador semántico).

Salida: eval/relevantes.json ({id: [ocid, ...]}) y eval/preguntas.csv (resumen documentado).
Uso: python eval/construir_verdad.py
"""
import csv
import json
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import BASE, ruta, cargar_config  # noqa: E402
from src.territorio import clave  # noqa: E402


def filtrar(d: pd.DataFrame, f: dict) -> pd.DataFrame:
    if f.get("departamento"):
        d = d[d["departamento"] == f["departamento"]]
    if f.get("categoria"):
        d = d[d["categoria_es"] == f["categoria"]]
    if f.get("monto_min") is not None:
        d = d[d["monto_valido"] & (d["monto_pen"] >= f["monto_min"])]
    if f.get("monto_max") is not None:
        d = d[d["monto_valido"] & (d["monto_pen"] <= f["monto_max"])]
    fecha = d["fecha_publicacion_dt"].dt.strftime("%Y-%m-%d")
    if f.get("fecha_desde"):
        d = d[fecha >= f["fecha_desde"]]
        fecha = d["fecha_publicacion_dt"].dt.strftime("%Y-%m-%d")
    if f.get("fecha_hasta"):
        d = d[fecha <= f["fecha_hasta"]]
    return d


def main():
    cfg = cargar_config()
    defs = yaml.safe_load(open(BASE / "eval" / "definiciones.yaml", encoding="utf-8"))
    d = pd.read_parquet(ruta(cfg, "processed") / "procesos_validados.parquet")
    d = d[d["incluir_en_analisis"]].copy()
    d["clave_desc"] = d["descripcion_limpia"].map(clave)
    relevantes, filas = {}, []
    for q in defs["dentro"]:
        x = filtrar(d, q.get("filtros") or {})
        hit = x[x["clave_desc"].str.contains(q["incluir"], regex=True)]
        if q.get("excluir"):
            hit = hit[~hit["clave_desc"].str.contains(q["excluir"], regex=True)]
        relevantes[q["id"]] = hit["ocid"].tolist()
        filas.append({"id": q["id"], "tipo": "dentro", "pregunta": q["pregunta"],
                      "filtros": json.dumps(q.get("filtros") or {}, ensure_ascii=False),
                      "procesos_tras_filtros": len(x), "relevantes": len(hit),
                      "como_se_armo": f"filtros {q.get('filtros') or {}} + incluir /{q['incluir']}/"
                                      + (f" − excluir /{q['excluir']}/" if q.get("excluir") else "")
                                      + (f". {q['nota']}" if q.get("nota") else "")})
    for q in defs.get("sin_resultados", []):
        x = filtrar(d, q["filtros"])
        relevantes[q["id"]] = []
        filas.append({"id": q["id"], "tipo": "sin_resultados", "pregunta": q["pregunta"],
                      "filtros": json.dumps(q["filtros"], ensure_ascii=False), "procesos_tras_filtros": len(x),
                      "relevantes": 0, "como_se_armo": f"filtros {q['filtros']} dejan {len(x)} procesos. {q.get('nota', '')}"})
    for q in defs["fuera"]:
        relevantes[q["id"]] = []
        filas.append({"id": q["id"], "tipo": "fuera", "pregunta": q["pregunta"], "filtros": "{}",
                      "procesos_tras_filtros": "", "relevantes": 0, "como_se_armo": q["porque"]})
    # verificación de las preguntas "fuera" con palabras clave
    for pat in ("AVION|AERONAVE DE COMBATE|F-35", "SUBMARIN"):
        n = int(d["clave_desc"].str.contains(pat, regex=True).sum())
        print(f"verificación fuera /{pat}/: {n} procesos")
    (BASE / "eval" / "relevantes.json").write_text(json.dumps(relevantes, indent=1), encoding="utf-8")
    with open(BASE / "eval" / "preguntas.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    for f in filas:
        print(f"{f['id']} {f['tipo']:6s} tras filtros {f['procesos_tras_filtros']!s:>6} → relevantes {f['relevantes']:>3} | {f['pregunta']}")


if __name__ == "__main__":
    main()
