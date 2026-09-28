"""App Streamlit de la Tarea 1 (SOLO interfaz).

Toda la lógica RAG está en src/motor.py: esta app solo llama a `responder(pregunta)` y muestra
el resultado. Nunca construye el índice ni lee los PDFs; los paneles leen reportes ya generados.

Ejecutar (desde la carpeta tarea1_rag_normativo):
    streamlit run app.py
"""
import json

import pandas as pd
import streamlit as st

from src.config import BASE, cargar_config

cfg = cargar_config()
A = cfg["app"]
st.set_page_config(page_title=A["titulo"], page_icon="⚖️", layout="wide")


@st.cache_resource(show_spinner=A["cargando"])
def obtener_responder():
    """Importa el motor y lo inicializa una sola vez (modelo de embeddings + índice existente)."""
    from src.motor import responder
    responder(" ")  # pregunta vacía: inicializa el motor sin buscar ni llamar a la IA
    return responder


@st.cache_data
def leer_texto(clave: str) -> str | None:
    ruta = BASE / A["rutas_reportes"][clave]
    return ruta.read_text(encoding="utf-8") if ruta.exists() else None


@st.cache_data
def leer_json(clave: str) -> dict | None:
    texto = leer_texto(clave)
    return json.loads(texto) if texto else None


def mostrar_fuentes(fuentes: list[dict], titulo: str):
    st.subheader(titulo)
    cortas = cfg["motor"]["citas_cortas"]
    for f in fuentes:
        marca = f" · ✅ {A['etiqueta_citada']}" if f["citada"] else ""
        encabezado = f"{cortas.get(f['documento'], f['documento'])} — pág. {f['pagina']} — similitud {f['similitud']:.3f}{marca}"
        with st.expander(encabezado, expanded=f["citada"]):
            st.caption(f"{f['titulo']}" + (f" · {f['articulo']}" if f["articulo"] else "")
                       + (f" · modificado por {f['modificado_por']}" if f["modificado_por"] else ""))
            st.text(f["texto"])


def mostrar_resultado(r: dict):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("¿Se abstuvo?", "Sí" if r["abstuvo"] else "No")
    c2.metric("Similitud máxima", f"{r['similitud_max']:.3f}" if r["similitud_max"] is not None else "—",
              help=f"Umbral de abstención: {r['umbral']}")
    c3.metric("Costo de la consulta", f"US$ {r['costo_usd']:.6f}")
    c4.metric("Tokens (entrada / salida)", f"{r['tokens_entrada']} / {r['tokens_salida']}")

    if r["error"]:
        st.error(r["error"])  # los errores de API se muestran como ERROR, nunca como respuesta
        if r["fuentes"]:
            mostrar_fuentes(r["fuentes"], A["titulo_fuentes_error"])
        return

    st.subheader(A["titulo_respuesta"])
    if r["abstuvo"]:
        st.warning(f"**{A['abstencion_titulo']}.** {r['respuesta']}")
        st.caption(A["motivos"].get(r["motivo_abstencion"], r["motivo_abstencion"]))
    else:
        st.success(r["respuesta"])
    if r["explicacion_limite"]:
        st.info(f"**{A['titulo_limite']}:** {r['explicacion_limite']}")
    for nota in r["notas_version"]:
        st.info(f"**{A['titulo_notas_version']}:** {nota}")
    st.caption(f"Modelo: {r['modelo'] or '— (no se llamó a la IA)'} · latencia {r['latencia_s']:.2f} s")
    if r["fuentes"]:
        mostrar_fuentes(r["fuentes"], A["titulo_fuentes"])


# ------------------------------------------------------------------ interfaz
st.title(A["titulo"])
st.write(A["subtitulo"])
st.caption(A["aviso_legal"])
tab_preg, tab_cal, tab_eval, tab_cost = st.tabs(A["pestanas"])

with tab_preg:
    try:
        responder = obtener_responder()
    except Exception as ex:  # índice inexistente u otro problema al cargar: la app NO lo reconstruye
        st.error(A["sin_indice"])
        st.caption(f"{type(ex).__name__}: {ex}")
        st.stop()

    st.write(f"**{A['ejemplos_titulo']}:**")
    cols = st.columns(len(A["ejemplos"]))
    for col, ejemplo in zip(cols, A["ejemplos"]):
        if col.button(ejemplo, width="stretch"):
            st.session_state["pregunta"] = ejemplo
    with st.form("form_pregunta"):
        pregunta = st.text_area(A["etiqueta_pregunta"], key="pregunta", height=90)
        enviar = st.form_submit_button(A["boton_preguntar"], type="primary")
    if enviar:
        with st.spinner("Buscando en los documentos..."):
            st.session_state["resultado"] = responder(pregunta)
    if st.session_state.get("resultado"):
        mostrar_resultado(st.session_state["resultado"])

with tab_cal:
    for clave in ("verificacion", "calidad", "ejemplos_limpieza"):
        texto = leer_texto(clave)
        if texto:
            with st.expander(texto.splitlines()[0].lstrip("# "), expanded=(clave == "calidad")):
                st.markdown(texto)

with tab_eval:
    st.subheader("Motor completo: abstención por umbral (sin IA) y final (con IA)")
    def fila(nombre, datos, con_umbral):
        f = {"Corrida": nombre}
        if con_umbral:
            f.update({f"umbral: {k}": v for k, v in datos["defensa1_sin_ia"].items() if "tasa" not in k})
        f.update({f"final: {k}": v for k, v in datos["final_con_ia"].items()
                  if k in ("abstenciones_correctas", "abstenciones_incorrectas", "acierto_de_cita", "costo_total_usd")})
        return f
    corridas = [("Prompt v1 (umbral 0.840)", "motor_v1", True),
                ("Prompt v2 (diagnóstico: el LLM ve las 25)", "motor_v2", False),
                ("Prompt v3 — en uso (diagnóstico: el LLM ve las 25)", "motor_v3", False)]
    filas = [fila(n, leer_json(k), u) for n, k, u in corridas if leer_json(k)]
    if filas:
        st.dataframe(pd.DataFrame(filas).fillna("—"), hide_index=True)
    opciones = leer_texto("opciones_umbral")
    if opciones:
        st.markdown("**Opciones de umbral con el prompt v3, en uso** (umbral elegido para el modelo local: "
                    f"{cfg['motor']['umbral_similitud']['local']})")
        st.markdown(opciones)
    barrido = BASE / A["rutas_reportes"]["barrido_png"]
    if barrido.exists():
        st.image(str(barrido), caption="Barrido del umbral (sin IA)")
    puntajes = leer_texto("puntajes")
    if puntajes:
        with st.expander("Similitud top-1 de las 25 preguntas de evaluación"):
            st.markdown(puntajes)

    st.subheader("Comparación de embeddings (Fase 4)")
    comp = leer_json("comparacion_embeddings")
    if comp:
        campos = ["recall@1", "recall@3", "recall@5", "mrr@5", "segundos_indexacion", "costo_indexacion_usd",
                  "latencia_consulta_media_s", "costo_por_consulta_usd", "dimension", "auc_dentro_fuera"]
        tabla = pd.DataFrame({m["modelo"]: {c: m.get(c) for c in campos} for m in comp["modelos"].values()})
        st.dataframe(tabla.astype(str))
    st.subheader("Fragmentos y recuperación (Fase 2)")
    frag = leer_texto("fragmentos")
    if frag:
        st.markdown(frag.split("![Distribución]")[0])
    graf = BASE / A["rutas_reportes"]["grafico_fragmentos"]
    if graf.exists():
        st.image(str(graf))

with tab_cost:
    log = BASE / cfg["precios"]["log_llamadas"]
    st.write(f"Precios: {cfg['precios']['fuente']} (verificados el {cfg['precios']['fecha_verificacion']}). "
             "OpenAI cobra igual a toda hora; la tabla de franjas horarias está en config.yaml.")
    if log.exists():
        df = pd.read_csv(log)
        df["costo_usd"] = pd.to_numeric(df["costo_usd"], errors="coerce").fillna(0)
        c1, c2, c3 = st.columns(3)
        c1.metric("Llamadas registradas", len(df))
        c2.metric("Costo total", f"US$ {df['costo_usd'].sum():.4f}")
        c3.metric("Llamadas fallidas", int((df["exito"].astype(str) != "True").sum()))
        st.dataframe(df.groupby("modelo").agg(llamadas=("modelo", "size"), costo_usd=("costo_usd", "sum")).reset_index(), hide_index=True)
        with st.expander("Últimas 20 llamadas"):
            st.dataframe(df.tail(20), hide_index=True)
