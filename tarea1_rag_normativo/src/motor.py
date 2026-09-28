"""MOTOR RAG (proceso online). Toda la lógica vive aquí; las interfaces solo llaman a `responder`.

Este módulo NO importa Streamlit ni ninguna librería de interfaz. Tampoco lee los PDFs:
solo consulta el índice ya construido por build_index.py.

Flujo de `responder(pregunta)`:
  1. Busca los k fragmentos más parecidos en el índice.
  2. DEFENSA 1 (sin IA): si la similitud del mejor fragmento < umbral, se abstiene
     SIN llamar al LLM (costo 0).
  3. Llama al LLM con los fragmentos numerados [F1]..[Fk] y un esquema JSON estricto.
  4. DEFENSA 2 (con IA): si el LLM marca "fuera_de_corpus", se abstiene y explica el límite.
  5. Reemplaza cada [Fn] por "(documento, pág. N)" usando los METADATOS del fragmento
     (el LLM nunca escribe números de página) y agrega la nota de versión.
  6. Registra la llamada (tokens, latencia, costo según la hora, éxito o error).
"""
import json
import re
import time
from dataclasses import asdict, dataclass, field

from src.config import cargar_config
from src.costos import ahora_utc, calcular_costo, registrar_llamada
from src.embeddings import crear_embedder
from src.indice import abrir_coleccion, buscar

ESQUEMA_RESPUESTA = {
    "name": "respuesta_rag",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "fuera_de_corpus": {"type": "boolean"},
            "respuesta": {"type": "string"},
            "explicacion_limite": {"type": "string"},
        },
        "required": ["fuera_de_corpus", "respuesta", "explicacion_limite"],
        "additionalProperties": False,
    },
}
CITA = re.compile(r"\[F(\d+)\]")


@dataclass
class Fuente:
    documento: str
    titulo: str
    pagina: int
    similitud: float
    articulo: str
    modificado_por: str
    texto: str
    fecha_modificacion: str = ""
    citada: bool = False


@dataclass
class ResultadoRAG:
    pregunta: str
    respuesta: str | None = None
    abstuvo: bool = False
    motivo_abstencion: str | None = None      # "umbral" | "fuera_de_corpus" | "sin_citas" | None
    explicacion_limite: str = ""
    # True = respondió, pero declaró que falta parte (explicacion_limite no vacía). NO es abstención.
    respuesta_parcial: bool = False
    fuentes: list[Fuente] = field(default_factory=list)
    similitud_max: float | None = None
    umbral: float | None = None
    notas_version: list[str] = field(default_factory=list)
    llamo_llm: bool = False
    modelo: str | None = None
    tokens_entrada: int = 0
    tokens_salida: int = 0
    costo_usd: float = 0.0
    latencia_s: float = 0.0
    error: str | None = None

    def a_dict(self) -> dict:
        return asdict(self)


class Motor:
    def __init__(self, cfg: dict | None = None, cliente_llm=None, conf_fragmentos: str | None = None):
        self.cfg = cfg or cargar_config()
        self.embedder = crear_embedder(self.cfg)
        conf = conf_fragmentos or self.cfg["fragmentos"]["elegida"]
        self.coleccion = abrir_coleccion(self.cfg, self.embedder.alias, conf, crear=False)  # nunca reconstruye
        self._cliente = cliente_llm  # se puede inyectar un cliente falso para pruebas sin costo

    # ---------- LLM ----------
    def _cliente_llm(self):
        if self._cliente is None:
            import os

            from dotenv import load_dotenv
            from openai import OpenAI

            load_dotenv()
            self._cliente = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"),
                                   timeout=self.cfg["llm"]["timeout_segundos"])
        return self._cliente

    def _llamar_llm(self, pregunta: str, fragmentos_txt: str):
        lcfg = self.cfg["llm"]
        return self._cliente_llm().chat.completions.create(
            model=lcfg["modelo"],
            reasoning_effort=lcfg["reasoning_effort"],
            max_completion_tokens=lcfg["max_tokens_salida"],
            response_format={"type": "json_schema", "json_schema": ESQUEMA_RESPUESTA},
            messages=[
                {"role": "system", "content": self.cfg["prompts"]["sistema"]},
                {"role": "user", "content": self.cfg["prompts"]["usuario"].format(
                    pregunta=pregunta, fragmentos=fragmentos_txt)},
            ],
        )

    # ---------- utilidades ----------
    def _formatear_fragmentos(self, fuentes: list[Fuente]) -> str:
        bloques = []
        for i, f in enumerate(fuentes, 1):
            enc = f"[F{i}] {f.titulo} — página {f.pagina}"
            if f.articulo:
                enc += f" — {f.articulo}"
            bloques.append(f"{enc}\n{f.texto}")
        return "\n\n".join(bloques)

    def _poner_citas(self, texto: str, fuentes: list[Fuente]) -> str:
        cortas = self.cfg["motor"]["citas_cortas"]

        def reemplazo(m):
            n = int(m.group(1))
            if 1 <= n <= len(fuentes):
                f = fuentes[n - 1]
                f.citada = True
                return f"({cortas.get(f.documento, f.documento)}, pág. {f.pagina})"
            return ""  # cita a un fragmento inexistente: se elimina
        return re.sub(r"\s+([.,;:])", r"\1", CITA.sub(reemplazo, texto)).strip()

    def _notas_version(self, fuentes: list[Fuente]) -> list[str]:
        """Capa 3 de versiones: nota explícita según los METADATOS de las fuentes citadas."""
        m = self.cfg["mensajes"]
        notas = []
        citadas = [f for f in fuentes if f.citada]
        for f in citadas:
            if f.modificado_por:
                for norma, fecha in zip(f.modificado_por.split("; "), f.fecha_modificacion.split("; ")):
                    notas.append(m["nota_modificado"].format(norma=norma, fecha=fecha))
        if any(f.documento == "ds001_2026_ef" for f in citadas):
            notas.append(m["nota_ds_parcial"])
        if any(f.documento == "dl1715" for f in citadas):
            notas.append(m["nota_dl1715"])
        return list(dict.fromkeys(notas))

    # ---------- función principal ----------
    def responder(self, pregunta: str, aplicar_umbral: bool = True) -> ResultadoRAG:
        """aplicar_umbral=False solo lo usa la evaluación diagnóstica (eval/evaluar_motor.py --sin-umbral)."""
        m = self.cfg["mensajes"]
        umbral = self.cfg["motor"]["umbral_similitud"]
        r = ResultadoRAG(pregunta=pregunta, umbral=umbral)
        if not pregunta or not pregunta.strip():
            r.error = m["pregunta_vacia"]
            return r

        encontrados = buscar(self.coleccion, self.embedder, pregunta, self.cfg["motor"]["k_contexto"])
        r.fuentes = []
        for e in encontrados:
            md = e["metadatos"]
            r.fuentes.append(Fuente(md["documento"], md["titulo"], md["pagina"], round(e["similitud"], 4),
                                    md.get("articulo", ""), md.get("modificado_por", ""), e["texto"],
                                    md.get("fecha_modificacion", "")))
        r.similitud_max = r.fuentes[0].similitud if r.fuentes else 0.0

        # DEFENSA 1: decidir ANTES de llamar al LLM
        if aplicar_umbral and r.similitud_max < umbral:
            r.abstuvo, r.motivo_abstencion, r.respuesta = True, "umbral", m["abstencion_umbral"]
            return r

        # Llamada al LLM
        r.llamo_llm, r.modelo = True, self.cfg["llm"]["modelo"]
        momento, inicio = ahora_utc(), time.time()
        fila_log = {"fecha_hora_utc": momento.isoformat(timespec="seconds"), "modelo": r.modelo,
                    "pregunta": pregunta[:200]}
        try:
            resp = self._llamar_llm(pregunta, self._formatear_fragmentos(r.fuentes))
            r.latencia_s = round(time.time() - inicio, 3)
            uso = resp.usage
            cache = getattr(getattr(uso, "prompt_tokens_details", None), "cached_tokens", 0) or 0
            r.tokens_entrada, r.tokens_salida = uso.prompt_tokens, uso.completion_tokens
            r.costo_usd, franja = calcular_costo(self.cfg, r.modelo, momento, r.tokens_entrada, r.tokens_salida, cache)
            fila_log.update(tokens_entrada=r.tokens_entrada, tokens_entrada_cache=cache, tokens_salida=r.tokens_salida,
                            latencia_s=r.latencia_s, costo_usd=f"{r.costo_usd:.8f}", franja=franja)
            datos = json.loads(resp.choices[0].message.content)
        except Exception as ex:  # errores de API o respuesta inválida: se devuelven como ERROR
            r.latencia_s = round(time.time() - inicio, 3)
            r.error = f"{m['error_api']} ({type(ex).__name__}: {str(ex)[:200]})"
            fila_log.update(latencia_s=r.latencia_s, exito=False, error=f"{type(ex).__name__}: {str(ex)[:200]}")
            registrar_llamada(self.cfg, fila_log)
            return r
        fila_log["exito"] = True
        registrar_llamada(self.cfg, fila_log)

        # DEFENSA 2: el LLM detectó que los fragmentos no responden la pregunta
        r.explicacion_limite = datos.get("explicacion_limite", "")
        if datos.get("fuera_de_corpus"):
            r.abstuvo, r.motivo_abstencion = True, "fuera_de_corpus"
            r.respuesta = m["abstencion_fuera_de_corpus"]
            if r.explicacion_limite:
                r.explicacion_limite = self._poner_citas(r.explicacion_limite, r.fuentes)
            return r

        r.respuesta = self._poner_citas(datos.get("respuesta", ""), r.fuentes)
        if r.explicacion_limite:  # respuesta parcial: se informa qué parte no está en el corpus
            r.explicacion_limite = self._poner_citas(r.explicacion_limite, r.fuentes)
        if not any(f.citada for f in r.fuentes):
            # Toda respuesta debe citar: sin citas no se muestra
            r.abstuvo, r.motivo_abstencion, r.respuesta = True, "sin_citas", m["abstencion_sin_citas"]
            return r
        r.respuesta_parcial = bool(r.explicacion_limite.strip())
        r.notas_version = self._notas_version(r.fuentes)
        return r


_MOTOR: Motor | None = None


def responder(pregunta: str) -> dict:
    """Función única que usan todas las interfaces (Streamlit, línea de comandos, ...)."""
    global _MOTOR
    if _MOTOR is None:
        _MOTOR = Motor()
    return _MOTOR.responder(pregunta).a_dict()
