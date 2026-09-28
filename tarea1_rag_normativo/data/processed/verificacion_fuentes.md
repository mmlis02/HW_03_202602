# Verificación de fuentes (Tarea 1, Fase 1)

Página sin texto = menos de 200 caracteres extraíbles.
orden_* = % de veces que el número de 'Artículo N.' siguiente es mayor o igual al anterior (en todo el PDF y solo en el texto de la norma, tras recortar las normas vecinas).

| id | paginas_pdf | paginas_con_texto_de_la_norma | chars_pagina_min | chars_pagina_mediana | chars_pagina_max | paginas_sin_texto | chars_de_otras_normas | articulos_detectados | orden_pdf_completo | orden_solo_la_norma | paginas_con_encabezado_elperuano | ligaduras_rotas | usable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ley32069 | 63 | 63 | 1234 | 3546 | 4268 | ninguna | 0 | 101 | 99% | 99% | 0 | 0 | SÍ |
| ds001_2026_ef | 16 | 16 | 6446 | 6980 | 8093 | ninguna | 6272 | 116 | 97% | 98% | 16 | 0 | SÍ, recortando otras normas |
| dl1715 | 2 | 2 | 6377 | 6659 | 6942 | ninguna | 6039 | 5 | 70% | revisión manual (pocos artículos) | 2 | 0 | SÍ, recortando otras normas |
| ley32069_original | 36 | 36 | 390 | 6451 | 6923 | ninguna | 0 | 101 | 99% | 99% | 36 | 411 | SÍ |
