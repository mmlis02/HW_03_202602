# Similitud top-1 de las 25 preguntas (e5small_c500)

Umbral elegido: **0.835** (defensa 1, sin IA). Ordenadas de mayor a menor similitud.

| # | id | Tipo | Similitud top-1 | Pregunta | Defensa 1 (umbral) |
|---|---|---|---|---|---|
| 1 | D14 | dentro | 0.9209 | ¿Cuándo se declara desierto un procedimiento de selección? | pasa ✅ |
| 2 | D07 | dentro | 0.9168 | ¿Pueden las micro y pequeñas empresas emitir facturas negociables al contratar con el Estado y por qué plazo máximo? | pasa ✅ |
| 3 | D10 | dentro | 0.8935 | Según la modificación del Reglamento, ¿quién revisa los requisitos de calificación en los procedimientos evaluados por jurados? | pasa ✅ |
| 4 | D08 | dentro | 0.8931 | ¿Procede una medida cautelar para paralizar la ejecución de una obra de infraestructura hidráulica? | pasa ✅ |
| 5 | D15 | dentro | 0.8861 | ¿Qué contracautela puede ofrecer una micro o pequeña empresa que solicita una medida cautelar? | pasa ✅ |
| 6 | D09 | dentro | 0.8859 | ¿Qué norma incorporó la infraestructura hidráulica entre las obras en que no proceden medidas cautelares, y con qué finalidad? | pasa ✅ |
| 7 | D12 | dentro | 0.8742 | ¿Qué formación mínima se exige para certificarse como comprador público? | pasa ✅ |
| 8 | D03 | dentro | 0.8724 | Ya entregué todo y me dieron el visto bueno, ¿cuánto se pueden demorar en pagarme? | pasa ✅ |
| 9 | F06 | fuera | 0.8712 | Me dieron la buena pro, ¿en cuántos días tengo que presentar los papeles para firmar el contrato? | **pasa → defensa 2 (IA)** |
| 10 | D11 | dentro | 0.8662 | ¿Cuál es el tope de penalidades en un contrato menor? | pasa ✅ |
| 11 | D05 | dentro | 0.8649 | Perdí una licitación y creo que fue injusto. Si soy pequeña empresa, ¿cuánta plata tengo que dejar para reclamar? | pasa ✅ |
| 12 | D02 | dentro | 0.8602 | Si una municipalidad quiere comprarme algo chiquito, de unos 3 mil soles, ¿igual tiene que hacer licitación? | pasa ✅ |
| 13 | D04 | dentro | 0.8596 | La entidad se está atrasando con mi pago, ¿puedo cobrarles algo extra por la demora? | pasa ✅ |
| 14 | D06 | dentro | 0.8584 | ¿El Estado me puede dar parte del pago por adelantado para comprar los materiales? ¿Cuánto como máximo? | pasa ✅ |
| 15 | D13 | dentro | 0.8574 | ¿Qué es la Pladicop? | pasa ✅ |
| 16 | F03 | fuera | 0.8552 | Ya entregué los productos, ¿cuántos días tienen para revisarlos y darme el ok? | **pasa → defensa 2 (IA)** |
| 17 | F02 | fuera | 0.8517 | ¿Cómo se calcula la penalidad diaria por mora en un contrato de bienes? | **pasa → defensa 2 (IA)** |
| 18 | D01 | dentro | 0.8398 | Recién formalicé mi negocio, ¿qué trámite tengo que hacer para poder venderle al Estado? | pasa ✅ |
| 19 | F01 | fuera | 0.8382 | ¿Puedo pasarle parte del trabajo a otra empresa? ¿Hasta cuánto? | **pasa → defensa 2 (IA)** |
| 20 | F04 | fuera | 0.8225 | ¿Cómo saco mi RUC en la SUNAT para mi negocio? | detenida ✅ |
| 21 | F07 | fuera | 0.8218 | ¿Cómo inscribo mi empresa en el REMYPE y qué beneficios tengo? | detenida ✅ |
| 22 | F09 | fuera | 0.8054 | ¿Cada cuántos kilómetros hay que cambiarle el aceite al carro? | detenida ✅ |
| 23 | F05 | fuera | 0.7982 | ¿Cómo se prepara un ceviche? | detenida ✅ |
| 24 | F10 | fuera | 0.7644 | ¿Qué equipo ganó la Copa América 2024? | detenida ✅ |
| 25 | F08 | fuera | 0.7533 | ¿Cuál es la capital de Australia? | detenida ✅ |

La pregunta legítima con menor similitud tiene **0.8398**. **3 preguntas fuera del corpus la superan**: F06 (0.8712), F03 (0.8552), F02 (0.8517). Ningún umbral puede detenerlas sin detener también preguntas legítimas: por eso existe la defensa 2.
