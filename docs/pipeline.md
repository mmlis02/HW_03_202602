# Diagramas del pipeline (usados en el video)

## Tarea 1 — RAG normativo

```mermaid
flowchart TB
    subgraph OFF["OFFLINE — se corre una vez (build_index.py y scripts/)"]
        A["PDFs oficiales<br/>gob.pe · El Peruano<br/>data/raw/ (no se modifican)"] --> B["Verificación de fuentes<br/>páginas, caracteres, orden de lectura"]
        B --> C["Extracción PÁGINA POR PÁGINA<br/>+ recorte de normas vecinas<br/>(código de publicación)"]
        C --> D["Limpieza R1–R7<br/>encabezados, sello, ligaduras,<br/>notas (*) de versión → texto vigente"]
        D --> E["data/processed/*.jsonl<br/>{documento, pagina, texto}"]
        E --> F["Fragmentos 500 chars / solape 150<br/>metadatos: documento, versión, PÁGINA,<br/>artículo, modificado_por"]
        F --> G["Embeddings locales<br/>multilingual-e5-small ('passage: ')"]
        G --> H[("ChromaDB persistente<br/>data/index/ · IDs estables<br/>idempotente y reanudable")]
    end

    subgraph ON["ONLINE — en cada pregunta (src/motor.py → responder)"]
        Q["Pregunta<br/>(app.py o preguntar.py)"] --> R["Embedding de la pregunta ('query: ')"]
        R --> S["Búsqueda top-5 en el índice"]
        H -.lectura.-> S
        S --> T{"DEFENSA 1<br/>similitud máx ≥ umbral 0.800?"}
        T -- "no" --> U["ABSTENCIÓN por umbral<br/>sin llamar al LLM · costo 0"]
        T -- "sí" --> V["LLM gpt-6-luna<br/>fragmentos [F1..F5] + esquema JSON"]
        V --> W{"DEFENSA 2<br/>fuera_de_corpus?"}
        W -- "sí" --> X["ABSTENCIÓN por la IA<br/>+ explicación del límite"]
        W -- "no" --> Y["[Fn] → (documento, pág. N)<br/>desde METADATOS + nota de versión"]
        V -. "error de API" .-> Z["campo error (se muestra en rojo)"]
        Y --> OUT["Resultado estructurado<br/>respuesta, fuentes, abstuvo, tokens, costo, error"]
        U --> OUT
        X --> OUT
        Z --> OUT
        V --> LOG["logs/costos_llm.csv<br/>tokens, latencia, costo según la hora"]
    end
```
