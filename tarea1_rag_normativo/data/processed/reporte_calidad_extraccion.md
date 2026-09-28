# Reporte de calidad de extracción (Tarea 1, Fase 1)

Generado por `scripts/procesar_documentos.py`. 'chars' = caracteres.

| Documento | Págs. PDF | Págs. conservadas | Págs. descartadas | chars PDF completo | chars de la norma (tras recorte) | chars limpios |
|---|---|---|---|---|---|---|
| ley32069 | 63 | 63 | 0 | 220,150 | 220,150 | 208,835 |
| ds001_2026_ef | 16 | 16 | 0 | 112,601 | 106,329 | 103,987 |
| dl1715 | 2 | 2 | 0 | 13,321 | 7,282 | 7,057 |

## ley32069 — Ley N.° 32069, Ley General de Contrataciones Públicas (versión actualizada al 19/07/2026)

- Páginas descartadas: ninguna (todas tienen texto de la norma).

Notas de versión "(*)": el PDF tiene **37 marcas "(*)"**, que corresponden a **20 notas** (líneas que empiezan con "(*)") más **17 marcas de llamada** (el "(*)" pegado al final del texto al que se refiere cada nota; los avisos de la primera página no tienen llamada).

| Tipo de nota | Cantidad |
|---|---|
| Numeral modificado | 6 |
| aviso de vigencia | 4 |
| Literal modificado | 4 |
| Disposición modificada | 2 |
| Literal incorporado | 1 |
| Numeral derogado | 1 |
| Numeral incorporado | 1 |
| fe de erratas | 1 |

Reglas de limpieza aplicadas:

- Párrafos de concordancias SPIJ eliminados: **1**
- Notas (*) partidas entre páginas unidas: **3**
- Avisos de vigencia conservados: **4**
- Modificaciones: texto antiguo eliminado, texto vigente etiquetado: **12**
- Incorporaciones etiquetadas: **2**
- Derogaciones: texto derogado eliminado: **1**
- Fe de erratas aplicada: **1**

Muestra del texto limpio (página 32, mitad del documento):

```text
Artículo 66. Adelantos

66.1. La entidad contratante puede entregar adelantos al contratista con la finalidad de otorgarle financiamiento o liquidez para la ejecución del contrato en las condiciones establecidas y fundamentadas en la estrategia de contratación.

66.2. El adelanto puede ser:

a) Directo. b) Para materiales e insumos, equipamiento y mobiliario. c) Otros que sean establecidos en el reglamento.

66.3. Los documentos del procedimiento de selección pueden establecer adelantos directos al contratista, los que en ningún caso exceden en conjunto del 30 % del monto del contrato original.

66.4. El reglamento establece las condiciones y demás criterios para otorgar los adelantos y para
```

## ds001_2026_ef — Decreto Supremo N.° 001-2026-EF, que modifica el Reglamento de la Ley N.° 32069

- Páginas descartadas: ninguna (todas tienen texto de la norma).

Reglas de limpieza aplicadas:

- Encabezado de página de El Peruano eliminado: **16**
- Sello 'Firmado por: Editora Peru' eliminado: **1**
- Código de publicación de cierre eliminado: **1**

Muestra del texto limpio (página 9, mitad del documento):

```text
“Artículo 194. Prestaciones adicionales de obra bajo el sistema de entrega solo construcción

(…)

194.3. No corresponde suscribir una adenda al contrato por la aprobación de la prestación adicional, bastando con su publicación en la Pladicop para que surta todos sus efectos. Se encuentra prohibida la aprobación de prestaciones adicionales en vía de regularización.

(…)”

“Artículo 195. Prestaciones adicionales de obra bajo el sistema de entrega diseño y construcción

(…)

195.2. La aprobación de las prestaciones adicionales en el componente de diseño se realiza conforme al numeral 193.1 del artículo 193.

(…)

195.4. No corresponde suscribir una adenda al contrato por la aprobación del adic
```

## dl1715 — Decreto Legislativo N.° 1715, que modifica el literal e) del numeral 85.1 del artículo 85 de la Ley N.° 32069

- Páginas descartadas: ninguna (todas tienen texto de la norma).

Reglas de limpieza aplicadas:

- Encabezado de página de El Peruano eliminado: **1**
- Sello 'Firmado por: Editora Peru' eliminado: **1**
- Código de publicación de cierre eliminado: **1**

Muestra del texto limpio (página 2, mitad del documento):

```text
ejecución de obras en salud, educación, infraestructura hidráulica, infraestructura vial y saneamiento, y la gestión y conservación por niveles de servicio para el mantenimiento vial”.

Artículo 4.- Refrendo El presente Decreto Legislativo es refrendado por el Presidente del Consejo de Ministros y la Ministra de Economía y Finanzas.

POR TANTO:

Mando se publique y cumpla, dando cuenta al Congreso de la República.

Dado en la Casa de Gobierno, en Lima, a los tres días del mes de febrero del año dos mil veintiséis.

JOSÉ ENRIQUE JERÍ ORÉ Presidente de la República ERNESTO JULIO ÁLVAREZ MIRANDA Presidente del Consejo de Ministros DENISSE AZUCENA MIRALLES MIRALLES Ministra de Economía y Finanza
```
