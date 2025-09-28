"""Esquemas Pydantic expuestos por la API."""

from __future__ import annotations

from typing import List, Literal

import numpy as np
from obspy import Trace
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.services import MagnitudeEstimate, PickPayload, PickSuggestion


class WaveformPayload(BaseModel):
    """Representa los datos mínimos para construir un ``Trace`` de ObsPy."""

    samples: List[float] = Field(min_length=1, description="Serie temporal del sismograma")
    sampling_rate: float = Field(gt=0, description="Frecuencia de muestreo en Hz")
    station: str = Field(default="UNK", min_length=1, description="Código de estación")
    channel: str = Field(default="HHZ", min_length=1, description="Código de canal")

    model_config = ConfigDict(extra="forbid")

    @field_validator("station", "channel", mode="before")
    @classmethod
    def _strip(cls, value: str) -> str:
        return str(value).strip().upper()

    def to_trace(self) -> Trace:
        """Convierte la carga útil en un ``Trace`` listo para análisis."""

        data = np.asarray(self.samples, dtype=float)
        trace = Trace(data=data)
        trace.stats.sampling_rate = float(self.sampling_rate)
        trace.stats.station = self.station
        trace.stats.channel = self.channel
        return trace


class PickSuggestionRequest(BaseModel):
    """Solicitud para obtener sugerencias de picks."""

    waveform: WaveformPayload


class MagnitudeRequest(BaseModel):
    """Solicitud para calcular magnitudes locales."""

    waveform: WaveformPayload
    picks: List[PickPayload] = Field(min_length=1, description="Lista de picks validados")
    algorithm: Literal["wood_anderson", "legacy"] = Field(
        default="wood_anderson",
        description="Algoritmo a ejecutar",
    )

    model_config = ConfigDict(extra="forbid")


class MagnitudeResponse(MagnitudeEstimate):
    """Respuesta derivada directamente del modelo de servicios."""

    model_config = ConfigDict(extra="ignore")


class PickSuggestionResponse(BaseModel):
    """Contenedor para normalizar la respuesta de sugerencias."""

    suggestions: List[PickSuggestion]

    model_config = ConfigDict(extra="ignore")
