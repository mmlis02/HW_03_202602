# Enunciado de la tarea

The Problem — "Selling to the State"
A small business (MYPE) in Peru wants to sell goods, services or works to the State. It faces two problems at once:

It does not understand the rules. Procurement norms are long, technical, and change often. Hiring a lawyer for every question costs more than many of the contracts the business would bid for.
It does not see the opportunities. Thousands of contracting processes are published every month. Nobody reads them all, and the ones that matter are hidden among the ones that do not.
Your job is to build the two tools this business needs.

A system that answers confidently and wrongly is worse than no system at all. In both tasks, knowing when not to answer is part of the grade.

Feasibility Evidence (verified by the teaching team)
Both tasks were run end to end by the teaching team on a regular laptop (CPU only) before publication. You will meet the following conditions. They are not bugs in the assignment; handling them is the assignment.

Finding	Implication for you
The two mandatory documents of Task 1 were read successfully with a standard PDF library: the text comes out complete and in order.	Extraction is a solved problem here. What you must get right is what you keep, how you clean it and how you label it.
Both documents are published by different institutions and in different formats: one is a law, the other a decree that modifies a regulation.	Your metadata must distinguish them, and your answers must say which one they come from.
El Peruano PDFs are dense: around 7,000 characters per page, with page headers (page number, section name, date) glued to the body text.	Cleaning and checking the reading order are part of Phase 1.
With a local multilingual embeddings model, an out-of-domain question ("how do I cook ceviche?") scored 0.79 in cosine similarity, above a threshold of 0.78 chosen by intuition.	Similarity scores are not intuitive. The threshold must be calibrated with evidence.
OECE publishes monthly bulk files (CSV, XLSX, JSON) in addition to a paginated API.	Choose the right access method for each purpose and justify it.
Documents attached to contracting processes are often ZIP archives, and their content varies a lot.	Tender documents are not required in the mandatory corpus of Task 2 (see Innovation).
Mandatory Scope
Task 1 corpus: the two mandatory documents listed in Task 1, Phase 1, plus any optional document you add and justify.
Task 2 corpus: at least three monthly files of OECE open contracting data from 2026.
Generation model: any provider is allowed (DeepSeek, OpenAI, Gemini, Anthropic, other). Whatever you use, your cost table must state the prices and the date you verified them.
Embeddings: your main model must run locally (for example, a multilingual model from sentence-transformers). You will compare it against an API model in Task 1, Phase 4.
Vector store: any persistent option (ChromaDB, FAISS, other). Justify your choice.
Every source must have extractable text. Verify it before you build anything (Task 1, Phase 1). If a document you wanted to use does not qualify, leave it out and say so in your README.

TASK 1 — Normative RAG: Public Procurement Assistant
Value: 6.0 points

Objective
Design and build an assistant that answers questions about Peruvian public procurement rules only with what the indexed documents say, cites document and page for every claim, and abstains when the answer is not in the corpus.

Required architecture (you design it)
Your system must satisfy these properties. How you achieve them is your decision, and you will explain it in the video.

Two separate processes. An offline process that turns documents into a searchable index (run once, or when documents change), and an online process that answers each question using that index. The online process never re-reads the PDFs.
One engine, many interfaces. All the RAG logic lives in one module that exposes one function receiving a question and returning a structured result (at minimum: answer, sources with document/page/similarity, whether it abstained, tokens, cost, and error if any). The Streamlit app, and any other interface you add, only calls that function.
The engine does not know about interfaces. Your engine module must not import Streamlit, Telegram or any UI library. Include in your README the command you use to verify it (for example, a grep over the imports).
Configuration outside the code. Every path, model name, chunk size, threshold, prompt and user-facing message lives in a configuration file (config.yaml or similar). Credentials live in .env and never reach the repository.
Observable cost. Every call to the generation model is logged (date, model, tokens in/out, latency, cost in USD, success or failure).
Include a pipeline diagram (Mermaid is enough) in your README.

Phase 1 — Sources, Extraction and Cleaning
Value: 1.0 point

Mandatory documents
Document	Source
Ley N.° 32069, Ley General de Contrataciones Públicas	https://www.gob.pe/institucion/osce/colecciones/45029-ley-n-32069-ley-general-de-contrataciones-publicas
Decreto Supremo N.° 001-2026-EF, which modifies the Reglamento of that law	https://busquedas.elperuano.pe/dispositivo/NL/2474920-3
Optional document (recommended)
You may add one further official norm that modifies the law or its regulation, if and only if it passes the source check of this phase. Document what you added, why, and the result of the check. This makes the version questions of Phase 3 richer.

Only official sources (gob.pe, El Peruano) are accepted. Consolidated versions from private legal portals are not. Record the download date of every file.

Requirements
Source check (required). Before building anything, verify for each PDF: number of pages, characters per page, pages without extractable text, and whether the text is readable in the right order. Report the result as a small table, and state explicitly whether each file is usable as it is. Do this before writing the rest of the pipeline: a source that cannot be read changes your whole plan.
Every piece of text must keep the page number it came from from the very first step, so that any answer can cite it. You will be asked in the video how you guaranteed this, and why a design that joins the whole document into one string and splits it later tends to lose citations.
Clean the text. El Peruano pages carry headers (page number, section title, date) that get glued to the body text, and the law uses numbered articles and lettered lists. Remove the noise with a documented rule, and show a before-and-after example.
Produce an extraction quality report per document: pages, characters, pages discarded and why, and a sample of the extracted text from the middle of each document.
Technical Considerations
Raw PDFs go to data/raw/ and are never modified.
Extracted text goes to data/processed/, with its page number attached.

Phase 2 — Chunking, Embeddings and Index
Value: 1.0 point

Split the text into fragments. Choose the size and overlap with evidence (at least two configurations compared with your evaluation set), not by default.
Every fragment carries, at minimum: documento, version (or publication date) and pagina.
Every fragment has an ID that is unique across documents and stable between runs.
The index build must be idempotent (running it twice does not duplicate anything) and resumable (if it stops halfway, it continues). Adding a new document must not skip or overwrite the fragments of another one. Show that your design guarantees this.
Check your embeddings model's documentation: some model families expect different prefixes or instructions for queries and for passages, and every model has a maximum input length. Report what your model requires and how your fragment size relates to that limit.
Report the number of fragments per document and the fragment length distribution.

Phase 3 — RAG Engine: Threshold, Versions and Scope
Value: 1.5 points

Implement the engine with the architecture described above.
Decide before calling the LLM. If the best retrieved fragment is not similar enough, the engine abstains without calling the generation model. Calibrate that threshold with a sweep over your evaluation set, and show the evidence (a table or a chart). Explain the trade-off between answering wrong and not answering.
Handle versions. Your corpus contains a norm and a norm that modifies another one. An answer built from a modifying decree is incomplete if it is presented as if it were the whole rule, and an answer built from an original text is wrong if that text was already modified. Describe your strategy (metadata, re-ranking, prompt instructions, an explicit version note in the answer, or another) and show one example where it works.
Know the limits of your corpus. Many real questions about procurement are answered by the Reglamento, which is not part of your index. When a question falls outside what you indexed, the assistant must say so explicitly instead of improvising with the closest fragment it found. Show one example.
Every answer cites document and page. The prompt forbids answering from outside the retrieved context.
Abstention must be represented as a structured field of the result, not inferred by comparing the text of the answer.
API errors are returned as errors (never as a normal answer), and the interface shows them as errors.
Many providers charge different prices at different hours. Your cost calculation must apply the correct price according to the time of each call, and document the source and date of the prices.

Phase 4 — Evaluation and Embeddings Comparison
Value: 1.5 points

Evaluation set
Create an evaluation file (for example, eval/preguntas.csv) with at least:

15 in-domain questions, each with the expected document and page(s). At least 3 must concern articles affected by the modifying norm. At least 5 must be phrased the way a small business owner would ask, not the way the law is written.
5 out-of-domain questions, some of them deliberately close to the domain (for example, a question that only the Reglamento could answer).
All in-domain questions must be answerable within your indexed corpus.

Write a script that computes Recall@1, Recall@3, Recall@5 and the abstention rate (correct and incorrect abstentions) without calling the generation model. Explain which stage of the pipeline each metric evaluates, and why it matters that the evaluation costs nothing.

Embeddings comparison (mandatory)
Build two indexes with exactly the same fragments:

Index	Model
Local	Your local model from Phase 2
API	text-embedding-3-small (OpenAI)
Report, for each model: Recall@k, indexing time, cost in USD, average query latency, and vector dimension. Then answer in your README: which one would you choose for this case, and why? Price alone is not a sufficient argument; calculate it and you will see why.

Your embeddings code must expose one common interface with two implementations, so that switching models is a configuration change.

Phase 5 — Streamlit Interface (local deployment)
Value: 1.0 point

The app runs with a single streamlit run app.py on a clean machine after installing requirements.txt. Document the exact steps in the README (Windows), including any special installation (for example, PyTorch for CPU).
The app shows the answer, the cited fragments (document, page, similarity), whether it abstained, and the cost of the query.
A panel shows the extraction quality report from Phase 1 and the evaluation results from Phase 4.
The app loads the existing index; it never rebuilds it at start-up.
A public deployment (Streamlit Community Cloud, Hugging Face Spaces, other) is not required. It counts as innovation.

Recommended reading
Sentence Transformers documentation: https://sbert.net
ChromaDB documentation: https://docs.trychroma.com
LangChain conceptual guide (text splitters, retrieval): https://python.langchain.com/docs/concepts/
Streamlit documentation: https://docs.streamlit.io

TASK 2 — RAG Radar: What Is the State Buying, and Where?
Value: 6.0 points

Objective
Build a data product that collects open procurement data, validates it, locates it on a map, and lets a user ask questions in natural language, combining structured filters (region, amount, date, category) with semantic search over process descriptions. Reuse the engine you built in Task 1.

Phase 1 — Data Acquisition
Value: 1.5 points

Required sources
Source	Link
OECE — Open Contracting portal (OCDS standard)	https://contratacionesabiertas.oece.gob.pe/
Bulk downloads	https://contratacionesabiertas.oece.gob.pe/descargas
API documentation	https://contratacionesabiertas.oece.gob.pe/api
Dataset description and known quality issues (Open Contracting Partnership)	https://data.open-contracting.org/es/publication/135
Department polygons	Any declared source (you may reuse the one from Issue 2)
Requirements
Download at least three monthly files of 2026. This is your corpus.
Use the API only for what it is good at: fetching recent updates. Implement it with throttling, error handling and caching; a failed request must not lose previous work.
The download step is re-runnable and never downloads what already exists.
Learn the OCDS data model well enough to explain it in the video: the difference between a release and a record, and what an ocid identifies. Your processed dataset must contain exactly one row per contracting process. Report how many rows you had before and after reaching that.
Log elapsed time, request count, and file sizes.

Phase 2 — Validation and Territorial Normalization
Value: 1.0 point

The data contains real errors. Your pipeline must detect and log, at minimum:

Repeated records for the same contracting process.
Processes with a missing or zero amount.
Processes without a description.
Location fields whose values are not departments (you will find provinces mixed with departments).
Encoding and accent inconsistencies in text fields (for example JUNÍN vs JUNIN).
Normalize the buyer's location to the 25 departments (including Callao) with an explicit, documented rule. State how many processes you could not locate and why.

Produce a data quality report stating, for each rule, how many records were flagged and what was done with them (corrected, dropped, kept with a warning).

Silently dropping bad rows is a failing approach. Dropping them with a logged, justified rule is a passing approach. Correcting the recoverable ones and reporting the recovery rate is an excellent approach.

Phase 3 — Hybrid RAG
Value: 1.5 points

Index the process descriptions with the same local embeddings model as Task 1, and store the structured fields (department, amount, date, category, buyer, ocid) as metadata.
Questions such as "water and sewage works in Cusco above one million soles" contain two kinds of conditions. Numeric and territorial conditions must be applied as filters, not left to the embeddings. Explain why.
Reuse the abstention logic from Task 1. Show whether the threshold you calibrated in Task 1 transfers to this corpus, and recalibrate it if it does not.
The generated answer cites every process by its ocid.
Evaluate with at least 10 questions with known relevant processes, and report Recall@k.

Phase 4 — Streamlit Dashboard
Value: 1.5 points

Minimum required views
KPI header — number of processes, total amount, number of departments, and the risk indicator from Phase 5. Updates with filters.
Choropleth map — departments colored by number of processes or amount, with a legend and tooltips.
Question box — the hybrid RAG from Phase 3, showing the answer and the retrieved processes with their similarity.
Ranked table — sortable, with download to CSV.
Distribution view — amounts or processes by category, department or month (seaborn or native charts).
Data quality panel — the Phase 2 counts, so the user can see what the analysis is standing on.
Technical Considerations
The dashboard reads precomputed files. It must not download bulk files or rebuild the index at load time.
Use @st.cache_data and @st.cache_resource appropriately.
Sidebar filters: department, category, amount range, date range, similarity threshold.
Handle the empty-selection case without crashing.
The app must run with a single streamlit run command after pip install -r requirements.txt.

Phase 5 — Risk Indicator: Single-Bidder Awards
Value: 0.5 points

Among awarded processes, calculate the share that received exactly one bidder, by department and by buyer. Show the ten buyers with the highest share, with a minimum number of processes that you define and justify.

This indicator comes from the international literature on procurement integrity. Read these references before implementing it:

Open Contracting Partnership — Red Flags in Public Procurement (2024): https://www.open-contracting.org/resources/red-flags-in-public-procurement-a-guide-to-using-data-to-detect-and-mitigate-risks/
Ojo Público — Funes, un algoritmo contra la corrupción: https://ojo-publico.com/especiales/funes/
A red flag is a reason to look closer, not evidence of wrongdoing. Your dashboard and your video must say so explicitly. Do not publish names of individuals.

Presentation
Value: 8.0 points

You must submit a single video of up to 12 minutes covering both tasks.

The pipeline-first rule
The video must explain the complete pipeline of both tasks before showing a single line of code.
If the first technical content of your video is code, the criterion Pipeline explained before code is graded zero.

Use a diagram (the Mermaid diagram of your README is enough). Someone who understands the flow can explain any line; someone who only shows code is usually reading what an agent wrote.

Suggested structure
Time	Content	What is on screen
0:00–1:00	The problem and the user	Slides
1:00–3:00	Task 1 pipeline: what happens once (offline) and what happens on every question (online)	Diagram only
3:00–4:30	Task 2 pipeline: acquisition, validation, index, query, dashboard	Diagram only
4:30–6:30	Technical decisions with their numbers (sources, chunking, threshold, versions, embeddings, filters)	Tables and charts
6:30–9:30	Live demonstration of both Streamlit apps	Apps running
9:30–10:30	Code: only the two or three parts that support your decisions	Editor
10:30–12:00	Findings, limitations and real cost	Report
While explaining the pipeline, you must say
Where the page number (Task 1) and the department (Task 2) live, and why they are metadata and not text.
At which point your system decides not to call the LLM.
What Recall@k measures and what the abstention rate measures.
Why numeric conditions are filters and not embeddings.
What your corpus cannot answer, and how your assistant behaves when asked.
How much a query costs, and how you know.
Evaluation of the presentation
Criterion	Points
Pipeline of both tasks explained before any code	2.0
Live demonstration of both working applications	2.5
Defence of methodology and technical decisions, with numbers	2.0
Findings, limitations and real cost	1.5
Total	8.0
Reading slides aloud will not score well. Expect to be evaluated on whether you understand what you built.

Deliverables

Own GitHub repository, public, with the structure below.

README.md with setup instructions (Windows), download steps, run commands, pipeline diagrams, and the results tables of both tasks.

A configuration file per task containing all parameters. No hardcoded paths, thresholds, prompts or messages.

.env.example with variable names only. No credentials in the repository (check your commit history too).

requirements.txt

Task 1: source check table, extraction outputs, index build script, evaluation set and results, embeddings comparison table, app.py.

Task 2: acquisition, validation, index and metrics modules; processed data (or a documented script that regenerates it); app.py.

Data quality reports of both tasks and execution logs.

Cost log with the real calls you made.

A single video of up to 12 minutes, linked in the README.

Commits distributed over time. A repository with all its history on the last day will be reviewed with that in mind.

Suggested repository structure
This is a suggestion, not a fixed template. You may organize your modules differently if you respect the required architecture and explain your choices.

```
├── README.md
├── requirements.txt
├── .env.example
├── tarea1_rag_normativo/
│   ├── config.yaml
│   ├── build_index.py        # offline process
│   ├── app.py                # Streamlit (interface only)
│   ├── src/                  # extraction, cleaning, chunking, embeddings, index, engine, costs
│   ├── eval/                 # evaluation set and script
│   ├── data/{raw,processed}/
│   └── logs/
├── tarea2_radar/
│   ├── config.yaml
│   ├── app.py
│   ├── src/                  # acquisition, validation, territory, index, engine, metrics
│   ├── eval/
│   ├── data/{raw,processed,outputs}/
│   └── logs/
└── docs/
    └── pipeline.md           # diagrams used in the video
```
