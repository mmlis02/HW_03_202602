"""Puente al módulo compartido comun/embeddings.py (misma interfaz común con dos implementaciones)."""
from comun.embeddings import Embedder, EmbedderLocal, EmbedderOpenAI  # noqa: F401
from comun.embeddings import crear_embedder as _crear
from src.config import BASE


def crear_embedder(cfg: dict, modelo: str | None = None) -> Embedder:
    return _crear(cfg, modelo, BASE)
