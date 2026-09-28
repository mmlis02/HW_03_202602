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

En macOS/Linux los pasos son iguales, con `python3 -m venv .venv` y `source .venv/bin/activate`. El paso 3 no hace falta en Mac, porque la versión por defecto ya es solo CPU.

## Datos grandes fuera de git

Los PDFs originales, los archivos mensuales de OECE y los índices vectoriales **no se suben al repositorio**; ver `.gitignore`. Cada tarea tiene un script de descarga (`scripts/`) que los vuelve a bajar y que no repite lo que ya existe. Los detalles se agregarán en cada fase.

## Estructura

```
├── README.md
├── requirements.txt
├── .env.example
├── docs/                    # enunciado, diagramas, notas para el video
├── tarea1_rag_normativo/    # config.yaml, build_index.py, app.py, src/, eval/, data/, logs/
└── tarea2_radar/            # config.yaml, app.py, src/, eval/, data/, logs/
```
