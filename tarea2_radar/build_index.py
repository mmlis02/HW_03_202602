"""PROCESO OFFLINE (Tarea 2): indexa las descripciones de los procesos validados en ChromaDB.

Lee data/processed/procesos_validados.parquet (nunca descarga nada). Idempotente: una segunda
corrida no recalcula lo que no cambió.

Uso (desde la carpeta tarea2_radar):  python build_index.py
"""
import time
from datetime import datetime

import pandas as pd

from src.config import BASE, cargar_config, ruta  # importar src primero: habilita el paquete comun/
from comun.embeddings import crear_embedder  # noqa: E402
from src.indice import abrir, indexar


def main():
    cfg = cargar_config()
    ruta(cfg, "logs").mkdir(exist_ok=True)
    log_f = open(ruta(cfg, "logs") / "build_index.log", "a", encoding="utf-8")

    def log(msg):
        linea = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
        print(linea)
        log_f.write(linea + "\n")

    df = pd.read_parquet(ruta(cfg, "processed") / "procesos_validados.parquet")
    emb = crear_embedder(cfg, base=BASE)
    col = abrir(cfg)
    t0 = time.time()
    r = indexar(col, emb, df, cfg["indice"]["lote_insercion"], log)
    log(f"Índice {cfg['indice']['coleccion']}: {r} | {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
