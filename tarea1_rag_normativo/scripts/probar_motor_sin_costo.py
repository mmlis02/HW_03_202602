"""Prueba todos los caminos del motor SIN llamar a OpenAI (costo 0).

Se inyecta un cliente falso que imita la respuesta de la API. Las "llamadas" falsas se
registran en logs/costos_llm_prueba.csv, no en el log real de costos.

Uso: python scripts/probar_motor_sin_costo.py
"""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import cargar_config  # noqa: E402
from src.motor import Motor  # noqa: E402


class ClienteFalso:
    """Imita client.chat.completions.create(...) devolviendo lo que se le indique."""

    def __init__(self):
        self.proxima = None
        self.llamadas = 0
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kwargs):
        self.llamadas += 1
        if isinstance(self.proxima, Exception):
            raise self.proxima
        return NS(choices=[NS(message=NS(content=json.dumps(self.proxima)))],
                  usage=NS(prompt_tokens=1500, completion_tokens=200, prompt_tokens_details=NS(cached_tokens=0)))


def main():
    cfg = copy.deepcopy(cargar_config())
    cfg["precios"]["log_llamadas"] = "logs/costos_llm_prueba.csv"
    cliente = ClienteFalso()
    motor = Motor(cfg, cliente_llm=cliente)
    ok = True

    def revisar(nombre, condicion, r):
        nonlocal ok
        ok &= condicion
        print(f"[{'OK ' if condicion else 'FALLA'}] {nombre}: abstuvo={r.abstuvo} motivo={r.motivo_abstencion} "
              f"llamo_llm={r.llamo_llm} error={bool(r.error)} costo={r.costo_usd:.6f}")
        if r.respuesta:
            print("       respuesta:", r.respuesta[:160])
        for n in r.notas_version:
            print("       nota:", n[:120])

    # 1. Defensa 1: fuera de dominio -> se abstiene sin llamar al LLM
    antes = cliente.llamadas
    r = motor.responder("¿Cómo se prepara un ceviche?")
    revisar("umbral (ceviche)", r.abstuvo and r.motivo_abstencion == "umbral" and cliente.llamadas == antes and not r.llamo_llm, r)

    # 2. Respuesta normal con citas -> [F1] se convierte en (doc, pág. N) desde los metadatos
    cliente.proxima = {"fuera_de_corpus": False, "respuesta": "No procede la medida cautelar [F1].", "explicacion_limite": ""}
    r = motor.responder("¿Procede una medida cautelar para paralizar una obra de infraestructura hidráulica?")
    f1 = r.fuentes[0]
    revisar("respuesta con cita", not r.abstuvo and f"pág. {f1.pagina}" in r.respuesta and f1.citada and r.costo_usd > 0, r)

    # 3. Defensa 2: el LLM dice que los fragmentos no responden
    cliente.proxima = {"fuera_de_corpus": True, "respuesta": "",
                       "explicacion_limite": "La ley solo remite al reglamento [F1]."}
    r = motor.responder("¿Qué porcentaje máximo de mi contrato puedo subcontratar?")
    revisar("fuera de corpus (IA)", r.abstuvo and r.motivo_abstencion == "fuera_de_corpus" and "pág." in r.explicacion_limite, r)

    # 4. Error de API -> se devuelve como ERROR, nunca como respuesta normal
    cliente.proxima = TimeoutError("simulado")
    r = motor.responder("¿Cuándo se declara desierto un procedimiento de selección?")
    revisar("error de API", r.error is not None and r.respuesta is None and not r.abstuvo, r)

    # 5. Respuesta sin citas -> no se muestra
    cliente.proxima = {"fuera_de_corpus": False, "respuesta": "Sí, se puede.", "explicacion_limite": ""}
    r = motor.responder("¿Cuándo se declara desierto un procedimiento de selección?")
    revisar("sin citas", r.abstuvo and r.motivo_abstencion == "sin_citas", r)

    # 6. Pregunta vacía
    r = motor.responder("   ")
    revisar("pregunta vacía", r.error is not None and not r.llamo_llm, r)

    # 7. Precio según la hora: tabla ficticia con descuento nocturno (como DeepSeek)
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from src.costos import calcular_costo
    cfg_h = copy.deepcopy(cfg)
    cfg_h["precios"]["modelos"]["ficticio"] = {"franjas": [
        {"desde": "00:00", "hasta": "08:30", "entrada": 1.0, "entrada_cache": 1.0, "salida": 1.0},
        {"desde": "08:30", "hasta": "24:00", "entrada": 2.0, "entrada_cache": 2.0, "salida": 2.0}]}
    noche, _ = calcular_costo(cfg_h, "ficticio", datetime(2026, 9, 27, 3, 0, tzinfo=ZoneInfo("UTC")), 1_000_000, 0)
    dia, _ = calcular_costo(cfg_h, "ficticio", datetime(2026, 9, 27, 15, 0, tzinfo=ZoneInfo("UTC")), 1_000_000, 0)
    borde, _ = calcular_costo(cfg_h, "ficticio", datetime(2026, 9, 27, 8, 29, 59, tzinfo=ZoneInfo("UTC")), 1_000_000, 0)
    cond = noche == 1.0 and dia == 2.0 and borde == 1.0
    ok &= cond
    print(f"[{'OK ' if cond else 'FALLA'}] precio por hora: 03:00 UTC -> {noche} USD, 15:00 UTC -> {dia} USD (1M tokens)")

    print("\nTODAS LAS PRUEBAS OK" if ok else "\nHAY PRUEBAS QUE FALLARON")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
