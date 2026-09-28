"""Evaluación del motor del Radar CON IA (cuesta dinero), según las reglas fijadas en el README.

Una sola corrida diagnóstica: cada pregunta pasa por el motor completo (la IA extrae filtros y
redacta) SIN aplicar el umbral, para después simular cualquier umbral sin nuevas llamadas.

Reporta: acierto de filtros por campo; Recall@k con filtros correctos (hoja) vs filtros de la IA;
abstención por umbral (sin IA, filtros correctos) y final (con IA, filtros de la IA) por umbral;
preguntas sin resultados; validez de las citas por ocid; costo.
Uso: python eval/evaluar_motor.py --con-ia
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import BASE, cargar_config  # noqa: E402
from src.motor import CAMPOS, MotorRadar, validar_filtros  # noqa: E402
from src.territorio import clave  # noqa: E402


def campo_ok(campo, esperado, obtenido, tol) -> bool:
    if esperado is None and obtenido is None:
        return True
    if esperado is None or obtenido is None:
        return False
    if campo in ("monto_min", "monto_max"):
        return abs(float(obtenido) - float(esperado)) <= tol * float(esperado)
    if campo == "departamento":
        return clave(esperado) == clave(obtenido)
    return str(esperado) == str(obtenido)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--con-ia", action="store_true")
    ap.add_argument("--desde-csv", action="store_true",
                    help="SIN IA: reutiliza filtros y veredictos de la última corrida y recalcula la búsqueda y las métricas")
    args = ap.parse_args()
    if args.desde_csv:
        return recalcular_desde_csv()
    if not args.con_ia:
        print("Usa --con-ia (esta evaluación llama al LLM y cuesta dinero).")
        return
    cfg = cargar_config()
    ev = cfg["evaluacion"]
    res = BASE / ev["resultados"]
    defs = yaml.safe_load(open(BASE / ev["definiciones"], encoding="utf-8"))
    rel = json.loads((BASE / ev["relevantes"]).read_text(encoding="utf-8"))
    oro = {r["id"]: r for r in csv.DictReader(open(res / "recuperacion.csv", encoding="utf-8"))
           if r["modo"] == "con_filtros" or r["tipo"] == "fuera"}
    motor = MotorRadar(cfg)
    preguntas = [(t, q) for t in ("dentro", "sin_resultados", "fuera") for q in defs.get(t, [])]
    filas, costo = [], 0.0
    for tipo, q in preguntas:
        esperado = {k: (q.get("filtros") or {}).get(k) for k in CAMPOS}
        r = motor.responder(q["pregunta"], aplicar_umbral=False)
        costo += r.costo_usd
        validos, _ = validar_filtros(r.filtros_ia, motor.departamentos)
        obtenido = {k: validos.get(k) for k in CAMPOS}
        ok = {k: campo_ok(k, esperado[k], obtenido[k], ev["tolerancia_monto"]) for k in CAMPOS}
        relev = set(rel[q["id"]])
        tops = [p["ocid"] for p in r.procesos]
        fila = {"id": q["id"], "tipo": tipo, "estado_sin_umbral": r.estado, "error": r.error or "",
                "filtros_esperados": json.dumps({k: v for k, v in esperado.items() if v is not None}, ensure_ascii=False),
                "filtros_ia": json.dumps({k: v for k, v in obtenido.items() if v is not None}, ensure_ascii=False),
                **{f"ok_{k}": int(ok[k]) for k in CAMPOS}, "filtros_todos_ok": int(all(ok.values())),
                "consulta_semantica": r.consulta_semantica, "n_filtrados_ia": r.n_procesos_filtrados,
                "sim_top1_ia": r.similitud_max if r.similitud_max is not None else "",
                "sim_top1_oro": float(oro[q["id"]]["sim_top1"]) if q["id"] in oro else "",
                "llm_abstuvo": int(r.estado == "abstencion_ia"), "motivo": r.motivo_abstencion or "",
                "sin_resultados": int(r.sin_resultados),
                "ocids_citados": " ".join(r.ocids_citados), "ocids_invalidos": " ".join(r.ocids_invalidos),
                "cita_relevante": int(bool(set(r.ocids_citados) & relev)) if tipo == "dentro" and r.estado == "respondido" else "",
                "respuesta": (r.respuesta or "")[:400], "costo_usd": round(r.costo_usd, 6), "llamadas": r.llamadas_llm}
        for k in ev["k_valores"]:
            fila[f"hit@{k}_ia"] = int(bool(set(tops[:k]) & relev)) if tipo == "dentro" else ""
            fila[f"hit@{k}_oro"] = int(oro[q["id"]][f"hit@{k}"]) if tipo == "dentro" else ""
        filas.append(fila)
        print(f"{q['id']} {tipo:14s} estado={r.estado:18s} filtros_ok={fila['filtros_todos_ok']} sim_ia={fila['sim_top1_ia']} "
              f"citados={len(r.ocids_citados)} inval={len(r.ocids_invalidos)} error={bool(r.error)}")
    with open(res / "evaluacion_motor_con_ia.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    resumir(filas, costo, cfg)


def resumir(filas, costo, cfg):
    ev = cfg["evaluacion"]
    res = BASE / ev["resultados"]
    dentro = [f for f in filas if f["tipo"] == "dentro"]
    fuera = [f for f in filas if f["tipo"] == "fuera"]
    sinr = [f for f in filas if f["tipo"] == "sin_resultados"]
    todas_con_hoja = dentro + sinr + fuera
    resumen = {"preguntas": len(filas), "costo_total_usd": round(costo, 6),
               "llamadas_llm": sum(f["llamadas"] for f in filas), "errores_api": sum(1 for f in filas if f["error"]),
               "filtros_acierto_por_campo": {k: f"{sum(f[f'ok_{k}'] for f in todas_con_hoja)}/{len(todas_con_hoja)}" for k in CAMPOS},
               "filtros_todos_correctos": f"{sum(f['filtros_todos_ok'] for f in todas_con_hoja)}/{len(todas_con_hoja)}",
               "recall": {f"recall@{k}": {"filtros_correctos": round(sum(f[f'hit@{k}_oro'] for f in dentro) / len(dentro), 3),
                                          "filtros_ia": round(sum(f[f'hit@{k}_ia'] for f in dentro) / len(dentro), 3)}
                          for k in ev["k_valores"]},
               "sin_resultados_correctos": f"{sum(f['sin_resultados'] for f in sinr)}/{len(sinr)}",
               "fuera_que_terminan_en_sin_resultados": [f["id"] for f in fuera if f["sin_resultados"]],
               "dentro_que_terminan_en_sin_resultados": [f["id"] for f in dentro if f["sin_resultados"]],
               "citas": {"respondidas_dentro": sum(1 for f in dentro if f["estado_sin_umbral"] == "respondido"),
                         "con_ocid_invalido": sum(1 for f in filas if f["ocids_invalidos"]),
                         "citan_proceso_relevante": f"{sum(1 for f in dentro if f['cita_relevante'] == 1)}/"
                                                    f"{sum(1 for f in dentro if f['cita_relevante'] != '')}"},
               "opciones_umbral": []}
    for u in ev["opciones_umbral"]:
        def abst_final(f):
            if f["sin_resultados"] or f["error"]:
                return False
            return (f["sim_top1_ia"] != "" and float(f["sim_top1_ia"]) < u) or bool(f["llm_abstuvo"])
        resumen["opciones_umbral"].append({
            "umbral": u,
            "umbral_sin_ia_correctas": f"{sum(1 for f in fuera if f['sim_top1_oro'] < u)}/{len(fuera)}",
            "umbral_sin_ia_incorrectas": f"{sum(1 for f in dentro if f['sim_top1_oro'] < u)}/{len(dentro)}",
            "final_con_ia_correctas": f"{sum(1 for f in fuera if abst_final(f))}/{len(fuera)}",
            "final_con_ia_incorrectas": f"{sum(1 for f in dentro if abst_final(f))}/{len(dentro)}",
            "dentro_perdidas": " ".join(f["id"] for f in dentro if abst_final(f)) or "ninguna",
            "fuera_respondidas": " ".join(f["id"] for f in fuera if not abst_final(f) and not f["sin_resultados"]) or "ninguna",
            "llamadas_de_redaccion": sum(1 for f in filas if not f["sin_resultados"] and f["sim_top1_ia"] != "" and float(f["sim_top1_ia"]) >= u)})
    (res / "evaluacion_motor_con_ia.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resumen, indent=1, ensure_ascii=False))


def recalcular_desde_csv():
    """Recalcula búsqueda y métricas con la hoja de respuestas ACTUAL, sin llamar a la IA:
    usa los filtros que extrajo la IA y sus veredictos (abstención / citas) de la última corrida."""
    from comun.embeddings import crear_embedder
    from src.indice import abrir, buscar
    cfg = cargar_config()
    ev = cfg["evaluacion"]
    res = BASE / ev["resultados"]
    rel = json.loads((BASE / ev["relevantes"]).read_text(encoding="utf-8"))
    oro = {r["id"]: r for r in csv.DictReader(open(res / "recuperacion.csv", encoding="utf-8"))
           if r["modo"] == "con_filtros" or r["tipo"] == "fuera"}
    emb, col = crear_embedder(cfg, base=BASE), abrir(cfg, crear=False)
    filas = list(csv.DictReader(open(res / "evaluacion_motor_con_ia.csv", encoding="utf-8")))
    K = max(ev["k_valores"])
    for f in filas:
        for c in [c for c in f if c.startswith(("ok_", "hit@", "filtros_todos", "llm_abstuvo", "sin_resultados", "llamadas"))]:
            f[c] = int(f[c]) if f[c] != "" else ""
        f["sim_top1_ia"] = float(f["sim_top1_ia"]) if f["sim_top1_ia"] != "" else ""
        f["sim_top1_oro"] = float(oro[f["id"]]["sim_top1"]) if f["id"] in oro else ""
        f["costo_usd"] = float(f["costo_usd"])
        relev = set(rel[f["id"]])
        if f["tipo"] == "dentro":
            tops = [r["ocid"] for r in buscar(col, emb, f["consulta_semantica"], K, json.loads(f["filtros_ia"]))]
            for k in ev["k_valores"]:
                f[f"hit@{k}_ia"] = int(bool(set(tops[:k]) & relev))
                f[f"hit@{k}_oro"] = int(oro[f["id"]][f"hit@{k}"])
            if f["estado_sin_umbral"] == "respondido":
                f["cita_relevante"] = int(bool(set(f["ocids_citados"].split()) & relev))
    with open(res / "evaluacion_motor_con_ia.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    resumir(filas, sum(f["costo_usd"] for f in filas), cfg)


if __name__ == "__main__":
    main()
