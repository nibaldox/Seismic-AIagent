# SeismoAnalyzer Pro Roadmap

This document condenses the master requirements for the Rapid Seismic Analyzer and tracks their phased implementation.

## Phase Overview

1. **Core ingestion & visualization** – file loading, waveform viewer, baseline filters
2. **Advanced analysis** – spectral views, phase picking, magnitude calculators
3. **AI interpretation** – Agno-AGI agent team, contextual searches, Markdown reports
4. **Extended tooling** – location engine, Gecko histograms, export utilities
5. **Polish & deployment** – performance tuning, documentation, packaging

Each phase should produce an executable Streamlit app (`streamlit_app.py`) and pass unit tests (`pytest`).

## Testing Strategy

- Run `streamlit run streamlit_app.py` after each significant UI change
- Execute `pytest tests/` for regression coverage
- Add targeted CLI scripts for connectivity checks (USGS/EMSC, provider status)

## Deployment Targets

- Local desktop usage (PyInstaller bundle)
- Streamlit Cloud prototype
- Docker container for on-premise deployment

Update this roadmap as milestones are delivered (semantic versioning recommended).

## Recent Progress Snapshots

- **2025-05-22** — Bulk completion of tasks 8-22:
  - ✅ Ollama local profiles with health check (`src/ai_agent/ollama_utils.py`)
  - ✅ 3D location MVP (x/y/z grid search in `one_d_location.py`, integrated in API)
  - ✅ Synthetic 3D location tests (≥80% repeatability, error ≤5 km, RMS ≤0.5 s)
  - ✅ PyInstaller desktop spec (`acelerografo.spec` with full hidden imports)
  - ✅ Docker hardening: multi-stage build, non-root user, read-only FS, cap_drop ALL
  - ✅ Structured JSON logging with rotating file + trace IDs
  - ✅ Diagnostic guide (`DIAGNOSTIC.md`), Client Manual, Pilot Checklist
  - ✅ Demo dataset scripts (`load_demo.sh`, `validate_demo.sh`, `validate_pilot.sh`)
  - ✅ Requirements split into `base.txt` / `dev.txt`
  - ✅ `.dockerignore`, `.env.example`, `requirements/base.txt`, `requirements/dev.txt`
  - ✅ Bitácora updated (all tasks 8-22 marked complete)
- ✅ Unified dataset/session switching across uploader, waveform viewer, spectrum, and AI interpreter pages.
- ✅ Expanded Agno agent suite with phase identification, magnitude estimation, and QA specialists; added caching + monitoring hooks.
- ✅ Hardened USGS/EMSC integrations via retries/backoff and contextual error surfacing.
- ✅ Added Dockerfile for reproducible deployments (Streamlit served on port 8501).
- ✅ Reportes automáticos ahora se generan en español con secciones estandarizadas y niveles de confianza.