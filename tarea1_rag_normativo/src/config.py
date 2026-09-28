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


def umbral_activo(cfg: dict, modelo: str | None = None) -> float:
    """Umbral de similitud del modelo de embeddings activo (o del indicado)."""
    return cfg["motor"]["umbral_similitud"][modelo or cfg["embeddings"]["modelo_activo"]]
