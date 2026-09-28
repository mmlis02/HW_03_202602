"""Evaluación del motor completo, separando las dos defensas.

  python eval/evaluar_motor.py              -> DEFENSA 1 (umbral, SIN IA, costo 0)
  python eval/evaluar_motor.py --estimar    -> cuenta los tokens exactos de cada prompt y estima el costo
  python eval/evaluar_motor.py --con-ia     -> ABSTENCIÓN FINAL (con IA): llama al LLM, CUESTA DINERO
  python eval/evaluar_motor.py --con-ia --sin-umbral --etiqueta X
        -> diagnóstico: pasa TODAS las preguntas por el LLM (ignora el umbral) para poder simular
           cualquier umbral después con eval/opciones_umbral.py. CUESTA DINERO.

Métricas (regla fijada ANTES de la corrida con prompt v2; ver README, "Qué cuenta como acierto"):
- Solo cuenta el campo estructurado `abstuvo`; nunca se interpreta el texto de la respuesta.
- Abstención correcta = pregunta FUERA del corpus con abstuvo=True.
  Una respuesta PARCIAL (abstuvo=False, respuesta_parcial=True) a una pregunta fuera del corpus
  cuenta como FALLO aunque su explicacion_limite diga que el dato está en el Reglamento.
- Abstención incorrecta = pregunta DENTRO del corpus con abstuvo=True.
  Una respuesta parcial a una pregunta dentro del corpus cuenta como respondida.
- Con IA, además: en las preguntas dentro del corpus respondidas, si alguna página citada
  está entre las páginas esperadas (acierto de cita).
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from eval.evaluar_recuperacion import paginas_validas  # noqa: E402
from src.config import BASE, cargar_config, umbral_activo  # noqa: E402
from src.costos import ahora_utc, calcular_costo  # noqa: E402
from src.indice import buscar  # noqa: E402
from src.motor import Fuente, Motor  # noqa: E402


def resumen_abstencion(filas: list[dict], campo: str) -> dict:
    dentro = [f for f in filas if f["tipo"] == "dentro"]
    fuera = [f for f in filas if f["tipo"] == "fuera"]
    cor = sum(1 for f in fuera if f[campo])
    inc = sum(1 for f in dentro if f[campo])
    return {"abstenciones_correctas": f"{cor}/{len(fuera)}", "tasa_abstencion_correcta": round(cor / len(fuera), 3),
            "abstenciones_incorrectas": f"{inc}/{len(dentro)}", "tasa_abstencion_incorrecta": round(inc / len(dentro), 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--con-ia", action="store_true", help="llama al LLM (cuesta dinero)")
    ap.add_argument("--estimar", action="store_true", help="estima el costo sin llamar al LLM")
    ap.add_argument("--sin-umbral", action="store_true", help="con --con-ia: el LLM ve todas las preguntas")
    ap.add_argument("--etiqueta", default="", help="sufijo para los archivos de salida")
    args = ap.parse_args()
    cfg = cargar_config()
    salida = BASE / cfg["evaluacion"]["resultados"]
    preguntas = list(csv.DictReader(open(BASE / cfg["evaluacion"]["preguntas"], encoding="utf-8")))
    motor = Motor(cfg)
    umbral = umbral_activo(cfg)

    # ---------------- DEFENSA 1: umbral (sin IA) ----------------
    filas = []
    for p in preguntas:
        top = buscar(motor.coleccion, motor.embedder, p["pregunta"], cfg["motor"]["k_contexto"])
        filas.append({"id": p["id"], "tipo": p["tipo"], "pregunta": p["pregunta"], "sim_top1": round(top[0]["similitud"], 4),
                      "abst_umbral": top[0]["similitud"] < umbral, "_top": top, "_p": p})
    r1 = resumen_abstencion(filas, "abst_umbral")
    print(f"DEFENSA 1 — umbral {umbral} (sin IA, costo 0): {r1}")
    resultado = {"umbral": umbral, "defensa1_sin_ia": r1}

    pasan = filas if args.sin_umbral else [f for f in filas if not f["abst_umbral"]]
    if args.estimar:
        import tiktoken
        enc = tiktoken.get_encoding("o200k_base")
        salida_supuesta = cfg["llm"]["max_tokens_salida"]  # peor caso: el modelo usa todo el máximo
        total_in = 0
        for f in pasan:
            fuentes = [Fuente(t["metadatos"]["documento"], t["metadatos"]["titulo"], t["metadatos"]["pagina"],
                              t["similitud"], t["metadatos"].get("articulo", ""), "", t["texto"]) for t in f["_top"]]
            prompt = cfg["prompts"]["sistema"] + cfg["prompts"]["usuario"].format(
                pregunta=f["pregunta"], fragmentos=motor._formatear_fragmentos(fuentes))
            total_in += len(enc.encode(prompt)) + 30  # + formato de mensajes y esquema
        costo_max, franja = calcular_costo(cfg, cfg["llm"]["modelo"], ahora_utc(), total_in, salida_supuesta * len(pasan))
        costo_tipico, _ = calcular_costo(cfg, cfg["llm"]["modelo"], ahora_utc(), total_in, 250 * len(pasan))
        print(f"ESTIMACIÓN con IA: {len(pasan)} llamadas | tokens de entrada totales ≈ {total_in} "
              f"(≈ {total_in // max(1, len(pasan))} por pregunta)")
        print(f"   costo típico (250 tokens de salida c/u) ≈ US${costo_tipico:.4f} | "
              f"peor caso ({salida_supuesta} tokens de salida c/u) ≈ US${costo_max:.4f} | franja {franja}")
        return

    if args.con_ia:
        costo_total = 0.0
        for f in filas:
            r = motor.responder(f["pregunta"], aplicar_umbral=not args.sin_umbral)
            costo_total += r.costo_usd
            citadas = {(x.documento, x.pagina) for x in r.fuentes if x.citada}
            validas = paginas_validas(f["_p"]["paginas_esperadas"])
            f.update(parcial=r.respuesta_parcial, abst_llm=(r.motivo_abstencion in ("fuera_de_corpus", "sin_citas")), abst_final=r.abstuvo, motivo=r.motivo_abstencion or "", error=r.error or "",
                     cita_correcta=(bool(citadas & validas) if (f["tipo"] == "dentro" and not r.abstuvo and not r.error) else ""),
                     respuesta=r.respuesta or "", explicacion_limite=r.explicacion_limite,
                     notas_version=" | ".join(r.notas_version), citas=" ".join(f"{d}:p{pg}" for d, pg in sorted(citadas)),
                     tokens_entrada=r.tokens_entrada, tokens_salida=r.tokens_salida, costo_usd=round(r.costo_usd, 6))
            print(f"  {f['id']} ({f['tipo']}): abstuvo={r.abstuvo} motivo={r.motivo_abstencion} citas={f['citas']} error={bool(r.error)}")
        r2 = resumen_abstencion([f for f in filas if not f.get("error")], "abst_final")
        dentro_resp = [f for f in filas if f["tipo"] == "dentro" and f["cita_correcta"] != ""]
        r2["acierto_de_cita"] = f"{sum(1 for f in dentro_resp if f['cita_correcta'])}/{len(dentro_resp)}"
        r2["errores_api"] = sum(1 for f in filas if f.get("error"))
        r2["costo_total_usd"] = round(costo_total, 6)
        r2["abstenciones_por_motivo"] = {m: sum(1 for f in filas if f.get("motivo") == m) for m in ("umbral", "fuera_de_corpus", "sin_citas")}
        print(f"ABSTENCIÓN FINAL (con IA): {r2}")
        resultado["final_con_ia"] = r2

    campos = [k for k in filas[0] if not k.startswith("_")]
    nombre = ("evaluacion_motor_con_ia" if args.con_ia else "evaluacion_motor_sin_ia") + \
        ("_sin_umbral" if args.sin_umbral else "") + (f"_{args.etiqueta}" if args.etiqueta else "")
    with open(salida / f"{nombre}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    (salida / f"{nombre}.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
