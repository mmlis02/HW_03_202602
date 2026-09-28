# Ejemplos de limpieza: antes y después

## R1 + R6 — Encabezado de El Peruano pegado al texto y líneas cortadas (D.S. 001-2026-EF, pág. 4)

**Antes (texto crudo del PDF):**

```text
36
NORMAS LEGALES
Jueves 8 de enero de 2026
 El Peruano 
/
“Artículo 72. Requisitos de calificación
(…)
72.2. Los evaluadores revisan los requisitos de 
calificación de las ofertas que sean admitidas. En el 
caso de procedimientos de selección evaluados por 
jurados, los requisitos de calificación son revisados 
por la DEC, para lo cual puede solicitar opinión a los 
miembros del jurado.
(…)”
“Artículo 75. Determinac
```

**Después (texto limpio):**

```text
“Artículo 72. Requisitos de calificación

(…)

72.2. Los evaluadores revisan los requisitos de calificación de las ofertas que sean admitidas. En el caso de procedimientos de selección evaluados por jurados, los requisitos de calificación son revisados por la DEC, para lo cual puede solicitar opinión a los miembros del jurado.
```

## Recorte + R3 — Fin de la norma y otra norma en la misma página (D.S. 001-2026-EF, pág. 16)

**Antes (texto crudo del PDF):**

```text
la Casa de Gobierno, en Lima, a los siete 
días del mes de enero del año dos mil veintiséis.
JOSÉ ENRIQUE JERÍ ORÉ
Presidente de la República
DENISSE AZUCENA MIRALLES MIRALLES
Ministra de Economía y Finanzas
2474920-3
Fijan índices de corrección monetaria para 
efectos de determinar el costo computable 
de los inmuebles enajenados por personas 
naturales, sucesiones indivisas o sociedades 
conyugales que optaron por tributar como 
tales
RESOLUCIÓN VICEMINISTERIAL
Nº 001-2026-EF/15.01
Lima, 6 de enero de 2026
CONSIDERANDO:
Que, mediante el artículo 21 del Texto Único Ordenado 
de la Ley del Impuesto a la Renta, aprobado por el Decreto 
Supremo Nº 179-2004-EF, se dispone que en el caso de 
en
```

**Después (texto limpio):**

```text
Dado en la Casa de Gobierno, en Lima, a los siete días del mes de enero del año dos mil veintiséis.

JOSÉ ENRIQUE JERÍ ORÉ Presidente de la República DENISSE AZUCENA MIRALLES MIRALLES Ministra de Economía y Finanzas
```

## R2 — Sello de firma digital (D.Leg. 1715, pág. 1)

**Antes (texto crudo del PDF):**

```text
(…)
e) No proceden las medidas cautelares destinadas a 
impedir, paralizar o retrasar el inicio o continuidad de la 
Firmado por: Editora Peru
Fecha: 04/02/2026 02:11
```

**Después (texto limpio):**

```text
(…)

e) No proceden las medidas cautelares destinadas a impedir, paralizar o retrasar el inicio o continuidad de la
```

## R7 — Versión: texto antiguo + nota '(*) modificado por' (Ley 32069 actualizada, pág. 43, art. 85.1.e)

**Antes (texto crudo del PDF):**

```text
e) No proceden las medidas cautelares destinadas a impedir, paralizar o retrasar el inicio o 
continuidad de la ejecución de obras en salud, educación, infraestructura vial y saneamiento, y 
la gestión y conservación por niveles de servicio para el mantenimiento vial.(*) 
 
(*) Literal modificado por el Artículo 3 del Decreto Legislativo N° 1715, publicada el 04 
febrero 2026, cuyo texto es el siguiente: 
 
"e) No proceden las medidas cautelares destinadas a impedir, paralizar o retrasar el inicio o 
continuidad de la ejecución de obras en salud, educación, infraestructura hidráulica, 
infraestructura vial y saneamiento, y la gestión y conservación por niveles de servicio para el 
mantenimiento vial.” 
  
85.2. En todo lo no previsto y, siempre que las referidas medidas cautelares no se opongan a la 
presente norma, se apli
```

**Después (texto limpio):**

```text
[Texto vigente — Literal modificado por el Artículo 3 del Decreto Legislativo N° 1715, publicada el 04 febrero 2026] "e) No proceden las medidas cautelares destinadas a impedir, paralizar o retrasar el inicio o continuidad de la ejecución de obras en salud, educación, infraestructura hidráulica, infraestructura vial y saneamiento, y la gestión y conservación por niveles de servicio para el mantenimiento vial.”

85.2.
```

## R4 — Ligaduras rotas (texto original de la ley, pág. 11; no aparece en el corpus final)

**Antes (texto crudo del PDF):**

```text
aboración de documentos del 
procedimiento de selección.
c. Caliﬁ cación o evaluación de 
ofertas.
d. Conformidad de los
```

**Después (texto limpio):**

```text
aboración de documentos del 
procedimiento de selección.
c. Calificación o evaluación de 
ofertas.
d. Conformidad de los
```
