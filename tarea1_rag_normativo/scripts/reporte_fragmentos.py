"""Reporte de la Fase 2: fragmentos por documento, distribución de longitudes y
comparación de configuraciones de fragmentos con el set de evaluación.

Lee data/processed/fragmentos_<alias>.json (lo escribe build_index.py) y
eval/resultados/resumen_recuperacion.json (lo escribe eval/evaluar_recuperacion.py).
Escribe data/processed/reporte_fragmentos.md y distribucion_fragmentos.png

Uso: python scripts/reporte_fragmentos.py
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import BASE, cargar_config, ruta  # noqa: E402


def main():
    cfg = cargar_config()
    alias = cfg["embeddings"]["modelos"]["local"]["alias"]
    frag = json.loads((ruta(cfg, "processed") / f"fragmentos_{alias}.json").read_text(encoding="utf-8"))
    rec = json.loads((BASE / cfg["evaluacion"]["resultados"] / "resumen_recuperacion.json").read_text(encoding="utf-8"))
    elegida = cfg["fragmentos"]["elegida"]
    docs = [d["id"] for d in cfg["documentos"] if d["incluir"]]
    confs = list(cfg["fragmentos"]["configuraciones"])

    L = ["# Fragmentos e índice (Tarea 1, Fase 2)", "",
         f"Modelo local: `{cfg['embeddings']['modelos']['local']['nombre']}` "
         f"(límite {cfg['embeddings']['modelos']['local']['max_tokens']} tokens). Configuración elegida: **{elegida}**.", "",
         "## Comparación de configuraciones (eval/preguntas.csv, 15 preguntas dentro del corpus)", "",
         "| Config. | Tamaño / solape (chars) | Fragmentos | Recall@1 | Recall@3 | Recall@5 | MRR@5 | Tokens mediana / máx. | Sobre el límite |",
         "|---|---|---|---|---|---|---|---|---|"]
    for c in confs:
        f, r = frag[c], rec[f"{alias}_{c}"]
        marca = " ✅" if c == elegida else ""
        L.append(f"| {c}{marca} | {f['tamano']} / {f['solape']} | {f['fragmentos_total']} | {r['recall@1']:.2f} | {r['recall@3']:.2f} | "
                 f"{r['recall@5']:.2f} | {r['mrr@5']:.2f} | {f['tokens']['mediana']} / {f['tokens']['max']} | {f['tokens']['sobre_limite']} |")
    L += ["", "## Fragmentos por documento", "", "| Documento | " + " | ".join(confs) + " |", "|---|" + "---|" * len(confs)]
    for d in docs:
        L.append(f"| {d} | " + " | ".join(str(frag[c]["fragmentos_por_documento"][d]) for c in confs) + " |")
    L += ["", "## Distribución de longitudes", "", "| Config. | chars mín / mediana / p90 / máx | tokens mín / mediana / p90 / máx |", "|---|---|---|"]
    for c in confs:
        ch, tk = frag[c]["chars"], frag[c]["tokens"]
        L.append(f"| {c} | {ch['min']} / {ch['mediana']} / {ch['p90']} / {ch['max']} | {tk['min']} / {tk['mediana']} / {tk['p90']} / {tk['max']} |")
    L += ["", "Tokens = lo que realmente ve el modelo: prefijo `passage: ` + encabezado corto + texto.", "",
          "![Distribución](distribucion_fragmentos.png)"]
    (ruta(cfg, "processed") / "reporte_fragmentos.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    fig, ejes = plt.subplots(1, len(confs), figsize=(4 * len(confs), 3.2), sharey=False)
    for ax, c in zip(ejes, confs):
        ax.hist(frag[c]["tokens_lista"], bins=25, color="#4C78A8")
        ax.axvline(frag[c]["tokens"]["limite"], color="#E45756", linestyle="--", label="límite 512")
        ax.set_title(f"{c} ({frag[c]['fragmentos_total']} fragmentos)")
        ax.set_xlabel("tokens por fragmento")
        ax.set_xlim(0, 560)
    ejes[0].set_ylabel("n.º de fragmentos")
    ejes[-1].legend()
    fig.tight_layout()
    fig.savefig(ruta(cfg, "processed") / "distribucion_fragmentos.png", dpi=120)
    print("\n".join(L))


if __name__ == "__main__":
    main()
