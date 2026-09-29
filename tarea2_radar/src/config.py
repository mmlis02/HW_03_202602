"""Carga config.yaml de la Tarea 2 y resuelve rutas relativas a esta carpeta."""
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parent.parent


def cargar_config(ruta: Path = BASE / "config.yaml") -> dict:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def ruta(cfg: dict, clave: str) -> Path:
    return BASE / cfg["rutas"][clave]


def archivo(cfg: dict, clave: str) -> Path:
    """Ruta absoluta de cfg['archivos'][clave] (datos que pasan de una etapa a otra)."""
    return BASE / cfg["archivos"][clave]
