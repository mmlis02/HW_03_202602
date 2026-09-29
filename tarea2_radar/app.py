"""Tablero Streamlit de la Tarea 2 (SOLO interfaz).

- Lee archivos precalculados (parquet, GeoJSON, reportes). Nunca descarga datos ni construye el índice.
- Los filtros de la barra lateral actúan sobre la tabla con pandas, SIN llamar a la IA.
- La caja de preguntas llama a `src.motor.responder` (RAG híbrido) y muestra los filtros que extrajo la IA.

Ejecutar (desde la carpeta tarea2_radar):   streamlit run app.py
"""
import json
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import BASE, cargar_config
from src.riesgo import por_grupo, universo

cfg = cargar_config()
A, R = cfg["app"], cfg["riesgo"]
MOSTRAR = cfg["validacion"]["departamentos_mostrar"]
st.set_page_config(page_title=A["titulo"], page_icon="🗺️", layout="wide")


# ------------------------------------------------------------------ datos (cacheados)
@st.cache_data
def cargar_procesos() -> pd.DataFrame:
    d = pd.read_parquet(BASE / A["rutas"]["procesos"])
    d = d[d["incluir_en_analisis"]].copy()   # sin copias de re-registros ni duplicados por tender_id
    d["fecha"] = d["fecha_publicacion_dt"].dt.tz_convert("America/Lima").dt.date
    d["departamento_mostrar"] = d["departamento"].map(MOSTRAR)
    return d


@st.cache_data
def cargar_novedades() -> pd.DataFrame | None:
    ruta = BASE / A["rutas"]["novedades"]
    return pd.read_parquet(ruta) if ruta.exists() else None


@st.cache_data
def cargar_json(clave: str):
    ruta = BASE / A["rutas"][clave]
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


@st.cache_data
def cargar_texto(clave: str) -> str | None:
    ruta = BASE / A["rutas"][clave]
    return ruta.read_text(encoding="utf-8") if ruta.exists() else None


@st.cache_resource(show_spinner="Cargando el buscador (modelo de embeddings e índice)...")
def obtener_responder():
    from src.motor import responder
    return responder


def soles(x: float) -> str:
    return f"S/ {x:,.0f}"


d = cargar_procesos()

# ------------------------------------------------------------------ barra lateral (sin IA)
st.sidebar.header("Filtros")
st.sidebar.caption("Filtran la tabla, el mapa y los indicadores sin llamar a la IA. También se aplican a la caja de preguntas.")
deps = st.sidebar.multiselect("Departamento", sorted(MOSTRAR), format_func=lambda k: MOSTRAR[k])
cats = st.sidebar.multiselect("Categoría", ["Bienes", "Servicios", "Obras"])
c1, c2 = st.sidebar.columns(2)
monto_min = c1.number_input("Monto mínimo (S/)", min_value=0.0, value=0.0, step=10000.0, format="%.0f")
monto_max = c2.number_input("Monto máximo (S/)", min_value=0.0, value=0.0, step=10000.0, format="%.0f",
                            help="0 = sin tope")
fmin, fmax = d["fecha"].min(), d["fecha"].max()
rango = st.sidebar.date_input("Fecha de publicación", value=(fmin, fmax), min_value=fmin, max_value=fmax)
umbral = st.sidebar.slider("Umbral de similitud (preguntas)", 0.70, 0.95, float(cfg["motor"]["umbral_similitud"]), 0.005,
                           help="Por debajo de este valor el buscador se abstiene sin llamar a la IA. Calibrado: 0,830.")

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
k1.metric("Procesos", f"{len(f):,}")
k2.metric("Monto total", soles(f.loc[f["monto_valido"], "monto_pen"].sum()))
k2.caption(A["nota_monto"].format(n=int((~f["monto_valido"]).sum())))
anteriores = f[f["monto_valido"] & ~f["es_version_vigente"]]
if len(anteriores):
    k2.caption(A["nota_reconvocatorias"].format(s=soles(anteriores["monto_pen"].sum()), n=len(anteriores),
                                                t=soles(f.loc[f["monto_valido"] & f["es_version_vigente"], "monto_pen"].sum())))
k3.metric("Departamentos", f"{f['departamento'].nunique()}")
tasa = (conteo["un_postor"] / conteo["denominador"]) if conteo["denominador"] else None
k4.metric("Un solo postor (riesgo)", f"{tasa:.1%}" if tasa is not None else "—",
          help=A["nota_riesgo_kpi"])
k4.caption(f"{conteo['un_postor']} de {conteo['denominador']:,} adjudicaciones competitivas. Alerta, no prueba.")

tabs = st.tabs(A["pestanas"])
vacio = len(f) == 0

# ------------------------------------------------------------------ Mapa
with tabs[0]:
    if vacio:
        st.warning(A["sin_datos"])
    else:
        medida = st.radio("Colorear por", ["Número de procesos", "Monto (S/)"], horizontal=True)
        g = (f.groupby("departamento").agg(procesos=("ocid", "size"),
                                           monto=("monto_pen", lambda s: s[f.loc[s.index, "monto_valido"]].sum()))
             .reindex(list(MOSTRAR), fill_value=0).reset_index())
        g["nombre"] = g["departamento"].map(MOSTRAR)
        col = "procesos" if medida.startswith("Número") else "monto"
        fig = px.choropleth(g, geojson=cargar_json("geojson"), locations="departamento",
                            featureidkey="properties.departamento", color=col, color_continuous_scale="Blues",
                            hover_name="nombre", hover_data={"departamento": False, "procesos": ":,", "monto": ":,.0f"},
                            labels={"procesos": "Procesos", "monto": "Monto (S/)"})
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(height=620, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, width="stretch")
        st.caption("Límites: IGN (Datos Abiertos), simplificados. Ubicación = departamento de la entidad compradora.")

# ------------------------------------------------------------------ Preguntar (RAG híbrido)
with tabs[1]:
    st.write("Pregunta en lenguaje natural. La IA separa los **filtros** (lugar, monto, fecha, categoría) del **tema**; "
             "los filtros se aplican exactos y el tema se busca por significado. También se aplican los filtros de la barra lateral.")
    cols = st.columns(len(A["ejemplos"]))
    for col, ej in zip(cols, A["ejemplos"]):
        if col.button(ej, width="stretch"):
            st.session_state["pregunta_radar"] = ej
    with st.form("form_radar"):
        pregunta = st.text_input("Tu pregunta", key="pregunta_radar")
        enviar = st.form_submit_button("Buscar", type="primary")
    if enviar and pregunta.strip():
        with st.spinner("Buscando procesos..."):
            try:
                st.session_state["resultado_radar"] = obtener_responder()(pregunta, filtros_barra, umbral)
            except Exception as ex:  # índice ausente: la app no lo reconstruye
                st.error(f"No se pudo usar el buscador: ejecuta `python build_index.py` una vez. ({type(ex).__name__})")
    r = st.session_state.get("resultado_radar")
    if r:
        st.subheader("Filtros que extrajo la IA (verifícalos)")
        etiquetas = {"departamento": "Departamento", "categoria": "Categoría", "monto_min": "Monto mínimo",
                     "monto_max": "Monto máximo", "fecha_desde": "Desde", "fecha_hasta": "Hasta"}
        filas = [{"Campo": etiquetas[k], "Extraído por la IA": "—" if r["filtros_ia"].get(k) is None else r["filtros_ia"][k],
                  "Aplicado": r["filtros_aplicados"].get(k, "—")} for k in etiquetas]
        if r["filtros_aplicados"].get("departamentos"):
            filas.append({"Campo": "Departamentos (barra)", "Extraído por la IA": "—", "Aplicado": ", ".join(r["filtros_aplicados"]["departamentos"])})
        if r["filtros_aplicados"].get("categorias"):
            filas.append({"Campo": "Categorías (barra)", "Extraído por la IA": "—", "Aplicado": ", ".join(r["filtros_aplicados"]["categorias"])})
        st.dataframe(pd.DataFrame(filas).astype(str), hide_index=True)
        st.caption(f"Tema buscado por significado: «{r['consulta_semantica']}» · procesos que cumplen los filtros: {r['n_procesos_filtrados']:,}")
        for a in r["avisos_filtros"]:
            st.warning(f"Filtro descartado: {a}")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Estado", r["estado"] or "—")
        m2.metric("Similitud máxima", f"{r['similitud_max']:.3f}" if r["similitud_max"] is not None else "—", help=f"Umbral: {r['umbral']}")
        m3.metric("Costo", f"US$ {r['costo_usd']:.6f}")
        m4.metric("Llamadas a la IA", r["llamadas_llm"])
        if r["error"]:
            st.error(r["error"])
        elif r["sin_resultados"]:
            st.info(f"**{r['respuesta']}** (no es una abstención: los filtros no dejan ningún proceso)")
        elif r["abstuvo"]:
            st.warning(f"**El buscador se abstuvo ({r['motivo_abstencion']}).** {r['respuesta']}")
        else:
            # Caja neutra (no verde): la IA puede decir aquí que ningún proceso coincide exactamente
            # (limitación conocida: F03/F07), y el usuario debe poder leerlo como advertencia.
            st.info(f"**Respuesta de la IA (léela completa):**\n\n{r['respuesta']}")
            st.warning(A["explicacion_ia"])
            if r["ocids_invalidos"]:
                st.warning(f"Se eliminaron {len(r['ocids_invalidos'])} ocid citados que no estaban entre los procesos encontrados.")
        if r["procesos"]:
            st.subheader("Procesos recuperados")
            tp = pd.DataFrame(r["procesos"])
            tp["monto"] = tp.apply(lambda x: soles(x["monto_pen"]) if x["monto_valido"] else "sin monto", axis=1)
            tp["departamento"] = tp["departamento"].map(MOSTRAR)
            st.dataframe(tp[["citado", "similitud", "ocid", "comprador", "departamento", "monto", "categoria", "estados", "descripcion"]],
                         hide_index=True, column_config={"citado": st.column_config.CheckboxColumn("Citado")})

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
        st.caption(f"{len(t):,} procesos. Haz clic en una columna para ordenar. Monto −1 = sin monto publicado.")
        st.dataframe(t, hide_index=True, height=520)
        st.download_button("Descargar CSV", t.to_csv(index=False).encode("utf-8"), "procesos_filtrados.csv", "text/csv")

# ------------------------------------------------------------------ Distribución
with tabs[3]:
    if vacio:
        st.warning(A["sin_datos"])
    else:
        dim = st.selectbox("Agrupar por", ["categoria_es", "departamento_mostrar", "mes", "metodo"],
                           format_func={"categoria_es": "Categoría", "departamento_mostrar": "Departamento",
                                        "mes": "Mes", "metodo": "Método de contratación"}.get)
        met = st.radio("Medida", ["Procesos", "Monto (S/)"], horizontal=True)
        g = f.groupby(dim).agg(Procesos=("ocid", "size"),
                               Monto=("monto_pen", lambda s: s[f.loc[s.index, "monto_valido"]].sum())).reset_index()
        y = "Procesos" if met == "Procesos" else "Monto"
        fig = px.bar(g.sort_values(y, ascending=False), x=dim, y=y, labels={dim: "", "Monto": "Monto (S/)"})
        fig.update_layout(height=450, margin=dict(t=10))
        st.plotly_chart(fig, width="stretch")
        if met != "Procesos":
            st.caption(A["nota_monto"].format(n=int((~f["monto_valido"]).sum())))

# ------------------------------------------------------------------ Riesgo
with tabs[4]:
    st.warning(R["aviso"])
    res = cargar_json("riesgo_resumen")
    st.markdown(
        "**Indicador:** entre los procesos **adjudicados** de **método competitivo**, porcentaje que recibió "
        "**exactamente un postor** (bandera *R018 Single bid received*, Open Contracting Partnership 2024). "
        "Se excluyen los métodos no competitivos (contratación directa, convenios, régimen especial...), donde un solo "
        "postor es lo esperado, y los procesos **sin dato** de número de postores.")
    if len(u) == 0:
        st.info("Con los filtros actuales no hay adjudicaciones competitivas con dato de postores.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Tasa (con filtros)", f"{conteo['un_postor'] / conteo['denominador']:.2%}")
        c2.metric("Adjudicaciones competitivas con dato", f"{conteo['denominador']:,}")
        c3.metric("Sin dato de postores (excluidas)", f"{conteo['sin_dato_postores']:,}")
        st.caption(f"Excluidas por método no competitivo: {conteo['excluidos_no_competitivos']:,} ({conteo['excluidos_por_metodo']})")
        st.subheader("Por departamento")
        dep = por_grupo(u, "departamento")
        dep["departamento"] = dep["departamento"].map(MOSTRAR)
        st.dataframe(dep, hide_index=True, column_config={
            "tasa_un_postor": st.column_config.NumberColumn("Tasa", format="percent"),
            "ic95_inf": st.column_config.NumberColumn("IC95 inf.", format="percent"),
            "ic95_sup": st.column_config.NumberColumn("IC95 sup.", format="percent")})
        st.subheader(f"Las {R['top_entidades']} entidades con mayor proporción (mínimo {R['min_procesos_entidad']} procesos)")
        ent = por_grupo(u, "comprador_id", "comprador_nombre_limpio")
        ent = ent[ent["procesos"] >= R["min_procesos_entidad"]].head(R["top_entidades"])
        if len(ent) == 0:
            st.info(f"Con los filtros actuales ninguna entidad llega a {R['min_procesos_entidad']} procesos.")
        else:
            ent["departamento"] = ent["departamento"].map(MOSTRAR)
            st.dataframe(ent[["nombre", "departamento", "procesos", "un_postor", "tasa_un_postor", "ic95_inf", "ic95_sup"]],
                         hide_index=True, column_config={
                             "nombre": "Entidad compradora", "un_postor": "Con un postor",
                             "tasa_un_postor": st.column_config.NumberColumn("Tasa", format="percent"),
                             "ic95_inf": st.column_config.NumberColumn("IC95 inf.", format="percent"),
                             "ic95_sup": st.column_config.NumberColumn("IC95 sup.", format="percent")})
            st.caption("IC95 = intervalo de confianza de Wilson: con pocos procesos la tasa es muy incierta. "
                       "Solo se muestran entidades públicas, nunca personas.")
    if res:
        with st.expander(f"¿Por qué un mínimo de {R['min_procesos_entidad']} procesos por entidad?"):
            st.write(f"Procesos por entidad (percentiles): {res['percentiles_procesos_por_entidad']}. "
                     "Con un mínimo bajo, una entidad con 1 proceso y 1 postor aparece con 100 %.")
            st.dataframe(pd.DataFrame(res["distribucion_minimos"]), hide_index=True)

# ------------------------------------------------------------------ Calidad de datos
with tabs[5]:
    cj = cargar_json("calidad_json")
    if cj:
        rs = cj["resumen"]
        a, b, c = st.columns(3)
        a.metric("Procesos en el corpus", f"{rs['filas']:,}")
        b.metric("Procesos en el análisis", f"{rs['incluidas_en_analisis']:,}")
        c.metric("Con alguna advertencia", f"{rs['filas_con_alguna_advertencia']:,}")
    texto = cargar_texto("reporte_calidad")
    if texto:
        st.markdown(texto.split("## Verificación")[0])

# ------------------------------------------------------------------ Novedades recientes
with tabs[6]:
    st.info(A["novedades_aviso"])
    nov = cargar_novedades()
    if nov is not None:
        n = nov if not deps else nov[nov["departamento"].isin(deps)]
        st.caption(f"{len(n):,} procesos de septiembre 2026 ({int(n['departamento'].isna().sum())} sin departamento).")
        st.dataframe(n[["ocid", "fecha_publicacion", "departamento", "comprador_nombre", "categoria_es", "monto", "moneda", "descripcion"]],
                     hide_index=True, height=480)

# ------------------------------------------------------------------ Costos
with tabs[7]:
    log = BASE / cfg["precios"]["log_llamadas"]
    st.write(f"Precios: {cfg['precios']['fuente']} (verificados el {cfg['precios']['fecha_verificacion']}); igual a toda hora.")
    if log.exists():
        lg = pd.read_csv(log)
        lg["costo_usd"] = pd.to_numeric(lg["costo_usd"], errors="coerce").fillna(0)
        a, b = st.columns(2)
        a.metric("Llamadas a la IA registradas", len(lg))
        b.metric("Costo total", f"US$ {lg['costo_usd'].sum():.4f}")
        st.dataframe(lg.tail(20), hide_index=True)
