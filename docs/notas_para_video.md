# Notas para el video (en palabras simples)

Este archivo explica, paso a paso y sin tecnicismos, qué se hizo y por qué. Sirve como guion de apoyo para el video.

---

## Fase 0 — Preparar el proyecto

**Qué hice**
- Creé las carpetas que sugiere el enunciado: una para la Tarea 1 (`tarea1_rag_normativo`), otra para la Tarea 2 (`tarea2_radar`) y `docs` para los documentos de apoyo.
- Creé un **entorno virtual** (`.venv`): una "caja" aislada donde se instalan las librerías del proyecto sin tocar el resto de la computadora.
- Escribí `requirements.txt`, la lista de librerías con su versión exacta, para que cualquiera pueda instalar exactamente lo mismo.
- Creé `.env.example`. La clave de OpenAI va en un archivo `.env` que **nunca** se sube a GitHub; `.env.example` solo muestra el nombre de la variable, vacía.
- Creé `.gitignore`, la lista de cosas que git debe ignorar: la clave, el entorno virtual y los archivos de datos grandes. Los datos se vuelven a descargar con un script.

**Por qué**
- **Reproducible:** otra persona, por ejemplo el profesor en Windows, puede instalar todo con los pasos del README.
- **Seguro:** la clave de la API nunca queda en el historial de git.
- **Liviano:** el repositorio no se llena de archivos pesados que se pueden volver a bajar.

**Dato útil para el video**
- Probé que todas las librerías funcionan con Python 3.14 antes de empezar. El entorno ocupa unos 1.9 GB, casi todo por PyTorch, el motor que usa el modelo de embeddings.
- Elegí `pyshp` para leer el mapa de departamentos en lugar de `geopandas`: es mucho más liviana y no necesita instalar programas extra en Windows.

---

## Tarea 1 · Fase 1 · Paso 1 — Descargar y verificar las fuentes (antes de programar lo demás)

**Qué hice**
- Busqué los PDFs **solo en fuentes oficiales**: gob.pe (MEF y OECE) y El Peruano. Un script (`scripts/descargar_fuentes.py`) los baja a `data/raw/`, no repite descargas y anota la fecha de descarga y una "huella" (sha256) de cada archivo en `data/manifiesto_descargas.json`.
- Otro script (`scripts/verificar_fuentes.py`) revisa cada PDF: cuántas páginas tiene, cuántas letras hay por página, si alguna página no tiene texto (sería una imagen escaneada) y si el texto sale en el orden correcto.
- Para comprobar el orden usé un truco simple: si los "Artículo 1, 2, 3…" aparecen en orden creciente, las columnas se están leyendo bien. En la ley sale 99 %; los pocos saltos son citas a otros artículos.

**Qué encontré (esto sirve para el video)**
- **El Peruano imprime varias normas en la misma página.** El PDF del D.S. 001-2026-EF trae en su última página otra norma completa, una resolución sobre índices de corrección monetaria. Si no se recorta, el asistente podría "citar" algo que no es del decreto.
- **Cómo lo resolví:** El Peruano cierra cada norma con un código (por ejemplo `2474920-3`), así que recorto el texto exactamente en ese código. Esa regla está escrita en `config.yaml`.
- **La versión actualizada de la ley** (compilada por OECE) conserva el texto antiguo y, al lado, una nota "(*) Literal modificado por…" con el texto nuevo. Eso ayuda con las versiones, pero es una trampa: si el asistente lee solo el texto antiguo, respondería algo que ya no rige.
- Hay letras "rotas" (ﬁ, ﬂ) en la ley publicada en El Peruano, por ejemplo "Caliﬁ cación". Se limpiarán en el siguiente paso.

**Decisión: qué versión de la ley usar (opción B)**
- Revisé dos versiones de la Ley 32069: el texto original de 2024 y la versión actualizada al 19/07/2026 que publica OECE en gob.pe. Las dos se pueden leer bien.
- Elegí la **actualizada** porque desde 2024 varias leyes cambiaron artículos. Con el texto original, el asistente podría responder algo que ya no rige, y para una MYPE eso es peor que no responder.
- La del texto original queda en la tabla como prueba de que también la revisé.
- Agregué el **D.Leg. 1715** como documento opcional. Es la norma que cambió un literal de la ley (agregó la "infraestructura hidráulica" a las obras que no se pueden paralizar con medidas cautelares). Sirve para mostrar en el video cómo el asistente explica qué norma cambió qué y cuándo.

---

## Tarea 1 · Fase 1 · Paso 2 — Limpiar el texto y medir su calidad

**Qué hice**
- **La página va pegada al texto desde el primer momento.** Leo cada PDF página por página, y cada pedazo de texto sale con su número de página. Nunca junto todo el documento en un solo texto.
  - *Para el video:* si juntara todo y lo cortara después, tendría que adivinar de qué página viene cada pedazo contando letras. Al limpiar se borran letras (encabezados, notas), así que esa cuenta se descuadra y las citas saldrían con páginas equivocadas.
- **Limpié el ruido con reglas escritas y contadas:**
  - borré el encabezado de El Peruano en cada página (número, "NORMAS LEGALES", fecha);
  - borré el sello de firma digital y el código de cierre de la norma;
  - uní las líneas que el PDF cortaba por el ancho de la columna (a veces cortaba cada palabra en una línea);
  - quité las "concordancias" del SPIJ.
- **Resolví las versiones de la ley.** La versión actualizada trae el texto viejo y, al lado, la nota "(*) modificado por…" con el texto nuevo. Mi programa:
  - borra el texto viejo para que el buscador **no pueda encontrarlo**;
  - deja el texto nuevo con una etiqueta: "[Texto vigente — modificado por el D.Leg. 1715, publicada el 04 febrero 2026]".

  Eran 20 notas: 12 modificaciones, 2 incorporaciones, 1 derogación, 4 avisos y 1 fe de erratas. Las 12 modificaciones se resolvieron todas.
- Generé un **reporte de calidad** por documento (páginas, letras, páginas descartadas, reglas aplicadas y una muestra del medio del texto) y un archivo con **ejemplos de antes y después**.

**Por qué**
- Si el texto lleva basura (encabezados, otras normas), el buscador puede traer un pedazo que no dice nada útil, o que es de otra norma.
- Si el texto viejo sigue en el índice, el asistente podría responder algo que **ya no rige**. Borrarlo antes de indexar es la forma más segura: lo que no está en el índice no se puede citar.

**Números para decir en el video**
- De 112.601 letras del PDF del D.S. 001-2026-EF, 6.272 eran de otra norma y se recortaron.
- Ninguna página se descartó: todas tienen texto de su norma.
- Ejemplo estrella para el video: el art. 85.1.e) antes (sin "infraestructura hidráulica") y después (con la etiqueta del D.Leg. 1715).

---

## Tarea 1 · Fase 2 — Fragmentos, embeddings e índice

**Qué hice**
- **Preguntas de prueba.** Armé 25 preguntas: 15 que el corpus sí responde (6 escritas por mí como las haría una dueña de MYPE) y 10 que no. De esas 10, varias son "trampas" que solo responde el Reglamento: subcontratación, penalidad por mora, plazo de conformidad y plazo para firmar el contrato.
  - La página correcta de cada pregunta la busqué **leyendo el texto**, no con el buscador. Así la prueba no se "copia" las respuestas del propio sistema.
- **Fragmentos.** Corté el texto en pedazos. Cada pedazo pertenece a **una sola página**, así su cita es exacta. Lleva sus datos aparte del texto: documento, versión, página, artículo y, si cambió, "modificado por D.Leg. 1715".
- **Probé tres tamaños** (500, 1000 y 1800 letras) con las preguntas y elegí 500:
  - es el que más veces pone la respuesta correcta en el **primer lugar** (80 %);
  - es el que mejor distingue preguntas de dentro y de fuera.
- **Embeddings.** Cada pedazo se convierte en una lista de 384 números (su "huella de significado") con el modelo local e5-small, que corre en mi computadora sin pagar nada. El modelo pide dos cosas:
  - poner "query: " delante de las preguntas y "passage: " delante de los pedazos;
  - no pasar de 512 tokens. Mi pedazo más largo tiene 183, así que nunca se corta nada.
- **Índice (ChromaDB).** Guardé las huellas, el texto y los datos en una base en disco (`data/index/`). La app solo **lee** este índice; nunca vuelve a leer los PDFs.

**Por qué el índice es seguro de reconstruir (para el video)**
- Cada pedazo tiene un nombre fijo, por ejemplo `dl1715:p1:c3`: documento, página y número de pedazo.
- Si corro el proceso dos veces, ve que ya existen y no duplica nada.
- Si se corta a la mitad, la próxima vez sigue donde quedó. Lo probé cortando a propósito: completó los 154 que faltaban.
- Si agrego un documento nuevo, no toca los pedazos de los otros. También lo probé.

**Qué es Recall@k (para el video)**
- Recall@5 = en cuántas preguntas la página correcta aparece entre los 5 pedazos que trae el buscador.
- Mide **solo el buscador**, sin llamar al modelo que redacta. Por eso la evaluación **cuesta cero** y la puedo repetir cada vez que cambio algo.

**Hallazgo importante**
- Las similitudes de este modelo están muy apretadas: todas entre 0,75 y 0,89.
- El ceviche saca 0,80, igual que en la prueba del profesor.
- Las trampas del Reglamento sacan hasta 0,87, más que algunas preguntas legítimas (0,84). Un solo umbral no alcanza para separarlas; en la Fase 3 hay que calibrarlo con datos y agregar otra defensa.

**Corrección posterior (importante para el video)**
- "500" son **caracteres**, no tokens (500 caracteres ≈ 120 tokens).
- Después también comparé el **solapamiento**: dejé fijo el tamaño en 500 y probé solapes de 0, 75 y 150 caracteres. Luego corregí un detalle de las etiquetas de artículos, recalculé todo y **ganó 500 con solape 150**. Pone la respuesta entre los 5 primeros en 14 de 15 preguntas y es la que mejor ordena (MRR 0,85).
- Hay que decirlo con honestidad: con 15 preguntas, cada una vale 6,7 %. Las diferencias entre configuraciones son de 1 o 2 preguntas, así que elegí mirando varios criterios juntos, no un solo número.

---

## Tarea 1 · Fase 3 — El motor, el umbral y las dos defensas

**Qué hice**
- **El motor** (`src/motor.py`) es una sola función: `responder(pregunta)`. La app y la línea de comandos solo llaman a esa función. El motor no sabe nada de pantallas y nunca abre los PDFs: solo lee el índice.
- **Defensa 1, el umbral (gratis, sin IA).** Si el mejor pedazo encontrado se parece poco a la pregunta (menos de 0,840), el sistema dice "no tengo información" **sin llamar a la IA**.
  - Así se detienen, gratis, 7 de las 10 preguntas de fuera: ceviche, capital de Australia, RUC, REMYPE…
  - No se detiene ninguna de las 15 legítimas.
- **Defensa 2, la IA.** Para las preguntas que pasan, la IA recibe los 5 pedazos. Tiene prohibido usar lo que "sabe" y debe marcar "fuera del corpus" si los pedazos solo *mencionan* el tema sin responderlo.
- **Por qué hacen falta dos defensas (tabla para el video):** hay 3 preguntas del Reglamento que se parecen **más** a nuestros documentos que algunas preguntas legítimas:
  - "¿en cuántos días presento los papeles para firmar el contrato?" = 0,879;
  - la legítima "recién formalicé mi negocio…" = 0,845.

  Si subiera el umbral para frenar esas trampas, también frenaría preguntas buenas. Por eso el umbral frena lo claramente ajeno y la IA frena lo cercano.
- **Cómo elegí 0,840 (barrido):** probé todos los umbrales entre 0,74 y 0,90, y el gráfico muestra qué pasa con cada uno. Elegí el más alto que no bloquea ninguna pregunta legítima, con un pequeño margen.
  - A 0,86 bloquearía 5 de 15 legítimas.
  - A 0,78 (el umbral "intuitivo" del enunciado) dejaría pasar el ceviche, que saca 0,79, igual que en la prueba del profesor.
- **Las páginas las pone el sistema, no la IA.** La IA escribe "[F2]" y el programa lo reemplaza por "(D.S. 001-2026-EF, pág. 4)" usando los datos guardados del pedazo. Así la IA no puede inventar una página.
- **Nota de versión automática:** si el pedazo citado fue modificado, el sistema agrega "Texto vigente: modificado por el D.Leg. 1715, publicada el 04 febrero 2026". Si cita el D.S. 001-2026-EF, avisa que solo trae algunos artículos del Reglamento.
- **Errores:** si la API falla, el resultado trae el campo "error" y la app lo mostrará en rojo. Nunca se disfraza de respuesta.
- **Costos:**
  - Modelo: gpt-6-luna, verificado el 27/09/2026 a US$0,10 por millón de tokens de entrada y US$0,50 por millón de salida.
  - Tabla de precios por hora en `config.yaml`: OpenAI cobra igual a toda hora, pero el programa ya elige el precio según la hora de cada llamada, y lo probé con una tabla inventada de día/noche.
  - Cada llamada queda anotada en `logs/costos_llm.csv`.
- **Probé todo sin gastar** con una "IA falsa" que imita las respuestas de OpenAI: abstención por umbral, respuesta con cita, fuera del corpus, error de la API, respuesta sin citas y pregunta vacía.

**Qué mide cada tasa (para el video)**
- **Abstención por umbral (sin IA):** 7/10 correctas, 0/15 incorrectas. Cuesta 0.
- **Abstención final (con IA):** pendiente de la corrida autorizada.

---

## Tarea 1 · Fase 3 (cont.) — Primeras llamadas reales y ajuste del umbral

**Qué hice**
- **Regla antes de mirar.** Antes de correr la segunda prueba escribí en el README qué cuenta como acierto y lo subí a GitHub, así la fecha prueba que no la acomodé a los resultados:
  - si la pregunta es de fuera del corpus y el sistema da una respuesta "a medias", cuenta como **error**, aunque aclare que falta el dato;
  - solo cuenta el campo "abstuvo" (sí/no), no lo que dice el texto.
- **Primera corrida real (prompt v1):**
  - las 10 preguntas de fuera: 10 bien;
  - pero se abstuvo en 4 legítimas. En 3 de ellas la IA tenía la página correcta y se negó a responder porque "faltaban detalles": mi instrucción era demasiado estricta.
- **Corregí el prompt (v2):** abstenerse solo si falta el **dato central**; si la respuesta es parcial, responder y decir qué falta. Resultado: siguen 10/10 bien afuera y bajan a 2 las legítimas perdidas.
  - **Advertencia honesta:** ajusté el prompt mirando estas mismas preguntas, así que la mejora puede estar inflada.
- **Bajé el umbral de 0,840 a 0,800.**
  - Con 0,840 había solo 0,005 de margen sobre la pregunta legítima más baja: en la demo en vivo, una pregunta dicha con otras palabras podía quedar bloqueada sin razón.
  - Con 0,800 el margen es 9 veces mayor.
  - Se siguen bloqueando gratis el ceviche y las otras preguntas absurdas.
  - Lo que pasa, la IA lo atrapa: en la prueba atrapó las 6 que pasaron.

**Ejemplos reales para mostrar en el video**
- **Versión:** "¿Procede una medida cautelar para paralizar una obra de infraestructura hidráulica?" → "No… (Ley 32069 actualizada, pág. 43)", con la nota automática "Texto vigente: modificado por el D.Leg. 1715, publicada el 04 febrero 2026".
- **Límite del corpus:** "¿En cuántos días presento los papeles para firmar el contrato?" → el sistema se abstiene y explica que el único plazo que encontró es para *después* de firmar, así que no responde la pregunta.
- **Respuesta parcial:** "Recién formalicé mi negocio, ¿qué trámite…?" → "inscribirte en el RNP (pág. 17)" + "los requisitos específicos están en el Reglamento".

**Limitaciones que debo mencionar**
- **D02 ("3 mil soles") y D12:** el buscador no le entregó a la IA el pedazo correcto. En D12 la página sí llegó, pero no el párrafo exacto: medir "por página" es un poco optimista.
- **D13 (Pladicop):** la IA no siempre elige el mejor fragmento para citar.

**Costo real:** 44 llamadas, **US$0,0072 en total**. Una pregunta cuesta unos US$0,00017 (menos de un milésimo de sol). Lo sé porque cada llamada queda anotada en `logs/costos_llm.csv` con sus tokens y su precio.

---

## Tarea 1 · Fase 4 — Comparar el modelo local con el de OpenAI

**Qué hice**
- Armé un segundo índice con el modelo de OpenAI (`text-embedding-3-small`), usando **exactamente los mismos pedazos de texto**. Solo cambia el modelo, y cambiarlo es una línea en `config.yaml`.
- Indexar todo con OpenAI costó **US$0,0029** (147.090 tokens). Quedó anotado en el log de costos.

**Resultados (para mostrar en una tabla)**
- **Buscador:** empate técnico.
  - OpenAI trae la página correcta entre las 5 primeras en 15 de 15 preguntas; el local, en 14 de 15.
  - El local la pone **primera** más veces (12 frente a 10).
  - Son diferencias de 1 o 2 preguntas.
- **Velocidad:** el local responde en 14 milisegundos y OpenAI en 303 (21 veces más lento), porque cada pregunta viaja por internet.
- **Precio:** con OpenAI, un millón de preguntas costaría unos US$0,43. Es el 0,25 % de lo que cuesta la respuesta de la IA. **Por eso el precio no sirve para decidir: los dos son casi gratis.**
- **Umbral:** cada modelo tiene su propia escala. En el local todo sale entre 0,75 y 0,92; en OpenAI, entre 0,15 y 0,74. El umbral no se puede copiar de un modelo a otro, así que ahora hay uno por modelo en la configuración.

**Por qué elegí el local**
- Funciona **sin internet**: el buscador y la primera defensa siguen andando.
- **Privacidad:** las preguntas que el umbral detiene nunca salen de la computadora. Las que pasan sí van a OpenAI para redactar la respuesta, así que la ventaja es parcial, y hay que decirlo.
- Es **más rápido** y no cambia con el tiempo. Un modelo de API puede actualizarse o retirarse, y eso obliga a reindexar y a recalibrar.
- **Contras:** pesa 471 MB más PyTorch, y entiende un poco peor el lenguaje cotidiano. Por ejemplo, OpenAI sí encontró la pregunta de "3 mil soles".

**Qué mide cada métrica**
- **Recall@k** mide el buscador.
- **La abstención por umbral** mide la primera defensa.
- **La abstención final** mide todo el sistema.

Las dos primeras se calculan sin llamar a la IA, **gratis**, así que pude probar 5 tamaños de pedazo y 33 umbrales sin gastar nada.

---

## Tarea 1 · Fase 5 — La app (Streamlit)

**Qué hice**
- Armé la app con 4 pestañas:
  - **Preguntar:** respuesta con citas, fragmentos con su página y similitud, si se abstuvo y cuánto costó la consulta.
  - **Calidad de extracción:** los reportes de la Fase 1.
  - **Evaluación:** tablas y gráficos de las fases 2 a 4.
  - **Costos:** todo lo gastado, leído del log.
- La app **no piensa**: solo llama a la función `responder` del motor y muestra lo que devuelve. Tampoco construye el índice; si falta, explica cómo crearlo.
- Los colores tienen significado:
  - **verde** = respuesta;
  - **amarillo** = se abstuvo (y dice por qué: umbral o IA);
  - **azul** = límite del corpus o nota de versión;
  - **rojo** = error de la API.
- Probé la app sin navegador con cuatro casos:
  - el ceviche (se abstiene gratis);
  - la obra hidráulica (responde con la nota del D.Leg. 1715);
  - la subcontratación (la IA se abstiene);
  - una clave falsa (sale el error en rojo y aun así muestra los fragmentos).
- **Seguridad extra:** el error de OpenAI traía un pedacito de la clave. Ahora cualquier cosa con forma de clave se reemplaza por "sk-[oculta]" antes de mostrarla o guardarla.
- **Ajuste final del prompt (v3):** la IA ponía "límite del corpus" en casi todas las respuestas, aunque no faltara nada, y confundía. Ahora solo lo pone cuando de verdad falta algo (bajó de 10 a 2).
  - **Costo de ese cambio:** una pregunta límite (D06, el tope del adelanto para materiales, que no está en el corpus) pasó a abstenerse.
  - No cambié la regla para que "cuente bien": según lo que fijé antes, es un error, y lo digo.

**Costo total de toda la Tarea 1:** 141 llamadas, **US$0,0148**, menos de 6 céntimos de sol.

**Diagrama del pipeline:** está en el README y en `docs/pipeline.md`. Hay que mostrarlo al inicio del video, **antes de cualquier código**.

---

## Tarea 1 · Cierre — Prueba de la app por la usuaria y cómo mostrarla en el video

**Cómo abrir la app para la demo en vivo** (terminal de VS Code):
```bash
cd /Users/michelle.li/Documents/HW_03_202602
source .venv/bin/activate
cd tarea1_rag_normativo
streamlit run app.py
```
Se abre en http://localhost:8501; se cierra con Ctrl+C. Consejo: abrirla **antes** de grabar y hacer una pregunta de calentamiento, porque la primera carga el modelo y tarda unos segundos.

**Guion sugerido para la demo (Tarea 1)**
1. **Una pregunta que responde:** "¿Cuánto tiempo tiene el Estado para pagarme después de entregar?" Mostrar la cita (pág. 32), el costo (~US$0,0002) y los fragmentos.
2. **Una pregunta con versión:** el botón de la obra hidráulica. Mostrar la **nota de versión** del D.Leg. 1715.
3. **Una trampa del Reglamento:** el botón de subcontratación. **La IA** se abstiene y explica que el porcentaje está en el Reglamento.
4. **El ceviche:** se abstiene **sin llamar a la IA**. Costo US$0; mostrar que la similitud (0,792) está bajo el umbral (0,800).
5. **Las pestañas** de calidad de extracción, evaluación y costos.

**Lo que encontré con tu prueba (vale la pena contarlo)**
- Hiciste 3 preguntas y quedaron registradas en el log de costos: la de "¿en cuántos días me pagan?", una con tus propias palabras y un "hola!".
- **El "hola!" pasó el umbral.** Los saludos cortos se parecen "demasiado" a todo con este modelo ("hola" 0,804, "gracias" 0,834). La IA igual no respondió nada inventado; la segunda defensa lo frenó. Pero costó una llamada (US$0,00013).
- **Por qué pasa:** es el precio de haber bajado el umbral de 0,840 a 0,800 para tener margen en la demo. Es un buen ejemplo en vivo de por qué hacen falta **dos defensas**.
- **Mejora posible (no hecha):** un filtro previo que ignore saludos o textos demasiado cortos.

---

# TAREA 2 — Radar de compras públicas

## Tarea 2 · Fase 1 — Conseguir los datos

**Qué hice**
- Averigüé cómo descarga los archivos la página de OECE, leyendo su código, porque la página se arma con JavaScript. Hay archivos mensuales en CSV, Excel y JSON.
- Elegí **JSON** (el formato del estándar OCDS) de **junio, julio y agosto de 2026**, los 3 meses completos más recientes. En total pesan **30 MB comprimidos**. Para no llenar el disco, los leo sin descomprimirlos.
- **Verifiqué cada archivo con su "huella" SHA-256** (un código que cambia si el archivo cambia en un solo byte).
  - *Anécdota útil para el video:* la primera verificación falló. Resulta que la huella que publica OECE es la del archivo **de adentro** del ZIP, no la del ZIP. Mi programa hizo lo correcto: rechazó el archivo en vez de usarlo "a ciegas".
- **Release, record y ocid (hay que explicarlo en el video):**
  - **release** = una foto del proceso en un momento (convocatoria, adjudicación…);
  - **record** = el álbum con todas las fotos de un proceso, más un resumen con el estado actual;
  - **ocid** = el número de identidad del proceso.
- **Una fila por proceso:** las 288.548 "fotos" (releases) se agrupan en **20.476 procesos**. Junté los 3 meses y busqué procesos repetidos entre meses: **no hubo ninguno**, porque OECE pone cada proceso en el mes en que empezó su convocatoria.
  - La regla, por si aparecen: me quedo con la versión más reciente del resumen.
- **La API la usé solo para lo nuevo:** los procesos de septiembre (el mes en curso), 5.435 procesos.
  - Pido una página por segundo para no saturar el portal.
  - Guardo cada página apenas llega. Probé "cortar internet" a propósito a mitad de camino: al volver a correr, solo pidió las 7 páginas que faltaban.

**Por qué**
- Los archivos mensuales son la forma eficiente de bajar mucho de una vez. La API sirve para lo reciente, no para bajar todo: su lista general ni siquiera se puede ordenar por fecha.

## Tarea 2 · Fase 2 — Revisar y ordenar los datos (validación)

**Qué hice**
- **Regla de oro: no borré ninguna fila.** Cada problema queda marcado, se corrige si se puede y se cuenta en el reporte de calidad. Si algo se excluye, queda escrito el porqué.
- **Ubicación: uso la dirección de la entidad que compra (el Estado)**, no la de las empresas. Una empresa de Lima puede ganar una obra en Puno; lo que interesa es dónde compra el Estado.
- **Hallazgo:** el campo "department" venía bien en el 100 % de los casos. El campo "region" en realidad traía **provincias** (Huari, Trujillo, La Convención…), justo la mezcla que avisa el enunciado.
  - Para comprobarlo, convertí cada provincia a su departamento con la **tabla oficial del IGN** y comparé: coincidieron todas.
  - Solo una provincia estaba escrita distinto: **NAZCA** en los datos, **NASCA** en el IGN. La corregí con un "alias".
- **Las comparaciones ignoran tildes y mayúsculas** (JUNÍN = JUNIN = Junín).
- **Hallazgo de codificación (bueno para el video):** en **5.564 descripciones** las comillas “ ” se habían convertido en "¿". Por ejemplo: `OBRA: ¿MEJORAMIENTO… CUSCO¿`. Las devolví a comillas, pero solo cuando no había un "?" (así no toco preguntas reales).
- **Montos:**
  - 2.120 procesos tenían monto 0, casi todos todavía "convocados". Solo pude recuperar 38 con el monto adjudicado; los demás se cuentan como procesos, pero no entran a las sumas de dinero.
  - Los montos en dólares y euros se pasaron a soles con la conversión que publica OECE.
- **Posibles reconvocatorias (1.072 grupos):** misma nomenclatura, misma entidad, distinto ocid. **No las borré.** Revisé la historia de cada grupo:
  - **647 son reconvocatorias confirmadas:** la versión anterior quedó nula, desierta, cancelada o "retrotraída". Ejemplo: una obra de agua potable anulada el 14/08 y convocada de nuevo el 26/08, con el mismo monto.
  - 365 son re-registros del mismo día, 44 parecen compras distintas con el mismo código y 16 no se pudieron clasificar.
- **Septiembre (API)** va aparte, como "novedades recientes". Como la API no trae la dirección, ubiqué cada proceso buscando la misma entidad en junio–agosto: funcionó en el 97 %.
- **El mapa:** pasé el mapa oficial del IGN (5,4 MB) a un archivo liviano de 0,11 MB, con los mismos nombres de departamento que uso en los datos.

**Números para el video:** 20.476 procesos, **100 % ubicados** en los 25 departamentos, 0 filas borradas y 2 excluidas con motivo (el mismo proceso registrado dos veces).

## Tarea 2 · Fase 3 — Búsqueda híbrida: filtros + significado

**Qué hice**
- **Reutilicé el motor de la Tarea 1:** junté las piezas comunes en una carpeta compartida (`comun/`) que usan las dos tareas. Es el mismo modelo local, el mismo cálculo de costos y la misma llamada a la IA.
- **Indexé las 20.101 descripciones en unos 6 minutos.** El departamento, el monto, la fecha y la categoría van como **datos aparte (metadatos)**, no dentro del texto.
- **Por qué filtros y no embeddings (clave para el video):**
  - El modelo de significado no sabe que 200 mil es menos que 1 millón, ni que Cusco no es Puno.
  - Sin filtros, **2 de cada 3 resultados no cumplían** lo pedido.
  - Con filtros, el 100 % cumple, y el proceso correcto aparece entre los 5 primeros en el 94 % de las preguntas.
- **La IA extrae los filtros de la pregunta** y la app los mostrará para que el usuario los revise. Acertó todos los campos en las 25 preguntas.
- **Cero resultados ≠ fuera del tema:** si los filtros no dejan ningún proceso, el sistema dice "no hay procesos que cumplan esas condiciones" y lo marca con un campo propio (`sin_resultados`).
- **El umbral de la Tarea 1 (0,800) no sirvió aquí:** el ceviche sacaba 0,837. Recalibré a **0,830** con los datos.
  - Verifiqué que el umbral se calcula **después** de filtrar, y que no bloquea preguntas con muy pocos procesos: probé una con solo 6.
- **Fallas honestas:**
  - Para "aviones de combate F-35" y "submarinos nucleares", la IA dijo en el texto "no hay compras de eso", pero no marcó la casilla de "fuera de tema". Con la regla que fijé antes, cuenta como error.
  - Mi hoja de respuestas tenía un error (contaba "combustible para ambulancias" como compra de ambulancias) y **la IA lo detectó**. Lo corregí y lo declaro.
- **Costo de toda la evaluación con IA:** US$0,008.
