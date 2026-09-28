"""Trae las NOVEDADES del mes en curso desde la API de OECE (tabla aparte del corpus mensual).

Uso (desde la carpeta tarea2_radar):  python scripts/actualizar_api.py
Salida: data/processed/novedades_api.parquet y logs/api.log
"""
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.api_oece import ClienteOECE  # noqa: E402
from src.config import BASE, cargar_config, ruta  # noqa: E402


def main():
    cfg = cargar_config()
    p = cfg["api"]["parametros"]
    ruta(cfg, "logs").mkdir(exist_ok=True)
    log_f = open(ruta(cfg, "logs") / "api.log", "a", encoding="utf-8")

    def log(msg):
        linea = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
        print(linea)
        log_f.write(linea + "\n")

    cliente = ClienteOECE(cfg, BASE / cfg["api"]["cache"] / f"{p['year']}-{p['month']}", log)
    inicio, filas, de_cache, n = time.time(), [], 0, 1
    while n <= cfg["api"]["max_paginas"]:
        try:
            datos, cache = cliente.pagina(n)
        except RuntimeError as ex:
            log(f"[detenido] {ex}. Las páginas anteriores quedaron en caché; vuelve a correr el script para continuar.")
            break
        de_cache += cache
        for r in datos.get("results", []):
            cr = r.get("compiledRelease") or {}
            t, v = cr.get("tender") or {}, (cr.get("tender") or {}).get("value") or {}
            filas.append({"ocid": cr.get("ocid"), "fecha_compilado": cr.get("date"),
                          "segmentacion": (cr.get("dataSegmentation") or {}).get("id"),
                          "nomenclatura": t.get("title"), "descripcion": t.get("description"),
                          "metodo": t.get("procurementMethodDetails"), "categoria": t.get("mainProcurementCategory"),
                          "monto": v.get("amount"), "moneda": v.get("currency"), "fecha_publicacion": t.get("datePublished"),
                          "comprador_id": (cr.get("buyer") or {}).get("id"), "comprador_nombre": (cr.get("buyer") or {}).get("name"),
                          "n_releases": len(r.get("releases") or [])})
        pag = datos.get("pagination") or {}
        if n == 1:
            log(f"API {p['year']}-{p['month']}: {pag.get('total_results')} procesos en {pag.get('num_pages')} páginas")
        if not pag.get("has_next"):
            break
        n += 1
    df = pd.DataFrame(filas).drop_duplicates("ocid")
    df.to_parquet(ruta(cfg, "processed") / "novedades_api.parquet", index=False)
    log(f"Resumen API: {len(df)} procesos únicos | páginas {n} ({de_cache} de caché) | pedidos HTTP {cliente.pedidos} | "
        f"{cliente.bytes / 1e6:.1f} MB descargados | {time.time() - inicio:.1f} s")


if __name__ == "__main__":
    main()
