"""Puente al módulo compartido comun/costos.py (el log se guarda en la carpeta de la Tarea 1)."""
from comun.costos import (COLUMNAS_LOG, ahora_utc, calcular_costo, franja_vigente,  # noqa: F401
                          limpiar_error)
from comun.costos import registrar_llamada as _registrar
from src.config import BASE


def registrar_llamada(cfg: dict, fila: dict) -> None:
    _registrar(cfg, fila, BASE)
