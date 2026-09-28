"""Descarga los archivos mensuales de OECE (descargas masivas) a data/raw/.

- Re-ejecutable: no vuelve a descargar un archivo que ya existe y cuya huella SHA-256 coincide.
- Verifica cada ZIP con la huella SHA-256 publicada por OECE. OJO: la huella oficial corresponde al
  archivo JSON que va DENTRO del ZIP (no al ZIP). Se calcula leyendo el JSON desde el ZIP, sin
  descomprimirlo en disco (ahorra espacio).
- Descarga a un archivo temporal (.part) y solo lo renombra al terminar: un corte no deja
  un ZIP a medias que parezca bueno.
- Registra en logs/descargas.log: tiempo, número de pedidos HTTP y tamaño de cada archivo.

Uso (desde la carpeta tarea2_radar):
    python scripts/descargar_datos.py
"""
import hashlib
import json
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import cargar_config, ruta  # noqa: E402


def sha256(archivo: Path) -> str:
    h = hashlib.sha256()
    with open(archivo, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def sha256_interno(zip_path: Path) -> str:
    """Huella SHA-256 del (único) archivo dentro del ZIP, leído en bloques sin extraerlo."""
    with zipfile.ZipFile(zip_path) as z:
        nombres = z.namelist()
        if len(nombres) != 1:
            raise ValueError(f"{zip_path.name}: se esperaba 1 archivo dentro del ZIP y hay {len(nombres)}")
        h = hashlib.sha256()
        with z.open(nombres[0]) as f:
            for bloque in iter(lambda: f.read(1 << 20), b""):
                h.update(bloque)
    return h.hexdigest()


def main():
    cfg = cargar_config()
    o = cfg["oece"]
    raw = ruta(cfg, "raw")
    raw.mkdir(parents=True, exist_ok=True)
    ruta(cfg, "logs").mkdir(exist_ok=True)
    log = open(ruta(cfg, "logs") / "descargas.log", "a", encoding="utf-8")
    man_path = ruta(cfg, "manifiesto_descargas")
    manifiesto = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}
    sesion = requests.Session()
    sesion.headers["User-Agent"] = o["user_agent"]
    pedidos, inicio_total = 0, time.time()

    def registrar(msg):
        linea = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
        print(linea)
        log.write(linea + "\n")

    def pedir(url, stream=False):
        nonlocal pedidos
        for intento in range(1, o["reintentos"] + 1):
            pedidos += 1
            try:
                r = sesion.get(url, timeout=o["timeout_segundos"], stream=stream)
                r.raise_for_status()
                return r
            except requests.RequestException as ex:
                registrar(f"   intento {intento} falló: {ex}")
                time.sleep(o["pausa_entre_pedidos_s"] * 2 ** intento)
        raise RuntimeError(f"No se pudo descargar {url}")

    for m in o["meses"]:
        clave = f"{m['anio']}-{m['mes']}_{o['fuente']}_{o['formato']}"
        destino = raw / f"{clave}.zip"
        url = o["plantilla_archivo"].format(base=o["base"], fuente=o["fuente"], formato=o["formato"], anio=m["anio"], mes=m["mes"])
        url_sha = o["plantilla_archivo"].format(base=o["base"], fuente=o["fuente"], formato="sha", anio=m["anio"], mes=m["mes"])
        sha_oficial = pedir(url_sha).text.strip().split()[0].lower()
        time.sleep(o["pausa_entre_pedidos_s"])

        if destino.exists() and sha256_interno(destino) == sha_oficial:
            registrar(f"[ya existe, huella OK] {destino.name} ({destino.stat().st_size / 1e6:.1f} MB)")
            continue
        registrar(f"[descargando] {clave} desde {url}")
        t0 = time.time()
        temporal = destino.with_suffix(".zip.part")
        with pedir(url, stream=True) as r, open(temporal, "wb") as f:
            for bloque in r.iter_content(1 << 20):
                f.write(bloque)
        huella = sha256_interno(temporal)
        if huella != sha_oficial:
            temporal.unlink()
            raise ValueError(f"{clave}: la huella SHA-256 NO coincide (descargada {huella[:12]}…, oficial {sha_oficial[:12]}…)")
        temporal.rename(destino)
        segundos = time.time() - t0
        with zipfile.ZipFile(destino) as z:
            interno = z.infolist()[0]
        registrar(f"   OK {destino.name}: {destino.stat().st_size / 1e6:.1f} MB (JSON interno {interno.file_size / 1e6:.1f} MB) "
                  f"en {segundos:.1f} s, huella SHA-256 del JSON interno verificada")
        manifiesto[clave] = {"archivo": destino.name, "archivo_interno": interno.filename, "bytes_interno": interno.file_size,
                             "url": url, "url_sha": url_sha, "sha256_json_interno": huella, "sha256_zip": sha256(destino),
                             "bytes": destino.stat().st_size, "fecha_descarga": datetime.now().isoformat(timespec="seconds"),
                             "segundos_descarga": round(segundos, 1)}
        time.sleep(o["pausa_entre_pedidos_s"])

    man_path.write_text(json.dumps(manifiesto, indent=2, ensure_ascii=False), encoding="utf-8")
    registrar(f"Resumen: {pedidos} pedidos HTTP, {time.time() - inicio_total:.1f} s en total")


if __name__ == "__main__":
    main()
