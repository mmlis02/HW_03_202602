"""Prueba las garantías del índice sobre una colección TEMPORAL (se borra al final).

1. Idempotente: indexar dos veces no duplica.
2. Reanudable: se simula un corte a mitad de camino y la segunda corrida solo completa lo que falta.
3. Aislado: agregar un documento nuevo no borra ni reescribe los fragmentos de otro.

Uso: python scripts/probar_indice.py   (resultado también en logs/prueba_indice.log)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import chromadb  # noqa: E402

from src.config import BASE, cargar_config, ruta  # noqa: E402
from src.embeddings import crear_embedder  # noqa: E402
from src.fragmentos import fragmentar_documento  # noqa: E402
from src.indice import indexar_documento  # noqa: E402


def main():
    cfg = cargar_config()
    conf = cfg["fragmentos"]["configuraciones"][cfg["fragmentos"]["elegida"]]
    nombres = cfg["fragmentos"]["nombres_cortos"]
    docs = {d["id"]: d for d in cfg["documentos"] if d["incluir"]}
    frags = {k: fragmentar_documento(d, ruta(cfg, "processed"), conf["tamano"], conf["solape"]) for k, d in docs.items()}
    emb = crear_embedder(cfg)
    cliente = chromadb.PersistentClient(path=str(BASE / cfg["indice"]["carpeta"]))
    nombre = "prueba_temporal"
    if nombre in [c.name for c in cliente.list_collections()]:
        cliente.delete_collection(nombre)
    col = cliente.create_collection(nombre, metadata={"hnsw:space": "cosine"})
    lineas = []

    def reg(msg):
        print(msg)
        lineas.append(msg)

    silencio = lambda *_: None  # noqa: E731
    try:
        # --- 2. Reanudable: corte simulado después de la mitad de la ley ---
        mitad = len(frags["ley32069"]) // 2
        indexar_documento(col, emb, frags["ley32069"][:mitad], "ley32069", nombres, 64, silencio)
        # Nota: indexar solo la mitad simula un corte; los IDs de la otra mitad aún no existen.
        reg(f"[reanudable] tras el 'corte': {col.count()} de {len(frags['ley32069'])} fragmentos de la ley")
        r = indexar_documento(col, emb, frags["ley32069"], "ley32069", nombres, 64, silencio)
        reg(f"[reanudable] segunda corrida: ya_estaban={r['ya_estaban']}, insertados={r['insertados_o_actualizados']}, "
            f"total={col.count()}")

        # --- 3. Aislado: se agrega un documento nuevo ---
        antes = col.get(where={"documento": "ley32069"}, include=["metadatas"])
        r = indexar_documento(col, emb, frags["dl1715"], "dl1715", nombres, 64, silencio)
        despues = col.get(where={"documento": "ley32069"}, include=["metadatas"])
        igual = sorted(antes["ids"]) == sorted(despues["ids"]) and \
            sorted(m["hash"] for m in antes["metadatas"]) == sorted(m["hash"] for m in despues["metadatas"])
        reg(f"[aislado] dl1715 agregado ({r['insertados_o_actualizados']} fragmentos); "
            f"fragmentos de la ley sin cambios: {igual} ({len(despues['ids'])} IDs)")

        # --- 1. Idempotente ---
        total = col.count()
        for k in ("ley32069", "dl1715"):
            indexar_documento(col, emb, frags[k], k, nombres, 64, silencio)
        reg(f"[idempotente] reindexar todo otra vez: total antes={total}, después={col.count()}")

        # --- IDs únicos entre documentos y estables entre corridas ---
        todos = [f["id"] for fs in frags.values() for f in fs]
        otra_vez = [f["id"] for k, d in docs.items()
                    for f in fragmentar_documento(d, ruta(cfg, "processed"), conf["tamano"], conf["solape"])]
        reg(f"[IDs] únicos: {len(todos) == len(set(todos))} ({len(todos)} IDs); "
            f"idénticos al volver a fragmentar: {todos == otra_vez}")
    finally:
        cliente.delete_collection(nombre)
    (ruta(cfg, "logs") / "prueba_indice.log").write_text("\n".join(lineas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
