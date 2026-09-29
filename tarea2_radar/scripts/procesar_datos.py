"""Fase 1 (Tarea 2): de los ZIP mensuales a UNA FILA POR PROCESO (ocid).

1. Lee los 3 ZIP (sin descomprimirlos en disco) y convierte cada record en una fila.
2. Junta los 3 meses en una sola tabla (la deduplicación se hace sobre el conjunto, no mes por mes,
   porque un proceso puede aparecer en más de un mes).
3. Deduplica por ocid con una regla explícita (ver REGLA abajo) y registra cuántas filas había,
   cuántos ocid aparecían en más de un mes y cuántas filas quedaron.

Salidas:
  data/processed/procesos_por_mes.parquet   todas las filas (una por record y por archivo mensual)
  data/processed/procesos.parquet           una fila por ocid (entrada de la Fase 2)
  data/processed/reporte_adquisicion.md/.json
  logs/procesar_datos.log

Uso (desde la carpeta tarea2_radar):  python scripts/procesar_datos.py
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.adquisicion import aplanar, leer_records  # noqa: E402
from src.config import archivo, cargar_config, ruta  # noqa: E402

# REGLA de deduplicación: de todas las filas con el mismo ocid se conserva la de compiledRelease
# MÁS RECIENTE (fecha_compilado), porque el compiledRelease es el estado consolidado del proceso y
# el más nuevo incluye todo lo anterior. Desempates, en orden: más releases; mes de archivo más reciente.
ORDEN_REGLA = ["fecha_compilado", "n_releases", "mes_archivo"]
CAMPOS_COMPARACION = ["descripcion", "monto", "comprador_id", "n_postores", "estados_items", "n_adjudicaciones"]


def main():
    cfg = cargar_config()
    raw, proc = ruta(cfg, "raw"), ruta(cfg, "processed")
    proc.mkdir(parents=True, exist_ok=True)
    ruta(cfg, "logs").mkdir(exist_ok=True)
    log = open(ruta(cfg, "logs") / "procesar_datos.log", "a", encoding="utf-8")

    def registrar(msg):
        linea = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
        print(linea)
        log.write(linea + "\n")

    o, inicio = cfg["oece"], time.time()
    filas, por_mes = [], {}
    for m in o["meses"]:
        mes = f"{m['anio']}-{m['mes']}"
        zip_path = raw / f"{mes}_{o['fuente']}_{o['formato']}.zip"
        t0 = time.time()
        n_rel, n = 0, 0
        for rec in leer_records(zip_path):
            filas.append(aplanar(rec, mes))
            n_rel += len(rec.get("releases", []))
            n += 1
        por_mes[mes] = {"records": n, "releases_listadas": n_rel, "segundos_lectura": round(time.time() - t0, 1)}
        registrar(f"{zip_path.name}: {n} records, {n_rel} releases listadas ({time.time() - t0:.1f} s)")

    todas = pd.DataFrame(filas)
    todas.to_parquet(archivo(cfg, "procesos_por_mes"), index=False)

    # --- Duplicados ENTRE meses (sobre el conjunto de los 3 meses) ---
    meses_por_ocid = todas.groupby("ocid")["mes_archivo"].agg(lambda s: sorted(set(s)))
    repetidos = meses_por_ocid[meses_por_ocid.map(len) > 1]
    dup_dentro_de_mes = int(todas.duplicated(["ocid", "mes_archivo"]).sum())
    # ¿Las versiones repetidas son iguales o cambian? (en los campos que usa el análisis)
    sub = todas[todas["ocid"].isin(repetidos.index)]
    distintas = int((sub.groupby("ocid")[CAMPOS_COMPARACION].nunique(dropna=False).max(axis=1) > 1).sum()) if len(sub) else 0

    unicos = (todas.sort_values(ORDEN_REGLA, ascending=False)
                   .drop_duplicates("ocid", keep="first")
                   .assign(meses_en_que_aparece=lambda d: d["ocid"].map(lambda x: ",".join(meses_por_ocid[x])))
                   .sort_values("ocid").reset_index(drop=True))
    unicos.to_parquet(archivo(cfg, "procesos"), index=False)

    rep = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "por_mes": por_mes,
        "filas_antes": len(todas),
        "ocid_distintos": int(todas["ocid"].nunique()),
        "ocid_en_mas_de_un_mes": int(len(repetidos)),
        "ejemplos_ocid_repetidos": {k: v for k, v in list(repetidos.items())[:5]},
        "duplicados_dentro_de_un_mismo_mes": dup_dentro_de_mes,
        "repetidos_con_datos_distintos": distintas,
        "filas_despues": len(unicos),
        "filas_eliminadas": len(todas) - len(unicos),
        "regla": "se conserva la fila con compiledRelease más reciente (fecha_compilado); desempates: más releases, "
                 "mes de archivo más reciente",
        "segundos_total": round(time.time() - inicio, 1),
    }
    (proc / "reporte_adquisicion.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    L = ["# Reporte de adquisición y deduplicación (Tarea 2, Fase 1)", "",
         "| Archivo (mes) | Records (procesos) | Releases listadas |", "|---|---|---|"]
    L += [f"| {k} | {v['records']:,} | {v['releases_listadas']:,} |" for k, v in por_mes.items()]
    L += ["", f"- Filas antes de deduplicar (3 meses juntos): **{rep['filas_antes']:,}**",
          f"- ocid distintos: **{rep['ocid_distintos']:,}**",
          f"- ocid que aparecen en más de un mes: **{rep['ocid_en_mas_de_un_mes']:,}**"
          f" (de ellos, con datos distintos entre meses: {distintas:,})",
          f"- Duplicados dentro de un mismo mes: {dup_dentro_de_mes}",
          f"- Filas después (una por ocid): **{rep['filas_despues']:,}** ({rep['filas_eliminadas']:,} eliminadas)",
          f"- Regla: {rep['regla']}."]
    (proc / "reporte_adquisicion.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    registrar(f"filas antes {rep['filas_antes']} | ocid en >1 mes {rep['ocid_en_mas_de_un_mes']} | "
              f"filas después {rep['filas_despues']} | {rep['segundos_total']} s")
    print("\n".join(L))


if __name__ == "__main__":
    main()
