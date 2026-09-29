"""Fase 5: calcula el indicador de un solo postor por departamento y por entidad.
Salidas en data/outputs/: riesgo_departamentos.csv, riesgo_entidades.csv, riesgo_top_entidades.csv, riesgo_resumen.json
Uso (desde tarea2_radar): python scripts/calcular_riesgo.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import BASE, cargar_config, ruta  # noqa: E402
from src.riesgo import distribucion_entidades, por_grupo, universo  # noqa: E402


def main():
    cfg = cargar_config()
    rc = cfg["riesgo"]
    out = BASE / rc["salidas"]
    df = pd.read_parquet(ruta(cfg, "processed") / "procesos_validados.parquet")
    u, conteo = universo(df, rc["metodos_competitivos"])
    dep = por_grupo(u, "departamento")
    ent = por_grupo(u, "comprador_id", "comprador_nombre_limpio")
    ent_min = ent[ent["procesos"] >= rc["min_procesos_entidad"]]
    top = ent_min.head(rc["top_entidades"])
    dist, pct = distribucion_entidades(u)
    dep.to_csv(out / "riesgo_departamentos.csv", index=False)
    ent_min.to_csv(out / "riesgo_entidades.csv", index=False)
    top.to_csv(out / "riesgo_top_entidades.csv", index=False)
    resumen = {**conteo, "min_procesos_entidad": rc["min_procesos_entidad"], "percentiles_procesos_por_entidad": pct,
               "distribucion_minimos": dist.to_dict("records"), "entidades_en_ranking": len(ent_min),
               "empates_en_el_corte_del_top": int((ent_min["tasa_un_postor"] == top["tasa_un_postor"].min()).sum()) if len(top) else 0}
    (out / "riesgo_resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False, default=int), encoding="utf-8")
    print(json.dumps({k: v for k, v in resumen.items() if k != "distribucion_minimos"}, indent=1, ensure_ascii=False, default=int))
    print(dist.to_string(index=False))
    print("\nTop entidades:"); print(top[["nombre", "departamento", "procesos", "un_postor", "tasa_un_postor", "ic95_inf", "ic95_sup"]].to_string(index=False))
    print("\nDepartamentos:"); print(dep.head(8).to_string(index=False))


if __name__ == "__main__":
    main()
