"""Tablero Streamlit de la Tarea 2 (SOLO interfaz).

- Lee archivos precalculados (parquet, GeoJSON, reportes). Nunca descarga datos ni construye el índice.
- Los filtros de la barra lateral actúan sobre la tabla con pandas, SIN llamar a la IA.
- La caja de preguntas llama a `src.motor.responder` (RAG híbrido) y muestra los filtros que extrajo la IA.
- Todos los textos, rutas y parámetros de la interfaz vienen de config.yaml (sección `app`).

Ejecutar (desde la carpeta tarea2_radar):   streamlit run app.py
"""
import json

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import BASE, archivo, cargar_config
from src.riesgo import por_grupo, universo

cfg = cargar_config()
A, R = cfg["app"], cfg["riesgo"]
T, B = A["textos"], A["barra"]
MOSTRAR = cfg["validacion"]["departamentos_mostrar"]
st.set_page_config(page_title=A["titulo"], page_icon=T["icono"], layout="wide")


# ------------------------------------------------------------------ datos (cacheados)
@st.cache_data
def cargar_procesos() -> pd.DataFrame:
    d = pd.read_parquet(archivo(cfg, "procesos_validados"))
    d = d[d["incluir_en_analisis"]].copy()   # sin copias del mismo día ni duplicados por tender_id
    d["fecha"] = d["fecha_publicacion_dt"].dt.tz_convert(A["zona_horaria"]).dt.date
    d["departamento_mostrar"] = d["departamento"].map(MOSTRAR)
    return d


@st.cache_data
def cargar_novedades() -> pd.DataFrame | None:
    ruta = archivo(cfg, "novedades_validadas")
    return pd.read_parquet(ruta) if ruta.exists() else None


@st.cache_data
def cargar_json(clave: str):
    ruta = BASE / A["rutas"][clave]
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


@st.cache_data
def cargar_texto(clave: str) -> str | None:
    ruta = BASE / A["rutas"][clave]
    return ruta.read_text(encoding="utf-8") if ruta.exists() else None


@st.cache_resource(show_spinner=T["cargando_motor"])
def obtener_responder():
    from src.motor import responder
    return responder


def soles(x: float) -> str:
    return T["moneda"].format(x=x)


def monto_valido_sum(df: pd.DataFrame) -> float:
    return df.loc[df["monto_valido"], "monto_pen"].sum()


d = cargar_procesos()

# ------------------------------------------------------------------ barra lateral (sin IA)
st.sidebar.header(T["barra_titulo"])
st.sidebar.caption(T["barra_ayuda"])
deps = st.sidebar.multiselect(T["f_departamento"], sorted(MOSTRAR), format_func=lambda k: MOSTRAR[k])
cats = st.sidebar.multiselect(T["f_categoria"], T["categorias"])
c1, c2 = st.sidebar.columns(2)
monto_min = c1.number_input(T["f_monto_min"], min_value=0.0, value=0.0, step=B["monto_paso"], format="%.0f")
monto_max = c2.number_input(T["f_monto_max"], min_value=0.0, value=0.0, step=B["monto_paso"], format="%.0f",
                            help=T["f_monto_max_ayuda"])
fmin, fmax = d["fecha"].min(), d["fecha"].max()
rango = st.sidebar.date_input(T["f_fecha"], value=(fmin, fmax), min_value=fmin, max_value=fmax)
umbral_cfg = float(cfg["motor"]["umbral_similitud"])
umbral = st.sidebar.slider(T["f_umbral"], B["umbral_min"], B["umbral_max"], umbral_cfg, B["umbral_paso"],
                           help=T["f_umbral_ayuda"].format(umbral=umbral_cfg))

f = d
if deps:
    f = f[f["departamento"].isin(deps)]
if cats:
    f = f[f["categoria_es"].isin(cats)]
if monto_min > 0:
    f = f[f["monto_valido"] & (f["monto_pen"] >= monto_min)]
if monto_max > 0:
    f = f[f["monto_valido"] & (f["monto_pen"] <= monto_max)]
if isinstance(rango, tuple) and len(rango) == 2:
    f = f[(f["fecha"] >= rango[0]) & (f["fecha"] <= rango[1])]

filtros_barra = {}
if deps:
    filtros_barra["departamentos"] = deps
if cats:
    filtros_barra["categorias"] = cats
if monto_min > 0:
    filtros_barra["monto_min"] = monto_min
if monto_max > 0:
    filtros_barra["monto_max"] = monto_max
if isinstance(rango, tuple) and len(rango) == 2 and (rango[0] != fmin or rango[1] != fmax):
    filtros_barra["fecha_desde"], filtros_barra["fecha_hasta"] = rango[0].isoformat(), rango[1].isoformat()

# ------------------------------------------------------------------ encabezado de indicadores
st.title(A["titulo"])
st.caption(A["subtitulo"])
u, conteo = universo(f, R["metodos_competitivos"]) if len(f) else (pd.DataFrame(), {"denominador": 0, "un_postor": 0})
k1, k2, k3, k4 = st.columns(4)
k1.metric(T["k_procesos"], f"{len(f):,}")
k2.metric(T["k_monto"], soles(monto_valido_sum(f)))
k2.caption(A["nota_monto"].format(n=int((~f["monto_valido"]).sum())))
anteriores = f[f["monto_valido"] & ~f["es_version_vigente"]]
if len(anteriores):
    k2.caption(A["nota_reconvocatorias"].format(s=soles(anteriores["monto_pen"].sum()), n=len(anteriores),
                                                t=soles(monto_valido_sum(f[f["es_version_vigente"]]))))
k3.metric(T["k_departamentos"], f"{f['departamento'].nunique()}")
tasa = (conteo["un_postor"] / conteo["denominador"]) if conteo["denominador"] else None
k4.metric(T["k_riesgo"], f"{tasa:.1%}" if tasa is not None else T["sin_valor"], help=A["nota_riesgo_kpi"])
k4.caption(T["k_riesgo_nota"].format(uno=conteo["un_postor"], den=conteo["denominador"]))

tabs = st.tabs(A["pestanas"])
vacio = len(f) == 0

# ------------------------------------------------------------------ Mapa
with tabs[0]:
    if vacio:
        st.warning(A["sin_datos"])
    else:
        medida = st.radio(T["mapa_colorear"], T["mapa_opciones"], horizontal=True)
        g = (f.groupby("departamento").agg(procesos=("ocid", "size"),
                                           monto=("monto_pen", lambda s: s[f.loc[s.index, "monto_valido"]].sum()))
             .reindex(list(MOSTRAR), fill_value=0).reset_index())
        g["nombre"] = g["departamento"].map(MOSTRAR)
        col = "procesos" if medida == T["mapa_opciones"][0] else "monto"
        fig = px.choropleth(g, geojson=cargar_json("geojson"), locations="departamento",
                            featureidkey="properties.departamento", color=col, color_continuous_scale="Blues",
                            hover_name="nombre", hover_data={"departamento": False, "procesos": ":,", "monto": ":,.0f"},
                            labels=T["mapa_etiquetas"])
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(height=620, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, width="stretch")
        st.caption(T["mapa_fuente"])

# ------------------------------------------------------------------ Preguntar (RAG híbrido)
with tabs[1]:
    st.write(T["preguntar_intro"])
    cols = st.columns(len(A["ejemplos"]))
    for col, ej in zip(cols, A["ejemplos"]):
        if col.button(ej, width="stretch"):
            st.session_state["pregunta_radar"] = ej
    with st.form("form_radar"):
        pregunta = st.text_input(T["preguntar_label"], key="pregunta_radar")
        enviar = st.form_submit_button(T["preguntar_boton"], type="primary")
    if enviar and pregunta.strip():
        with st.spinner(T["preguntar_buscando"]):
            try:
                st.session_state["resultado_radar"] = obtener_responder()(pregunta, filtros_barra, umbral)
            except Exception as ex:  # índice ausente: la app no lo reconstruye
                st.error(T["preguntar_sin_indice"].format(error=type(ex).__name__))
    r = st.session_state.get("resultado_radar")
    if r:
        st.subheader(T["filtros_titulo"])
        C, CAMPOS = T["filtros_columnas"], T["filtros_campos"]
        filas = [{C["campo"]: CAMPOS[k],
                  C["ia"]: T["sin_valor"] if r["filtros_ia"].get(k) is None else r["filtros_ia"][k],
                  C["aplicado"]: r["filtros_aplicados"].get(k, T["sin_valor"])} for k in CAMPOS]
        if r["filtros_aplicados"].get("departamentos"):
            filas.append({C["campo"]: T["filtros_barra_dep"], C["ia"]: T["sin_valor"],
                          C["aplicado"]: ", ".join(r["filtros_aplicados"]["departamentos"])})
        if r["filtros_aplicados"].get("categorias"):
            filas.append({C["campo"]: T["filtros_barra_cat"], C["ia"]: T["sin_valor"],
                          C["aplicado"]: ", ".join(r["filtros_aplicados"]["categorias"])})
        st.dataframe(pd.DataFrame(filas).astype(str), hide_index=True)
        st.caption(T["tema_buscado"].format(tema=r["consulta_semantica"], n=r["n_procesos_filtrados"]))
        for a in r["avisos_filtros"]:
            st.warning(T["filtro_descartado"].format(aviso=a))

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(T["m_estado"], r["estado"] or T["sin_valor"])
        m2.metric(T["m_similitud"], f"{r['similitud_max']:.3f}" if r["similitud_max"] is not None else T["sin_valor"],
                  help=T["m_umbral"].format(umbral=r["umbral"]))
        m3.metric(T["m_costo"], f"US$ {r['costo_usd']:.6f}")
        m4.metric(T["m_llamadas"], r["llamadas_llm"])
        if r["error"]:
            st.error(r["error"])
        elif r["sin_resultados"]:
            st.info(T["sin_resultados_nota"].format(respuesta=r["respuesta"]))
        elif r["abstuvo"]:
            st.warning(T["abstencion"].format(motivo=r["motivo_abstencion"], respuesta=r["respuesta"]))
        else:
            # Caja neutra (no verde): la IA puede decir aquí que ningún proceso coincide exactamente
            # (limitación conocida: F03/F07), y el usuario debe poder leerlo como advertencia.
            st.info(T["respuesta_ia"].format(respuesta=r["respuesta"]))
            st.warning(A["explicacion_ia"])
            if r["ocids_invalidos"]:
                st.warning(T["ocids_eliminados"].format(n=len(r["ocids_invalidos"])))
        if r["procesos"]:
            st.subheader(T["procesos_titulo"])
            tp = pd.DataFrame(r["procesos"])
            tp["monto"] = tp.apply(lambda x: soles(x["monto_pen"]) if x["monto_valido"] else T["sin_monto"], axis=1)
            tp["departamento"] = tp["departamento"].map(MOSTRAR)
            st.dataframe(tp[["citado", "similitud", "ocid", "comprador", "departamento", "monto", "categoria", "estados", "descripcion"]],
                         hide_index=True, column_config={"citado": st.column_config.CheckboxColumn(T["col_citado"])})

# ------------------------------------------------------------------ Tabla
with tabs[2]:
    if vacio:
        st.warning(A["sin_datos"])
    else:
        t = f.sort_values("monto_pen", ascending=False)[
            ["ocid", "fecha", "departamento_mostrar", "comprador_nombre_limpio", "categoria_es", "metodo",
             "monto_pen", "monto_valido", "estados_items", "n_postores", "descripcion_limpia", "advertencias"]]
        t = t.rename(columns={"departamento_mostrar": "departamento", "comprador_nombre_limpio": "entidad",
                              "categoria_es": "categoria", "descripcion_limpia": "descripcion"})
        st.caption(T["tabla_nota"].format(n=len(t)))
        st.dataframe(t, hide_index=True, height=520)
        st.download_button(T["tabla_descargar"], t.to_csv(index=False).encode("utf-8"), T["tabla_archivo"], "text/csv")

# ------------------------------------------------------------------ Distribución (gráfico nativo de Streamlit)
with tabs[3]:
    if vacio:
        st.warning(A["sin_datos"])
    else:
        DIM = T["dist_dimensiones"]
        dim = st.selectbox(T["dist_agrupar"], list(DIM), format_func=DIM.get)
        met = st.radio(T["dist_medida"], T["dist_medidas"], horizontal=True)
        por_procesos = met == T["dist_medidas"][0]
        g = f.groupby(dim).agg(procesos=("ocid", "size"),
                               monto=("monto_pen", lambda s: s[f.loc[s.index, "monto_valido"]].sum()))
        serie = g["procesos" if por_procesos else "monto"].sort_values(ascending=False).rename(met)
        serie.index.name = DIM[dim]
        st.bar_chart(serie, horizontal=True, height=max(300, 24 * len(serie)))
        if not por_procesos:
            st.caption(A["nota_monto"].format(n=int((~f["monto_valido"]).sum())))

# ------------------------------------------------------------------ Riesgo
with tabs[4]:
    st.warning(R["aviso"])
    res = cargar_json("riesgo_resumen")
    st.markdown(T["riesgo_definicion"])
    RC = T["riesgo_columnas"]
    fmt = {"tasa_un_postor": st.column_config.NumberColumn(RC["tasa_un_postor"], format="percent"),
           "ic95_inf": st.column_config.NumberColumn(RC["ic95_inf"], format="percent"),
           "ic95_sup": st.column_config.NumberColumn(RC["ic95_sup"], format="percent")}
    if len(u) == 0:
        st.info(T["riesgo_sin_universo"])
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric(T["riesgo_tasa"], f"{conteo['un_postor'] / conteo['denominador']:.2%}")
        c2.metric(T["riesgo_denominador"], f"{conteo['denominador']:,}")
        c3.metric(T["riesgo_sin_dato"], f"{conteo['sin_dato_postores']:,}")
        st.caption(T["riesgo_excluidas"].format(n=conteo["excluidos_no_competitivos"], detalle=conteo["excluidos_por_metodo"]))
        st.subheader(T["riesgo_por_dep"])
        dep = por_grupo(u, "departamento")
        dep["departamento"] = dep["departamento"].map(MOSTRAR)
        st.dataframe(dep, hide_index=True, column_config=fmt)
        st.subheader(T["riesgo_top"].format(top=R["top_entidades"], minimo=R["min_procesos_entidad"]))
        ent = por_grupo(u, "comprador_id", "comprador_nombre_limpio")
        ent = ent[ent["procesos"] >= R["min_procesos_entidad"]].head(R["top_entidades"])
        if len(ent) == 0:
            st.info(T["riesgo_sin_entidades"].format(minimo=R["min_procesos_entidad"]))
        else:
            ent["departamento"] = ent["departamento"].map(MOSTRAR)
            st.dataframe(ent[["nombre", "departamento", "procesos", "un_postor", "tasa_un_postor", "ic95_inf", "ic95_sup"]],
                         hide_index=True, column_config={"nombre": RC["nombre"], "un_postor": RC["un_postor"], **fmt})
            st.caption(T["riesgo_ic_nota"])
    if res:
        with st.expander(T["riesgo_minimo_titulo"].format(minimo=R["min_procesos_entidad"])):
            st.write(T["riesgo_minimo_texto"].format(percentiles=res["percentiles_procesos_por_entidad"]))
            st.dataframe(pd.DataFrame(res["distribucion_minimos"]), hide_index=True)

# ------------------------------------------------------------------ Calidad de datos
with tabs[5]:
    cj = cargar_json("calidad_json")
    if cj:
        rs = cj["resumen"]
        a, b, c = st.columns(3)
        a.metric(T["calidad_corpus"], f"{rs['filas']:,}")
        b.metric(T["calidad_analisis"], f"{rs['incluidas_en_analisis']:,}")
        c.metric(T["calidad_advertencias"], f"{rs['filas_con_alguna_advertencia']:,}")
    texto = cargar_texto("reporte_calidad")
    if texto:
        st.markdown(texto.split("## Verificación")[0])

# ------------------------------------------------------------------ Novedades recientes
with tabs[6]:
    st.info(A["novedades_aviso"])
    nov = cargar_novedades()
    if nov is not None:
        n = nov if not deps else nov[nov["departamento"].isin(deps)]
        st.caption(T["novedades_conteo"].format(n=len(n), sin=int(n["departamento"].isna().sum())))
        st.dataframe(n[["ocid", "fecha_publicacion", "departamento", "comprador_nombre", "categoria_es", "monto", "moneda", "descripcion"]],
                     hide_index=True, height=480)

# ------------------------------------------------------------------ Costos
with tabs[7]:
    log = BASE / cfg["precios"]["log_llamadas"]
    st.write(T["costos_precios"].format(fuente=cfg["precios"]["fuente"], fecha=cfg["precios"]["fecha_verificacion"]))
    if log.exists():
        lg = pd.read_csv(log)
        lg["costo_usd"] = pd.to_numeric(lg["costo_usd"], errors="coerce").fillna(0)
        a, b = st.columns(2)
        a.metric(T["costos_llamadas"], len(lg))
        b.metric(T["costos_total"], f"US$ {lg['costo_usd'].sum():.4f}")
        st.dataframe(lg.tail(20), hide_index=True)
