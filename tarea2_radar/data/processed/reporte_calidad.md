# Reporte de calidad de datos (Tarea 2, Fase 2)

Corpus: 20,476 procesos (jun–ago 2026). Ninguna fila se borra: se marcan, se corrigen si es posible o se excluyen del análisis con motivo.

| Regla | Casos detectados | Qué se hizo | Resultado |
|---|---|---|---|
| R1a. Mismo ocid repetido | 0 | deduplicación por ocid en la Fase 1 | — |
| R1b. Mismo tender_id con distinto ocid (proceso registrado dos veces) | 4 filas (2 procesos) | se conserva el de compiledRelease más reciente; la copia queda con `incluir_en_analisis=False` | 2 excluidos con motivo |
| R1c. Misma nomenclatura y entidad, distinto ocid (posible reconvocatoria) | 2,241 filas en 1,072 grupos | **se conservan** con advertencia; `tipo_repeticion` y `es_version_vigente` | A reconvocatoria confirmada: 647 · C re-registro mismo día: 365 · B ítems distintos (no es repetición): 44 · D indeterminado: 16 grupos |
| R2. Monto faltante o cero | 2,167 (monto nulo 0, monto 0: 2,120, moneda extranjera sin conversión a soles: 47) | se recupera con el monto adjudicado; el resto `monto_valido=False` (fuera de sumas de monto, dentro de conteos) | 38 recuperados (tasa 1.8%); 2,129 con advertencia |
| R2c. amount_PEN = 0 con monto en soles > 0 | 113 | se usa el monto en soles de la convocatoria | corregidos |
| R2b. Moneda extranjera | 334 (USD 303, EUR 23, GBP 8) | `monto_pen` = amount_PEN publicado por OECE | 271/334 convertidos; 63 con amount_PEN = 0 (cuentan en R2) |
| R3. Sin descripción | 0 | se recupera con la descripción de ítems si existe | 0 recuperados; 4 descripciones muy cortas con advertencia |
| R4. Codificación y tildes (JUNÍN vs JUNIN) | variantes por tildes/espacios: departamento 0, provincia 0, entidad 0; **5,564 descripciones con comillas “ ” perdidas y publicadas como '¿'**; 2 con mojibake ('Â'); 347 con '\n' escrito como texto; 594 nombres con espacios dobles | comparación con clave sin tildes/mayúsculas; '¿' sin '?' → comillas (7 con pregunta real no se tocan); se quita 'Â' y el '\n' literal; espacios normalizados | corregidos (ej.: `¿CONTRATACIÓN DEL SERVICIO DE MANTENIMIENTO CORRECTIVO DE ELEMENTOS NO ESTRUCTURALES, COBE` → `"CONTRATACIÓN DEL SERVICIO DE MANTENIMIENTO CORRECTIVO DE ELEMENTOS NO ESTRUCTURALES, COBE`) |
| R5a. `department` no es un departamento válido | 0 | respaldo: provincia → distrito → misma entidad | — |
| R5b. Campo `region` con provincias (no departamentos) | 20,476 | no se usa como departamento; se valida contra el IGN | inconsistencias department vs provincia: 0 |
| R5c. Provincia escrita distinto que en el IGN | 92 (NAZCA→NASCA) | alias documentado en config.yaml | corregidos |
| R5d. Sin departamento al final | 0 | — | **tasa de ubicación 100.0%** (25 departamentos) |
| R6. Número de postores faltante | 2,750 (3 con adjudicación) | se conserva; se trata en la Fase 5 | — |

**Ubicación por fuente:** {'department': 20476}. Campo usado: parties[rol=buyer].address.department (dirección de la entidad compradora).

**Novedades recientes (API, septiembre 2026, aparte):** 5,435 procesos; departamento recuperado por la misma entidad del corpus en 5,277 (**tasa de recuperación 97.1%**); 158 sin ubicar (la búsqueda de la API no trae la dirección y la entidad no aparece en junio-agosto). tabla aparte 'novedades recientes'; NO entra al corpus ni a los indicadores.

**Resumen:** 20,474 procesos incluidos en el análisis; 2 excluidos con motivo; 3,956 con alguna advertencia.

## Verificación de posibles reconvocatorias (ejemplos)

**A_reconvocatoria_confirmada**

| ocid | fecha | estados | monto | vigente | descripción |
|---|---|---|---|---|---|
| ocds-dgv273-seacev3-1200987 | 2026-08-14 | NULO | 603,426.19 | no | EJECUCION DE LA OBRA:CREACIÓN DEL SERVICIO DE AGUA POTABLE RURAL Y CREACIÓN DEL  |
| ocds-dgv273-seacev3-1244498 | 2026-08-26 | APELADO | 603,426.19 | sí | EJECUCION DE LA OBRA:CREACIÓN DEL SERVICIO DE AGUA POTABLE RURAL Y CREACIÓN DEL  |

| ocid | fecha | estados | monto | vigente | descripción |
|---|---|---|---|---|---|
| ocds-dgv273-seacev3-1214519 | 2026-06-03 | NULO | 243,397.50 | no | CONTRATACION DE CEMENTO PORTLAND TIPO HS CON ALTA RESISTENCIA A LOS SULFATOS PAR |
| ocds-dgv273-seacev3-1223670 | 2026-06-09 | CONTRATADO | 243,397.50 | sí | CONTRATACION DE CEMENTO PORTLAND TIPO HS CON ALTA RESISTENCIA A LOS SULFATOS PAR |

**B_items_distintos_misma_nomenclatura**

| ocid | fecha | estados | monto | vigente | descripción |
|---|---|---|---|---|---|
| ocds-dgv273-seacev3-1222632 | 2026-06-05 | CONVOCADO | 0.00 | sí | "Adquisición de motoniveladora y retroexcavadora" en el marco de la IOARR "ADQUI |
| ocds-dgv273-seacev3-1228906 | 2026-06-05 | CONTRATADO | 526,400.00 | sí | ADQUISICIÓN DE RETROEXCAVADORA PARA LA IOARR DENOMINADA "ADQUISICION DE MOTONIVE |

| ocid | fecha | estados | monto | vigente | descripción |
|---|---|---|---|---|---|
| ocds-dgv273-seacev3-1223445 | 2026-06-09 | CONVOCADO | 0.00 | sí | UISICION DE AGUJA ESPINAL DESCARTABLE PARA EL DEPARTAMENTO DE FARMACIA DEL HOSPI |
| ocds-dgv273-seacev3-1223493 | 2026-06-09 | DESIERTO | 49,980.00 | sí | ADQUISICION DE AGUJA ESPINAL DESCARTABLE PARA EL DEPARTAMENTO DE FARMACIA DEL HO |

**C_reregistro_mismo_dia**

| ocid | fecha | estados | monto | vigente | descripción |
|---|---|---|---|---|---|
| ocds-dgv273-seacev3-1218760 | 2026-08-18 | CONVOCADO | 0.00 | no | ADQUISICIÓN DE MATERIAL, INSUMOS, INSTRUMENTAL Y ACCESORIOS MÉDICOS PARA LA ATEN |
| ocds-dgv273-seacev3-1243247 | 2026-08-18 | CONSENTIDO | 72,545.45 | sí | ADQUISICIÓN DE MATERIAL, INSUMOS, INSTRUMENTAL Y ACCESORIOS MÉDICOS PARA LA ATEN |

| ocid | fecha | estados | monto | vigente | descripción |
|---|---|---|---|---|---|
| ocds-dgv273-seacev3-1218919 | 2026-06-02 | CONVOCADO | 0.00 | no | "CONTRATACIÓN DEL SERVICIO DE MANTENIMIENTO CORRECTIVO DE ELEMENTOS NO ESTRUCTUR |
| ocds-dgv273-seacev3-1225289 | 2026-06-02 | CONTRATADO | 58,250.00 | sí | "CONTRATACIÓN DEL SERVICIO DE MANTENIMIENTO CORRECTIVO DE ELEMENTOS NO ESTRUCTUR |

**D_indeterminado**

| ocid | fecha | estados | monto | vigente | descripción |
|---|---|---|---|---|---|
| ocds-dgv273-seacev3-1223866 | 2026-06-10 | CONVOCADO | 0.00 | no | EJECUCION DE OBRA: MEJORAMIENTO DEL SERVICIO DE MOVILIDAD URBANA EN EL JIRON MAR |
| ocds-dgv273-seacev3-1229907 | 2026-07-01 | CONVOCADO | 0.00 | sí | EJECUCION DE OBRA: MEJORAMIENTO DEL SERVICIO DE MOVILIDAD URBANA EN EL JIRON MAR |

| ocid | fecha | estados | monto | vigente | descripción |
|---|---|---|---|---|---|
| ocds-dgv273-seacev3-1223890 | 2026-06-19 | CONVOCADO | 5,727,335.87 | no | obra "MEJORAMIENTO DEL SERVICIO DE SEGURIDAD CIUDADANA LOCAL EN LA CIUDAD DE TAY |
| ocds-dgv273-seacev3-1229271 | 2026-06-27 | CONTRATADO | 5,727,335.87 | sí | obra "MEJORAMIENTO DEL SERVICIO DE SEGURIDAD CIUDADANA LOCAL EN LA CIUDAD DE TAY |

