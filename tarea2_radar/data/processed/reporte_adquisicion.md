# Reporte de adquisición y deduplicación (Tarea 2, Fase 1)

| Archivo (mes) | Records (procesos) | Releases listadas |
|---|---|---|
| 2026-06 | 7,321 | 95,257 |
| 2026-07 | 6,570 | 102,597 |
| 2026-08 | 6,585 | 90,694 |

- Filas antes de deduplicar (3 meses juntos): **20,476**
- ocid distintos: **20,476**
- ocid que aparecen en más de un mes: **0** (de ellos, con datos distintos entre meses: 0)
- Duplicados dentro de un mismo mes: 0
- Filas después (una por ocid): **20,476** (0 eliminadas)
- Regla: se conserva la fila con compiledRelease más reciente (fecha_compilado); desempates: más releases, mes de archivo más reciente.
