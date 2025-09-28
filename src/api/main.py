"""Aplicación FastAPI que expone los servicios de análisis sísmico."""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, status

from src.services.waveform_service import WaveformAnalysisService

from .config import ApiSettings, get_settings
from .dependencies import get_waveform_service
from .schemas import (
    MagnitudeRequest,
    MagnitudeResponse,
    PickSuggestionRequest,
    PickSuggestionResponse,
)

app = FastAPI(title="Seismic AI API", version="0.1.0")


@app.get("/health", summary="Revisión básica de salud")
def health(settings: ApiSettings = Depends(get_settings)) -> dict[str, object]:
    """Retorna información básica para monitoreo."""

    return {"status": "ok", "app": settings.app_name, "debug": settings.debug}


@app.post(
    "/waveform/picks/suggest",
    response_model=PickSuggestionResponse,
    summary="Genera sugerencias de picks STA/LTA",
)
def suggest_picks(
    payload: PickSuggestionRequest,
    service: WaveformAnalysisService = Depends(get_waveform_service),
) -> PickSuggestionResponse:
    """Deriva picks sugeridos a partir de la señal recibida."""

    trace = payload.waveform.to_trace()
    try:
        suggestions = service.suggest_picks(trace)
    except ValueError as exc:  # conversión de errores de validación
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return PickSuggestionResponse(suggestions=suggestions)


@app.post(
    "/waveform/magnitude",
    response_model=MagnitudeResponse,
    summary="Calcula magnitud local",
)
def compute_magnitude(
    payload: MagnitudeRequest,
    service: WaveformAnalysisService = Depends(get_waveform_service),
) -> MagnitudeResponse:
    """Ejecuta el algoritmo indicado y regresa la magnitud estimada."""

    trace = payload.waveform.to_trace()
    try:
        if payload.algorithm == "wood_anderson":
            result = service.estimate_magnitude_wood_anderson(
                picks=payload.picks,
                trace=trace,
            )
        else:
            result = service.estimate_magnitude_placeholder(
                picks=payload.picks,
                trace=trace,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return MagnitudeResponse.model_validate(result.model_dump())


__all__ = ["app"]
