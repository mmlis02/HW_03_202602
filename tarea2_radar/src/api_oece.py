"""Cliente de la API de OECE para NOVEDADES recientes, con pausas, reintentos y caché.

- Pausa fija entre pedidos (no sobrecargar el portal).
- Reintentos con espera creciente ante errores de red o respuestas 5xx/429.
- Caché en disco por página: cada página descargada se guarda apenas llega. Si un pedido falla,
  las páginas anteriores ya están guardadas y la próxima corrida continúa desde donde quedó.
"""
import json
import time
from pathlib import Path

import requests


class ClienteOECE:
    def __init__(self, cfg: dict, carpeta_cache: Path, log=print):
        self.a, self.o = cfg["api"], cfg["oece"]
        self.cache = carpeta_cache
        self.cache.mkdir(parents=True, exist_ok=True)
        self.log = log
        self.sesion = requests.Session()
        self.sesion.headers["User-Agent"] = self.o["user_agent"]
        self.pedidos = 0
        self.bytes = 0

    def _pedir(self, url: str, params: dict) -> dict:
        for intento in range(1, self.a["reintentos"] + 1):
            time.sleep(self.a["pausa_entre_pedidos_s"])
            self.pedidos += 1
            try:
                r = self.sesion.get(url, params=params, timeout=self.o["timeout_segundos"])
                if r.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"HTTP {r.status_code}")
                r.raise_for_status()
                self.bytes += len(r.content)
                return r.json()
            except (requests.RequestException, ValueError) as ex:
                espera = 2 ** intento
                self.log(f"   intento {intento}/{self.a['reintentos']} falló ({ex}); reintento en {espera} s")
                time.sleep(espera)
        raise RuntimeError(f"Falló definitivamente: {url} {params}")

    def pagina(self, n: int) -> tuple[dict, bool]:
        """Devuelve (datos, vino_de_cache)."""
        archivo = self.cache / f"pagina_{n:03d}.json"
        if archivo.exists() and (time.time() - archivo.stat().st_mtime) < self.a["cache_horas"] * 3600:
            return json.loads(archivo.read_text(encoding="utf-8")), True
        url = self.a["url_busqueda"].format(base=self.o["base"])
        datos = self._pedir(url, {**self.a["parametros"], "page": n, "paginateBy": self.a["por_pagina"]})
        archivo.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")  # se guarda YA
        return datos, False
