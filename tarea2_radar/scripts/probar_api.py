"""Prueba de resiliencia de la API: simula una caída de red a mitad de camino.

1. Se fuerza que, después de 3 pedidos reales, todos los pedidos fallen.
2. El script se detiene con aviso; las páginas bajadas antes del fallo quedan en caché.
3. Una segunda corrida normal continúa desde la caché y completa lo que falta.
Uso: python scripts/probar_api.py   (resultado también en logs/api.log)
"""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import scripts.actualizar_api as act  # noqa: E402
from src import api_oece  # noqa: E402

original = api_oece.requests.Session.get
contador = {"n": 0}


def get_que_falla(self, *a, **k):
    contador["n"] += 1
    if contador["n"] > 3:
        raise requests.ConnectionError("caída de red SIMULADA")
    return original(self, *a, **k)


print("=== Corrida 1: la red 'se cae' después de 3 pedidos ===")
api_oece.requests.Session.get = get_que_falla
api_oece.time.sleep = lambda s: None  # sin esperas en la prueba
act.main()
print("\n=== Corrida 2: red normal, continúa desde la caché ===")
api_oece.requests.Session.get = original
act.main()
