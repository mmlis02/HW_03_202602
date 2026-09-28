"""PROCESO OFFLINE: convierte el texto procesado en un índice vectorial.

Lee data/processed/*.jsonl (nunca los PDFs), arma los fragmentos, calcula los
embeddings y los guarda en ChromaDB (data/index/). Se corre una vez, o cuando
cambian los documentos. Es idempotente y reanudable (ver src/indice.py).

Uso (desde la carpeta tarea1_rag_normativo):
    python build_index.py                       # configuración elegida + modelo activo
    python build_index.py --fragmentos todas    # las tres configuraciones (comparación)
    python build_index.py --modelo openai       # índice API (Fase 4, cuesta dinero)
"""
import argparse
import json
import statistics
import time
from datetime import datetime

from src.config import cargar_config, ruta
from src.embeddings import crear_embedder
from src.fragmentos import fragmentar_documento
from src.indice import abrir_coleccion, indexar_documento, texto_para_embedding


def main():
    cfg = cargar_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--fragmentos", default=cfg["fragmentos"]["elegida"],
                    help="nombre de configuración de fragmentos o 'todas'")
    ap.add_argument("--modelo", default=cfg["embeddings"]["modelo_activo"])
    args = ap.parse_args()

    confs = cfg["fragmentos"]["configuraciones"]
    nombres = list(confs) if args.fragmentos == "todas" else [args.fragmentos]
    docs = [d for d in cfg["documentos"] if d["incluir"]]
    logs = ruta(cfg, "logs")
    logs.mkdir(exist_ok=True)
    archivo_log = open(logs / "build_index.log", "a", encoding="utf-8")

    def log(msg):
        linea = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
        print(linea)
        archivo_log.write(linea + "\n")

    embedder = crear_embedder(cfg, args.modelo)
    max_tokens = cfg["embeddings"]["modelos"][args.modelo]["max_tokens"]
    pref = cfg["embeddings"]["modelos"][args.modelo]["prefijo_pasaje"]
    resumen = {}
    for nombre in nombres:
        tam, sol = confs[nombre]["tamano"], confs[nombre]["solape"]
        log(f"== Índice {embedder.alias}/{nombre} (tamaño {tam}, solape {sol}) ==")
        coleccion = abrir_coleccion(cfg, embedder.alias, nombre)
        inicio = time.time()
        stats, todos = [], []
        for doc in docs:
            frags = fragmentar_documento(doc, ruta(cfg, "processed"), tam, sol)
            todos += frags
            stats.append(indexar_documento(coleccion, embedder, frags, doc["id"],
                                           cfg["fragmentos"]["nombres_cortos"], cfg["indice"]["lote_insercion"], log))
        segundos = time.time() - inicio
        for s in stats:
            log(f"   {s}")
        log(f"   total en la colección: {coleccion.count()} | tiempo: {segundos:.1f} s")

        # Distribución de longitudes (caracteres y tokens reales que ve el modelo)
        tokens = [embedder.contar_tokens(pref + texto_para_embedding(f, cfg["fragmentos"]["nombres_cortos"])) for f in todos]
        chars = [f["metadatos"]["chars"] for f in todos]
        por_doc = {d["id"]: sum(1 for f in todos if f["metadatos"]["documento"] == d["id"]) for d in docs}
        resumen[nombre] = {
            "tamano": tam, "solape": sol, "modelo": embedder.nombre, "fragmentos_por_documento": por_doc,
            "fragmentos_total": len(todos), "coleccion_count": coleccion.count(),
            "segundos_indexacion_esta_corrida": round(segundos, 1),
            "chars": {"min": min(chars), "mediana": int(statistics.median(chars)), "max": max(chars),
                      "p90": int(statistics.quantiles(chars, n=10)[-1])},
            "tokens": {"min": min(tokens), "mediana": int(statistics.median(tokens)), "max": max(tokens),
                       "p90": int(statistics.quantiles(tokens, n=10)[-1]),
                       "sobre_limite": sum(t > max_tokens for t in tokens), "limite": max_tokens},
            "chars_lista": chars, "tokens_lista": tokens,
        }

    salida = ruta(cfg, "processed") / f"fragmentos_{embedder.alias}.json"
    previo = json.loads(salida.read_text(encoding="utf-8")) if salida.exists() else {}
    previo.update(resumen)
    salida.write_text(json.dumps(previo, indent=1, ensure_ascii=False), encoding="utf-8")
    log(f"Resumen de fragmentos escrito en {salida}")


if __name__ == "__main__":
    main()
