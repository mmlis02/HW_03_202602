"""Prueba todos los caminos del motor del Radar SIN llamar a OpenAI (costo 0).

Un cliente falso imita la API: a la llamada de EXTRACCIÓN devuelve los filtros indicados y a la
de RESPUESTA arma un JSON según el caso (cita un ocid real de la lista recibida, un ocid inventado,
ninguno, fuera de tema o un error). Las llamadas falsas van a logs/costos_llm_prueba.csv.
Uso: python scripts/probar_motor_sin_costo.py
"""
import copy
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import cargar_config  # noqa: E402
from src.motor import MotorRadar, validar_filtros  # noqa: E402

VACIO = {"departamento": None, "categoria": None, "monto_min": None, "monto_max": None,
         "fecha_desde": None, "fecha_hasta": None}


class ClienteFalso:
    def __init__(self):
        self.filtros, self.modo, self.llamadas = {}, "real", 0
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kw):
        self.llamadas += 1
        es_extraccion = kw["response_format"]["json_schema"]["name"] == "filtros"
        if self.modo == "error" and es_extraccion:
            raise TimeoutError("simulado")
        if es_extraccion:
            datos = {**VACIO, **self.filtros, "consulta_semantica": kw["messages"][-1]["content"]}
        else:
            ocid_real = re.search(r"ocid=(\S+)", kw["messages"][-1]["content"]).group(1)
            datos = {"real": {"fuera_de_tema": False, "respuesta": f"Hay una obra ({ocid_real}).", "ocids_citados": [ocid_real]},
                     "inventado": {"fuera_de_tema": False, "respuesta": f"Obras ({ocid_real}) y (ocds-dgv273-seacev3-999999999).",
                                   "ocids_citados": [ocid_real, "ocds-dgv273-seacev3-999999999"]},
                     "sin_citas": {"fuera_de_tema": False, "respuesta": "Hay varias obras.", "ocids_citados": []},
                     "fuera": {"fuera_de_tema": True, "respuesta": "No trata de compras.", "ocids_citados": []}}[self.modo]
        return NS(choices=[NS(message=NS(content=json.dumps(datos)))],
                  usage=NS(prompt_tokens=800, completion_tokens=80, prompt_tokens_details=NS(cached_tokens=0)))


def main():
    cfg = copy.deepcopy(cargar_config())
    cfg["precios"]["log_llamadas"] = "logs/costos_llm_prueba.csv"
    cli = ClienteFalso()
    motor = MotorRadar(cfg, cliente_llm=cli)
    ok = True

    def caso(nombre, cond, r):
        nonlocal ok
        ok &= cond
        print(f"[{'OK ' if cond else 'FALLA'}] {nombre}: estado={r.estado} abstuvo={r.abstuvo} sin_resultados={r.sin_resultados} "
              f"n_filtrados={r.n_procesos_filtrados} llamadas={r.llamadas_llm} sim={r.similitud_max} citados={r.ocids_citados} "
              f"invalidos={r.ocids_invalidos}")

    Q01 = "Obras de agua potable y saneamiento en Cusco por más de un millón de soles"
    cli.filtros, cli.modo = {"departamento": "TUMBES", "categoria": "Obras", "monto_min": 1e7}, "real"
    r = motor.responder("Obras en Tumbes por más de 10 millones de soles")
    caso("cero procesos -> sin_resultados (no es abstención, 1 sola llamada)", r.sin_resultados and not r.abstuvo and r.llamadas_llm == 1, r)

    cli.filtros = {}
    r = motor.responder("¿Cuál es la capital de Australia?")
    caso("umbral después de filtrar -> abstención sin la IA que redacta", r.estado == "abstencion_umbral" and r.llamadas_llm == 1, r)

    cli.filtros = {"departamento": "CUSCO", "categoria": "Obras", "monto_min": 1e6}
    r = motor.responder(Q01)
    todos_cumplen = all(p["departamento"] == "CUSCO" and p["categoria"] == "Obras" and p["monto_pen"] >= 1e6 for p in r.procesos)
    caso("respuesta con ocid real; los procesos cumplen los filtros", r.estado == "respondido" and len(r.ocids_citados) == 1 and todos_cumplen, r)

    cli.modo = "inventado"
    r = motor.responder(Q01)
    caso("ocid inventado se elimina y se reporta", r.ocids_invalidos == ["ocds-dgv273-seacev3-999999999"] and "999999999" not in r.respuesta, r)

    cli.modo = "sin_citas"
    r = motor.responder(Q01)
    caso("respuesta sin ocid -> abstención sin_citas", r.motivo_abstencion == "sin_citas", r)

    cli.modo = "fuera"
    r = motor.responder(Q01)
    caso("la IA marca fuera de tema -> abstencion_ia", r.estado == "abstencion_ia" and r.motivo_abstencion == "fuera_de_tema", r)

    cli.modo = "error"
    r = motor.responder(Q01)
    caso("error de API en la extracción -> estado error", r.estado == "error" and r.error and r.respuesta is None, r)

    cli.modo, cli.filtros = "real", {"departamento": "CUSCO"}
    r = motor.responder("Obras en Cusco", filtros_barra={"departamentos": ["PUNO"]})
    caso("IA dice Cusco y la barra dice Puno -> contradicción = sin_resultados", r.sin_resultados, r)

    cli.filtros = {}
    r = motor.responder(Q01, filtros_barra={"departamentos": ["CUSCO"], "monto_min": 1e6, "categorias": ["Obras"]})
    caso("filtros de la barra se aplican aunque la IA no extraiga nada", r.filtros_aplicados.get("departamentos") == ["CUSCO"] and r.estado == "respondido", r)

    v, av = validar_filtros({"departamento": "Lima Metropolitana", "categoria": "Consultoría", "fecha_desde": "junio", "monto_max": -5},
                            motor.departamentos)
    cond = v == {} and len(av) == 4
    ok &= cond
    print(f"[{'OK ' if cond else 'FALLA'}] filtros inválidos se descartan con aviso: {av}")
    v, _ = validar_filtros({"departamento": "Junín", "monto_min": 1000000}, motor.departamentos)
    cond = v == {"departamento": "JUNIN", "monto_min": 1000000.0}
    ok &= cond
    print(f"[{'OK ' if cond else 'FALLA'}] 'Junín' se normaliza a JUNIN: {v}")

    print("\nTODAS LAS PRUEBAS OK" if ok else "\nHAY PRUEBAS QUE FALLARON")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
