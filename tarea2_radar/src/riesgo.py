"""Indicador de riesgo: proporción de adjudicaciones con UN SOLO POSTOR (bandera R018, Open Contracting
Partnership, 2024: "Single bid received" = número de postores = 1 en un procedimiento competitivo).

Universo (denominador): procesos del análisis (incluir_en_analisis) ADJUDICADOS (con al menos una
adjudicación), de MÉTODO COMPETITIVO y CON dato de número de postores. Los que no tienen el dato
se excluyen del denominador y se reportan.

Una bandera roja es una razón para mirar con más atención, no evidencia de irregularidad.
"""
import math

import numpy as np
import pandas as pd


def universo(df: pd.DataFrame, metodos_competitivos: list[str]) -> tuple[pd.DataFrame, dict]:
    base = df[df["incluir_en_analisis"]]
    adj = base[base["n_adjudicaciones"] > 0]
    comp = adj[adj["metodo"].isin(metodos_competitivos)]
    con_dato = comp[comp["n_postores"].notna()].copy()
    con_dato["un_postor"] = con_dato["n_postores"] == 1
    conteo = {"procesos_analisis": len(base), "adjudicados": len(adj),
              "excluidos_no_competitivos": len(adj) - len(comp),
              "excluidos_por_metodo": adj.loc[~adj["metodo"].isin(metodos_competitivos), "metodo"].value_counts().to_dict(),
              "competitivos_adjudicados": len(comp), "sin_dato_postores": len(comp) - len(con_dato),
              "denominador": len(con_dato), "un_postor": int(con_dato["un_postor"].sum())}
    conteo["tasa_global"] = round(conteo["un_postor"] / conteo["denominador"], 4) if conteo["denominador"] else None
    return con_dato, conteo


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confianza de Wilson (95 %) para una proporción: muestra la incertidumbre con pocos procesos."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    c = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    return (max(0.0, centro - c), min(1.0, centro + c))


def por_grupo(u: pd.DataFrame, columna: str, nombre_col: str | None = None) -> pd.DataFrame:
    g = u.groupby(columna).agg(procesos=("ocid", "size"), un_postor=("un_postor", "sum"))
    if nombre_col:
        g["nombre"] = u.groupby(columna)[nombre_col].agg(lambda s: s.mode().iat[0])
        g["departamento"] = u.groupby(columna)["departamento"].agg(lambda s: s.mode().iat[0])
    g["tasa_un_postor"] = (g["un_postor"] / g["procesos"]).round(4)
    ic = [wilson(int(k), int(n)) for k, n in zip(g["un_postor"], g["procesos"])]
    g["ic95_inf"], g["ic95_sup"] = [round(a, 4) for a, _ in ic], [round(b, 4) for _, b in ic]
    return g.reset_index().sort_values(["tasa_un_postor", "un_postor", "procesos"], ascending=[False, False, False])


def distribucion_entidades(u: pd.DataFrame, minimos=(1, 5, 10, 15, 20, 30)) -> pd.DataFrame:
    g = u.groupby("comprador_id").agg(n=("ocid", "size"), uno=("un_postor", "sum"))
    filas = []
    for m in minimos:
        s = g[g["n"] >= m]
        filas.append({"minimo": m, "entidades": len(s), "pct_entidades": round(len(s) / len(g), 3),
                      "procesos_cubiertos": int(s["n"].sum()), "pct_procesos": round(s["n"].sum() / len(u), 3),
                      "peso_de_un_caso": round(1 / m, 3), "tasa_maxima": round((s["uno"] / s["n"]).max(), 3) if len(s) else None})
    percentiles = {p: int(np.percentile(g["n"], p)) for p in (25, 50, 75, 90, 95, 99)}
    return pd.DataFrame(filas), percentiles
