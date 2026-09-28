"""Compara umbrales candidatos mostrando AMBAS abstenciones, sin nuevas llamadas al LLM.

Usa la corrida diagnóstica (evaluar_motor.py --con-ia --sin-umbral), donde el LLM vio las 25
preguntas. Para un umbral u:
  abstención por umbral (sin IA)  = similitud top-1 < u
  abstención final (con IA)       = similitud top-1 < u  O  el LLM se abstuvo
  llamadas / costo                = solo las preguntas con similitud >= u llegan al LLM

Uso: python eval/opciones_umbral.py --etiqueta prompt_v2
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import BASE, cargar_config  # noqa: E402


def main():
    cfg = cargar_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiqueta", default="")
    args = ap.parse_args()
    res = BASE / cfg["evaluacion"]["resultados"]
    suf = f"_{args.etiqueta}" if args.etiqueta else ""
    filas = list(csv.DictReader(open(res / f"evaluacion_motor_con_ia_sin_umbral{suf}.csv", encoding="utf-8")))
    for f in filas:
        f["sim"] = float(f["sim_top1"])
        f["llm_abst"] = f["abst_llm"] == "True"
    dentro = [f for f in filas if f["tipo"] == "dentro"]
    fuera = [f for f in filas if f["tipo"] == "fuera"]

    salida, L = [], []
    for u in cfg["evaluacion"]["opciones_umbral"]:
        umb_ok = [f["id"] for f in fuera if f["sim"] < u]
        umb_mal = [f["id"] for f in dentro if f["sim"] < u]
        fin_ok = [f["id"] for f in fuera if f["sim"] < u or f["llm_abst"]]
        fin_mal = [f["id"] for f in dentro if f["sim"] < u or f["llm_abst"]]
        fuera_respondidas = [f["id"] for f in fuera if f["sim"] >= u and not f["llm_abst"]]
        llamadas = [f for f in filas if f["sim"] >= u]
        costo = sum(float(f["costo_usd"] or 0) for f in llamadas)
        margen = min(f["sim"] for f in dentro) - u
        salida.append({"umbral": u, "margen_sobre_legitima_mas_baja": round(margen, 4),
                       "umbral_abst_correctas": f"{len(umb_ok)}/{len(fuera)}", "umbral_abst_incorrectas": f"{len(umb_mal)}/{len(dentro)}",
                       "final_abst_correctas": f"{len(fin_ok)}/{len(fuera)}", "final_abst_incorrectas": f"{len(fin_mal)}/{len(dentro)}",
                       "fuera_respondidas_por_error": " ".join(fuera_respondidas) or "ninguna",
                       "dentro_perdidas": " ".join(fin_mal) or "ninguna",
                       "llamadas_llm_de_25": len(llamadas), "costo_eval_usd": round(costo, 6)})
    with open(res / f"opciones_umbral{suf}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(salida[0]))
        w.writeheader()
        w.writerows(salida)
    L = ["| Umbral | Margen sobre la legítima más baja | Umbral (sin IA): correctas / incorrectas | Final (con IA): correctas / incorrectas | Fuera respondidas por error | Dentro perdidas | Llamadas al LLM (de 25) |",
         "|---|---|---|---|---|---|---|"]
    for s in salida:
        L.append(f"| {s['umbral']:.2f} | {s['margen_sobre_legitima_mas_baja']:+.4f} | {s['umbral_abst_correctas']} / {s['umbral_abst_incorrectas']} | "
                 f"{s['final_abst_correctas']} / {s['final_abst_incorrectas']} | {s['fuera_respondidas_por_error']} | {s['dentro_perdidas']} | {s['llamadas_llm_de_25']} |")
    (res / f"opciones_umbral{suf}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print("\nDecisión del LLM por pregunta (sin umbral):")
    for f in sorted(filas, key=lambda x: -x["sim"]):
        print(f"  {f['id']} {f['tipo']:6s} sim={f['sim']:.4f} LLM_se_abstuvo={f['llm_abst']} citas={f['citas']}")


if __name__ == "__main__":
    main()
