# Revisión contra el enunciado (28/09/2026)

Cada requisito de `docs/enunciado.md`, dónde se cumple y qué faltaba o falta. "Arreglado" = se corrigió en esta revisión final.

## Alcance obligatorio y arquitectura (Tarea 1)

| Requisito | Dónde se cumple | Estado |
|---|---|---|
| Corpus: los 2 documentos obligatorios + 1 opcional justificado | `tarea1_rag_normativo/config.yaml` (documentos), README T1 F1 | ✅ (D.Leg. 1715 como opcional) |
| Solo fuentes oficiales y fecha de descarga | `data/manifiesto_descargas.json`, README T1 F1 | ✅ |
| Dos procesos separados (offline/online); el online no relee PDFs | `build_index.py` / `src/motor.py` | ✅ |
| Un motor con una función y resultado estructurado | `src/motor.py` → `responder()` | ✅ |
| El motor no importa librerías de UI + comando de verificación en el README | README T1 F3 (grep) | ✅ |
| Todo en config (rutas, modelos, tamaños, umbrales, prompts, mensajes); credenciales en .env | `config.yaml`, `.env.example` | ✅ **Arreglado:** los textos de `app.py` se movieron a `config.yaml > app.textos` |
| Log de cada llamada (fecha, modelo, tokens, latencia, costo, éxito) | `logs/costos_llm.csv`, `comun/costos.py`, `comun/llm.py` | ✅ |
| Diagrama Mermaid en el README | README "Tarea 1 — Pipeline", `docs/pipeline.md` | ✅ |

## Tarea 1 por fase

| Fase / requisito | Dónde | Estado |
|---|---|---|
| F1 Verificación de fuentes (páginas, chars, páginas sin texto, orden, ¿usable?) | `scripts/verificar_fuentes.py`, `data/processed/verificacion_fuentes.md` | ✅ |
| F1 Página desde el primer paso + por qué unir y cortar pierde citas | `src/extraccion.py`, README T1 F1 | ✅ |
| F1 Limpieza documentada con ejemplo antes/después | `src/limpieza.py`, `data/processed/ejemplos_limpieza.md` | ✅ |
| F1 Reporte de calidad por documento con muestra del medio | `data/processed/reporte_calidad_extraccion.md` | ✅ |
| F1 raw/ intacto, processed/ con página | `data/raw` (fuera de git), `data/processed/*.jsonl` | ✅ |
| F2 ≥2 configuraciones de tamaño y solape comparadas con evaluación | README T1 F2 (5 configuraciones) | ✅ |
| F2 Metadatos documento/versión/página; ID único y estable | `src/fragmentos.py` | ✅ |
| F2 Idempotente, reanudable, no pisa otros documentos (demostrado) | `src/indice.py`, `scripts/probar_indice.py`, `logs/prueba_indice.log` | ✅ |
| F2 Prefijos y longitud máxima del modelo | README T1 F2 | ✅ |
| F2 Fragmentos por documento y distribución de longitudes | `data/processed/reporte_fragmentos.md` | ✅ |
| F3 Abstención antes del LLM con umbral calibrado (barrido) y trade-off | `eval/barrido_umbral.py`, `eval/opciones_umbral.py`, README T1 F3 | ✅ |
| F3 Estrategia de versiones + ejemplo | README T1 F3 (4 capas, D08) | ✅ |
| F3 Límites del corpus + ejemplo | README T1 F3 (F06, F01) | ✅ |
| F3 Citas documento/página; prompt prohíbe salir del contexto | `config.yaml > prompts`, `src/motor.py` | ✅ |
| F3 Abstención como campo estructurado | `abstuvo`, `motivo_abstencion` | ✅ |
| F3 Errores de API como errores (y la UI los muestra) | `comun/llm.py`, `app.py` (st.error) | ✅ |
| F3 Precio según la hora de cada llamada + fuente y fecha | `config.yaml > precios`, `comun/costos.py` | ✅ |
| F4 ≥15 dentro (≥3 modificados, ≥5 estilo MYPE) + ≥5 fuera | `eval/preguntas.csv` (15 + 10) | ✅ |
| F4 Script Recall@1/3/5 y abstención sin LLM + qué etapa mide cada uno | `eval/evaluar_recuperacion.py`, `eval/evaluar_motor.py`, README T1 F4 | ✅ |
| F4 Comparación local vs text-embedding-3-small (Recall, tiempo, costo, latencia, dimensión) y elección argumentada | `eval/comparar_embeddings.py`, README T1 F4 | ✅ |
| F4 Interfaz común de embeddings, cambio por config | `comun/embeddings.py` | ✅ |
| F5 `streamlit run app.py` + pasos Windows (PyTorch CPU) | README instalación | ✅ (probado en macOS; los pasos de Windows no se probaron en una máquina Windows) |
| F5 Respuesta, fragmentos (doc, página, similitud), abstención, costo | `app.py` | ✅ |
| F5 Panel de calidad de extracción y resultados de evaluación | `app.py` (pestañas) | ✅ |
| F5 No reconstruye el índice al iniciar | `app.py` (`get_collection`) | ✅ |

## Tarea 2 por fase

| Fase / requisito | Dónde | Estado |
|---|---|---|
| F1 ≥3 archivos mensuales de 2026 | `scripts/descargar_datos.py` (jun–ago) | ✅ |
| F1 API solo para lo reciente, con pausas, errores y caché | `src/api_oece.py`, `scripts/probar_api.py` | ✅ |
| F1 Re-ejecutable, no descarga lo existente | `scripts/descargar_datos.py`, `logs/descargas.log` | ✅ |
| F1 Release vs record, ocid; una fila por proceso; antes/después | README T2 F1, `data/processed/reporte_adquisicion.md` | ✅ |
| F1 Log de tiempo, pedidos y tamaños | `logs/descargas.log`, `logs/api.log` | ✅ |
| F2 Repetidos, montos, descripciones, provincias, tildes | `src/validacion.py`, `data/processed/reporte_calidad.md` | ✅ |
| F2 25 departamentos con regla explícita; cuántos sin ubicar y por qué | `src/territorio.py`, README T2 F2 | ✅ |
| F2 Reporte por regla: casos, acción, recuperación | `reporte_calidad.md` | ✅ |
| F3 Índice de descripciones con metadatos estructurados | `src/indice.py`, `build_index.py` | ✅ |
| F3 Numéricos y territoriales como filtros + por qué | `src/motor.py`, README T2 F3 | ✅ |
| F3 Reutiliza la abstención de la Tarea 1; transferencia del umbral y recalibración | `comun/`, `eval/barrido_umbral.py`, README T2 F3 | ✅ |
| F3 Respuesta cita cada proceso por ocid | `src/motor.py` (validación de ocid) | ✅ |
| F3 ≥10 preguntas con relevantes conocidos y Recall@k | `eval/definiciones.yaml` (16 + 1 + 8), `eval/evaluar_recuperacion.py` | ✅ |
| F4 KPIs con indicador de riesgo, se actualizan con filtros | `app.py` | ✅ |
| F4 Mapa coroplético con leyenda y tooltips | `app.py` (pestaña Mapa) | ✅ |
| F4 Caja de preguntas con procesos y similitud | `app.py` (pestaña Preguntar) | ✅ |
| F4 Tabla ordenable con descarga CSV | `app.py` (pestaña Tabla) | ✅ |
| F4 Vista de distribución (seaborn o gráficos nativos) | `app.py` (pestaña Distribución) | ✅ **Arreglado:** plotly → `st.bar_chart` nativo |
| F4 Panel de calidad de datos | `app.py` (pestaña Calidad) | ✅ |
| F4 Lee archivos precalculados; cache_data / cache_resource | `app.py` | ✅ |
| F4 Barra lateral: departamento, categoría, monto, fecha, umbral | `app.py` | ✅ |
| F4 Selección vacía sin errores | `app.py` (probado con AppTest) | ✅ |
| F5 Tasa de un postor por departamento y entidad; top 10 con mínimo justificado | `src/riesgo.py`, `scripts/calcular_riesgo.py`, README T2 F5 | ✅ |
| F5 Referencias leídas; "no es evidencia" explícito; sin nombres de personas | README T2 F5, `app.py`, `config.yaml > riesgo.aviso` | ✅ |
| Config: "sin rutas, umbrales ni mensajes en el código" | `config.yaml` | ✅ **Arreglado:** textos de `app.py`, parámetros del deslizador y archivos de datos entre etapas (`archivos:`) movidos a la config. Los reportes y logs conservan nombres fijos dentro de las carpetas configuradas (documentado). |

## Entregables

| Entregable | Dónde | Estado |
|---|---|---|
| Repositorio propio y público | https://github.com/mmlis02/HW_03_202602 (responde sin iniciar sesión) | ✅ |
| README: instalación Windows, descargas, comandos, diagramas, tablas de resultados de ambas tareas | README | ✅ **Arreglado:** se quitó "en construcción" y se agregaron "Resultados en resumen", "Regenerar todo desde cero" y la estructura actualizada |
| Costo real total | README "Costo real total" (202 llamadas, US$0,0243) | ✅ **Arreglado:** faltaba el total conjunto; también se corrigió el conteo de la Tarea 1 (145 llamadas, no 148) |
| Config por tarea | `*/config.yaml` | ✅ |
| .env.example sin credenciales; sin claves en el historial | `.env.example`, `.githooks/pre-commit` | ✅ (0 claves en todos los commits) |
| requirements.txt | raíz | ✅ |
| Reportes de calidad de ambas tareas y logs de ejecución | `*/data/processed/`, `*/logs/` | ✅ |
| Log de costos con llamadas reales | `*/logs/costos_llm.csv` | ✅ |
| Video ≤ 12 min enlazado en el README | README (espacio reservado) | ⏳ **Pendiente de la autora:** grabar y pegar el enlace |
| Commits distribuidos en el tiempo | historial git | ⚠️ 21 commits en 2 días (27 y 28/09). No se puede corregir sin falsificar fechas; se recomienda seguir commiteando los ajustes finales y el video en días siguientes |
