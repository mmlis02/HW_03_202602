"""Evalúa SOLO la etapa de recuperación (buscador), sin llamar al modelo de generación.

Para cada pregunta de eval/preguntas.csv busca los k fragmentos más parecidos y mide:
- Recall@k (preguntas dentro del corpus): % de preguntas en que al menos una de las
  páginas esperadas aparece entre los k primeros fragmentos. Una pregunta puede tener
  varias páginas válidas (p. ej. D08: "ley32069:43;dl1715:1,2"); basta con cualquiera.
- Similitud del mejor fragmento (top-1) de cada pregunta, dentro y fuera del corpus:
  es la materia prima para calibrar el umbral de abstención (Fase 3).

Uso (desde la carpeta tarea1_rag_normativo):
    python eval/evaluar_recuperacion.py                    # config elegida, modelo activo
    python eval/evaluar_recuperacion.py --fragmentos todas
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import BASE, cargar_config  # noqa: E402
from src.embeddings import crear_embedder  # noqa: E402
from src.indice import abrir_coleccion, buscar  # noqa: E402


def paginas_validas(campo: str) -> set[tuple[str, int]]:
    """'ley32069:43;dl1715:1,2' -> {('ley32069',43), ('dl1715',1), ('dl1715',2)}"""
    validas = set()
    for parte in filter(None, campo.split(";")):
        doc, pags = parte.split(":")
        validas |= {(doc.strip(), int(p)) for p in pags.split(",")}
    return validas


def evaluar(coleccion, embedder, preguntas: list[dict], k_max: int) -> list[dict]:
    filas = []
    for p in preguntas:
        inicio = time.time()
        res = buscar(coleccion, embedder, p["pregunta"], k_max)
        latencia = time.time() - inicio
        validas = paginas_validas(p["paginas_esperadas"])
        rango = next((i + 1 for i, r in enumerate(res)
                      if (r["metadatos"]["documento"], r["metadatos"]["pagina"]) in validas), None)
        filas.append({
            "id": p["id"], "tipo": p["tipo"], "estilo": p["estilo"],
            "sim_top1": round(res[0]["similitud"], 4),
            "rango_primer_acierto": rango if p["tipo"] == "dentro" else "",
            "top_recuperados": " | ".join(f"{r['metadatos']['documento']}:p{r['metadatos']['pagina']}"
                                          f"({r['similitud']:.3f})" for r in res),
            "latencia_s": round(latencia, 4),
        })
    return filas


def recall(filas: list[dict], k: int) -> float:
    dentro = [f for f in filas if f["tipo"] == "dentro"]
    return sum(1 for f in dentro if f["rango_primer_acierto"] and f["rango_primer_acierto"] <= k) / len(dentro)


def mrr(filas: list[dict]) -> float:
    """Mean Reciprocal Rank: 1 si el acierto está 1.º, 1/2 si está 2.º, ... 0 si no aparece."""
    dentro = [f for f in filas if f["tipo"] == "dentro"]
    return sum(1 / f["rango_primer_acierto"] for f in dentro if f["rango_primer_acierto"]) / len(dentro)


def main():
    cfg = cargar_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--fragmentos", default=cfg["fragmentos"]["elegida"])
    ap.add_argument("--modelo", default=cfg["embeddings"]["modelo_activo"])
    args = ap.parse_args()

    ks = cfg["evaluacion"]["k_valores"]
    preguntas = list(csv.DictReader(open(BASE / cfg["evaluacion"]["preguntas"], encoding="utf-8")))
    salida = BASE / cfg["evaluacion"]["resultados"]
    salida.mkdir(parents=True, exist_ok=True)
    embedder = crear_embedder(cfg, args.modelo)
    confs = list(cfg["fragmentos"]["configuraciones"]) if args.fragmentos == "todas" else [args.fragmentos]

    resumen_path = salida / "resumen_recuperacion.json"
    resumen = json.loads(resumen_path.read_text(encoding="utf-8")) if resumen_path.exists() else {}
    for conf in confs:
        col = abrir_coleccion(cfg, embedder.alias, conf, crear=False)
        filas = evaluar(col, embedder, preguntas, max(ks))
        with open(salida / f"recuperacion_{embedder.alias}_{conf}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
        clave = f"{embedder.alias}_{conf}"
        resumen[clave] = {f"recall@{k}": round(recall(filas, k), 3) for k in ks}
        resumen[clave]["mrr@5"] = round(mrr(filas), 3)
        resumen[clave]["latencia_media_s"] = round(sum(f["latencia_s"] for f in filas) / len(filas), 4)
        dentro = [f["sim_top1"] for f in filas if f["tipo"] == "dentro"]
        fuera = [f["sim_top1"] for f in filas if f["tipo"] == "fuera"]
        resumen[clave]["sim_top1_dentro_min"] = min(dentro)
        resumen[clave]["sim_top1_fuera_max"] = max(fuera)
        print(clave, resumen[clave])
        for f in filas:
            if f["tipo"] == "dentro" and (not f["rango_primer_acierto"] or f["rango_primer_acierto"] > 1):
                print(f"   {f['id']}: primer acierto en posición {f['rango_primer_acierto'] or '>' + str(max(ks))} -> {f['top_recuperados']}")
    resumen_path.write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
