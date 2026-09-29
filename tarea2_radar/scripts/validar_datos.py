"""Fase 2 (Tarea 2): validación, normalización territorial y reporte de calidad.

Entradas:  data/processed/procesos.parquet (Fase 1), novedades_api.parquet, límites del IGN
Salidas:
  data/processed/procesos_validados.parquet   corpus validado (una fila por ocid, con marcas)
  data/processed/novedades_validadas.parquet  septiembre (API), APARTE: no entra a los indicadores
  data/processed/reporte_calidad.md / .json   cada regla: casos, acción y resultado
  data/outputs/departamentos.geojson          mapa liviano (nombres = los de la normalización)

Uso (desde la carpeta tarea2_radar):  python scripts/validar_datos.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import BASE, archivo, cargar_config, ruta  # noqa: E402
from src.territorio import Territorio, geojson_departamentos  # noqa: E402
from src.validacion import validar  # noqa: E402


def main():
    cfg = cargar_config()
    proc = ruta(cfg, "processed")
    ign = BASE / cfg["ign"]["carpeta"]
    terr = Territorio(ign, cfg["validacion"]["alias_provincias"])

    df = pd.read_parquet(archivo(cfg, "procesos"))
    val, rep = validar(df, terr, cfg["validacion"])
    val.to_parquet(archivo(cfg, "procesos_validados"), index=False)

    # --- Ejemplos para verificar a mano las posibles reconvocatorias ---
    ejemplos = {}
    for tipo, x in val[val["tipo_repeticion"] != ""].groupby("tipo_repeticion"):
        filas = []
        for g in list(x["grupo_repeticion"].unique())[:3]:
            y = x[x["grupo_repeticion"] == g].sort_values("fecha_publicacion_dt")
            filas.append([{"ocid": r.ocid, "fecha": str(r.fecha_publicacion_dt)[:10], "estados": r.estados_items,
                           "monto": r.monto, "vigente": bool(r.es_version_vigente),
                           "descripcion": (r.descripcion_limpia or "")[:80]} for r in y.itertuples()])
        ejemplos[tipo] = filas
    rep["R1c_misma_nomenclatura_y_entidad"]["ejemplos"] = ejemplos

    # --- Novedades (API, septiembre): aparte; ubicación por la misma entidad del corpus ---
    nov_path = archivo(cfg, "novedades_api")
    if nov_path.exists():
        nov = pd.read_parquet(nov_path)
        por_entidad = val.dropna(subset=["departamento"]).groupby("comprador_id")["departamento"].agg(lambda s: s.mode().iat[0])
        nov["departamento"] = nov["comprador_id"].map(por_entidad)
        nov["departamento_fuente"] = nov["departamento"].notna().map({True: "misma_entidad", False: ""})
        nov["categoria_es"] = nov["categoria"].map(cfg["validacion"]["categorias"]).fillna("Sin categoría")
        nov["tipo_dato"] = "novedad reciente (API, mes en curso, no validada ni incluida en indicadores)"
        nov.to_parquet(archivo(cfg, "novedades_validadas"), index=False)
        rep["novedades_api"] = {"procesos": len(nov), "ubicados_por_misma_entidad": int(nov["departamento"].notna().sum()),
                                "tasa_recuperacion_departamento": round(nov["departamento"].notna().mean(), 4),
                                "sin_ubicar": int(nov["departamento"].isna().sum()),
                                "motivo_sin_ubicar": "la búsqueda de la API no trae la dirección y la entidad no aparece en junio-agosto",
                                "uso": "tabla aparte 'novedades recientes'; NO entra al corpus ni a los indicadores"}

    # --- GeoJSON del mapa ---
    m = cfg["mapa"]
    geo = geojson_departamentos(ign, m["tolerancia_simplificacion_grados"], m["decimales"], cfg["validacion"]["departamentos_mostrar"])
    salida_geo = BASE / m["geojson"]
    salida_geo.parent.mkdir(parents=True, exist_ok=True)
    salida_geo.write_text(json.dumps(geo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    nombres_mapa = {f["properties"]["departamento"] for f in geo["features"]}
    rep["mapa"] = {"geojson": m["geojson"], "bytes": salida_geo.stat().st_size, "departamentos": len(nombres_mapa),
                   "departamentos_de_los_datos_que_no_estan_en_el_mapa": sorted(set(val["departamento"].dropna()) - nombres_mapa)}

    rep["fecha"] = datetime.now().isoformat(timespec="seconds")
    (proc / "reporte_calidad.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (proc / "reporte_calidad.md").write_text(reporte_md(rep), encoding="utf-8")
    print(reporte_md(rep))


def reporte_md(r: dict) -> str:
    R = r
    L = ["# Reporte de calidad de datos (Tarea 2, Fase 2)", "",
         f"Corpus: {R['resumen']['filas']:,} procesos (jun–ago 2026). Ninguna fila se borra: se marcan, se corrigen si es posible o se excluyen del análisis con motivo.", "",
         "| Regla | Casos detectados | Qué se hizo | Resultado |", "|---|---|---|---|"]
    a, b, c = R["R1a_ocid_repetido"], R["R1b_tender_id_repetido"], R["R1c_misma_nomenclatura_y_entidad"]
    L.append(f"| R1a. Mismo ocid repetido | {a['casos']} | deduplicación por ocid en la Fase 1 | — |")
    L.append(f"| R1b. Mismo tender_id con distinto ocid (proceso registrado dos veces) | {b['casos']} filas ({b['grupos']} procesos) | se conserva el de compiledRelease más reciente; la copia queda con `incluir_en_analisis=False` | {len(b['ocid_excluidos'])} excluidos con motivo |")
    t = c["grupos_por_tipo"]
    L.append(f"| R1c. Misma nomenclatura y entidad, distinto ocid (posible reconvocatoria) | {c['casos']:,} filas en {c['grupos']:,} grupos | **se conservan** con advertencia; `tipo_repeticion` y `es_version_vigente`; **las copias del mismo día (misma fecha y descripción que otro registro del grupo) se excluyen del análisis**: {c['copias_C_excluidas_del_analisis']} copias ({', '.join(f'{k.split("_")[0]}: {v}' for k, v in c['copias_excluidas_por_tipo_de_grupo'].items())}) | A reconvocatoria confirmada: {t.get('A_reconvocatoria_confirmada', 0)} · C re-registro mismo día: {t.get('C_reregistro_mismo_dia', 0)} · B ítems distintos (no es repetición): {t.get('B_items_distintos_misma_nomenclatura', 0)} · D indeterminado: {t.get('D_indeterminado', 0)} grupos |")
    m, mb = R["R2_monto_nulo_o_cero"], R["R2b_moneda_extranjera"]
    L.append(f"| R2. Monto faltante o cero | {m['casos']:,} (monto nulo {m['nulos']}, monto 0: {m['ceros']:,}, moneda extranjera sin conversión a soles: {m['moneda_extranjera_sin_conversion']}) | se recupera con el monto adjudicado; el resto `monto_valido=False` (fuera de sumas de monto, dentro de conteos) | {m['recuperados_con_monto_adjudicado']} recuperados (tasa {m['tasa_recuperacion']:.1%}); {m['sin_recuperar']:,} con advertencia |")
    pc = R["R2c_amount_PEN_cero_con_monto_en_soles"]
    L.append(f"| R2c. amount_PEN = 0 con monto en soles > 0 | {pc['casos']} | se usa el monto en soles de la convocatoria | corregidos |")
    L.append(f"| R2b. Moneda extranjera | {mb['casos']} ({', '.join(f'{k} {v}' for k, v in mb['por_moneda'].items())}) | `monto_pen` = amount_PEN publicado por OECE | {mb['convertidos_con_amount_PEN_de_OECE']}/{mb['casos']} convertidos; {mb['sin_conversion_amount_PEN_cero']} con amount_PEN = 0 (cuentan en R2) |")
    s = R["R3_sin_descripcion"]
    L.append(f"| R3. Sin descripción | {s['casos']} | se recupera con la descripción de ítems si existe | {s['recuperados_con_items']} recuperados; {s['descripcion_muy_corta']} descripciones muy cortas con advertencia |")
    k = R["R4_codificacion_y_tildes"]
    var = k["valores_que_solo_difieren_en_tildes_mayusculas_o_espacios"]
    L.append(f"| R4. Codificación y tildes (JUNÍN vs JUNIN) | variantes por tildes/espacios: departamento {var['comprador_departamento_raw']}, provincia {var['comprador_region_raw']}, entidad {var['comprador_nombre_limpio']}; **{k['descripciones_con_comillas_perdidas_como_signo_de_pregunta']:,} descripciones con comillas “ ” perdidas y publicadas como '¿'**; {k['descripciones_con_mojibake']} con mojibake ('Â'); {k['descripciones_con_barra_n_literal']} con '\\n' escrito como texto; {k['nombres_de_entidad_con_espacios_dobles']:,} nombres con espacios dobles | comparación con clave sin tildes/mayúsculas; '¿' sin '?' → comillas ({k['descripciones_con_signo_de_pregunta_real_no_tocadas']} con pregunta real no se tocan); se quita 'Â' y el '\\n' literal; espacios normalizados | corregidos (ej.: `{k['ejemplo_comillas'][0]}` → `{k['ejemplo_comillas'][1]}`) |")
    u = R["R5_ubicacion_comprador"]
    L.append(f"| R5a. `department` no es un departamento válido | {u['department_no_es_departamento_valido']} | respaldo: provincia → distrito → misma entidad | — |")
    L.append(f"| R5b. Campo `region` con provincias (no departamentos) | {u['region_contiene_provincia_no_departamento']:,} | no se usa como departamento; se valida contra el IGN | inconsistencias department vs provincia: {u['department_vs_provincia_IGN_inconsistentes']} |")
    L.append(f"| R5c. Provincia escrita distinto que en el IGN | {u['alias_de_provincia_aplicado']} (NAZCA→NASCA) | alias documentado en config.yaml | corregidos |")
    L.append(f"| R5d. Sin departamento al final | {u['sin_ubicar']} | — | **tasa de ubicación {u['tasa_ubicacion_final']:.1%}** ({u['departamentos_distintos']} departamentos) |")
    p = R["R6_numero_de_postores"]
    L.append(f"| R6. Número de postores faltante | {p['casos_numberOfTenderers_faltante']:,} ({p['de_ellos_con_adjudicacion']:,} con adjudicación) | se conserva; se trata en la Fase 5 | — |")
    L += ["", f"**Ubicación por fuente:** {u['ubicados_por_fuente']}. Campo usado: {u['campo_usado']}."]
    if "novedades_api" in R:
        n = R["novedades_api"]
        L += ["", f"**Novedades recientes (API, septiembre 2026, aparte):** {n['procesos']:,} procesos; departamento recuperado por la misma entidad del corpus en {n['ubicados_por_misma_entidad']:,} (**tasa de recuperación {n['tasa_recuperacion_departamento']:.1%}**); {n['sin_ubicar']:,} sin ubicar ({n['motivo_sin_ubicar']}). {n['uso']}."]
    rs = R["resumen"]
    L += ["", "## Procesos que quedan para el análisis", "",
          "| | Procesos |", "|---|---|",
          f"| Procesos en el corpus (una fila por ocid) | {rs['filas']:,} |"]
    L += [f"| − Excluidos: {k} | {v:,} |" for k, v in rs["excluidas_por_motivo"].items()]
    L += [f"| **= Procesos para el análisis** (conteos e indicador de riesgo) | **{rs['incluidas_en_analisis']:,}** |",
          f"| de ellos con monto válido (entran a las sumas de monto) | {rs['incluidas_con_monto_valido']:,} |",
          f"| de ellos sin monto (cuentan como proceso, no suman monto) | {rs['incluidas_sin_monto']:,} |",
          "", f"{rs['filas_con_alguna_advertencia']:,} procesos tienen alguna advertencia (columna `advertencias`).",
          "", "## Verificación de posibles reconvocatorias (ejemplos)", ""]
    for tipo, grupos in c.get("ejemplos", {}).items():
        L.append(f"**{tipo}**")
        for g in grupos[:2]:
            L.append("")
            L.append("| ocid | fecha | estados | monto | vigente | descripción |")
            L.append("|---|---|---|---|---|---|")
            L += [f"| {e['ocid']} | {e['fecha']} | {e['estados']} | {e['monto']:,.2f} | {'sí' if e['vigente'] else 'no'} | {e['descripcion']} |" for e in g]
        L.append("")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
