"""Descarga los PDFs de la Tarea 1 a data/raw/.

- No vuelve a descargar un archivo que ya existe (se puede correr muchas veces).
- Guarda en data/manifiesto_descargas.json la fecha de descarga, el tamaño y la
  huella sha256 de cada archivo, para saber exactamente qué versión se usó.

Uso (desde la carpeta tarea1_rag_normativo):
    python scripts/descargar_fuentes.py
"""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import cargar_config, ruta  # noqa: E402


def sha256(archivo: Path) -> str:
    return hashlib.sha256(archivo.read_bytes()).hexdigest()


def main():
    cfg = cargar_config()
    carpeta_raw = ruta(cfg, "raw")
    carpeta_raw.mkdir(parents=True, exist_ok=True)
    ruta_manifiesto = ruta(cfg, "manifiesto_descargas")
    manifiesto = json.loads(ruta_manifiesto.read_text(encoding="utf-8")) if ruta_manifiesto.exists() else {}

    cabeceras = {"User-Agent": cfg["descarga"]["user_agent"]}
    for doc in cfg["documentos"]:
        destino = carpeta_raw / doc["archivo"]
        if destino.exists():
            print(f"[ya existe] {destino.name} ({destino.stat().st_size / 1e6:.2f} MB)")
        else:
            print(f"[descargando] {doc['id']} ...")
            r = requests.get(doc["url_pdf"], headers=cabeceras, timeout=cfg["descarga"]["timeout_segundos"])
            r.raise_for_status()
            if not r.content.startswith(b"%PDF"):
                raise ValueError(f"{doc['id']}: la respuesta no es un PDF (¿página bloqueada?)")
            destino.write_bytes(r.content)
            print(f"   guardado {destino.name} ({len(r.content) / 1e6:.2f} MB)")
            manifiesto[doc["id"]] = {"fecha_descarga": datetime.now().isoformat(timespec="seconds")}

        # Siempre se actualizan tamaño y huella (por si alguien bajó el PDF a mano).
        info = manifiesto.setdefault(doc["id"], {"fecha_descarga": "desconocida (descarga manual)"})
        info.update({
            "archivo": doc["archivo"],
            "url_pdf": doc["url_pdf"],
            "bytes": destino.stat().st_size,
            "sha256": sha256(destino),
        })

    # Se quitan entradas de documentos que ya no están en config.yaml
    ids = {d["id"] for d in cfg["documentos"]}
    manifiesto = {k: v for k, v in manifiesto.items() if k in ids}
    ruta_manifiesto.write_text(json.dumps(manifiesto, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Manifiesto actualizado: {ruta_manifiesto}")


if __name__ == "__main__":
    main()
