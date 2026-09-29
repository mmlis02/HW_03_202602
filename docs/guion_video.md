# Guion del video (12 minutos)

Sigue la estructura sugerida del enunciado. **No se muestra código antes del minuto 9:30**: primero el problema y los diagramas.

Cada bloque indica **qué decir** (en palabras simples, para leer o parafrasear) y **qué mostrar en pantalla**. Los seis puntos que el enunciado exige decir están marcados con **[OBLIGATORIO]**.

**Antes de grabar:**
- Abre las dos apps (Tarea 1 en http://localhost:8501 y Tarea 2 en http://localhost:8502) y haz una pregunta de calentamiento en cada una. La primera pregunta tarda porque carga el modelo.
- Ten abiertos `docs/pipeline.md` (diagramas), el README (tablas) y `eval/resultados/barrido_umbral*.png`.
- Cierra `.env`: no debe aparecer en pantalla.

---

## 0:00 – 1:00 · El problema y el usuario
**Pantalla:** una diapositiva con dos frases: "No entiende las reglas" y "No ve las oportunidades".

> "Una MYPE peruana quiere venderle al Estado, pero tiene dos problemas. Primero, no entiende las reglas: la ley de contrataciones es larga, técnica y cambia seguido, y pagar un abogado por cada duda cuesta más que muchos de los contratos. Segundo, no ve las oportunidades: cada mes se publican miles de procesos y nadie los lee todos.
> Construí dos herramientas. La primera responde preguntas sobre la ley citando documento y página. La segunda es un radar que muestra qué compra el Estado y dónde, y permite preguntar en lenguaje natural.
> Una idea guía las dos: un sistema que responde con seguridad y se equivoca es peor que no tener sistema. Por eso las dos saben cuándo **no** responder."

---

## 1:00 – 3:00 · Tarea 1: el pipeline (solo el diagrama)
**Pantalla:** el diagrama Mermaid de la Tarea 1 (`docs/pipeline.md`). Ve señalando cada caja mientras hablas.

**La parte que se hace una vez (offline):**
> "Arriba está lo que se hace **una sola vez**. Bajo los PDFs oficiales de gob.pe y El Peruano: la Ley 32069 en su versión actualizada al 19 de julio de 2026, el Decreto Supremo 001-2026-EF que modifica el Reglamento, y el Decreto Legislativo 1715 como documento extra.
> Leo cada PDF **página por página**. Limpio los encabezados de El Peruano y recorto las otras normas que el diario imprime en la misma página. Después corto el texto en 1.039 pedazos de 500 letras, convierto cada pedazo en una huella numérica con un modelo local y lo guardo en una base de datos."

**[OBLIGATORIO] Dónde vive el número de página y por qué:**
> "El número de página va pegado a cada pedazo **desde el primer paso**, como un dato aparte: un metadato, no parte del texto. Si juntara todo el documento en un solo texto y lo cortara después, tendría que adivinar la página contando letras. Al limpiar borro encabezados y notas, esa cuenta se descuadra y las citas saldrían mal. Además, el modelo nunca escribe la página: escribe 'fragmento 2', y el sistema pone la página desde el metadato. Así no la puede inventar."

**La parte que se hace en cada pregunta (online):**
> "Abajo está lo que pasa **en cada pregunta**. Nunca se vuelven a leer los PDFs: solo se consulta la base."

**[OBLIGATORIO] En qué punto decide no llamar a la IA:**
> "Busco los 5 pedazos más parecidos a la pregunta. **Antes de llamar a la IA** miro el parecido del mejor pedazo. Si está por debajo de 0,800, el sistema dice 'no tengo información' **sin llamar a la IA**, así que cuesta cero. Esa es la primera defensa. Si pasa, la IA recibe los 5 pedazos y tiene prohibido usar lo que 'sabe'. Si los pedazos no contienen el dato que se pide, marca 'fuera del corpus'. Esa es la segunda defensa."

---

## 3:00 – 4:30 · Tarea 2: el pipeline (solo el diagrama)
**Pantalla:** el diagrama Mermaid de la Tarea 2.

> "Para el radar bajé de OECE los archivos mensuales de junio, julio y agosto de 2026, en el estándar OCDS, y verifiqué cada uno con su huella SHA-256. La API la usé solo para lo nuevo, septiembre, con pausas y memoria para no perder nada si se corta.
> En OCDS, una **release** es una foto del proceso en un momento, un **record** junta todas las fotos de un proceso y el **ocid** es su número de identidad. Las 288.548 releases corresponden a 20.476 procesos. Después de quitar copias quedaron 19.616 procesos para el análisis."

**[OBLIGATORIO] Dónde vive el departamento y por qué:**
> "El departamento sale de la dirección de la **entidad que compra** y lo normalicé a los 25 departamentos con la tabla oficial del IGN. Igual que la página en la Tarea 1, se guarda como **metadato**, junto al monto, la fecha y la categoría, y no dentro del texto. Solo la descripción se compara por significado. Así puedo filtrar 'Cusco' o 'más de un millón' de forma exacta."

> "En cada pregunta, la IA **separa los filtros** (lugar, monto, fecha, categoría) del **tema**. Los filtros se aplican exactos, y solo entre los procesos que pasan se busca por significado. Si no queda ningún proceso, el sistema dice 'no hay procesos que cumplan esas condiciones', que es distinto de abstenerse. La primera defensa se aplica **después de filtrar**, con umbral 0,830. Luego la IA redacta citando cada proceso por su ocid."

---

## 4:30 – 6:30 · Decisiones técnicas con números
**Pantalla:** las tablas del README y los gráficos. Una tabla por decisión.

1. **Fuentes (tabla de verificación de la Tarea 1):**
   > "Antes de programar verifiqué cada PDF: páginas, letras por página, páginas sin texto y orden de lectura. El hallazgo: El Peruano imprime varias normas por página. El PDF del decreto traía en su última página otra resolución completa, y la recorté con el código de cierre de cada norma."

2. **Versiones:**
   > "La ley actualizada trae el texto viejo y, al lado, 'modificado por…' con el texto nuevo. Borré del índice el texto viejo de las 12 modificaciones y dejé el nuevo con una etiqueta. Por ejemplo, el artículo 85 ahora dice 'infraestructura hidráulica', con la nota del Decreto Legislativo 1715."

3. **Tamaño de pedazo (tabla de 5 configuraciones):**
   > "Probé 500, 1000 y 1800 letras y tres solapamientos. Elegí 500 con solape 150: trae la página correcta entre las 5 primeras en 14 de 15 preguntas. Pero cada pregunta vale 6,7 %, así que las diferencias son de una o dos preguntas y decidí mirando varios criterios juntos."

4. **Umbral (gráfico del barrido y tabla de puntajes):**
   > "Los parecidos no son intuitivos. El ceviche saca 0,79, casi igual que en la prueba del profesor. Peor todavía: tres preguntas del Reglamento sacan **más** que una pregunta legítima (0,879 frente a 0,845). Ningún umbral puede separarlas; por eso hacen falta dos defensas. Probé todos los umbrales y elegí 0,800: no bloquea ninguna pregunta legítima y deja margen para la demo."

5. **[OBLIGATORIO] Qué mide Recall@k y qué mide la abstención:**
   > "**Recall@k** mide el **buscador**: en cuántas preguntas la página correcta está entre los k pedazos que recibe la IA. En la Tarea 1, Recall@5 es 0,93. La **tasa de abstención** mide si el sistema sabe callarse: 'correcta' cuando se abstiene en una pregunta de fuera, 'incorrecta' cuando se abstiene en una legítima. Con IA: 10 de 10 correctas y 3 de 15 incorrectas. Recall y abstención por umbral se miden **sin llamar a la IA**, gratis, y por eso pude probar decenas de variantes."

6. **Embeddings (tabla local frente a OpenAI):**
   > "Comparé mi modelo local con el de OpenAI usando los mismos pedazos. OpenAI trae un poco más entre los 5 primeros (15 frente a 14), pero el local es 21 veces más rápido (14 frente a 303 milisegundos), funciona sin internet y las preguntas no salen de mi computadora. ¿Precio? Un millón de consultas con OpenAI costaría unos 43 centavos de dólar: ambos son casi gratis, así que el precio no decide."

7. **[OBLIGATORIO] Por qué los filtros no son embeddings (tabla de la Tarea 2):**
   > "Un modelo de significado no sabe que 200 mil es menos que 1 millón, ni que Cusco no es Puno. Lo medí: sin filtros, solo el 32 % de los primeros resultados cumplía lo pedido y Recall@5 era 0,69. Con filtros, el 100 % cumple y Recall@5 sube a 0,94. Y el umbral de la Tarea 1 no servía aquí, porque el ceviche sacaba 0,837, así que lo recalibré a 0,830."

---

## 6:30 – 9:30 · Demostración en vivo (las dos apps)

### Tarea 1 (≈ 1:30), en http://localhost:8501
Haz estas preguntas en orden y di lo que se ve:

| Pregunta | Qué mostrar / decir |
|---|---|
| "¿Cuánto tiempo tiene el Estado para pagarme después de entregar?" | Respuesta con **cita (Ley 32069 actualizada, pág. 32)**, los pedazos con su similitud y el **costo** (~US$0,0002). |
| Botón "¿Procede una medida cautelar para paralizar una obra de infraestructura hidráulica?" | La **nota de versión**: "Texto vigente: modificado por el Artículo 3 del Decreto Legislativo N° 1715…". |
| Botón "¿Qué porcentaje máximo de mi contrato puedo subcontratar?" | **La IA se abstiene** y explica que el porcentaje está en el Reglamento, que no está indexado. |
| Botón "¿Cómo se prepara un ceviche?" | Se abstiene **sin llamar a la IA**: similitud 0,792 frente al umbral 0,800; costo US$0. |

**[OBLIGATORIO] Qué no puede responder el corpus:**
> "Muchas preguntas reales se responden con el Reglamento completo, que no indexé. El decreto solo trae los artículos que cambia. Cuando la respuesta está ahí, el asistente lo **dice** en vez de improvisar, como con la subcontratación. Y si cita el decreto, agrega una nota: 'solo trae algunos artículos del Reglamento'."

Muestra rápido las pestañas "Calidad de extracción" y "Evaluación".

### Tarea 2 (≈ 1:30), en http://localhost:8502
| Acción | Qué mostrar / decir |
|---|---|
| Pestaña Mapa | Indicadores arriba: 19.616 procesos, monto total (con la nota "excluye 1.854 sin monto"), 25 departamentos, 1,1 % con un solo postor. Cambia a "Monto". |
| Barra lateral: elige Cusco | El mapa, los indicadores y la tabla cambian **sin llamar a la IA**. Vuelve a limpiar el filtro. |
| Preguntar: "Obras de agua potable y saneamiento en Cusco por más de un millón de soles" | La **tabla de filtros que extrajo la IA** (Cusco, Obras, 1.000.000), la respuesta con **ocid**, los procesos con similitud y el costo (~US$0,0004). |
| Preguntar: "Obras en Tumbes por más de 10 millones de soles" | **"No hay procesos que cumplan esas condiciones"**: no es una abstención. |
| Preguntar: "¿Cuál es la capital de Australia?" | Abstención por umbral, sin la IA que redacta. |
| Preguntar: "Compra de aviones de combate F-35" | **Limitación honesta:** la IA dice en el texto "ninguno corresponde a la compra de F-35", pero no marca la casilla de "fuera de tema". La caja neutra y la advertencia lo dejan visible. |
| Pestaña Riesgo | Lee el aviso en voz alta (ver abajo). Muestra el top 10 con sus intervalos. |
| Pestaña Tabla | Ordena por monto y señala "Descargar CSV". |

**Qué decir en la pestaña Riesgo:**
> "Entre las adjudicaciones de procedimientos **competitivos**, 134 de 11.833 tuvieron un solo postor: 1,1 %. Excluí la contratación directa, donde un solo postor es lo normal. Solo muestro entidades con al menos 10 procesos, porque la mitad tiene 3 o menos y una sola podría salir con '100 %' por un caso. **Una bandera roja es una razón para mirar con más atención, no es evidencia de irregularidad.** Solo aparecen entidades públicas, nunca personas."

---

## 9:30 – 10:30 · Código: solo lo que respalda las decisiones
**Pantalla:** el editor. Tres fragmentos, unos 20 segundos cada uno.

1. **`tarea1_rag_normativo/src/extraccion.py`, línea ~50** (`paginas.append({"pagina": n, ...})`) y **`src/fragmentos.py`, líneas ~91–97** (`"pagina"`, `"modificado_por"`):
   > "Aquí la página nace pegada al texto y viaja como metadato hasta cada pedazo, junto con 'modificado por'."
2. **`tarea1_rag_normativo/src/motor.py`, líneas ~149–150** (`# DEFENSA 1` / `if aplicar_umbral and r.similitud_max < umbral`):
   > "Esta es la línea donde el sistema decide **no** llamar a la IA."
3. **`tarea2_radar/src/indice.py`, línea ~76** (`construir_filtro`) y **`tarea2_radar/src/motor.py`, líneas ~202–218** (primero cuenta los procesos filtrados, luego aplica el umbral **después** de filtrar):
   > "Los montos y el departamento se convierten en un filtro exacto de la base de datos, nunca en un embedding."

---

## 10:30 – 12:00 · Hallazgos, limitaciones y costo real
**Pantalla:** la sección "Resultados en resumen" y "Costo real total" del README.

**Hallazgos:**
> "Tres cosas me sorprendieron. Primero, el texto de El Peruano trae otras normas pegadas y hay que recortarlas. Segundo, en los datos de OECE, 5.564 descripciones tenían las comillas convertidas en signos '¿', y el campo 'región' traía provincias en vez de departamentos. Tercero, los parecidos de los embeddings no son intuitivos: una pregunta del Reglamento puede parecerse más que una legítima, y el umbral no se puede copiar de una tarea a otra."

**Limitaciones (dilas con honestidad):**
> "Primero: con la IA, la Tarea 1 todavía se abstiene en 3 de 15 preguntas legítimas, dos porque el buscador no le entregó el párrafo correcto. Segundo: ajusté el prompt mirando las mismas preguntas de evaluación, así que la mejora puede estar inflada. Tercero: en la Tarea 2, la IA no marca como 'fuera de tema' dos trampas cercanas, aunque en el texto dice que no hay coincidencia. Cuarto: en mi hoja de respuestas conté por error 'combustible para ambulancias' como 'compra de ambulancias'; lo detectó la IA y lo corregí. Quinto: los saludos como 'hola' pasan el umbral."

**[OBLIGATORIO] Cuánto cuesta una consulta y cómo lo sé:**
> "Una pregunta a la Tarea 1 cuesta unos 0,00017 dólares; a la Tarea 2, unos 0,0003 porque son dos llamadas. Si el umbral la detiene, cuesta cero. Lo sé porque **cada llamada** queda anotada en un log con la fecha, el modelo, los tokens, el tiempo y el costo. El costo se calcula con la tabla de precios de `config.yaml`, verificada el 27 de septiembre de 2026, y según la hora de cada llamada: OpenAI hoy cobra igual a toda hora, pero el cálculo ya soporta tarifas por horario.
> En todo el proyecto hice **202 llamadas** y gasté **2,4 centavos de dólar**."

**Cierre (5 segundos):**
> "Dos herramientas para que una MYPE entienda las reglas y vea las oportunidades, y que saben decir 'no lo sé'. Gracias."

---

## Lista de control de los "you must say"
- [ ] Dónde vive la página (Tarea 1) y el departamento (Tarea 2), y por qué son metadatos → 1:00–3:00 y 3:00–4:30
- [ ] En qué punto no se llama a la IA → 1:00–3:00 (y el código en 9:30)
- [ ] Qué mide Recall@k y qué mide la abstención → 4:30–6:30, punto 5
- [ ] Por qué los montos y el lugar son filtros y no embeddings → 4:30–6:30, punto 7
- [ ] Qué no puede responder el corpus y cómo se comporta → demo de la Tarea 1 (subcontratación)
- [ ] Cuánto cuesta una consulta y cómo lo sé → 10:30–12:00
