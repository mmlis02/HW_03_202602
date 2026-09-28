"""Barrido del umbral de abstención (defensa 1: SIN IA, costo 0).

Usa la similitud del mejor fragmento (top-1) de cada pregunta, calculada por
eval/evaluar_recuperacion.py, y para cada umbral posible cuenta:
- abstenciones correctas: preguntas FUERA del corpus que el umbral detiene
- abstenciones incorrectas: preguntas DENTRO del corpus que el umbral detiene (se pierde una respuesta)
- fuera que pasan: preguntas fuera del corpus que llegarían al LLM (las debe frenar la defensa 2)

Escribe en eval/resultados/:
  barrido_umbral_<alias>_<conf>.csv / .png   tabla y gráfico del barrido
  puntajes_top1_<alias>_<conf>.md            tabla de las 25 preguntas ordenadas por similitud

Uso: python eval/barrido_umbral.py   (usa la configuración elegida y el umbral de config.yaml)
"""
import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import BASE, cargar_config  # noqa: E402


def main():
    cfg = cargar_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--fragmentos", default=cfg["fragmentos"]["elegida"])
    ap.add_argument("--alias", default=cfg["embeddings"]["modelos"][cfg["embeddings"]["modelo_activo"]]["alias"])
    args = ap.parse_args()
    res = BASE / cfg["evaluacion"]["resultados"]
    umbral_elegido = cfg["motor"]["umbral_similitud"]

    preguntas = {p["id"]: p for p in csv.DictReader(open(BASE / cfg["evaluacion"]["preguntas"], encoding="utf-8"))}
    filas = list(csv.DictReader(open(res / f"recuperacion_{args.alias}_{args.fragmentos}.csv", encoding="utf-8")))
    dentro = [float(f["sim_top1"]) for f in filas if f["tipo"] == "dentro"]
    fuera = [float(f["sim_top1"]) for f in filas if f["tipo"] == "fuera"]

    # --- Barrido ---
    p = cfg["evaluacion"]["barrido"]
    umbrales = [round(p["desde"] + i * p["paso"], 4) for i in range(int(round((p["hasta"] - p["desde"]) / p["paso"])) + 1)]
    tabla = []
    for u in umbrales:
        inc = sum(s < u for s in dentro)
        cor = sum(s < u for s in fuera)
        tabla.append({"umbral": u, "abstenciones_correctas": cor, "abstenciones_incorrectas": inc,
                      "fuera_que_pasan_al_llm": len(fuera) - cor, "dentro_que_responde": len(dentro) - inc,
                      "tasa_abst_correcta": round(cor / len(fuera), 3), "tasa_abst_incorrecta": round(inc / len(dentro), 3)})
    nombre = f"{args.alias}_{args.fragmentos}"
    with open(res / f"barrido_umbral_{nombre}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(tabla[0]))
        w.writeheader()
        w.writerows(tabla)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(umbrales, [t["tasa_abst_correcta"] for t in tabla], label="fuera del corpus detenidas (bien)", color="#4C78A8")
    ax.plot(umbrales, [t["tasa_abst_incorrecta"] for t in tabla], label="dentro del corpus detenidas (mal)", color="#E45756")
    ax.axvline(umbral_elegido, color="black", linestyle="--", label=f"umbral elegido {umbral_elegido}")
    ax.set_xlabel("umbral de similitud top-1")
    ax.set_ylabel("proporción de preguntas")
    ax.set_title(f"Barrido del umbral ({nombre}): 15 preguntas dentro, 10 fuera")
    ax.legend(loc="center left", fontsize=8)
    fig.tight_layout()
    fig.savefig(res / f"barrido_umbral_{nombre}.png", dpi=120)

    # --- Tabla de puntajes ordenada (evidencia para las dos defensas) ---
    orden = sorted(filas, key=lambda f: -float(f["sim_top1"]))
    L = [f"# Similitud top-1 de las 25 preguntas ({nombre})", "",
         f"Umbral elegido: **{umbral_elegido}** (defensa 1, sin IA). Ordenadas de mayor a menor similitud.", "",
         "| # | id | Tipo | Similitud top-1 | Pregunta | Defensa 1 (umbral) |", "|---|---|---|---|---|---|"]
    for i, f in enumerate(orden, 1):
        s = float(f["sim_top1"])
        if f["tipo"] == "fuera":
            decision = "detenida ✅" if s < umbral_elegido else "**pasa → defensa 2 (IA)**"
        else:
            decision = "pasa ✅" if s >= umbral_elegido else "**detenida por error ❌**"
        tipo = "fuera" if f["tipo"] == "fuera" else "dentro"
        L.append(f"| {i} | {f['id']} | {tipo} | {s:.4f} | {preguntas[f['id']]['pregunta']} | {decision} |")
    menor_dentro = min(dentro)
    trampas = [f for f in orden if f["tipo"] == "fuera" and float(f["sim_top1"]) > menor_dentro]
    L += ["", f"La pregunta legítima con menor similitud tiene **{menor_dentro:.4f}**. "
          f"**{len(trampas)} preguntas fuera del corpus la superan**: " +
          ", ".join(f"{f['id']} ({float(f['sim_top1']):.4f})" for f in trampas) +
          ". Ningún umbral puede detenerlas sin detener también preguntas legítimas: por eso existe la defensa 2."]
    (res / f"puntajes_top1_{nombre}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    elegido = next(t for t in tabla if abs(t["umbral"] - umbral_elegido) < 1e-9) if umbral_elegido in umbrales else None
    print("\nEn el umbral elegido:", elegido)


if __name__ == "__main__":
    main()
