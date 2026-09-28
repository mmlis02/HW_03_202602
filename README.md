# Vender al Estado — Asistente normativo (Tarea 1) y Radar de compras (Tarea 2)

Proyecto para una MYPE peruana que quiere venderle al Estado:

- **Tarea 1 — RAG normativo** (`tarea1_rag_normativo/`): responde preguntas sobre la Ley N.° 32069 y el D.S. N.° 001-2026-EF citando documento y página, y se abstiene cuando la respuesta no está en el corpus.
- **Tarea 2 — Radar RAG** (`tarea2_radar/`): datos abiertos de contrataciones de OECE (OCDS) validados, ubicados en un mapa por departamento y consultables en lenguaje natural con filtros más búsqueda semántica.

El enunciado completo está en [docs/enunciado.md](docs/enunciado.md). Las notas para el video están en [docs/notas_para_video.md](docs/notas_para_video.md).

> Estado: en construcción. Cada fase agrega su sección a este README.

## Instalación en Windows (paso a paso)

Probado con **Python 3.14.7**. En Windows:

1. Instala Python desde https://www.python.org/downloads/windows/ y marca **"Add python.exe to PATH"** durante la instalación.
2. Abre **PowerShell** en la carpeta del proyecto:
   ```powershell
   git clone https://github.com/mmlis02/HW_03_202602.git
   cd HW_03_202602
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   ```
   Si PowerShell bloquea la activación, ejecuta una vez: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
3. Instala **PyTorch solo CPU** primero; así no se descargan los paquetes de GPU, que pesan varios GB:
   ```powershell
   pip install torch --index-url https://download.pytorch.org/whl/cpu
   ```
4. Instala el resto:
   ```powershell
   pip install -r requirements.txt
   ```
5. Credenciales: copia `.env.example` como `.env` y pon tu clave de OpenAI:
   ```powershell
   copy .env.example .env
   notepad .env
   ```

6. (Recomendado) Activa la revisión automática que bloquea commits con claves de API o archivos `.env`:
   ```powershell
   git config core.hooksPath .githooks
   ```

En macOS/Linux los pasos son iguales, con `python3 -m venv .venv` y `source .venv/bin/activate`. El paso 3 no hace falta en Mac, porque la versión por defecto ya es solo CPU.

## Datos grandes fuera de git

Los PDFs originales, los archivos mensuales de OECE y los índices vectoriales **no se suben al repositorio**; ver `.gitignore`. Cada tarea tiene un script de descarga (`scripts/`) que los vuelve a bajar y que no repite lo que ya existe. Los detalles se agregarán en cada fase.

## Tarea 1 — Fase 1: fuentes, extracción y limpieza

### Corpus

| id | Documento | Institución y formato | Publicación | Rol |
|---|---|---|---|---|
| `ley32069` | Ley N.° 32069, Ley General de Contrataciones Públicas, **versión actualizada al 19/07/2026** | OECE en gob.pe (compilación basada en el SPIJ), PDF de texto corrido | ley: 24/06/2024; versión: 19/07/2026 | norma principal |
| `ds001_2026_ef` | Decreto Supremo N.° 001-2026-EF, que modifica el Reglamento de la Ley 32069 | MEF, publicado en El Peruano (PDF del diario, varias columnas) | 08/01/2026 | norma modificatoria (del Reglamento) |
| `dl1715` | Decreto Legislativo N.° 1715, que modifica el art. 85.1.e) de la Ley 32069 | Poder Ejecutivo, publicado en El Peruano | 04/02/2026 | **documento opcional**: norma modificatoria de la propia ley |

Las URLs exactas, la fecha de descarga (27/09/2026) y la huella sha256 de cada PDF están en [`tarea1_rag_normativo/config.yaml`](tarea1_rag_normativo/config.yaml) y en [`tarea1_rag_normativo/data/manifiesto_descargas.json`](tarea1_rag_normativo/data/manifiesto_descargas.json).

Para volver a descargarlos (no repite lo que ya existe):

```bash
cd tarea1_rag_normativo
python scripts/descargar_fuentes.py
```

### Verificación de fuentes (hecha antes de construir el resto)

```bash
python scripts/verificar_fuentes.py   # escribe data/processed/verificacion_fuentes.md y .csv
```

| Documento | Págs. PDF | Caracteres por página (mín / mediana / máx) | Págs. sin texto | Caracteres de otras normas recortados | Orden de lectura* | ¿Se puede usar? |
|---|---|---|---|---|---|---|
| `ley32069` (actualizada 19/07/2026) | 63 | 1.234 / 3.546 / 4.268 | ninguna | 0 | 99 % | **SÍ** |
| `ds001_2026_ef` | 16 | 6.446 / 6.980 / 8.093 | ninguna | 6.272 (pág. 16) | 98 % | **SÍ, recortando otras normas** |
| `dl1715` | 2 | 6.377 / 6.659 / 6.942 | ninguna | 6.039 (págs. 1–2) | revisión manual: correcto** | **SÍ, recortando otras normas** |
| `ley32069_original` (24/06/2024) — *revisada, no usada* | 36 | 390 / 6.451 / 6.923 | ninguna | 0 | 99 % | SÍ (descartada por la decisión de abajo) |

\* Porcentaje de veces que el siguiente "Artículo N." tiene un número mayor o igual al anterior. Los pocos saltos hacia atrás son citas a otros artículos.
\*\* El D.Leg. 1715 tiene solo 5 artículos, y uno es el "Artículo 85" de la ley que cita. Con tan pocos artículos, la medida no es confiable, así que el texto se leyó completo a mano.

**Hallazgo:** El Peruano imprime varias normas en la misma página. El PDF del D.S. 001-2026-EF trae en su página 16 la R.VM. N.° 001-2026-EF/15.01, y el del D.Leg. 1715 comparte páginas con el final de otra norma y con el D.Leg. 1716. **Regla:** cada norma de El Peruano termina con su código de publicación en una línea sola (por ejemplo `2474920-3`). Se recorta en ese código, y la regla está en `config.yaml` (`recorte`). Las páginas conservan su número original del PDF.

### ¿Por qué la versión actualizada de la ley y no el texto original? (opción B)

Se verificaron ambas y las dos son legibles. Se eligió la **versión actualizada al 19/07/2026** por tres razones:

1. **Es la versión vigente.** Desde 2024, la ley fue modificada por las Leyes 32103, 32187, 32515 y 32732 y por el D.Leg. 1715. Con el texto original, el asistente respondería con artículos que ya no rigen, que es justo el error de "texto original ya modificado" que pide evitar el enunciado.
2. **Es oficial.** La publica OECE, el organismo rector, en gob.pe, dentro de la colección de la Ley 32069 que enlaza el enunciado. No es una consolidación de un portal jurídico privado, que el enunciado no acepta.
3. **Marca cada cambio.** Junto a cada artículo modificado trae una nota "(\*) Literal modificado por el Artículo 3 del Decreto Legislativo N° 1715, publicada el 04 febrero 2026, cuyo texto es el siguiente: …". Eso permite decirle al usuario qué norma cambió el texto y desde cuándo.

**Riesgo conocido:** esta versión conserva el texto antiguo junto al nuevo. Se trata con la regla R7 (ver más abajo).

Sobre el D.Leg. 1715 como documento opcional: su contenido ya está incorporado en la versión actualizada, pero se incluye porque es la **norma modificatoria original**, con su propia fecha, finalidad y vigencia. Así se pueden hacer preguntas de versión ("¿qué norma agregó la infraestructura hidráulica y cuándo?") y citar la fuente primaria.

### Extracción y limpieza

```bash
python scripts/procesar_documentos.py
```

Salidas en `tarea1_rag_normativo/data/processed/`:

| Archivo | Contenido |
|---|---|
| `<id>.jsonl` | una línea por página: `documento`, `pagina` (número de página del PDF) y `texto` limpio |
| `reporte_calidad_extraccion.md` / `.json` | páginas, caracteres, páginas descartadas y por qué, reglas aplicadas y una muestra de la mitad de cada documento |
| `ejemplos_limpieza.md` | ejemplos **antes/después** de cada regla |
| `versiones_ley32069.json` | cada nota "(\*)" de la ley: qué texto antiguo se quitó y qué texto quedó vigente |

**Cómo se conserva la página desde el primer paso.** `src/extraccion.py` lee el PDF **página por página** y cada texto sale como `{"pagina": n, "texto": ...}`. El recorte de otras normas, la limpieza y la división en párrafos trabajan siempre sobre esa lista. Un párrafo que cruza de una página a otra se deja partido en dos, uno por página. Nunca se une el documento entero en un solo texto.

Si se unieran todas las páginas en un solo string para cortarlo después, los cortes ya no coincidirían con los saltos de página. Habría que adivinar la página de cada fragmento contando caracteres, y cualquier cambio de longitud durante la limpieza (quitar encabezados o notas) desplaza esa cuenta. El resultado serían citas a páginas equivocadas.

**Reglas de limpieza** (patrones en `config.yaml > limpieza`, código en `src/limpieza.py`):

| Regla | Qué quita o corrige | ley32069 | ds001_2026_ef | dl1715 |
|---|---|---|---|---|
| Recorte | texto de otras normas en la misma página de El Peruano (por código de publicación) | 0 | 6.272 chars | 6.039 chars |
| R1 | encabezado de página de El Peruano (n.° de página, "NORMAS LEGALES", fecha, "El Peruano /") | 0 | 16 | 1 |
| R2 | sello "Firmado por: Editora Peru / Fecha: …" | 0 | 1 | 1 |
| R3 | código de publicación que cierra la norma (`2474920-3`) | 0 | 1 | 1 |
| R4 | ligaduras rotas ("Caliﬁ cación" → "Calificación") | 0 | 0 | 0 |
| R5 | párrafos "CONCORDANCIAS:" del SPIJ | 1 | 0 | 0 |
| R6 | re-armado de líneas cortadas por el ancho de columna, incluidas líneas de una sola palabra | todas | todas | todas |
| R7 | notas de versión "(\*)" (ver abajo) | 20 notas | — | — |

R4 no se aplica en el corpus final. Se escribió para el texto original de la ley, que tenía 411 ligaduras rotas, y se deja activa por si se agrega otro PDF de El Peruano. Los ejemplos antes/después están en [`ejemplos_limpieza.md`](tarea1_rag_normativo/data/processed/ejemplos_limpieza.md). Un ejemplo de R1 + R6:

```text
ANTES:  36\nNORMAS LEGALES\nJueves 8 de enero de 2026\n El Peruano \n/\n“Artículo 72. Requisitos de calificación\n(…)\n72.2. Los evaluadores revisan los requisitos de \ncalificación de las ofertas que sean admitidas. En el \ncaso de ...
DESPUÉS: “Artículo 72. Requisitos de calificación

         (…)

         72.2. Los evaluadores revisan los requisitos de calificación de las ofertas que sean admitidas. En el caso de ...
```

### Versiones: cómo se evita responder con el texto antiguo (capa 1 de 4)

La versión actualizada trae, por ejemplo, el literal 85.1.e) **antiguo** terminado en "(\*)", seguido de "(\*) Literal modificado por el Artículo 3 del Decreto Legislativo N° 1715, publicada el 04 febrero 2026, cuyo texto es el siguiente: "e) … infraestructura hidráulica …"". La regla R7 recorre las 20 notas de la ley:

| Tipo de nota | Casos | Qué se hace |
|---|---|---|
| modificado | 12 | se **borra del índice** el texto antiguo (desde el párrafo que empieza con la misma etiqueta que el texto nuevo, p. ej. `e)`, `41.1`, `VIGÉSIMA NOVENA.`, hasta la marca "(\*)") y queda `[Texto vigente — Literal modificado por …, publicada el …] "e) …"` |
| incorporado | 2 | el texto ya es el nuevo; se agrega `[Literal incorporado por …]` |
| derogado | 1 | se borra el numeral 67.8 y queda `[Numeral 67.8 derogado por la … Ley N° 32103 …]` |
| "De conformidad con…" | 4 | aviso de vigencia; se conserva como `[Nota de vigencia] …` |
| fe de erratas SPIJ | 1 | se corrige "vretirado" → "retirado" en el art. 94 k) |

Tres notas empezaban al final de una página y seguían en la siguiente. Se unen, y el texto vigente se cita con la página donde realmente está. Las 12 modificaciones ubicaron su texto antiguo (0 casos sin resolver) y no quedan marcas "(\*)" en el texto limpio. El detalle de cada caso está en `versiones_ley32069.json`.

Las otras tres capas se implementan en las fases 2–4: metadatos `modificado_por`/fecha en cada fragmento, instrucciones en el prompt y preguntas de evaluación sobre artículos modificados.

## Estructura

```
├── README.md
├── requirements.txt
├── .env.example
├── docs/                    # enunciado, diagramas, notas para el video
├── tarea1_rag_normativo/    # config.yaml, build_index.py, app.py, src/, eval/, data/, logs/
└── tarea2_radar/            # config.yaml, app.py, src/, eval/, data/, logs/
```
