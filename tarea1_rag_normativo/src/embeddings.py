"""Embeddings: UNA interfaz común y dos implementaciones.

Cambiar de modelo es cambiar `embeddings.modelo_activo` en config.yaml; el resto del
código solo usa `crear_embedder(cfg)` y los métodos de la clase base.
"""
import os
import time

import numpy as np


class Embedder:
    """Interfaz común. Devuelve vectores normalizados (producto punto = similitud coseno)."""

    nombre: str
    alias: str
    dimension: int

    def embed_pasajes(self, textos: list[str]) -> np.ndarray:
        raise NotImplementedError

    def embed_consulta(self, texto: str) -> np.ndarray:
        raise NotImplementedError

    def contar_tokens(self, texto: str) -> int:
        raise NotImplementedError


class EmbedderLocal(Embedder):
    """Modelo local de sentence-transformers (p. ej. multilingual-e5-small), corre en CPU."""

    def __init__(self, mcfg: dict):
        from sentence_transformers import SentenceTransformer  # import aquí: es pesado

        self.nombre, self.alias = mcfg["nombre"], mcfg["alias"]
        self.pref_q, self.pref_p = mcfg["prefijo_consulta"], mcfg["prefijo_pasaje"]
        self.lote = mcfg["lote"]
        self.modelo = SentenceTransformer(self.nombre, device="cpu")
        self.modelo.max_seq_length = mcfg["max_tokens"]
        self.dimension = (self.modelo.get_embedding_dimension() if hasattr(self.modelo, "get_embedding_dimension")
                          else self.modelo.get_sentence_embedding_dimension())

    def embed_pasajes(self, textos):
        return self.modelo.encode([self.pref_p + t for t in textos], batch_size=self.lote,
                                  normalize_embeddings=True, show_progress_bar=False)

    def embed_consulta(self, texto):
        return self.modelo.encode([self.pref_q + texto], normalize_embeddings=True)[0]

    def contar_tokens(self, texto):
        return len(self.modelo.tokenizer(texto, add_special_tokens=True)["input_ids"])


class EmbedderOpenAI(Embedder):
    """text-embedding-3-small por API. Cada llamada cuesta dinero: se usa solo en la Fase 4."""

    def __init__(self, mcfg: dict):
        from dotenv import load_dotenv
        from openai import OpenAI
        import tiktoken

        load_dotenv()
        self.nombre, self.alias, self.lote = mcfg["nombre"], mcfg["alias"], mcfg["lote"]
        self.cliente = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.tokenizador = tiktoken.get_encoding("cl100k_base")
        self.dimension = 1536
        self.tokens_usados = 0

    def _llamar(self, textos):
        inicio = time.time()
        r = self.cliente.embeddings.create(model=self.nombre, input=textos)
        self.tokens_usados += r.usage.total_tokens
        self.ultima_latencia = time.time() - inicio
        return np.array([d.embedding for d in r.data], dtype=np.float32)

    def embed_pasajes(self, textos):
        partes = [self._llamar(textos[i:i + self.lote]) for i in range(0, len(textos), self.lote)]
        return np.vstack(partes)

    def embed_consulta(self, texto):
        return self._llamar([texto])[0]

    def contar_tokens(self, texto):
        return len(self.tokenizador.encode(texto))


def crear_embedder(cfg: dict, modelo: str | None = None) -> Embedder:
    clave = modelo or cfg["embeddings"]["modelo_activo"]
    mcfg = cfg["embeddings"]["modelos"][clave]
    if mcfg["tipo"] == "sentence_transformers":
        return EmbedderLocal(mcfg)
    if mcfg["tipo"] == "openai":
        return EmbedderOpenAI(mcfg)
    raise ValueError(f"Tipo de embeddings desconocido: {mcfg['tipo']}")
