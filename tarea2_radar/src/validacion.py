"""Validación y normalización (Fase 2). Ninguna fila se borra: cada problema se MARCA con una
columna, se corrige cuando es recuperable y se reporta en el reporte de calidad.

Columna clave: `incluir_en_analisis`. Solo es False para registros que son copia exacta de otro
proceso (mismo tender_id con distinto ocid); siguen en el archivo, con el motivo en `motivo_exclusion`.
"""
import re

import numpy as np
import pandas as pd

from src.territorio import Territorio, clave


def _espacios(s):
    return " ".join(str(s).split()) if isinstance(s, str) else s


def validar(df: pd.DataFrame, terr: Territorio, vcfg: dict) -> tuple[pd.DataFrame, dict]:
    d = df.copy()
    rep = {}
    total = len(d)
    fallidos = tuple(vcfg["estados_fallidos"])
    d["fecha_publicacion_dt"] = pd.to_datetime(d["fecha_publicacion"], utc=True, errors="coerce")
    d["mes"] = d["segmentacion"].fillna(d["mes_archivo"])
    d["categoria_es"] = d["categoria"].map(vcfg["categorias"]).fillna("Sin categoría")
    d["incluir_en_analisis"] = True
    d["motivo_exclusion"] = ""
    d["advertencias"] = [[] for _ in range(total)]

    def advertir(mascara, texto):
        for i in d.index[mascara]:
            d.at[i, "advertencias"].append(texto)

    # ---------------- R1: registros repetidos ----------------------------------------------
    rep["R1a_ocid_repetido"] = {"casos": int(d["ocid"].duplicated().sum()),
                                "accion": "ninguna (la deduplicación por ocid se hizo en la Fase 1)"}

    # R1b: mismo tender_id con distinto ocid = el mismo proceso registrado dos veces
    dup_t = d[d["tender_id"].notna() & d["tender_id"].duplicated(keep=False)]
    principal = (dup_t.sort_values(["fecha_compilado", "n_releases"], ascending=False)
                      .drop_duplicates("tender_id").index)
    copias = dup_t.index.difference(principal)
    d.loc[copias, "incluir_en_analisis"] = False
    d.loc[copias, "motivo_exclusion"] = "mismo tender_id que otro ocid (registro duplicado); se conserva el de compiledRelease más reciente"
    rep["R1b_tender_id_repetido"] = {"casos": int(len(dup_t)), "grupos": int(dup_t["tender_id"].nunique()),
                                     "accion": f"se conserva 1 por tender_id; {len(copias)} marcados incluir_en_analisis=False (no se borran)",
                                     "ocid_excluidos": d.loc[copias, "ocid"].tolist()}

    # R1c: misma nomenclatura + misma entidad, distinto ocid -> posible reconvocatoria / re-registro
    d["grupo_repeticion"] = ""
    d["tipo_repeticion"] = ""
    d["es_version_vigente"] = True
    grupos = d[d.duplicated(["comprador_id", "nomenclatura"], keep=False) & d["nomenclatura"].notna()]
    tipos = {}
    for (cid, nom), x in grupos.groupby(["comprador_id", "nomenclatura"]):
        x = x.sort_values(["fecha_publicacion_dt", "fecha_compilado"])
        previos = x.iloc[:-1]
        previo_fallido = previos["estados_items"].fillna("").apply(lambda s: any(f in s for f in fallidos)).any()
        misma_fecha = x["fecha_publicacion_dt"].dt.date.nunique() == 1
        desc_distintas = x["descripcion"].nunique() == len(x)
        if previo_fallido:
            tipo = "A_reconvocatoria_confirmada"
        elif misma_fecha and desc_distintas:
            tipo = "B_items_distintos_misma_nomenclatura"
        elif misma_fecha:
            tipo = "C_reregistro_mismo_dia"
        else:
            tipo = "D_indeterminado"
        tipos[tipo] = tipos.get(tipo, 0) + 1
        d.loc[x.index, "grupo_repeticion"] = f"{cid}|{nom}"
        d.loc[x.index, "tipo_repeticion"] = tipo
        if tipo != "B_items_distintos_misma_nomenclatura":  # en B son compras distintas: todas vigentes
            d.loc[x.index[:-1], "es_version_vigente"] = False
    advertir(d["tipo_repeticion"] != "", "posible reconvocatoria o re-registro (misma nomenclatura y entidad)")
    # Re-registro del mismo día = el MISMO proceso contado dos veces. En CUALQUIER grupo (no solo tipo C:
    # p. ej. una reconvocatoria registrada 3 veces el mismo día), los registros con la misma fecha de
    # publicación y la misma descripción que otro se consideran copias: se conserva el de compiledRelease
    # más reciente y las copias se excluyen de conteos, montos e indicador de riesgo (igual que R1b).
    en_grupo = d[(d["grupo_repeticion"] != "") & d["incluir_en_analisis"]].copy()
    en_grupo["_dia"] = en_grupo["fecha_publicacion_dt"].dt.date
    orden = en_grupo.sort_values(["fecha_compilado", "n_releases"], ascending=False)
    copia_c = pd.Series(False, index=d.index)
    copia_c[orden[orden.duplicated(["grupo_repeticion", "_dia", "descripcion"], keep="first")].index] = True
    d.loc[copia_c, "incluir_en_analisis"] = False
    d.loc[copia_c, "motivo_exclusion"] = "re-registro del mismo día (misma nomenclatura, entidad, fecha y descripción); se conserva uno"
    copias_por_tipo = d.loc[copia_c, "tipo_repeticion"].value_counts().to_dict()
    rep["R1c_misma_nomenclatura_y_entidad"] = {
        "casos": int(len(grupos)), "grupos": int(grupos.groupby(["comprador_id", "nomenclatura"]).ngroups),
        "grupos_por_tipo": tipos,
        "versiones_anteriores": int((~d["es_version_vigente"]).sum()),
        "copias_C_excluidas_del_analisis": int(copia_c.sum()),
        "copias_excluidas_por_tipo_de_grupo": copias_por_tipo,
        "accion": "se CONSERVAN todas con advertencia (tipo_repeticion, es_version_vigente); las copias del mismo día (misma fecha y descripción, en cualquier grupo) se excluyen del análisis"}

    # ---------------- R2: monto faltante o cero ----------------------------------------------
    # amount_PEN de OECE solo si es > 0 (en algunos procesos en soles OECE publica amount_PEN = 0 con monto > 0)
    usa_oece = d["monto_pen_oece"].fillna(0) > 0
    en_soles = d["moneda"].fillna("PEN") == "PEN"
    d["monto_pen"] = np.where(usa_oece, d["monto_pen_oece"], np.where(en_soles, d["monto"], np.nan))
    pen_oece_cero = (~usa_oece) & en_soles & (d["monto"].fillna(0) > 0)
    d["monto_fuente"] = np.where(d["monto_pen"].fillna(0) > 0, "convocatoria", "")
    sin_monto = d["monto_pen"].isna() | (d["monto_pen"] == 0)
    recuperable = sin_monto & (d["monto_adjudicado"].fillna(0) > 0) & (d["moneda"].fillna("PEN") == "PEN")
    d.loc[recuperable, "monto_pen"] = d.loc[recuperable, "monto_adjudicado"]
    d.loc[recuperable, "monto_fuente"] = "adjudicado"
    d["monto_valido"] = d["monto_pen"].fillna(0) > 0
    advertir(~d["monto_valido"], "monto nulo o cero (se excluye de las sumas de monto; sí cuenta como proceso)")
    rep["R2_monto_nulo_o_cero"] = {
        "casos": int(sin_monto.sum()), "nulos": int(d["monto"].isna().sum()), "ceros": int((d["monto"] == 0).sum()),
        "moneda_extranjera_sin_conversion": int((sin_monto & (d["monto"].fillna(0) > 0)).sum()),
        "recuperados_con_monto_adjudicado": int(recuperable.sum()),
        "tasa_recuperacion": round(recuperable.sum() / max(1, sin_monto.sum()), 4),
        "sin_recuperar": int((~d["monto_valido"]).sum()),
        "estados_mas_comunes_sin_recuperar": d.loc[~d["monto_valido"], "estados_items"].value_counts().head(3).to_dict(),
        "accion": "corregido con el monto adjudicado cuando existe; el resto se conserva con advertencia (monto_valido=False)"}

    # R2b: moneda extranjera
    extranjera = d["moneda"].notna() & (d["moneda"] != "PEN")
    rep["R2c_amount_PEN_cero_con_monto_en_soles"] = {"casos": int(pen_oece_cero.sum()),
                                                      "accion": "se usa el monto en soles de la convocatoria (amount_PEN = 0 es un error de publicación)"}
    rep["R2b_moneda_extranjera"] = {"casos": int(extranjera.sum()),
                                    "por_moneda": d.loc[extranjera, "moneda"].value_counts().to_dict(),
                                    "convertidos_con_amount_PEN_de_OECE": int((extranjera & (d["monto_pen_oece"].fillna(0) > 0)).sum()),
                                    "sin_conversion_amount_PEN_cero": int((extranjera & (d["monto_pen_oece"].fillna(0) <= 0)).sum()),
                                    "accion": "monto_pen = amount_PEN publicado por OECE (conversión oficial)"}

    # ---------------- R3: sin descripción --------------------------------------------------
    # Algunas descripciones traen "\\n" escrito como texto (dos caracteres) en vez de un salto de línea
    barra_n = d["descripcion"].fillna("").str.contains("\\n", regex=False)
    d["descripcion_limpia"] = d["descripcion"].fillna("").str.replace("\\n", " ", regex=False).map(_espacios)
    vacia = d["descripcion_limpia"].fillna("").str.strip() == ""
    rec_desc = vacia & (d["items_descripcion"].fillna("").str.strip() != "")
    d.loc[rec_desc, "descripcion_limpia"] = d.loc[rec_desc, "items_descripcion"]
    corta = ~vacia & (d["descripcion_limpia"].str.len() < vcfg["longitud_minima_descripcion"])
    advertir(vacia & ~rec_desc, "sin descripción (no se indexa para la búsqueda semántica)")
    advertir(corta, "descripción muy corta")
    rep["R3_sin_descripcion"] = {"casos": int(vacia.sum()), "recuperados_con_items": int(rec_desc.sum()),
                                 "descripcion_muy_corta": int(corta.sum()),
                                 "ejemplos_cortas": d.loc[corta, "descripcion_limpia"].head(5).tolist(),
                                 "accion": "se recupera con la descripción de los ítems si existe; las muy cortas se conservan con advertencia"}

    # ---------------- R4: codificación y tildes ------------------------------------------
    # Comillas perdidas: OECE publica "¿" en lugar de las comillas tipográficas “ ” (p. ej.
    # 'OBRA: ¿MEJORAMIENTO ... CUSCO¿'). Si el texto no tiene "?", los "¿" no abren una pregunta: se
    # reemplazan por comillas. "Â" es un espacio mal codificado (UTF-8 leído como Latin-1): se quita.
    txt = d["descripcion_limpia"].fillna("")
    comillas = txt.str.contains("¿", regex=False) & ~txt.str.contains("?", regex=False)
    pregunta_real = txt.str.contains("¿", regex=False) & txt.str.contains("?", regex=False)
    mojibake = txt.str.contains("Ã|Â|�", regex=True)
    d.loc[comillas, "descripcion_limpia"] = d.loc[comillas, "descripcion_limpia"].str.replace("¿", '"', regex=False)
    d.loc[mojibake, "descripcion_limpia"] = d.loc[mojibake, "descripcion_limpia"].str.replace("Â", "", regex=False).map(_espacios)
    danado = comillas | mojibake
    espacios_nombre = d["comprador_nombre"].fillna("").str.contains(r"\s{2,}|^\s|\s$", regex=True)
    d["comprador_nombre_limpio"] = d["comprador_nombre"].map(_espacios)
    variantes = {}
    for col in ("comprador_departamento_raw", "comprador_region_raw", "comprador_nombre_limpio"):
        g = d.groupby(d[col].map(clave))[col].nunique()
        variantes[col] = int((g > 1).sum())
    con_tilde_region = sorted({v for v in d["comprador_region_raw"].dropna().unique() if clave(v) != v})
    rep["R4_codificacion_y_tildes"] = {
        "descripciones_con_comillas_perdidas_como_signo_de_pregunta": int(comillas.sum()),
        "descripciones_con_signo_de_pregunta_real_no_tocadas": int(pregunta_real.sum()),
        "descripciones_con_mojibake": int(mojibake.sum()),
        "descripciones_con_barra_n_literal": int(barra_n.sum()),
        "ejemplo_comillas": (lambda i: [d.at[i, "descripcion"][:90], d.at[i, "descripcion_limpia"][:90]])(
            d.loc[comillas, "descripcion"].str.find("¿").where(lambda x: x >= 0).idxmin()) if comillas.any() else [],
        "nombres_de_entidad_con_espacios_dobles": int(espacios_nombre.sum()),
        "valores_que_solo_difieren_en_tildes_mayusculas_o_espacios": variantes,
        "provincias_con_tilde_o_enie": con_tilde_region,
        "accion": "comparaciones con clave sin tildes (JUNÍN = JUNIN); '¿' sin '?' -> comillas; se quita 'Â'; se normalizan espacios"}

    # ---------------- R5: ubicación de la entidad compradora -> 25 departamentos ---------------
    dep = d["comprador_departamento_raw"].map(terr.departamento_valido)
    prov = d["comprador_region_raw"].map(terr.provincia)
    dep_por_prov = prov.map(lambda t: t[0])
    alias_usado = prov.map(lambda t: t[1])
    dep_por_dist = d["comprador_localidad_raw"].map(terr.distrito)
    region_es_depto_solo = d["comprador_region_raw"].map(lambda v: clave(v) in terr.departamentos and clave(v) not in terr.prov_a_dep)

    d["departamento"] = dep
    d["departamento_fuente"] = np.where(dep.notna(), "department", "")
    for fuente, serie in (("provincia_ign", dep_por_prov), ("distrito_ign_unico", dep_por_dist)):
        faltan = d["departamento"].isna() & serie.notna()
        d.loc[faltan, "departamento"] = serie[faltan]
        d.loc[faltan, "departamento_fuente"] = fuente
    # misma entidad: si la entidad aparece ubicada en otros procesos, se usa ese departamento
    por_entidad = d.dropna(subset=["departamento"]).groupby("comprador_id")["departamento"].agg(lambda s: s.mode().iat[0])
    faltan = d["departamento"].isna() & d["comprador_id"].isin(por_entidad.index)
    d.loc[faltan, "departamento"] = d.loc[faltan, "comprador_id"].map(por_entidad)
    d.loc[faltan, "departamento_fuente"] = "misma_entidad"
    d["provincia"] = d["comprador_region_raw"].map(lambda v: terr.alias.get(clave(v), clave(v)) if clave(v) in terr.prov_a_dep or clave(v) in terr.alias else None)

    inconsist = dep.notna() & dep_por_prov.notna() & (dep != dep_por_prov)
    advertir(inconsist, "departamento declarado no coincide con la provincia según el IGN")
    advertir(d["departamento"].isna(), "sin departamento")
    no_depto = dep.isna()
    rep["R5_ubicacion_comprador"] = {
        "campo_usado": "parties[rol=buyer].address.department (dirección de la entidad compradora)",
        "department_no_es_departamento_valido": int(no_depto.sum()),
        "region_contiene_provincia_no_departamento": int(dep_por_prov.notna().sum()),
        "region_no_encontrada_en_IGN_ni_con_alias": int((d["comprador_region_raw"].notna() & dep_por_prov.isna() & ~region_es_depto_solo).sum()),
        "alias_de_provincia_aplicado": int(alias_usado.sum()),
        "department_vs_provincia_IGN_inconsistentes": int(inconsist.sum()),
        "ubicados_por_fuente": d["departamento_fuente"].replace("", "sin_ubicar").value_counts().to_dict(),
        "recuperados_por_respaldo": int((d["departamento_fuente"].isin(["provincia_ign", "distrito_ign_unico", "misma_entidad"])).sum()),
        "tasa_recuperacion_de_los_no_validos": round(((d["departamento_fuente"] != "department") & d["departamento"].notna()).sum() / max(1, no_depto.sum()), 4) if no_depto.sum() else None,
        "sin_ubicar": int(d["departamento"].isna().sum()),
        "tasa_ubicacion_final": round(d["departamento"].notna().mean(), 4),
        "departamentos_distintos": int(d["departamento"].nunique()),
        "accion": "department válido -> se usa; si no: provincia (IGN, con alias) -> distrito único (IGN) -> misma entidad en otros procesos"}

    # ---------------- R6: número de postores (insumo del indicador de riesgo) --------------------
    sin_postores = d["n_postores"].isna()
    rep["R6_numero_de_postores"] = {"casos_numberOfTenderers_faltante": int(sin_postores.sum()),
                                    "de_ellos_con_adjudicacion": int((sin_postores & (d["n_adjudicaciones"] > 0)).sum()),
                                    "accion": "se conserva; se trata en la Fase 5 (indicador de un solo postor)"}

    d["n_advertencias"] = d["advertencias"].map(len)
    d["advertencias"] = d["advertencias"].map(lambda a: " | ".join(a))
    rep["resumen"] = {"filas": total, "incluidas_en_analisis": int(d["incluir_en_analisis"].sum()),
                      "excluidas_con_motivo": int((~d["incluir_en_analisis"]).sum()),
                      "excluidas_por_motivo": d.loc[~d["incluir_en_analisis"], "motivo_exclusion"].str.split(";").str[0].value_counts().to_dict(),
                      "incluidas_con_monto_valido": int((d["incluir_en_analisis"] & d["monto_valido"]).sum()),
                      "incluidas_sin_monto": int((d["incluir_en_analisis"] & ~d["monto_valido"]).sum()),
                      "filas_con_alguna_advertencia": int((d["n_advertencias"] > 0).sum())}
    return d, rep
