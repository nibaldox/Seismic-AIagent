<div align="center">

# 🌊 Seismic AIagent — SeismoAnalyzer Pro v2.0
Análisis sísmico interactivo con asistencia de IA — optimizado para Chile y zona de subducción andina

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.56+-red.svg)](https://streamlit.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-202_✔️-brightgreen.svg)](https://github.com/)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-✔️-blueviolet.svg)](https://pages.github.com/)
[![Docker](https://img.shields.io/badge/Docker-✔️-2496ED.svg)](https://docker.com/)

</div>

---

## 📋 Resumen

Plataforma de análisis sísmico con **3 interfaces** + **8 agentes IA** + **deploy multiplataforma**.

Combina algoritmos clásicos de sismología (ObsPy/NumPy) con un sistema multi-agente IA que interpreta datos y sugiere acciones operativas.

**Diseñado para Chile:** calibración ML regional (CSN), modelo de velocidades cortical andino (Vp=6.0 km/s), agentes IA contextualizados en sismotectónica Nazca/Sudamérica.

---

## 🚀 Modos de Ejecución

### 1. Web App Streamlit
```bash
streamlit run streamlit_app.py         # → http://localhost:8501
```

### 2. API REST + Frontend SPA
```bash
python -m src.server                    # → :8000/api + :8000/app + /docs
```

### 3. CLI Batch
```bash
python -m src.cli "data/" -r -p "*.ms" -o resultados.json
```

### 4. Docker
```bash
docker-compose up -d                   # → http://localhost:8501
```

### 5. GitHub Pages + CI/CD
```bash
# Push a main → Actions: test → lint → Docker → Pages deploy
# Frontend en frontend/, configurable via config.json
```

---

## 🧪 Tests

```bash
python -m pytest tests/ -v
# 202 passed, 4 skipped (2 legacy, 2 requieren API key externa)
```

---

## ✨ Funcionalidades

### Procesamiento sísmico
- Ingesta multi-formato: MiniSEED, SAC, SEG-2, Gecko `.bin`, Kelunji `.ss`
- Filtros digitales: bandpass, highpass, lowpass (ObsPy zerophase, Butterworth 4 polos)
- Detección automática P/S con STA/LTA + prefiltro 2–15 Hz
  - Fase S: Vp/Vs=1.73 en canal Z, o STA/LTA independiente en horizontales
  - Picks con `uncertainty_s` y `snr_db`
- Magnitud local Wood-Anderson (ML):
  - PAZ reales (Uhrhammer & Collins 1990; polos ±4.44 rad/s, gain=2800)
  - Calibración regional: CSN Chile, Hutton-Boore California, Colombia, Brasil
  - Incertidumbre explícita (`ML ≈ X.X ± 1.0`)
- **Localización 3D** por grid-search (x, y, profundidad)
- Generador de datos sintéticos (`src/tools/simulator.py`)

### Análisis espectral
- Espectrograma (ventanas Hann/Hamming/Blackman, overlap configurable)
- FFT con normalización RMS, frecuencia dominante anotada
- PSD Welch con `detrend='linear'`, unidades `dB re counts²/Hz`
- **HVSR** — método Nakamura (1989), suavizado en octavas, f₀ anotada
- **RotD50/RotD100** — estándar PEER (Boore, 2010)
- **Espectros de diseño** — NCh433 (DS61-2011) + ASCE 7-22

### Sistema IA (8 agentes + calibración ML)
| Agente | Modelo | Función |
|--------|--------|---------|
| QC V1 | deepseek-chat | Evaluación de calidad (ACCEPTED/CONDITIONED/REJECTED) |
| Processing V2 | nemotron-nano | Recomendación de filtros y corrección de baseline |
| IMs Interpreter | nemotron-nano | Interpretación de PGA/PGV/Arias/CAV, detección outliers |
| Normative Comparison | deepseek-chat | Comparación vs NCh433/ASCE7-22 |
| Catalog Correlator | nemotron-nano | USGS/EMSC/CSN + distancia epicentral |
| COSMOS Synthesizer | deepseek-chat | Reporte final con estructura COSMOS |
| QA Auditor | deepseek-chat | Cross-consistency entre agentes |
| Magnitude Estimator | deepseek-chat | ML con calibración CSN Chile |

**Modelos locales (Ollama):** Configuración por tarea disponible. Si Ollama está corriendo en `localhost:11434`, los agentes usan modelos locales (mistral, gemma2:2b, codellama). Sinon fallback automático a OpenRouter.

### 3 Interfaces

| Interfaz | Tecnología | Uso |
|----------|-----------|-----|
| Streamlit | Python + Plotly | Análisis interactivo en escritorio |
| SPA Web | HTML/JS + Plotly.js | Dashboard liviano deployable a Pages |
| API REST | FastAPI + Swagger | Integración con otros sistemas |
| CLI | Python argparse | Procesamiento batch headless |

---

## 🏗️ Estructura

```
streamlit_app.py          → Entry point Streamlit (11 páginas)
src/
├── server.py             → FastAPI REST (18 endpoints)
├── cli.py                → CLI batch processing
├── core/                 → Algoritmos sismológicos (ObsPy)
│   ├── magnitude.py      → ML Wood-Anderson + calibración regional
│   ├── magnitude_backup.py → Versión legacy + WA con respuesta instrumental
│   ├── picking.py        → STA/LTA con detección P/S
│   ├── intensity_measures.py → PGA, PGV, PGD, Arias, CAV
│   ├── hvsr.py           → HVSR método Nakamura
│   ├── rotd50.py         → RotD50/RotD100
│   ├── design_spectra.py → NCh433 + ASCE 7-22
│   ├── data_reader.py    → Carga multi-formato
│   ├── signal_processing.py → Filtros digitales
│   ├── signal_qc.py      → Control de calidad COSMOS
│   └── location/         → Localización 1D/3D
├── ai_agent/             → 8 agentes IA (Agno v2)
│   ├── seismic_interpreter.py → Orquestador principal
│   ├── earthquake_search.py → Catálogos USGS/EMSC
│   ├── report_generator.py → Reportes HTML/Markdown
│   ├── dynamic_config.py → Configuración dinámica de modelos
│   └── ollama_utils.py  → Health check + perfiles Ollama
├── tools/simulator.py    → Generador de datos sintéticos
├── visualization/        → Gráficos Plotly
├── streamlit_utils/      → Session state, helpers UI
└── utils/                → Config, logger (JSON estructurado), geo

frontend/                 → SPA estática (8 páginas, Plotly.js, dark/light theme)
pages/                    → 11 páginas Streamlit
tests/                    → 17 archivos, 202+ tests (incluye tests 3D location)
config/agents_config.yaml → Configuración principal de agentes
scripts/                  → load_demo.sh, validate_demo.sh, validate_pilot.sh
requirements/
  base.txt                → Dependencias de producción
  dev.txt                 → Dependencias de desarrollo
.github/workflows/ci.yml  → CI/CD pipeline
```

---

## ⚙️ Instalación

```bash
git clone https://github.com/nibaldox/Seismic-AIagent.git
cd Seismic-AIagent
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Editar API keys
streamlit run streamlit_app.py
```

### Docker
```bash
docker-compose up -d
```

### Demo rápido
```bash
./scripts/load_demo.sh   # Carga dataset demo desde data/
./scripts/validate_demo.sh  # Verifica que todo funciona
```

---

## 🔧 Configuración IA

Variables de entorno en `.env`:

```ini
OPENROUTER_API_KEY=sk-or-v1-xxxxx   # Requerido
OPENAI_API_KEY=sk-xxxxx              # Opcional
ANTHROPIC_API_KEY=sk-ant-xxxxx       # Opcional
OLLAMA_HOST=http://localhost:11434   # Opcional, para modelos locales
USGS_API_URL=https://earthquake.usgs.gov/fdsnws/event/1
EMSC_API_URL=https://www.seismicportal.eu/fdsnws/event/1
```

Modelos soportados: DeepSeek Chat v3.1, NVIDIA Nemotron Nano, Gemma 3, Kimi K2, Grok 4, GLM 4.5, Qwen3, LM Studio (local). **Ollama local:** mistral (análisis), gemma2:2b (búsqueda), codellama (código). Los modelos se asignan por tarea en `config/agno_config.yaml`.

---

## 📐 Calibración ML Regional

Configurable en `config/agents_config.yaml`:

| Región | Referencia | Uso |
|--------|-----------|-----|
| `csn_chile` ✅ activa | CSN / Barrientos (1980) | Chile, subducción andina |
| `hutton_boore_california` | Hutton & Boore (1987) | Sur de California |
| `langer_colombia` | Langer et al. (1987) | Colombia, Andes del Norte |
| `usp_brasil` | Assumpção et al. (2002) | Brasil, escudo estable |
| `richter_original` | Richter (1935) | Referencia histórica |

---

## 🔗 Endpoints API

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/analyze` | POST | Upload + análisis completo |
| `/api/datasets` | GET | Listar datasets |
| `/api/datasets/{name}` | GET | Info de dataset |
| `/api/datasets/{name}/waveform` | GET | Waveform + picks |
| `/api/datasets/{name}/correct` | POST | Filtro o baseline correction |
| `/api/datasets/{name}/reset` | POST | Reset traza a V0 |
| `/api/datasets/{name}/picks` | POST | Detectar fases P/S |
| `/api/datasets/{name}/ims` | GET | Intensity measures |
| `/api/datasets/{name}/qc` | GET | Control de calidad |
| `/api/datasets/{name}/spectrum/fft` | GET | FFT |
| `/api/datasets/{name}/spectrum/psd` | GET | PSD Welch |
| `/api/datasets/{name}/spectrum/spectro` | GET | Espectrograma |
| `/api/datasets/{name}/spectrum/hvsr` | GET | HVSR Nakamura |
| `/api/datasets/{name}/spectrum/rotd50` | GET | RotD50 |
| `/api/datasets/{name}/spectrum/design` | GET | Espectro de diseño NCh433/ASCE |
| `/api/datasets/{name}/magnitude` | GET | Magnitud ML |
| `/api/datasets/{name}/location` | POST | Localización 3D (grid-search) |
| `/api/datasets/{name}/report/html` | GET | Reporte HTML |
| `/api/datasets/{name}/report/excel` | GET | Exportar Excel |
| `/api/location/demo` | GET | Demo localización |

---

## 📚 Documentación

| Archivo | Contenido |
|---------|-----------|
| `AGENTS.md` | Guía para asistentes IA (opencode, Claude Code) |
| `docs/USER_GUIDE.md` | Guía paso a paso |
| `docs/TECHNICAL_DOCS.md` | Arquitectura y APIs |
| `docs/AGENT_MODIFICATION_GUIDE.md` | Cómo modificar agentes |
| `docs/CLIENT_MANUAL.md` | Manual de operación para clientes |
| `docs/DIAGNOSTIC.md` | Guía de diagnóstico de fallos |
| `docs/OFFLINE.md` | Guía de uso offline / PyInstaller |
| `docs/PILOT_CHECKLIST.md` | Checklist de despliegue en cliente |

---

## 🧪 CI/CD (GitHub Actions)

4 jobs automáticos en push a `main`:

1. **Tests** — pytest suite completa
2. **Lint** — flake8
3. **Docker** — Build image multi-stage con cache GHA
4. **Deploy Pages** — Frontend SPA a GitHub Pages

---

<div align="center">
<strong>v2.1</strong> — Streamlit + FastAPI + CLI + SPA Frontend + GitHub Pages + GitHub Actions<br>
Hecho para análisis sísmico operativo asistido por IA · Optimizado para sismicidad de Chile<br>
<a href="AGENTS.md">AGENTS.md</a> · <a href="docs/TECHNICAL_DOCS.md">Technical Docs</a>
</div>