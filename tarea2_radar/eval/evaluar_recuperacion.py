"""Evalúa la recuperación (sin LLM, costo 0) de la Tarea 2 con las preguntas de eval/definiciones.yaml.

Para cada pregunta se busca de dos formas:
  - CON FILTROS: los filtros estructurados correctos de la pregunta (departamento, monto, fecha,
    categoría) se aplican como `where` en ChromaDB y los embeddings solo ordenan por significado.
  - SOLO EMBEDDINGS: la misma pregunta, sin filtros.
Métricas:
  - Recall@k: % de preguntas con al menos un proceso relevante entre los k primeros.
  - Precisión@k: % de los k primeros que son relevantes.
  - Cumplen condiciones@k (solo embeddings): % de los k primeros que cumplen los filtros de la
    pregunta (el departamento, el monto, la fecha...). Muestra lo que pasa si se dejan a los embeddings.
  - Similitud top-1 dentro/fuera (insumo del barrido del umbral).
Uso: python eval/evaluar_recuperacion.py
"""
import csv
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import BASE, cargar_config  # noqa: E402
from comun.embeddings import crear_embedder  # noqa: E402
from src.indice import abrir, buscar  # noqa: E402


def cumple(md: dict, f: dict) -> bool:
    if f.get("departamento") and md["departamento"] != f["departamento"]:
        return False
    if f.get("categoria") and md["categoria"] != f["categoria"]:
        return False
    if f.get("monto_min") is not None and not (md["monto_valido"] and md["monto_pen"] >= f["monto_min"]):
        return False
    if f.get("monto_max") is not None and not (md["monto_valido"] and md["monto_pen"] <= f["monto_max"]):
        return False
    if f.get("fecha_desde") and md["fecha_int"] < int(f["fecha_desde"].replace("-", "")):
        return False
    if f.get("fecha_hasta") and md["fecha_int"] > int(f["fecha_hasta"].replace("-", "")):
        return False
    return True


def main():
    cfg = cargar_config()
    ev = cfg["evaluacion"]
    defs = yaml.safe_load(open(BASE / ev["definiciones"], encoding="utf-8"))
    rel = json.loads((BASE / ev["relevantes"]).read_text(encoding="utf-8"))
    emb = crear_embedder(cfg, base=BASE)
    col = abrir(cfg, crear=False)
    K = max(ev["k_valores"])
    filas = []
    for tipo in ("dentro", "fuera"):
        for q in defs[tipo]:
            f = q.get("filtros") or {}
            relev = set(rel[q["id"]])
            for modo, filtros in (("con_filtros", f), ("solo_embeddings", {})):
                if tipo == "fuera" and modo == "con_filtros":
                    continue
                res = buscar(col, emb, q["pregunta"], K, filtros)
                fila = {"id": q["id"], "tipo": tipo, "modo": modo, "n_relevantes": len(relev),
                        "sim_top1": res[0]["similitud"] if res else 0.0, "n_resultados": len(res)}
                for k in ev["k_valores"]:
                    top = res[:k]
                    fila[f"hit@{k}"] = int(any(r["ocid"] in relev for r in top))
                    fila[f"prec@{k}"] = round(sum(r["ocid"] in relev for r in top) / k, 3)
                    # sobre los resultados devueltos (si el filtro deja menos de k procesos, se divide por los que hay)
                    fila[f"cumple@{k}"] = round(sum(cumple(r["metadatos"], f) for r in top) / max(1, len(top)), 3) if f else ""
                fila["top3"] = " | ".join(f"{r['metadatos']['departamento']} S/{r['metadatos']['monto_pen']:,.0f} "
                                          f"{r['descripcion'][:50]}" for r in res[:3])
                filas.append(fila)
    salida = BASE / ev["resultados"]
    salida.mkdir(parents=True, exist_ok=True)
    with open(salida / "recuperacion.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    resumen = {}
    for modo in ("con_filtros", "solo_embeddings"):
        x = [r for r in filas if r["tipo"] == "dentro" and r["modo"] == modo]
        resumen[modo] = {f"recall@{k}": round(sum(r[f"hit@{k}"] for r in x) / len(x), 3) for k in ev["k_valores"]}
        resumen[modo].update({f"precision@{k}": round(sum(r[f"prec@{k}"] for r in x) / len(x), 3) for k in ev["k_valores"]})
        con_f = [r for r in x if r["cumple@5"] != ""]
        resumen[modo]["cumplen_condiciones@5"] = round(sum(r["cumple@5"] for r in con_f) / len(con_f), 3) if con_f else None
    (salida / "resumen_recuperacion.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resumen, indent=1, ensure_ascii=False))
    for r in filas:
        if r["tipo"] == "dentro":
            print(f"{r['id']} {r['modo']:16s} hit@1={r['hit@1']} hit@5={r['hit@5']} prec@5={r['prec@5']} cumple@5={r['cumple@5']} sim={r['sim_top1']}")


if __name__ == "__main__":
    main()
