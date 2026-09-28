"""MOTOR del Radar (Tarea 2): RAG híbrido = filtros estructurados + búsqueda semántica.

Reutiliza de la Tarea 1 (paquete comun/): el mismo modelo local de embeddings, la misma llamada al
LLM con esquema JSON, el mismo cálculo de costo por hora y log, y la misma lógica de dos defensas.
No importa ninguna librería de interfaz.

Flujo de `responder(pregunta, filtros_barra)`:
  1. La IA EXTRAE los filtros de la pregunta (departamento, montos, fechas, categoría) y el texto a
     buscar. Se validan (departamento del IGN, categoría válida, fechas ISO).
  2. Se combinan con los filtros de la barra lateral (intersección: deben cumplirse ambos).
  3. Si los filtros dejan CERO procesos -> estado "sin_resultados" (no es una abstención).
  4. Búsqueda semántica SOLO entre los procesos que cumplen los filtros.
  5. DEFENSA 1: si la similitud top-1 (calculada DESPUÉS de filtrar) < umbral, se abstiene SIN llamar
     a la IA que redacta.
  6. La IA redacta citando cada proceso por su ocid. DEFENSA 2: puede marcar "fuera_de_tema".
  7. Se validan los ocid citados (deben estar entre los recuperados).
"""
import json
import re
from dataclasses import asdict, dataclass, field

from src.config import BASE, cargar_config
from comun.embeddings import crear_embedder  # noqa: E402
from comun.llm import cliente_openai, llamar_llm_json  # noqa: E402
from src.indice import abrir, buscar, construir_filtro  # noqa: E402
from src.territorio import clave  # noqa: E402

CATEGORIAS = ["Bienes", "Servicios", "Obras"]
OCID = re.compile(r"ocds-[a-z0-9]+-seacev3-[A-Za-z0-9-]+")
CAMPOS = ["departamento", "categoria", "monto_min", "monto_max", "fecha_desde", "fecha_hasta"]


def esquema_extraccion(departamentos: list[str]) -> dict:
    nulo_str = {"type": ["string", "null"]}
    nulo_num = {"type": ["number", "null"]}
    return {"name": "filtros", "strict": True, "schema": {
        "type": "object", "additionalProperties": False,
        "required": CAMPOS + ["consulta_semantica"],
        "properties": {"departamento": {"type": ["string", "null"], "enum": departamentos + [None]},
                       "categoria": {"type": ["string", "null"], "enum": CATEGORIAS + [None]},
                       "monto_min": nulo_num, "monto_max": nulo_num,
                       "fecha_desde": nulo_str, "fecha_hasta": nulo_str,
                       "consulta_semantica": {"type": "string"}}}}


ESQUEMA_RESPUESTA = {"name": "respuesta_radar", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "required": ["fuera_de_tema", "respuesta", "ocids_citados"],
    "properties": {"fuera_de_tema": {"type": "boolean"}, "respuesta": {"type": "string"},
                   "ocids_citados": {"type": "array", "items": {"type": "string"}}}}}


@dataclass
class ResultadoRadar:
    pregunta: str
    estado: str = ""                 # respondido | sin_resultados | abstencion_umbral | abstencion_ia | error
    abstuvo: bool = False
    motivo_abstencion: str | None = None   # umbral | fuera_de_tema | sin_citas
    sin_resultados: bool = False
    respuesta: str | None = None
    filtros_ia: dict = field(default_factory=dict)
    avisos_filtros: list[str] = field(default_factory=list)
    filtros_barra: dict = field(default_factory=dict)
    filtros_aplicados: dict = field(default_factory=dict)
    consulta_semantica: str = ""
    n_procesos_filtrados: int = 0
    procesos: list[dict] = field(default_factory=list)
    similitud_max: float | None = None
    umbral: float | None = None
    ocids_citados: list[str] = field(default_factory=list)
    ocids_invalidos: list[str] = field(default_factory=list)
    llamadas_llm: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    costo_usd: float = 0.0
    latencia_s: float = 0.0
    error: str | None = None

    def a_dict(self) -> dict:
        return asdict(self)


def validar_filtros(f: dict, departamentos: dict) -> tuple[dict, list[str]]:
    """Solo deja valores válidos; lo que no se reconoce se descarta con aviso (visible en la app)."""
    limpio, avisos = {}, []
    if f.get("departamento"):
        dep = departamentos.get(clave(f["departamento"]))
        if dep:
            limpio["departamento"] = dep
        else:
            avisos.append(f"departamento no reconocido: {f['departamento']}")
    if f.get("categoria"):
        if f["categoria"] in CATEGORIAS:
            limpio["categoria"] = f["categoria"]
        else:
            avisos.append(f"categoría no reconocida: {f['categoria']}")
    for k in ("monto_min", "monto_max"):
        v = f.get(k)
        if v is not None:
            if isinstance(v, (int, float)) and v >= 0:
                limpio[k] = float(v)
            else:
                avisos.append(f"{k} inválido: {v}")
    for k in ("fecha_desde", "fecha_hasta"):
        v = f.get(k)
        if v:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)):
                limpio[k] = str(v)
            else:
                avisos.append(f"{k} inválida: {v}")
    return limpio, avisos


def combinar(ia: dict, barra: dict) -> tuple[dict, bool]:
    """Intersección de filtros de la IA y de la barra lateral. Devuelve (filtros, contradicción)."""
    f = dict(ia)
    contradiccion = False
    if barra.get("departamentos"):
        if f.get("departamento"):
            contradiccion = f["departamento"] not in barra["departamentos"]
        else:
            f["departamentos"] = list(barra["departamentos"])
    if barra.get("categorias"):
        if f.get("categoria"):
            contradiccion |= f["categoria"] not in barra["categorias"]
        else:
            f["categorias"] = list(barra["categorias"])
    for k, elegir in (("monto_min", max), ("fecha_desde", max), ("monto_max", min), ("fecha_hasta", min)):
        valores = [v for v in (ia.get(k), barra.get(k)) if v is not None]
        if valores:
            f[k] = elegir(valores)
    return f, contradiccion


class MotorRadar:
    def __init__(self, cfg: dict | None = None, cliente_llm=None):
        self.cfg = cfg or cargar_config()
        self.embedder = crear_embedder(self.cfg, base=BASE)
        self.coleccion = abrir(self.cfg, crear=False)  # nunca reconstruye
        nombres = list(self.cfg["validacion"]["departamentos_mostrar"])
        self.departamentos = {clave(d): d for d in nombres}
        self.esquema_ext = esquema_extraccion(nombres)
        self._cliente = cliente_llm

    def _cliente_llm(self):
        if self._cliente is None:
            self._cliente = cliente_openai(self.cfg)
        return self._cliente

    def _sumar(self, r: ResultadoRadar, ll: dict):
        r.llamadas_llm += 1
        r.tokens_entrada += ll["tokens_entrada"]
        r.tokens_salida += ll["tokens_salida"]
        r.costo_usd += ll["costo_usd"]
        r.latencia_s = round(r.latencia_s + ll["latencia_s"], 3)

    def extraer_filtros(self, pregunta: str, r: ResultadoRadar) -> dict | None:
        p = self.cfg["prompts"]
        mensajes = [{"role": "system", "content": p["extraccion"].format(departamentos=", ".join(self.departamentos.values()))},
                    {"role": "user", "content": pregunta}]
        ll = llamar_llm_json(self._cliente_llm(), self.cfg, BASE, mensajes, self.esquema_ext, f"[filtros] {pregunta}")
        self._sumar(r, ll)
        if ll["error"]:
            r.error = f"{self.cfg['mensajes']['error_api']} ({ll['error']})"
            return None
        return ll["datos"]

    def _where(self, f: dict) -> dict | None:
        base = construir_filtro({k: v for k, v in f.items() if k in CAMPOS})
        extra = []
        if f.get("departamentos"):
            extra.append({"departamento": {"$in": f["departamentos"]}})
        if f.get("categorias"):
            extra.append({"categoria": {"$in": f["categorias"]}})
        partes = ([base] if base else []) + extra
        return None if not partes else partes[0] if len(partes) == 1 else {"$and": partes}

    def responder(self, pregunta: str, filtros_barra: dict | None = None, aplicar_umbral: bool = True,
                  filtros_forzados: dict | None = None) -> ResultadoRadar:
        """filtros_forzados: solo para la evaluación (usa los filtros correctos de la hoja, sin extraerlos)."""
        m = self.cfg["mensajes"]
        r = ResultadoRadar(pregunta=pregunta, umbral=self.cfg["motor"]["umbral_similitud"], filtros_barra=filtros_barra or {})
        if not pregunta or not pregunta.strip():
            r.estado, r.error = "error", m["pregunta_vacia"]
            return r

        # 1-2. Filtros: extraídos por la IA (o forzados en evaluación) + barra lateral
        if filtros_forzados is not None:
            extraidos = {**{k: None for k in CAMPOS}, **filtros_forzados, "consulta_semantica": pregunta}
        else:
            extraidos = self.extraer_filtros(pregunta, r)
            if extraidos is None:
                r.estado = "error"
                return r
        r.filtros_ia = {k: extraidos.get(k) for k in CAMPOS}
        validos, r.avisos_filtros = validar_filtros(r.filtros_ia, self.departamentos)
        r.consulta_semantica = (extraidos.get("consulta_semantica") or pregunta).strip() or pregunta
        r.filtros_aplicados, contradiccion = combinar(validos, r.filtros_barra)
        where = self._where(r.filtros_aplicados)

        # 3. ¿Cuántos procesos cumplen los filtros?
        r.n_procesos_filtrados = 0 if contradiccion else len(self.coleccion.get(where=where, include=[])["ids"])
        if r.n_procesos_filtrados == 0:
            r.estado, r.sin_resultados, r.respuesta = "sin_resultados", True, m["sin_resultados"]
            return r

        # 4. Búsqueda semántica SOLO entre los que cumplen los filtros
        k = min(self.cfg["motor"]["k_resultados"], r.n_procesos_filtrados)
        vec = self.embedder.embed_consulta(r.consulta_semantica)
        q = self.coleccion.query(query_embeddings=[vec.tolist()], n_results=k, where=where,
                                 include=["documents", "metadatas", "distances"])
        r.procesos = [{**md, "descripcion": doc, "similitud": round(1 - dist, 4), "citado": False}
                      for doc, md, dist in zip(q["documents"][0], q["metadatas"][0], q["distances"][0])]
        r.similitud_max = r.procesos[0]["similitud"] if r.procesos else 0.0

        # 5. DEFENSA 1: umbral aplicado DESPUÉS de filtrar, antes de la IA que redacta
        if aplicar_umbral and r.similitud_max < r.umbral:
            r.estado, r.abstuvo, r.motivo_abstencion, r.respuesta = "abstencion_umbral", True, "umbral", m["abstencion_umbral"]
            return r

        # 6. La IA redacta citando ocid
        def monto(p):  # -1 es el valor interno de "sin dato": nunca debe llegar al usuario como monto
            return f"S/ {p['monto_pen']:,.2f}" if p["monto_valido"] else "sin monto publicado"

        def fecha(p):
            f = str(p["fecha_int"])
            return f"{f[:4]}-{f[4:6]}-{f[6:]}" if p["fecha_int"] > 0 else "sin fecha"

        lista = "\n".join(f"[P{i}] ocid={p['ocid']} | entidad={p['comprador']} | departamento={p['departamento']} | "
                          f"monto={monto(p)} | fecha={fecha(p)} | categoría={p['categoria']} | "
                          f"estado={p['estados']} | descripción={p['descripcion']}" for i, p in enumerate(r.procesos, 1))
        pr = self.cfg["prompts"]
        mensajes = [{"role": "system", "content": pr["respuesta"]},
                    {"role": "user", "content": pr["respuesta_usuario"].format(
                        pregunta=pregunta, filtros=json.dumps(r.filtros_aplicados, ensure_ascii=False),
                        n_filtrados=r.n_procesos_filtrados, procesos=lista)}]
        ll = llamar_llm_json(self._cliente_llm(), self.cfg, BASE, mensajes, ESQUEMA_RESPUESTA, pregunta)
        self._sumar(r, ll)
        if ll["error"]:
            r.estado, r.error = "error", f"{m['error_api']} ({ll['error']})"
            return r
        datos = ll["datos"]

        # DEFENSA 2
        if datos.get("fuera_de_tema"):
            r.estado, r.abstuvo, r.motivo_abstencion = "abstencion_ia", True, "fuera_de_tema"
            r.respuesta = f"{m['abstencion_ia']} {datos.get('respuesta', '')}".strip()
            return r

        # 7. Validación de ocid: todos los citados deben estar entre los recuperados
        recuperados = {p["ocid"] for p in r.procesos}
        citados = list(dict.fromkeys(list(datos.get("ocids_citados", [])) + OCID.findall(datos.get("respuesta", ""))))
        r.ocids_citados = [o for o in citados if o in recuperados]
        r.ocids_invalidos = [o for o in citados if o not in recuperados]
        for p in r.procesos:
            p["citado"] = p["ocid"] in r.ocids_citados
        texto = datos.get("respuesta", "")
        for o in r.ocids_invalidos:  # un ocid inventado no se muestra como si fuera real
            texto = texto.replace(o, "[ocid no válido eliminado]")
        if not r.ocids_citados:
            r.estado, r.abstuvo, r.motivo_abstencion, r.respuesta = "abstencion_ia", True, "sin_citas", m["abstencion_sin_citas"]
            return r
        r.estado, r.respuesta = "respondido", texto
        return r


_MOTOR: MotorRadar | None = None


def responder(pregunta: str, filtros_barra: dict | None = None) -> dict:
    """Función única que usan las interfaces (dashboard, línea de comandos)."""
    global _MOTOR
    if _MOTOR is None:
        _MOTOR = MotorRadar()
    return _MOTOR.responder(pregunta, filtros_barra).a_dict()
