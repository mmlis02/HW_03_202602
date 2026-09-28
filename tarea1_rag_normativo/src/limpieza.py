"""Limpieza del texto extraído, sin perder nunca el número de página.

Unidad de trabajo: el PÁRRAFO, siempre con su página. Un párrafo que cruza de una
página a otra se deja partido en dos (uno por página) para que la cita sea exacta.

Reglas (los patrones están en config.yaml > limpieza):
  R1  Encabezado de página de El Peruano (n.° de página, "NORMAS LEGALES", fecha).
  R2  Sello de firma digital "Firmado por: Editora Peru / Fecha: ...".
  R3  Código de publicación que cierra la norma (p. ej. "2474920-3").
  R4  Ligaduras rotas ("Caliﬁ cación" -> "Calificación").
  R5  Párrafos "CONCORDANCIAS:" del SPIJ.
  R6  Re-armado de líneas: el PDF corta cada línea (y a veces cada palabra) por el
      ancho de columna; se unen las líneas de un mismo párrafo.
  R7  Notas de versión "(*)" de la ley actualizada (ver `aplicar_notas_de_version`).
"""
import re
from collections import Counter

# --- Patrones de las notas de versión (R7) ---------------------------------
# Ejemplo: "(*) Literal modificado por el Artículo 3 del Decreto Legislativo N° 1715,
#           publicada el 04 febrero 2026, cuyo texto es el siguiente: "e) ...""
NOTA = re.compile(r"^\(\*\)\s*")
NOTA_CAMBIO = re.compile(
    r"^\(\*\)\s*(?P<unidad>Literal|Numeral(?:\s+\d+)?|Disposición|Artículo|Párrafo)\s+"
    r"(?P<accion>modificad[oa]|incorporad[oa]|derogad[oa]|sustituid[oa])\s+por\s+"
    r"(?P<norma>.+?),\s*publicad[oa]\s+el\s+(?P<fecha>\d{1,2}\s+\w+\s+\d{4})",
    flags=re.S,
)
NOTA_AVISO = re.compile(r"^\(\*\)\s*De conformidad con")
NOTA_ERRATA = re.compile(r"^\(\*\)\s*NOTA SPIJ.*?dice:\s*[“\"](?P<dice>.+?)[”\"],\s*debiendo decir:\s*[“\"](?P<debe>.+?)[”\"]", flags=re.S)
CUYO_TEXTO = re.compile(r"cuyo texto es el siguiente:\s*", flags=re.I)
# Etiqueta con la que empieza una unidad: "e)", "41.1", "73.2.", "1.", "VIGÉSIMA NOVENA.", "PRIMERA."
ETIQUETA = re.compile(r"^[“\"]?\s*([a-zñ]\)|\d+(?:\.\d+)*\.?|[A-ZÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ]+)?\.)")

# --- Separación en párrafos para PDFs de El Peruano (sin líneas en blanco) ---
INICIO_ESTRUCTURAL = re.compile(
    r"^[“\"]?\s*(Artículo\s+\d+|\d+\.\d+\.?\s|[a-zñ]\)\s|\(…\)|Que,|POR TANTO|DECRETA|SE DECRETA|"
    r"DISPOSICI|PRIMERA\.|SEGUNDA\.|TERCERA\.|CUARTA\.|QUINTA\.|SEXTA\.|SÉPTIMA\.|OCTAVA\.|NOVENA\.|DÉCIMA|ÚNICA\.)"
)


def _etiqueta(texto: str) -> str | None:
    m = ETIQUETA.match(texto.strip())
    return m.group(1).rstrip(".").strip() if m else None


def limpiar_ruido_pagina(texto: str, reglas: dict, contador: Counter) -> str:
    """R1–R4 sobre el texto crudo de UNA página."""
    texto, n = re.subn(reglas["encabezado_elperuano"], "", texto)
    contador["R1_encabezado_elperuano"] += n
    texto, n = re.subn(reglas["sello_firma"], "", texto)
    contador["R2_sello_firma"] += n
    texto, n = re.subn(reglas["codigo_publicacion"], "", texto, flags=re.M)
    contador["R3_codigo_publicacion"] += n
    for mala, buena in reglas["ligaduras"].items():
        # la ligadura suele venir seguida de un espacio espurio: "Caliﬁ cación"
        texto, n = re.subn(rf"{mala}\s*(?=[a-záéíóúñ])", buena, texto)
        contador["R4_ligaduras"] += n
        texto = texto.replace(mala, buena)
    return texto


def _unir_lineas(lineas: list[str]) -> str:
    """R6: une las líneas de un párrafo. Si una línea termina en guion, se pega sin espacio."""
    salida = ""
    for linea in (l.strip() for l in lineas):
        if not linea:
            continue
        if salida.endswith("-"):
            salida += linea
        else:
            salida += (" " if salida else "") + linea
    return re.sub(r"\s{2,}", " ", salida).strip()


def partir_parrafos(texto: str, con_lineas_en_blanco: bool) -> list[str]:
    """Divide el texto de una página en párrafos ya re-armados (R6)."""
    lineas = texto.split("\n")
    grupos, actual = [], []
    for linea in lineas:
        limpia = linea.strip()
        if con_lineas_en_blanco:
            # Formato OECE/SPIJ: los párrafos van separados por líneas en blanco
            if not limpia:
                if actual:
                    grupos.append(actual)
                actual = []
                continue
            if NOTA.match(limpia) and actual:  # una nota "(*)" siempre abre párrafo propio
                grupos.append(actual)
                actual = []
            actual.append(limpia)
        else:
            # Formato El Peruano: no hay líneas en blanco; se corta cuando empieza una unidad
            # (artículo, numeral, literal...) o cuando la línea anterior cerró una oración.
            if not limpia:
                continue
            previo = actual[-1] if actual else ""
            cierra = re.search(r"[.:;][”\"]?$", previo)
            if actual and (INICIO_ESTRUCTURAL.match(limpia) or (cierra and limpia[:1].isupper())):
                grupos.append(actual)
                actual = []
            actual.append(limpia)
    if actual:
        grupos.append(actual)
    return [p for p in (_unir_lineas(g) for g in grupos) if p]


def aplicar_notas_de_version(parrafos: list[dict], ventana: int, contador: Counter) -> tuple[list[dict], list[dict]]:
    """R7: resuelve las notas "(*)" de la versión actualizada de la ley.

    parrafos = [{'pagina': n, 'texto': ...}, ...] en orden de lectura.
    - modificado/sustituido: se BORRA el texto antiguo (desde el párrafo que empieza con
      la misma etiqueta que el texto nuevo hasta el párrafo marcado con "(*)") y la nota
      se reescribe como "[Texto vigente — ... modificado por X, publicada el F] <texto nuevo>".
    - incorporado: el texto de arriba ya es el nuevo; la nota queda como "[... incorporado por X ...]".
    - derogado: se borra el párrafo derogado y queda "[... derogado por X ...]".
    - "De conformidad con...": aviso de vigencia; se conserva como "[Nota de vigencia] ...".
    - "NOTA SPIJ" (fe de erratas): se corrige la palabra en el texto y se quita la nota.
    Devuelve (parrafos_limpios, registro_de_cambios) para el reporte.
    """
    borrar = set()
    registro = []

    # Una nota que empieza al final de una página y sigue en la siguiente se une con su
    # continuación. La nota unida queda en la página SIGUIENTE, porque ahí está el texto vigente.
    for i in range(len(parrafos) - 1):
        texto, sig = parrafos[i]["texto"], parrafos[i + 1]
        es_nota_incompleta = NOTA.match(texto) and not (NOTA_CAMBIO.match(texto) or NOTA_AVISO.match(texto) or NOTA_ERRATA.match(texto))
        if es_nota_incompleta and sig["pagina"] != parrafos[i]["pagina"] and not NOTA.match(sig["texto"]):
            sig["texto"] = texto + " " + sig["texto"]
            parrafos[i]["texto"] = ""
            contador["R7_nota_partida_entre_paginas_unida"] += 1

    for i, p in enumerate(parrafos):
        texto = p["texto"]
        if not NOTA.match(texto):
            continue

        m_err = NOTA_ERRATA.match(texto)
        if m_err:
            dice, debe = m_err.group("dice"), m_err.group("debe")
            for q in parrafos:
                if dice in q["texto"]:
                    q["texto"] = re.sub(rf"{re.escape(dice)}\s*\(\*\)\s*NOTA SPIJ", debe, q["texto"]).replace(dice, debe)
            borrar.add(i)
            contador["R7_fe_de_erratas"] += 1
            registro.append({"accion": "fe de erratas", "pagina_nota": p["pagina"], "detalle": f"'{dice}' -> '{debe}'"})
            continue

        if NOTA_AVISO.match(texto):
            p["texto"] = "[Nota de vigencia] " + NOTA.sub("", texto)
            contador["R7_aviso_vigencia"] += 1
            registro.append({"accion": "aviso de vigencia (se conserva)", "pagina_nota": p["pagina"], "detalle": p["texto"][:120]})
            continue

        m = NOTA_CAMBIO.match(texto)
        if not m:
            contador["R7_nota_no_reconocida"] += 1
            registro.append({"accion": "NO RECONOCIDA (revisar)", "pagina_nota": p["pagina"], "detalle": texto[:160]})
            continue

        unidad, accion, norma, fecha = m["unidad"], m["accion"].lower(), " ".join(m["norma"].split()), m["fecha"]
        # El párrafo marcado con "(*)" al final es el último del texto afectado
        k = next((j for j in range(i - 1, max(-1, i - 1 - ventana), -1) if parrafos[j]["texto"].rstrip().endswith("(*)")), None)

        if accion.startswith(("modificad", "sustituid")):
            # El texto nuevo está después de "cuyo texto es el siguiente:" y puede seguir en
            # los párrafos siguientes hasta cerrar comillas.
            partes = CUYO_TEXTO.split(texto, maxsplit=1)
            nuevo = partes[1] if len(partes) > 1 else ""
            j = i
            while not re.search(r"[”\"]\s*$", nuevo) and j + 1 < len(parrafos) and not NOTA.match(parrafos[j + 1]["texto"]):
                j += 1
                if parrafos[j]["pagina"] != p["pagina"]:
                    break  # el texto nuevo sigue en otra página: esos párrafos se quedan con su página
                nuevo += "\n" + parrafos[j]["texto"]  # salto simple: sigue siendo UN bloque con su etiqueta
                borrar.add(j)
            etiqueta = _etiqueta(nuevo)
            inicio = None
            if k is not None and etiqueta:
                inicio = next(
                    (a for a in range(k, max(-1, k - ventana), -1) if _etiqueta(parrafos[a]["texto"]) == etiqueta),
                    None,
                )
            if inicio is None:
                contador["R7_modificacion_sin_texto_antiguo_ubicado"] += 1
                estado = "texto antiguo NO ubicado (revisar)"
                antiguo = ""
            else:
                antiguo = " ".join(parrafos[a]["texto"] for a in range(inicio, k + 1))
                borrar.update(range(inicio, k + 1))
                contador["R7_modificacion_texto_antiguo_eliminado"] += 1
                estado = "texto antiguo eliminado del índice"
            p["texto"] = f"[Texto vigente — {unidad} {accion} por {norma}, publicada el {fecha}] {nuevo.strip()}"
            registro.append({
                "accion": f"{unidad} {accion}", "norma": norma, "fecha": fecha, "pagina_nota": p["pagina"],
                "paginas_texto_antiguo": sorted({parrafos[a]["pagina"] for a in range(inicio, k + 1)}) if inicio is not None else [],
                "etiqueta": etiqueta, "estado": estado, "texto_antiguo": antiguo[:300], "texto_nuevo": nuevo.strip()[:300],
            })
        elif accion.startswith("derogad"):
            antiguo = parrafos[k]["texto"] if k is not None else ""
            etiqueta = _etiqueta(antiguo) or ""
            if k is not None:
                borrar.add(k)
            p["texto"] = f"[{unidad} {etiqueta} {accion} por {norma}, publicada el {fecha}]".replace("  ", " ")
            contador["R7_derogacion"] += 1
            registro.append({"accion": f"{unidad} {accion}", "norma": norma, "fecha": fecha, "pagina_nota": p["pagina"],
                             "estado": "texto derogado eliminado del índice", "texto_antiguo": antiguo[:300]})
        else:  # incorporado
            p["texto"] = f"[{unidad} {accion} por {norma}, publicada el {fecha}]"
            contador["R7_incorporacion"] += 1
            registro.append({"accion": f"{unidad} {accion}", "norma": norma, "fecha": fecha, "pagina_nota": p["pagina"],
                             "estado": "texto incorporado conservado"})

    limpios = []
    for i, p in enumerate(parrafos):
        if i in borrar:
            continue
        texto = re.sub(r"\s*\(\*\)", "", p["texto"]).strip()  # quita las marcas "(*)" sueltas
        if texto:
            limpios.append({**p, "texto": texto})
    return limpios, registro


def limpiar_documento(paginas: list[dict], doc_id: str, reglas: dict) -> tuple[list[dict], Counter, list[dict]]:
    """Aplica R1–R7 a un documento. Devuelve (paginas_limpias, contador_de_reglas, registro_de_versiones)."""
    contador = Counter()
    con_notas = doc_id in reglas["documentos_con_notas_de_version"]
    parrafos = []
    for pag in paginas:
        texto = limpiar_ruido_pagina(pag["texto"], reglas, contador)
        for par in partir_parrafos(texto, con_lineas_en_blanco=con_notas):
            if re.match(reglas["concordancias"], par):
                contador["R5_concordancias"] += 1
                continue
            parrafos.append({"pagina": pag["pagina"], "texto": par})

    registro = []
    if con_notas:
        parrafos, registro = aplicar_notas_de_version(parrafos, reglas["ventana_busqueda_texto_antiguo"], contador)

    # Volver a agrupar por página (el número de página nunca se perdió)
    por_pagina = {}
    for par in parrafos:
        por_pagina.setdefault(par["pagina"], []).append(par["texto"])
    limpias = [{"pagina": n, "texto": "\n\n".join(por_pagina[n])} for n in sorted(por_pagina)]
    return limpias, contador, registro
