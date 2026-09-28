"""Costo de cada llamada según la HORA en que se hizo, y registro de todas las llamadas.

La tabla de precios (config.yaml > precios) tiene franjas horarias por modelo. Para
cada llamada se busca la franja que contiene la hora de la llamada (en la zona horaria
configurada) y se aplica ese precio. OpenAI tiene hoy una sola franja (00:00-24:00).
"""
import csv
import re
from datetime import datetime, time as hora
from zoneinfo import ZoneInfo

from pathlib import Path

COLUMNAS_LOG = ["fecha_hora_utc", "modelo", "tokens_entrada", "tokens_entrada_cache", "tokens_salida",
                "latencia_s", "costo_usd", "franja", "exito", "error", "pregunta"]


def _a_hora(texto: str) -> hora | None:
    return None if texto == "24:00" else hora.fromisoformat(texto)  # None = fin del día


def franja_vigente(cfg: dict, modelo: str, momento: datetime) -> dict:
    """Devuelve la franja de precios que aplica a `momento` (datetime con zona horaria).
    Cada franja es [desde, hasta): incluye "desde" y excluye "hasta", así no quedan huecos."""
    local = momento.astimezone(ZoneInfo(cfg["precios"]["zona_horaria"])).time()
    for f in cfg["precios"]["modelos"][modelo]["franjas"]:
        fin = _a_hora(f["hasta"])
        if _a_hora(f["desde"]) <= local and (fin is None or local < fin):
            return f
    raise ValueError(f"No hay franja de precios para {modelo} a las {local}")


def calcular_costo(cfg: dict, modelo: str, momento: datetime, tokens_entrada: int,
                   tokens_salida: int, tokens_cache: int = 0) -> tuple[float, str]:
    f = franja_vigente(cfg, modelo, momento)
    sin_cache = tokens_entrada - tokens_cache
    costo = (sin_cache * f["entrada"] + tokens_cache * f["entrada_cache"] + tokens_salida * f["salida"]) / 1_000_000
    return costo, f"{f['desde']}-{f['hasta']}"


def registrar_llamada(cfg: dict, fila: dict, base: Path) -> None:
    """Agrega una fila al log de costos de la tarea (`base` = carpeta de la tarea)."""
    ruta = Path(base) / cfg["precios"]["log_llamadas"]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not ruta.exists()
    with open(ruta, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS_LOG)
        if nuevo:
            w.writeheader()
        w.writerow({c: fila.get(c, "") for c in COLUMNAS_LOG})


def ahora_utc() -> datetime:
    return datetime.now(ZoneInfo("UTC"))


def limpiar_error(ex: Exception) -> str:
    """Texto del error SIN nada que parezca una clave (OpenAI incluye la clave enmascarada en el 401)."""
    msg = re.sub(r"sk-[A-Za-z0-9*_\-]+", "sk-[oculta]", str(ex))
    return f"{type(ex).__name__}: {msg[:200]}"
