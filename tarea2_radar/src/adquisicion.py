"""Lectura de los archivos OCDS mensuales y aplanado: un record -> una fila.

Modelo OCDS (para el video):
- RELEASE: una "foto" de un proceso en un momento (planificación, convocatoria, adjudicación...).
  Un mismo proceso tiene muchas releases a lo largo del tiempo.
- RECORD: agrupa TODAS las releases de un proceso y trae su `compiledRelease`, que es la versión
  consolidada con el estado más reciente de cada campo.
- OCID: identificador único y permanente de UN proceso de contratación (p. ej.
  "ocds-dgv273-seacev3-1251524"); todas sus releases y su record lo comparten.

Los archivos de OECE son paquetes de RECORDS: cada record trae su compiledRelease y la lista de
sus releases (solo enlace, fecha y etiqueta). Aquí se toma el compiledRelease.
Los campos se copian tal cual (sin corregir): la validación y normalización es la Fase 2.
"""
import json
import zipfile
from collections.abc import Iterator
from pathlib import Path


def leer_records(zip_path: Path) -> Iterator[dict]:
    """Devuelve los records del JSON que va dentro del ZIP, sin descomprimirlo en disco."""
    with zipfile.ZipFile(zip_path) as z:
        with z.open(z.namelist()[0]) as f:
            paquete = json.load(f)
    yield from paquete["records"]


def _comprador(cr: dict) -> dict:
    """La parte con rol 'buyer' (la entidad que compra) y su dirección."""
    bid = (cr.get("buyer") or {}).get("id")
    partes = cr.get("parties", [])
    p = next((x for x in partes if "buyer" in x.get("roles", [])), None) or \
        next((x for x in partes if x.get("id") == bid), {})
    ruc = next((a.get("id") for a in p.get("additionalIdentifiers", []) if a.get("scheme") == "PE-RUC"), None)
    dir_ = p.get("address") or {}
    return {"comprador_id": bid, "comprador_nombre": (cr.get("buyer") or {}).get("name"), "comprador_ruc": ruc,
            "comprador_departamento_raw": dir_.get("department"), "comprador_region_raw": dir_.get("region"),
            "comprador_localidad_raw": dir_.get("locality")}


def aplanar(record: dict, mes_archivo: str) -> dict:
    cr = record["compiledRelease"]
    t = cr.get("tender") or {}
    valor = t.get("value") or {}
    items = t.get("items") or []
    awards = cr.get("awards") or []
    proveedores = {s.get("id") for a in awards for s in a.get("suppliers", []) if s.get("id")}
    fechas_rel = [r.get("date") for r in record.get("releases", []) if r.get("date")]
    clasif = [i.get("classification", {}).get("id") for i in items if i.get("classification")]
    return {
        "ocid": record.get("ocid") or cr.get("ocid"),
        "mes_archivo": mes_archivo,
        "segmentacion": (cr.get("dataSegmentation") or {}).get("id"),
        "fecha_compilado": cr.get("date"),
        "n_releases": len(record.get("releases", [])),
        "fecha_ultima_release": max(fechas_rel) if fechas_rel else None,
        "tender_id": t.get("id"),
        "nomenclatura": t.get("title"),
        "descripcion": t.get("description"),
        "metodo": t.get("procurementMethodDetails"),
        "categoria": t.get("mainProcurementCategory"),
        "monto": valor.get("amount"),
        "moneda": valor.get("currency"),
        "monto_pen_oece": valor.get("amount_PEN"),
        "fecha_publicacion": t.get("datePublished"),
        "fecha_inicio_convocatoria": (t.get("tenderPeriod") or {}).get("startDate"),
        **_comprador(cr),
        "n_postores": t.get("numberOfTenderers"),
        "n_postores_lista": len(t.get("tenderers") or []),
        "n_items": len(items),
        "estados_items": "|".join(sorted({i.get("statusDetails") for i in items if i.get("statusDetails")})),
        "items_descripcion": " | ".join(i.get("description", "") for i in items[:5]),
        "clasificacion_items": "|".join(sorted(set(clasif)))[:300],
        "n_adjudicaciones": len(awards),
        "monto_adjudicado": sum((a.get("value") or {}).get("amount") or 0 for a in awards) if awards else None,
        "n_proveedores_adjudicados": len(proveedores),
    }
