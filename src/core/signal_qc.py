"""
Control de calidad (QC) de registros sísmicos — etapa V0 → V1.

Implementa las verificaciones estándar COSMOS para determinar si un registro
es apto para procesamiento:

    ACEPTADO    — todas las verificaciones pasan
    CONDICIONADO — problemas menores; procesable con precaución
    RECHAZADO   — problemas graves; el registro no es confiable

Uso típico::

    from src.core.signal_qc import run_qc, qc_summary_markdown

    result = run_qc(trace)
    st.markdown(qc_summary_markdown(result))
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

import numpy as np

LOGGER = logging.getLogger(__name__)

# Umbrales por defecto (ajustables por el usuario si se expone en la UI)
_CLIP_RATIO_WARN = 0.01   # >1 % de muestras cerca del límite → CONDICIONADO
_CLIP_RATIO_REJECT = 0.05  # >5 % → RECHAZADO
_SNR_WARN_DB = 6.0         # SNR < 6 dB → CONDICIONADO
_SNR_REJECT_DB = 3.0       # SNR < 3 dB → RECHAZADO
_DRIFT_WARN_PCT = 5.0      # Deriva del baseline > 5 % del rango → CONDICIONADO
_DRIFT_REJECT_PCT = 20.0   # Deriva > 20 % → RECHAZADO
_MIN_DURATION_S = 10.0     # Duración mínima para análisis significativo


@dataclass
class QCResult:
    """Resultado completo del control de calidad de una traza."""

    trace_id: str = ""

    # --- Saturación / clipping ---
    clipped: bool = False
    clip_ratio: float = 0.0       # Fracción de muestras saturadas [0-1]
    n_clipped_samples: int = 0

    # --- Relación señal/ruido ---
    snr_db: float = 0.0
    noise_rms: float = 0.0
    signal_rms: float = 0.0
    noise_window_s: float = 0.0   # Duración de la ventana de ruido usada

    # --- Continuidad / gaps ---
    has_gaps: bool = False
    gaps: List[Dict] = field(default_factory=list)   # [{start_s, end_s, duration_s}]
    n_gaps: int = 0

    # --- Deriva de línea base ---
    baseline_drift: bool = False
    drift_magnitude_pct: float = 0.0  # % del rango pico a pico de la señal

    # --- Duración ---
    duration_s: float = 0.0
    short_record: bool = False

    # --- Veredicto ---
    verdict: Literal["ACEPTADO", "CONDICIONADO", "RECHAZADO"] = "ACEPTADO"
    reasons: List[str] = field(default_factory=list)   # Motivos del veredicto


# ---------------------------------------------------------------------------
# Funciones de análisis individuales
# ---------------------------------------------------------------------------

def detect_clipping(
    data: np.ndarray,
    threshold_pct: float = 0.99,
) -> Dict:
    """Detecta saturación (clipping) del ADC.

    Una muestra se considera saturada cuando su valor absoluto supera
    ``threshold_pct`` × max(|data|).  Retorna métricas para QCResult.
    """
    if data is None or len(data) == 0:
        return {"clipped": False, "clip_ratio": 0.0, "n_clipped_samples": 0}

    abs_data = np.abs(data)
    max_val = abs_data.max()
    if max_val == 0:
        return {"clipped": False, "clip_ratio": 0.0, "n_clipped_samples": 0}

    threshold = threshold_pct * max_val
    n_clipped = int(np.sum(abs_data >= threshold))
    clip_ratio = n_clipped / len(data)

    return {
        "clipped": clip_ratio > _CLIP_RATIO_WARN,
        "clip_ratio": float(clip_ratio),
        "n_clipped_samples": n_clipped,
    }


def compute_snr(
    data: np.ndarray,
    dt: float,
    noise_window_s: float = 10.0,
    signal_start_s: Optional[float] = None,
) -> Dict:
    """Calcula la relación señal/ruido usando ventana de pre-evento como ruido.

    Args:
        data: Array de amplitudes.
        dt: Intervalo de muestreo en segundos.
        noise_window_s: Duración de la ventana de ruido (primeros N segundos).
        signal_start_s: Inicio de la ventana de señal. Por defecto: fin del ruido.

    Returns:
        dict con snr_db, noise_rms, signal_rms, noise_window_s.
    """
    if data is None or len(data) == 0 or dt <= 0:
        return {"snr_db": 0.0, "noise_rms": 0.0, "signal_rms": 0.0, "noise_window_s": 0.0}

    noise_samples = max(1, int(noise_window_s / dt))
    noise_samples = min(noise_samples, len(data) // 3)  # máximo 1/3 del registro

    noise_segment = data[:noise_samples]
    noise_rms = float(np.sqrt(np.mean(noise_segment ** 2)))

    signal_start = int(signal_start_s / dt) if signal_start_s is not None else noise_samples
    signal_start = min(signal_start, len(data) - 1)
    signal_segment = data[signal_start:]

    if len(signal_segment) == 0:
        signal_segment = data

    signal_rms = float(np.sqrt(np.mean(signal_segment ** 2)))

    if noise_rms == 0:
        snr_db = 60.0 if signal_rms > 0 else 0.0
    else:
        ratio = signal_rms / noise_rms
        snr_db = float(20.0 * np.log10(ratio)) if ratio > 0 else -99.0

    return {
        "snr_db": round(snr_db, 1),
        "noise_rms": round(noise_rms, 6),
        "signal_rms": round(signal_rms, 6),
        "noise_window_s": round(noise_samples * dt, 2),
    }


def detect_gaps(trace) -> List[Dict]:
    """Detecta discontinuidades (gaps) en una traza ObsPy.

    Retorna lista de dicts con start_s, end_s, duration_s relativos al
    inicio de la traza.  Lista vacía si no hay gaps.
    """
    gaps = []

    # Intentar usar el método nativo de ObsPy si está disponible
    try:
        stream_gaps = trace.get_gaps() if hasattr(trace, "get_gaps") else []
        if stream_gaps:
            t0 = float(trace.stats.starttime)
            for g in stream_gaps:
                # g = [network, station, location, channel, starttime, endtime, duration, overlap]
                start_abs = float(g[4])
                end_abs = float(g[5])
                gaps.append({
                    "start_s": round(start_abs - t0, 3),
                    "end_s": round(end_abs - t0, 3),
                    "duration_s": round(float(g[6]), 3),
                })
            return gaps
    except Exception:
        pass

    # Fallback: detectar bloques de ceros largos como posibles gaps
    try:
        data = trace.data if hasattr(trace, "data") else np.asarray(trace)
        dt = float(trace.stats.delta) if hasattr(trace, "stats") else 1.0
        zero_mask = np.abs(data) < 1e-10
        in_gap = False
        gap_start = 0
        for i, is_zero in enumerate(zero_mask):
            if is_zero and not in_gap:
                in_gap = True
                gap_start = i
            elif not is_zero and in_gap:
                in_gap = False
                dur = (i - gap_start) * dt
                if dur > 0.5:  # ignorar micro-gaps < 0.5 s
                    gaps.append({
                        "start_s": round(gap_start * dt, 3),
                        "end_s": round(i * dt, 3),
                        "duration_s": round(dur, 3),
                    })
    except Exception as exc:
        LOGGER.debug("detect_gaps fallback falló: %s", exc)

    return gaps


def assess_baseline_drift(data: np.ndarray, dt: float) -> Dict:
    """Evalúa la deriva de la línea base ajustando un polinomio de grado 2.

    La magnitud de la deriva se expresa como porcentaje del rango pico a pico
    de la señal original.

    Returns:
        dict con drift_detected (bool) y drift_magnitude_pct (float).
    """
    if data is None or len(data) < 4 or dt <= 0:
        return {"drift_detected": False, "drift_magnitude_pct": 0.0}

    t = np.arange(len(data)) * dt
    try:
        coeffs = np.polyfit(t, data, 2)
        trend = np.polyval(coeffs, t)
        trend_range = float(trend.max() - trend.min())
        signal_range = float(data.max() - data.min())
        drift_pct = (trend_range / signal_range * 100.0) if signal_range > 0 else 0.0
    except Exception as exc:
        LOGGER.debug("assess_baseline_drift error: %s", exc)
        return {"drift_detected": False, "drift_magnitude_pct": 0.0}

    return {
        "drift_detected": drift_pct > _DRIFT_WARN_PCT,
        "drift_magnitude_pct": round(drift_pct, 1),
    }


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def run_qc(trace) -> QCResult:
    """Ejecuta el control de calidad completo sobre una traza ObsPy.

    Aplica todas las verificaciones y calcula el veredicto final según los
    umbrales COSMOS estándar.

    Args:
        trace: Traza ObsPy (``obspy.Trace``) o cualquier objeto con atributos
               ``.data`` y ``.stats``.

    Returns:
        :class:`QCResult` con todas las métricas y el veredicto.
    """
    result = QCResult()

    # --- Identificación ---
    try:
        result.trace_id = str(trace.id) if hasattr(trace, "id") else "desconocido"
    except Exception:
        result.trace_id = "desconocido"

    # --- Extraer datos y parámetros básicos ---
    try:
        data = np.asarray(trace.data, dtype=float)
        dt = float(trace.stats.delta)
        result.duration_s = round(len(data) * dt, 2)
    except Exception as exc:
        LOGGER.error("run_qc: no se pudo extraer datos de la traza: %s", exc)
        result.verdict = "RECHAZADO"
        result.reasons.append("No se pudieron extraer datos de la traza.")
        return result

    # --- Duración mínima ---
    if result.duration_s < _MIN_DURATION_S:
        result.short_record = True
        result.reasons.append(
            f"Registro muy corto: {result.duration_s:.1f}s (mínimo {_MIN_DURATION_S:.0f}s)."
        )

    # --- Clipping ---
    clip_info = detect_clipping(data)
    result.clipped = clip_info["clipped"]
    result.clip_ratio = clip_info["clip_ratio"]
    result.n_clipped_samples = clip_info["n_clipped_samples"]

    # --- SNR ---
    noise_window = min(10.0, result.duration_s * 0.2)
    snr_info = compute_snr(data, dt, noise_window_s=noise_window)
    result.snr_db = snr_info["snr_db"]
    result.noise_rms = snr_info["noise_rms"]
    result.signal_rms = snr_info["signal_rms"]
    result.noise_window_s = snr_info["noise_window_s"]

    # --- Gaps ---
    gaps = detect_gaps(trace)
    result.gaps = gaps
    result.n_gaps = len(gaps)
    result.has_gaps = len(gaps) > 0

    # --- Deriva de baseline ---
    drift_info = assess_baseline_drift(data, dt)
    result.baseline_drift = drift_info["drift_detected"]
    result.drift_magnitude_pct = drift_info["drift_magnitude_pct"]

    # --- Veredicto ---
    result.verdict = _compute_verdict(result)

    return result


def _compute_verdict(r: QCResult) -> Literal["ACEPTADO", "CONDICIONADO", "RECHAZADO"]:
    """Calcula el veredicto según los umbrales COSMOS."""
    # Condiciones de RECHAZO
    if r.snr_db < _SNR_REJECT_DB:
        r.reasons.append(f"SNR muy bajo: {r.snr_db:.1f} dB (umbral rechazo: {_SNR_REJECT_DB} dB).")
        return "RECHAZADO"
    if r.clip_ratio > _CLIP_RATIO_REJECT:
        r.reasons.append(
            f"Saturación severa: {r.clip_ratio*100:.1f}% de muestras (umbral: {_CLIP_RATIO_REJECT*100:.0f}%)."
        )
        return "RECHAZADO"
    if r.short_record:
        return "RECHAZADO"

    # Condiciones de CONDICIONADO
    conditioned = False
    if r.snr_db < _SNR_WARN_DB:
        r.reasons.append(f"SNR bajo: {r.snr_db:.1f} dB (recomendado ≥ {_SNR_WARN_DB} dB).")
        conditioned = True
    if r.clipped:
        r.reasons.append(
            f"Posible saturación: {r.clip_ratio*100:.2f}% de muestras cerca del límite del ADC."
        )
        conditioned = True
    if r.has_gaps:
        total_gap = sum(g["duration_s"] for g in r.gaps)
        r.reasons.append(f"{r.n_gaps} gap(s) detectado(s), duración total {total_gap:.1f}s.")
        conditioned = True
    if r.drift_magnitude_pct > _DRIFT_WARN_PCT:
        r.reasons.append(
            f"Deriva de baseline: {r.drift_magnitude_pct:.1f}% del rango de la señal. "
            "Se recomienda corrección V1."
        )
        conditioned = True

    if conditioned:
        return "CONDICIONADO"

    return "ACEPTADO"


# ---------------------------------------------------------------------------
# Utilidades de presentación
# ---------------------------------------------------------------------------

_VERDICT_EMOJI = {
    "ACEPTADO": "🟢",
    "CONDICIONADO": "🟡",
    "RECHAZADO": "🔴",
}


def qc_summary_markdown(result: QCResult) -> str:
    """Genera un resumen Markdown del resultado QC para mostrar en Streamlit."""
    emoji = _VERDICT_EMOJI.get(result.verdict, "⚪")
    lines = [
        f"### {emoji} {result.verdict} — `{result.trace_id}`",
        "",
        "| Métrica | Valor |",
        "|---------|-------|",
        f"| Duración | {result.duration_s:.1f} s |",
        f"| SNR | {result.snr_db:.1f} dB |",
        f"| Saturación | {result.clip_ratio*100:.2f}% ({result.n_clipped_samples} muestras) |",
        f"| Gaps | {result.n_gaps} |",
        f"| Deriva baseline | {result.drift_magnitude_pct:.1f}% |",
    ]

    if result.reasons:
        lines += ["", "**Observaciones:**"]
        for reason in result.reasons:
            lines.append(f"- {reason}")

    return "\n".join(lines)
