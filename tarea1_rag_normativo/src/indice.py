"""Índice vectorial persistente en ChromaDB.

Garantías del proceso de construcción:
- Idempotente: se usa `upsert` con IDs estables; correrlo dos veces no duplica nada.
- Reanudable: se guarda por lotes; si se corta, la siguiente corrida salta los
  fragmentos que ya están con el mismo contenido (mismo hash) y sigue con el resto.
- Aislado por documento: al (re)indexar un documento solo se leen y borran IDs con
  `documento == <ese id>`; los fragmentos de otros documentos no se tocan.
"""
import hashlib
import json

import chromadb

from src.config import BASE


def texto_para_embedding(frag: dict, nombres_cortos: dict) -> str:
    """Encabezado corto + texto. El encabezado ayuda a distinguir la ley del decreto."""
    md = frag["metadatos"]
    encabezado = nombres_cortos.get(md["documento"], md["documento"])
    if md["articulo"]:
        encabezado += f" — {md['articulo']}"
    return f"{encabezado}\n{frag['texto']}"


def nombre_coleccion(cfg: dict, alias_modelo: str, conf_fragmentos: str) -> str:
    return f"{cfg['indice']['prefijo_coleccion']}_{alias_modelo}_{conf_fragmentos}"


def abrir_coleccion(cfg: dict, alias_modelo: str, conf_fragmentos: str, crear: bool = True):
    cliente = chromadb.PersistentClient(path=str(BASE / cfg["indice"]["carpeta"]))
    nombre = nombre_coleccion(cfg, alias_modelo, conf_fragmentos)
    if crear:
        return cliente.get_or_create_collection(nombre, metadata={"hnsw:space": "cosine"})
    return cliente.get_collection(nombre)  # modo consulta: falla si el índice no existe


def indexar_documento(coleccion, embedder, fragmentos: list[dict], documento: str,
                      nombres_cortos: dict, lote: int, log=print) -> dict:
    # La huella cubre TODO lo que afecta al índice: texto, encabezado del embedding y metadatos.
    # Si cualquiera cambia, el fragmento se vuelve a calcular; si no, se salta.
    for f in fragmentos:
        md = {k: v for k, v in f["metadatos"].items() if k != "hash"}
        base = texto_para_embedding(f, nombres_cortos) + json.dumps(md, sort_keys=True, ensure_ascii=False)
        f["metadatos"]["hash"] = hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]

    existentes = coleccion.get(where={"documento": documento}, include=["metadatas"])
    hash_existente = {i: m["hash"] for i, m in zip(existentes["ids"], existentes["metadatas"])}
    nuevos_ids = {f["id"] for f in fragmentos}

    # Fragmentos de ESTE documento que ya no existen (p. ej. cambió la limpieza): se borran
    sobrantes = [i for i in hash_existente if i not in nuevos_ids]
    if sobrantes:
        coleccion.delete(ids=sobrantes)

    pendientes = [f for f in fragmentos if hash_existente.get(f["id"]) != f["metadatos"]["hash"]]
    for i in range(0, len(pendientes), lote):
        bloque = pendientes[i:i + lote]
        vectores = embedder.embed_pasajes([texto_para_embedding(f, nombres_cortos) for f in bloque])
        coleccion.upsert(
            ids=[f["id"] for f in bloque],
            documents=[f["texto"] for f in bloque],
            metadatas=[f["metadatos"] for f in bloque],
            embeddings=[v.tolist() for v in vectores],
        )
        log(f"   {documento}: {min(i + lote, len(pendientes))}/{len(pendientes)} fragmentos guardados")
    return {"documento": documento, "total": len(fragmentos), "ya_estaban": len(fragmentos) - len(pendientes),
            "insertados_o_actualizados": len(pendientes), "borrados": len(sobrantes)}


def buscar(coleccion, embedder, pregunta: str, k: int) -> list[dict]:
    """Devuelve los k fragmentos más parecidos con su similitud coseno (1 - distancia)."""
    vector = embedder.embed_consulta(pregunta)
    r = coleccion.query(query_embeddings=[vector.tolist()], n_results=k,
                        include=["documents", "metadatas", "distances"])
    return [{"id": i, "texto": t, "metadatos": m, "similitud": 1 - d}
            for i, t, m, d in zip(r["ids"][0], r["documents"][0], r["metadatas"][0], r["distances"][0])]
