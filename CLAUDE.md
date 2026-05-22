# AGENTS.md — SeismoAnalyzer Pro v2.0

Guía para asistentes de IA (opencode, Claude Code) al trabajar con este repositorio.

## Descripción General

Plataforma de análisis sísmico con 3 interfaces: **Streamlit** (web interactiva), **FastAPI REST** (API headless), **CLI** (batch processing). Incluye frontend SPA estático deployable a GitHub Pages + CI/CD via GitHub Actions.

Lenguaje: Python 3.13+. Frameworks: Streamlit 1.56, FastAPI, ObsPy, Plotly, Agno v2.

## Comandos Comunes

```bash
# Streamlit web
streamlit run streamlit_app.py          # → :8501

# API REST
python -m src.server                     # → :8000/api + :8000/app

# CLI batch
python -m src.cli "data/" -r -p "*.ms" -o out.json

# Tests
pytest -q                                 # 202 tests
pytest tests/test_server.py -v            # API tests
pytest tests/test_core.py::test_name -v   # Single test

# Lint
flake8 src/ pages/ tests/
```

## Arquitectura

```
streamlit_app.py          → Entry point Streamlit (11 páginas)
src/server.py             → FastAPI API + sirve frontend estático
src/cli.py                → CLI batch processing
src/
  core/                   → Algoritmos sismológicos (ObsPy)
  ai_agent/               → 7 agentes IA con Agno v2
  visualization/          → Gráficos Plotly
  streamlit_utils/        → Session state, helpers UI
  tools/simulator.py      → Generador de datos sintéticos
  utils/                  → Config, logger, geo
frontend/                 → SPA estática (7 páginas, Plotly.js)
pages/                    → 11 páginas Streamlit (00-10)
tests/                    → 17 archivos, 202 tests
.github/workflows/ci.yml  → CI/CD: test → lint → docker → Pages
```

### Endpoints API

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/analyze` | POST | Subir archivo sísmico |
| `/api/datasets` | GET | Listar datasets en caché |
| `/api/datasets/{name}` | GET | Info de dataset |
| `/api/datasets/{name}/waveform` | GET | Waveform data (downsampled) |
| `/api/datasets/{name}/spectrum` | GET | Espectro (FFT/PSD/HVSR/RotD50) |
| `/api/location/demo` | GET | Demo de localización |

### Módulos Core

- `data_reader.py` — FORMAT_REGISTRY: MSEED, SAC, SEG-2, Gecko .bin, Kelunji .ss
- `picking.py` — STA/LTA con detección P/S + SNR
- `magnitude.py` — ML Wood-Anderson, calibración regional (CSN Chile)
- `magnitude_backup.py` — Versión legacy + WA con respuesta instrumental
- `intensity_measures.py` — PGA, PGV, PGD, Arias, CAV, duración significativa
- `hvsr.py` — HVSR método Nakamura + criterios SESAME
- `rotd50.py` — RotD50/RotD100 (PEER)
- `design_spectra.py` — NCh433 (Chile) + ASCE 7-22
- `earthquake_search.py` — Catálogos USGS/EMSC

### Data Flow

1. **Upload** (Streamlit/API/CLI) → DataReader parsea archivo
2. **Procesamiento** → Filtros → Picks STA/LTA → IMs → Espectros
3. **AI** → 7 agentes Agno v2 vía OpenRouter o LM Studio
4. **Output** → Dashboard Streamlit / API JSON / CLI JSON / SPA web

### Bugs Conocidos / Fixes Aplicados

- `magnitude_backup.py:419` — docstring sin cerrar (FIXED)
- `earthquake_search.py` — `datetime.utcnow()` deprecado en 3.14 (FIXED)
- `test_core.py::test_data_reader_requires_obspy` — esperaba `ImportError` (FIXED → `DataReadError`)

## Tests (202 ✔️, 4 ⏭️)

```bash
pytest -q
# 202 passed, 4 skipped
```

Los 4 skipped son esperados: 2 por monkeypatch/legacy, 2 por requerir API key externa.

## Docs Relacionados

- `docs/TECHNICAL_DOCS.md` — arquitectura detallada
- `docs/AGENT_MODIFICATION_GUIDE.md` — cómo modificar agentes IA
- `docs/USER_GUIDE.md` — guía de usuario
