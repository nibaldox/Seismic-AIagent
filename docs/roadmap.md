# SeismoAnalyzer Pro Roadmap

This document condenses the master requirements for the Rapid Seismic Analyzer and tracks their phased implementation.

## Phase Overview

1. **Core ingestion & visualization** – file loading, waveform viewer, baseline filters
2. **Advanced analysis** – spectral views, phase picking, magnitude calculators
3. **AI interpretation** – Agno-AGI agent team, contextual searches, Markdown reports
4. **Extended tooling** – location engine, Gecko histograms, export utilities
5. **Polish & deployment** – performance tuning, documentation, packaging

Each phase should produce an executable Streamlit app (`streamlit_app.py`) and pass unit tests (`pytest`).

## Recent Progress

- 2025-09-24 – AI interpreter page gains multi-trace selection, context-aware prompts, and persistent AI outputs that reset whenever a new dataset is registered.

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

- ✅ Unified dataset/session switching across uploader, waveform viewer, spectrum, and AI interpreter pages.
- ✅ Expanded Agno agent suite with phase identification, magnitude estimation, and QA specialists; added caching + monitoring hooks.
- ✅ Hardened USGS/EMSC integrations via retries/backoff and contextual error surfacing.
- ✅ Added Dockerfile for reproducible deployments (Streamlit served on port 8501).
- ✅ Reportes automáticos ahora se generan en español con secciones estandarizadas y niveles de confianza.
