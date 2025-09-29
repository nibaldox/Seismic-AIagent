# Seismic Backend (FastAPI)

Backend Python que expone endpoints para análisis sísmico y gráficos generados con Plotly.

## Endpoints iniciales
- `GET /health` -> estado del servicio
- `POST /waveform/plot` -> genera PNG de waveform a partir de un archivo subido
- `POST /spectrum/plot` -> genera PNG de espectrograma/FFT/PSD

## Desarrollo
- Ejecutar con `uvicorn apps.backend.main:app --reload`
- Variables de entorno: `.env` (opcional)
