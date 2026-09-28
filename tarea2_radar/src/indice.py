"""Índice de descripciones de procesos en ChromaDB con los campos estructurados como METADATOS.

- Texto indexado: la descripción limpia del proceso (lo único que se compara por significado).
- Metadatos: ocid, departamento, monto, fecha, categoría, entidad, método, estados, n.º de postores.
  Las condiciones numéricas y territoriales se aplican como FILTROS sobre estos metadatos, nunca
  con embeddings (ver README, Fase 3).
- ID = ocid (único y estable). Idempotente: si la huella del texto+metadatos no cambió, se salta.
- Solo se indexan procesos con incluir_en_analisis=True y con descripción.
"""
import hashlib
import json

import chromadb
import pandas as pd

from src.config import BASE

SIN_DATO = -1  # ChromaDB no acepta None en metadatos numéricos


def _fecha_int(valor) -> int:
    f = pd.to_datetime(valor, utc=True, errors="coerce")
    return int(f.strftime("%Y%m%d")) if pd.notna(f) else SIN_DATO


def metadatos(fila) -> dict:
    return {
        "ocid": fila.ocid,
        "departamento": fila.departamento or "",
        "monto_pen": float(fila.monto_pen) if fila.monto_valido else float(SIN_DATO),
        "monto_valido": bool(fila.monto_valido),
        "fecha_int": _fecha_int(fila.fecha_publicacion),
        "mes": fila.mes or "",
        "categoria": fila.categoria_es or "",
        "comprador": fila.comprador_nombre_limpio or "",
        "comprador_id": fila.comprador_id or "",
        "metodo": fila.metodo or "",
        "estados": fila.estados_items or "",
        "n_postores": int(fila.n_postores) if pd.notna(fila.n_postores) else SIN_DATO,
    }


def abrir(cfg: dict, crear: bool = True):
    cliente = chromadb.PersistentClient(path=str(BASE / cfg["indice"]["carpeta"]))
    if crear:
        return cliente.get_or_create_collection(cfg["indice"]["coleccion"], metadata={"hnsw:space": "cosine"})
    return cliente.get_collection(cfg["indice"]["coleccion"])  # modo consulta: falla si no existe


def indexar(coleccion, embedder, df: pd.DataFrame, lote: int, log=print) -> dict:
    df = df[df["incluir_en_analisis"] & (df["descripcion_limpia"].fillna("").str.strip() != "")]
    registros = []
    for fila in df.itertuples():
        md = metadatos(fila)
        texto = fila.descripcion_limpia
        md["hash"] = hashlib.sha1((texto + json.dumps(md, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()[:16]
        registros.append((fila.ocid, texto, md))
    existentes = coleccion.get(include=["metadatas"])
    huella = {i: m.get("hash") for i, m in zip(existentes["ids"], existentes["metadatas"])}
    vigentes = {r[0] for r in registros}
    sobrantes = [i for i in huella if i not in vigentes]
    if sobrantes:
        coleccion.delete(ids=sobrantes)
    pendientes = [r for r in registros if huella.get(r[0]) != r[2]["hash"]]
    for i in range(0, len(pendientes), lote):
        b = pendientes[i:i + lote]
        vec = embedder.embed_pasajes([r[1] for r in b])
        coleccion.upsert(ids=[r[0] for r in b], documents=[r[1] for r in b],
                         metadatas=[r[2] for r in b], embeddings=[v.tolist() for v in vec])
        if (i // lote) % 10 == 0:
            log(f"   {min(i + lote, len(pendientes)):,}/{len(pendientes):,} procesos guardados")
    return {"a_indexar": len(registros), "ya_estaban": len(registros) - len(pendientes),
            "insertados_o_actualizados": len(pendientes), "borrados": len(sobrantes), "total": coleccion.count()}


def construir_filtro(f: dict) -> dict | None:
    """Filtros ESTRUCTURADOS -> cláusula `where` de ChromaDB (se aplican antes de comparar significados)."""
    c = []
    if f.get("departamento"):
        c.append({"departamento": {"$eq": f["departamento"]}})
    if f.get("categoria"):
        c.append({"categoria": {"$eq": f["categoria"]}})
    if f.get("monto_min") is not None:
        c.append({"monto_pen": {"$gte": float(f["monto_min"])}})
    if f.get("monto_max") is not None:
        c.append({"monto_pen": {"$lte": float(f["monto_max"])}})
        c.append({"monto_valido": {"$eq": True}})
    if f.get("fecha_desde"):
        c.append({"fecha_int": {"$gte": int(str(f["fecha_desde"]).replace("-", ""))}})
    if f.get("fecha_hasta"):
        c.append({"fecha_int": {"$lte": int(str(f["fecha_hasta"]).replace("-", ""))}})
    if not c:
        return None
    return c[0] if len(c) == 1 else {"$and": c}


def buscar(coleccion, embedder, consulta: str, k: int, filtros: dict | None = None) -> list[dict]:
    where = construir_filtro(filtros or {})
    vec = embedder.embed_consulta(consulta)
    r = coleccion.query(query_embeddings=[vec.tolist()], n_results=k, where=where,
                        include=["documents", "metadatas", "distances"])
    return [{"ocid": i, "descripcion": t, "metadatos": m, "similitud": round(1 - d, 4)}
            for i, t, m, d in zip(r["ids"][0], r["documents"][0], r["metadatas"][0], r["distances"][0])]
