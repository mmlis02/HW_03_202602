"""Carga config.yaml y convierte las rutas relativas en rutas absolutas."""
from pathlib import Path

import yaml

# Carpeta de la Tarea 1 (donde vive config.yaml)
BASE = Path(__file__).resolve().parent.parent


def cargar_config(ruta: Path = BASE / "config.yaml") -> dict:
    with open(ruta, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg


def ruta(cfg: dict, clave: str) -> Path:
    """Devuelve la ruta absoluta de cfg['rutas'][clave]."""
    return BASE / cfg["rutas"][clave]
