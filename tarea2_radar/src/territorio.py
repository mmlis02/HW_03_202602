"""Normalización territorial con la tabla OFICIAL del IGN (Datos Abiertos).

- Los 25 departamentos (incluido Callao) y sus nombres canónicos salen de DEPARTAMENTOS_LIMITES.
- La relación provincia -> departamento y distrito -> departamento sale de DISTRITOS_LIMITES.
  Los 196 nombres de provincia son únicos; de los distritos solo se usan los nombres que existen
  en UN solo departamento (95 nombres de distrito se repiten en varios y se descartan).
- Todas las comparaciones se hacen con `clave()`: mayúsculas, sin tildes, espacios simples.
  Así "JUNÍN", "Junín" y "JUNIN " son la misma clave.
"""
import io
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapefile


def clave(texto) -> str:
    """Forma normalizada para comparar: sin tildes (Ñ -> N), mayúsculas y espacios simples."""
    if texto is None or (isinstance(texto, float) and np.isnan(texto)):
        return ""
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.upper().split())


def _lector(zip_path: Path, base: str, geometria: bool = False) -> shapefile.Reader:
    z = zipfile.ZipFile(zip_path)
    partes = {"dbf": io.BytesIO(z.read(f"{base}.dbf"))}
    if geometria:
        partes.update(shp=io.BytesIO(z.read(f"{base}.shp")), shx=io.BytesIO(z.read(f"{base}.shx")))
    return shapefile.Reader(**partes, encoding="utf-8")


class Territorio:
    def __init__(self, carpeta_ign: Path, alias_provincias: dict):
        deps = [r.as_dict() for r in _lector(carpeta_ign / "DEPARTAMENTOS_LIMITES.zip", "DEPARTAMENTOS").records()]
        self.departamentos = {clave(d["DEPARTAMEN"]): d["DEPARTAMEN"] for d in deps}      # clave -> nombre IGN
        dist = [r.as_dict() for r in _lector(carpeta_ign / "DISTRITOS_LIMITES.zip", "DISTRITOS").records()]
        self.prov_a_dep = {clave(r["PROVINCIA"]): r["DEPARTAMEN"] for r in dist}
        por_distrito = defaultdict(set)
        for r in dist:
            por_distrito[clave(r["DISTRITO"])].add(r["DEPARTAMEN"])
        self.dist_a_dep = {k: next(iter(v)) for k, v in por_distrito.items() if len(v) == 1}
        self.alias = {clave(k): clave(v) for k, v in alias_provincias.items()}

    def departamento_valido(self, valor) -> str | None:
        return self.departamentos.get(clave(valor))

    def provincia(self, valor) -> tuple[str | None, bool]:
        """(departamento según el IGN, se_usó_alias)."""
        k = clave(valor)
        alias = k in self.alias
        return self.prov_a_dep.get(self.alias.get(k, k)), alias

    def distrito(self, valor) -> str | None:
        return self.dist_a_dep.get(clave(valor))


# ---------------------------------------------------------------- GeoJSON liviano para el mapa
def _rdp(puntos: np.ndarray, tol: float) -> np.ndarray:
    """Simplificación Ramer-Douglas-Peucker (iterativa) de una línea de puntos."""
    if len(puntos) < 3:
        return puntos
    conservar = np.zeros(len(puntos), dtype=bool)
    conservar[[0, -1]] = True
    pila = [(0, len(puntos) - 1)]
    while pila:
        i, j = pila.pop()
        a, b = puntos[i], puntos[j]
        seg = puntos[i + 1:j]
        if len(seg) == 0:
            continue
        ab = b - a
        norma = np.hypot(*ab)
        rel = seg - a
        # distancia de cada punto a la recta a-b (producto cruz 2D); si a == b, distancia a "a"
        dist = np.abs(ab[0] * rel[:, 1] - ab[1] * rel[:, 0]) / norma if norma else np.hypot(rel[:, 0], rel[:, 1])
        k = int(np.argmax(dist))
        if dist[k] > tol:
            m = i + 1 + k
            conservar[m] = True
            pila += [(i, m), (m, j)]
    return puntos[conservar]


def geojson_departamentos(carpeta_ign: Path, tol: float, decimales: int, nombres_mostrar: dict) -> dict:
    r = _lector(carpeta_ign / "DEPARTAMENTOS_LIMITES.zip", "DEPARTAMENTOS", geometria=True)
    features = []
    for forma, reg in zip(r.shapes(), r.records()):
        geo = forma.__geo_interface__
        poligonos = geo["coordinates"] if geo["type"] == "MultiPolygon" else [geo["coordinates"]]
        nuevos = []
        for pol in poligonos:
            anillos = []
            for n, anillo in enumerate(pol):
                s = np.round(_rdp(np.asarray(anillo, dtype=float), tol), decimales)
                if len(s) >= 4:
                    anillos.append(s.tolist())
                elif n == 0:
                    break  # el contorno exterior desapareció (isla diminuta): se omite el polígono
            if anillos:
                nuevos.append(anillos)
        d = reg.as_dict()
        features.append({"type": "Feature",
                         "properties": {"departamento": d["DEPARTAMEN"], "coddep": d["CODDEP"],
                                        "nombre": nombres_mostrar.get(d["DEPARTAMEN"], d["DEPARTAMEN"])},
                         "geometry": {"type": "MultiPolygon", "coordinates": nuevos}})
    return {"type": "FeatureCollection", "features": features}
