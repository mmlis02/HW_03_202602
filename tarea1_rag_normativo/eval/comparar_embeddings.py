"""Fase 4: compara el modelo de embeddings local con text-embedding-3-small (OpenAI).

Ambos índices usan EXACTAMENTE los mismos fragmentos (configuración elegida) y el mismo texto
(encabezado + fragmento); solo cambia el modelo, elegido por config (`crear_embedder(cfg, clave)`).

Mide para cada modelo: Recall@1/3/5, MRR, tiempo de indexación, costo en USD, latencia media
por consulta, dimensión del vector y la distribución de similitudes (¿sirve el mismo umbral?).

El índice de OpenAI se construye UNA vez (cuesta dinero); si ya está completo, se reutilizan
las métricas de indexación guardadas y solo se repiten las consultas.

Uso: python eval/comparar_embeddings.py
"""
import csv
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import chromadb  # noqa: E402

from eval.evaluar_recuperacion import evaluar, mrr, recall  # noqa: E402
from src.config import BASE, cargar_config, ruta, umbral_activo  # noqa: E402
from src.costos import ahora_utc, calcular_costo  # noqa: E402
from src.embeddings import crear_embedder  # noqa: E402
from src.fragmentos import fragmentar_documento  # noqa: E402
from src.indice import abrir_coleccion, indexar_documento, nombre_coleccion, texto_para_embedding  # noqa: E402


def auc(dentro, fuera):
    return sum((a > b) + 0.5 * (a == b) for a in dentro for b in fuera) / (len(dentro) * len(fuera))


def indexar(cfg, emb, coleccion, frags_por_doc):
    inicio = time.time()
    for doc, frags in frags_por_doc.items():
        indexar_documento(coleccion, emb, frags, doc, cfg["fragmentos"]["nombres_cortos"],
                          cfg["indice"]["lote_insercion"], log=lambda *_: None)
    return time.time() - inicio


def main():
    cfg = cargar_config()
    conf = cfg["fragmentos"]["elegida"]
    c = cfg["fragmentos"]["configuraciones"][conf]
    docs = [d for d in cfg["documentos"] if d["incluir"]]
    frags = {d["id"]: fragmentar_documento(d, ruta(cfg, "processed"), c["tamano"], c["solape"]) for d in docs}
    n_frags = sum(len(v) for v in frags.values())
    preguntas = list(csv.DictReader(open(BASE / cfg["evaluacion"]["preguntas"], encoding="utf-8")))
    res = BASE / cfg["evaluacion"]["resultados"]
    salida_json = res / "comparacion_embeddings.json"
    previo = json.loads(salida_json.read_text(encoding="utf-8")) if salida_json.exists() else {}
    cliente = chromadb.PersistentClient(path=str(BASE / cfg["indice"]["carpeta"]))
    ks = cfg["evaluacion"]["k_valores"]
    resultado = {"configuracion_fragmentos": conf, "fragmentos": n_frags, "preguntas": len(preguntas), "modelos": {}}

    for clave in ("local", "openai"):
        emb = crear_embedder(cfg, clave)
        mcfg = cfg["embeddings"]["modelos"][clave]
        info = {"modelo": mcfg["nombre"], "dimension": emb.dimension}

        if clave == "local":
            # Tiempo de indexación medido en una colección temporal NUEVA (costo 0)
            tmp = "cmp_tmp_local"
            if tmp in [x.name for x in cliente.list_collections()]:
                cliente.delete_collection(tmp)
            col_tmp = cliente.create_collection(tmp, metadata={"hnsw:space": "cosine"})
            info["segundos_indexacion"] = round(indexar(cfg, emb, col_tmp, frags), 1)
            cliente.delete_collection(tmp)
            info["costo_indexacion_usd"] = 0.0
            info["tokens_indexacion"] = None
            col = abrir_coleccion(cfg, emb.alias, conf, crear=False)
        else:
            nombre = nombre_coleccion(cfg, emb.alias, conf)
            col = abrir_coleccion(cfg, emb.alias, conf)
            guardado = previo.get("modelos", {}).get("openai", {})
            if col.count() == n_frags and guardado.get("segundos_indexacion"):
                print(f"[openai] índice {nombre} ya completo: se reutilizan las métricas de indexación guardadas")
                for k in ("segundos_indexacion", "costo_indexacion_usd", "tokens_indexacion"):
                    info[k] = guardado[k]
            else:
                textos = [texto_para_embedding(f, cfg["fragmentos"]["nombres_cortos"]) for fs in frags.values() for f in fs]
                estimado = sum(emb.contar_tokens(t) for t in textos)
                costo_est, _ = calcular_costo(cfg, mcfg["nombre"], ahora_utc(), estimado, 0)
                print(f"[openai] indexando {n_frags} fragmentos ≈ {estimado} tokens ≈ US${costo_est:.4f}")
                cliente.delete_collection(nombre)  # construcción limpia para medir el tiempo completo
                col = abrir_coleccion(cfg, emb.alias, conf)
                antes_tokens, antes_costo = emb.tokens_usados, emb.costo_usd
                info["segundos_indexacion"] = round(indexar(cfg, emb, col, frags), 1)
                info["tokens_indexacion"] = emb.tokens_usados - antes_tokens
                info["costo_indexacion_usd"] = round(emb.costo_usd - antes_costo, 6)

        # Consultas de evaluación (para OpenAI, cada pregunta es una llamada a la API)
        antes_tokens = getattr(emb, "tokens_usados", 0)
        antes_costo = getattr(emb, "costo_usd", 0.0)
        filas = evaluar(col, emb, preguntas, max(ks))
        tokens_consultas = getattr(emb, "tokens_usados", 0) - antes_tokens
        with open(res / f"recuperacion_{emb.alias}_{conf}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
        dentro = [f["sim_top1"] for f in filas if f["tipo"] == "dentro"]
        fuera = [f["sim_top1"] for f in filas if f["tipo"] == "fuera"]
        lat = [f["latencia_s"] for f in filas]
        info.update({f"recall@{k}": round(recall(filas, k), 3) for k in ks})
        info.update({
            "mrr@5": round(mrr(filas), 3),
            "latencia_consulta_media_s": round(statistics.mean(lat), 4),
            "latencia_consulta_p90_s": round(statistics.quantiles(lat, n=10)[-1], 4),
            "tokens_consultas": tokens_consultas or None,
            "costo_consultas_usd": round(getattr(emb, "costo_usd", 0.0) - antes_costo, 6),
            "costo_por_consulta_usd": round((getattr(emb, "costo_usd", 0.0) - antes_costo) / len(preguntas), 8),
            "sim_top1_dentro": [round(min(dentro), 4), round(max(dentro), 4)],
            "sim_top1_fuera": [round(min(fuera), 4), round(max(fuera), 4)],
            "auc_dentro_fuera": round(auc(dentro, fuera), 3),
            "fuera_sobre_legitima_mas_baja": sorted(f["id"] for f in filas if f["tipo"] == "fuera" and f["sim_top1"] > min(dentro)),
            "abst_umbral_del_modelo": f"{sum(s < umbral_activo(cfg, clave) for s in fuera)}/{len(fuera)} fuera, "
                                  f"{sum(s < umbral_activo(cfg, clave) for s in dentro)}/{len(dentro)} dentro",
        })
        resultado["modelos"][clave] = info
        print(clave, json.dumps(info, ensure_ascii=False))

    salida_json.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Escrito {salida_json}")


if __name__ == "__main__":
    main()
