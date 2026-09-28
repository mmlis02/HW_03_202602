"""Barrido del umbral de abstención (defensa 1, SIN IA) para la Tarea 2.

Similitud top-1 de cada pregunta: las de dentro con sus filtros correctos (como las buscará el
motor) y las de fuera sin filtros. Verifica si el umbral heredado de la Tarea 1 sirve aquí.
Salida: eval/resultados/barrido_umbral.csv / .png y puntajes_top1.md
Uso: python eval/barrido_umbral.py   (después de evaluar_recuperacion.py)
"""
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import yaml  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import BASE, cargar_config  # noqa: E402


def main():
    cfg = cargar_config()
    ev, res = cfg["evaluacion"], BASE / cfg["evaluacion"]["resultados"]
    heredado = cfg["motor"]["umbral_similitud"]
    defs = yaml.safe_load(open(BASE / ev["definiciones"], encoding="utf-8"))
    preg = {q["id"]: q["pregunta"] for t in ("dentro", "fuera") for q in defs[t]}
    filas = [r for r in csv.DictReader(open(res / "recuperacion.csv", encoding="utf-8"))
             if (r["tipo"] == "dentro" and r["modo"] == "con_filtros") or r["tipo"] == "fuera"]
    dentro = [float(r["sim_top1"]) for r in filas if r["tipo"] == "dentro"]
    fuera = [float(r["sim_top1"]) for r in filas if r["tipo"] == "fuera"]
    b = ev["barrido"]
    umbrales = [round(b["desde"] + i * b["paso"], 4) for i in range(int(round((b["hasta"] - b["desde"]) / b["paso"])) + 1)]
    tabla = [{"umbral": u, "fuera_detenidas": sum(s < u for s in fuera), "dentro_detenidas": sum(s < u for s in dentro),
              "fuera_que_pasan": sum(s >= u for s in fuera)} for u in umbrales]
    with open(res / "barrido_umbral.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(tabla[0]))
        w.writeheader()
        w.writerows(tabla)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(umbrales, [t["fuera_detenidas"] / len(fuera) for t in tabla], label="fuera detenidas (bien)", color="#4C78A8")
    ax.plot(umbrales, [t["dentro_detenidas"] / len(dentro) for t in tabla], label="dentro detenidas (mal)", color="#E45756")
    ax.axvline(heredado, color="black", linestyle="--", label=f"umbral heredado de la Tarea 1 ({heredado})")
    ax.set_xlabel("umbral de similitud top-1")
    ax.set_ylabel("proporción")
    ax.set_title(f"Tarea 2: barrido del umbral ({len(dentro)} preguntas dentro, {len(fuera)} fuera)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(res / "barrido_umbral.png", dpi=120)
    orden = sorted(filas, key=lambda r: -float(r["sim_top1"]))
    L = ["| # | id | tipo | similitud top-1 | pregunta |", "|---|---|---|---|---|"]
    L += [f"| {i} | {r['id']} | {r['tipo']} | {float(r['sim_top1']):.4f} | {preg[r['id']]} |" for i, r in enumerate(orden, 1)]
    (res / "puntajes_top1.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\ndentro: min {min(dentro):.4f} max {max(dentro):.4f} | fuera: min {min(fuera):.4f} max {max(fuera):.4f}")
    for t in tabla:
        if abs((t["umbral"] * 1000) % 10) < 1e-6 or abs(t["umbral"] - heredado) < 1e-9:
            print(f"umbral {t['umbral']:.3f}: fuera detenidas {t['fuera_detenidas']}/{len(fuera)} | dentro detenidas {t['dentro_detenidas']}/{len(dentro)}")


if __name__ == "__main__":
    main()
