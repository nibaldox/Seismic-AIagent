"""Módulo HVSR (Horizontal-to-Vertical Spectral Ratio).

Implementa el método de Nakamura (1989) con criterios de calidad SESAME (2004).

Pasos del algoritmo
-------------------
1. División en ventanas anti-solapantes (por defecto 50% de solapamiento).
2. Cálculo de FFT por ventana con taper coseno.
3. Suavizado Konno-Ohmachi (parámetro b) en cada ventana.
4. H/V(f) = sqrt((FFT_H1² + FFT_H2²) / 2) / FFT_Z  por ventana.
5. Promedio y desviación estándar de H/V entre ventanas.
6. Detección del pico f0 y evaluación de criterios SESAME básicos.

Referencias
-----------
- Nakamura, Y. (1989). A method for dynamic characteristics estimation of
  subsurface using microtremor on the ground surface.
- SESAME European Research Project (2004). Guidelines for the implementation
  of the H/V spectral ratio technique. WP12 — Deliverable D23.12.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Estructuras de resultado
# ---------------------------------------------------------------------------

@dataclass
class SESAMECriteria:
    """Criterios básicos de fiabilidad SESAME para la curva H/V."""

    # Criterio 1: suficientes ciclos (f0 * Lw * Nw ≥ 200)
    c1_passed: bool = False
    c1_detail: str = ""

    # Criterio 2: coeficiente de variación σ_A / A < 2 en el pico
    c2_passed: bool = False
    c2_detail: str = ""

    # Criterio 3: pico claro — amplitud H/V(f0) ≥ 2
    c3_passed: bool = False
    c3_detail: str = ""

    @property
    def all_passed(self) -> bool:
        return self.c1_passed and self.c2_passed and self.c3_passed

    @property
    def summary(self) -> str:
        status = "✅ VÁLIDA" if self.all_passed else "⚠️ DUDOSA"
        lines = [f"Curva H/V: {status}"]
        for label, passed, detail in [
            ("C1 (ciclos suficientes)", self.c1_passed, self.c1_detail),
            ("C2 (σ/A < 2 en f0)",     self.c2_passed, self.c2_detail),
            ("C3 (pico claro ≥ 2)",    self.c3_passed, self.c3_detail),
        ]:
            icon = "✅" if passed else "❌"
            lines.append(f"  {icon} {label}: {detail}")
        return "\n".join(lines)


@dataclass
class HVSRResult:
    """Resultado completo del análisis HVSR."""

    freqs: np.ndarray            # Frecuencias [Hz]
    hv_mean: np.ndarray          # H/V media entre ventanas
    hv_std: np.ndarray           # Desviación estándar H/V
    hv_plus1: np.ndarray         # hv_mean + hv_std
    hv_minus1: np.ndarray        # hv_mean - hv_std  (≥ 0)
    f0_hz: float                 # Frecuencia fundamental [Hz]
    a0: float                    # Amplitud H/V en f0
    t0_s: float                  # Período fundamental [s]
    n_windows: int               # Número de ventanas usadas
    window_len_s: float          # Longitud de ventana [s]
    sesame: SESAMECriteria = field(default_factory=SESAMECriteria)
    # H/V por ventana: shape (n_windows, n_freqs) — opcional
    hv_windows: Optional[np.ndarray] = None


# ---------------------------------------------------------------------------
# Suavizado Konno-Ohmachi
# ---------------------------------------------------------------------------

def _konno_ohmachi_weights(freqs: np.ndarray, fc: float, b: float = 40.0) -> np.ndarray:
    """Calcula el vector de pesos KO centrado en fc."""
    weights = np.zeros(len(freqs))
    for i, f in enumerate(freqs):
        if f <= 0 or fc <= 0:
            continue
        if f == fc:
            weights[i] = 1.0
        else:
            x = b * np.log10(f / fc)
            if abs(x) < 1e-6:
                weights[i] = 1.0
            else:
                sin_x = np.sin(x)
                weights[i] = (sin_x / x) ** 4
    s = weights.sum()
    return weights / s if s > 0 else weights


def konno_ohmachi_smooth(spectrum: np.ndarray, freqs: np.ndarray, b: float = 40.0) -> np.ndarray:
    """Suaviza un espectro de amplitud con la ventana Konno-Ohmachi.

    Args:
        spectrum: Amplitudes espectrales (valores reales ≥ 0).
        freqs:    Frecuencias correspondientes [Hz].
        b:        Parámetro de ancho de banda (mayor → más estrecho).
                  Valores típicos: 20–80.

    Returns:
        Espectro suavizado, mismo shape que ``spectrum``.
    """
    smoothed = np.zeros_like(spectrum)
    for i, fc in enumerate(freqs):
        if fc <= 0:
            continue
        w = _konno_ohmachi_weights(freqs, fc, b=b)
        smoothed[i] = np.dot(w, spectrum)
    return smoothed


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def compute_hvsr(
    acc_h1: np.ndarray,
    acc_h2: np.ndarray,
    acc_z: np.ndarray,
    dt: float,
    *,
    window_len_s: float = 20.0,
    overlap: float = 0.5,
    ko_b: float = 40.0,
    freq_min: float = 0.1,
    freq_max: float = 20.0,
    taper_frac: float = 0.05,
    store_windows: bool = False,
) -> HVSRResult:
    """Calcula la curva H/V por el método Nakamura con suavizado Konno-Ohmachi.

    Args:
        acc_h1:       Aceleración horizontal 1 (N, Y, eje 2), array 1-D.
        acc_h2:       Aceleración horizontal 2 (E, X, eje 1), array 1-D.
        acc_z:        Aceleración vertical, array 1-D.
        dt:           Paso de tiempo [s].
        window_len_s: Longitud de cada ventana [s].
        overlap:      Solapamiento entre ventanas (0–0.9).
        ko_b:         Parámetro Konno-Ohmachi (ancho de banda).
        freq_min:     Frecuencia mínima de análisis [Hz].
        freq_max:     Frecuencia máxima de análisis [Hz].
        taper_frac:   Fracción coseno para taper (0–0.5).
        store_windows: Si True, guarda H/V por ventana en el resultado.

    Returns:
        HVSRResult con curva H/V y criterios SESAME.

    Raises:
        ValueError: Si los arrays son demasiado cortos para la ventana requerida.
    """
    n = min(len(acc_h1), len(acc_h2), len(acc_z))
    acc_h1 = np.asarray(acc_h1[:n], dtype=float)
    acc_h2 = np.asarray(acc_h2[:n], dtype=float)
    acc_z  = np.asarray(acc_z[:n],  dtype=float)

    win_samples = int(window_len_s / dt)
    if win_samples < 16:
        raise ValueError(f"Ventana demasiado corta ({win_samples} muestras). Aumenta window_len_s.")
    if win_samples > n:
        raise ValueError(
            f"Señal ({n} muestras = {n * dt:.1f} s) más corta que la ventana requerida "
            f"({win_samples} muestras = {window_len_s:.1f} s)."
        )

    step = max(1, int(win_samples * (1.0 - overlap)))

    # Taper coseno
    taper = np.ones(win_samples)
    tap_n = max(1, int(taper_frac * win_samples))
    taper[:tap_n]  = 0.5 * (1 - np.cos(np.pi * np.arange(tap_n) / tap_n))
    taper[-tap_n:] = 0.5 * (1 - np.cos(np.pi * (np.arange(tap_n, 0, -1) - 1) / tap_n))

    # Frecuencias FFT
    nfft = win_samples
    freqs_all = np.fft.rfftfreq(nfft, d=dt)
    mask = (freqs_all >= freq_min) & (freqs_all <= freq_max)
    freqs = freqs_all[mask]
    if len(freqs) < 3:
        raise ValueError(
            f"Sin frecuencias en rango [{freq_min}, {freq_max}] Hz con nfft={nfft}."
        )

    # Recopilar H/V por ventana
    hv_list: List[np.ndarray] = []
    start = 0
    while start + win_samples <= n:
        seg_h1 = acc_h1[start:start + win_samples] * taper
        seg_h2 = acc_h2[start:start + win_samples] * taper
        seg_z  = acc_z[start:start + win_samples]  * taper

        fft_h1 = np.abs(np.fft.rfft(seg_h1))[mask]
        fft_h2 = np.abs(np.fft.rfft(seg_h2))[mask]
        fft_z  = np.abs(np.fft.rfft(seg_z))[mask]

        # Suavizado Konno-Ohmachi
        fft_h1 = konno_ohmachi_smooth(fft_h1, freqs, b=ko_b)
        fft_h2 = konno_ohmachi_smooth(fft_h2, freqs, b=ko_b)
        fft_z  = konno_ohmachi_smooth(fft_z,  freqs, b=ko_b)

        # Evitar división por cero
        fft_z_safe = np.where(fft_z > 1e-30, fft_z, 1e-30)
        hv = np.sqrt((fft_h1 ** 2 + fft_h2 ** 2) / 2.0) / fft_z_safe
        hv_list.append(hv)
        start += step

    if not hv_list:
        raise ValueError("No se generaron ventanas válidas. Señal demasiado corta.")

    hv_arr = np.stack(hv_list, axis=0)           # (n_windows, n_freqs)
    hv_mean = np.mean(hv_arr, axis=0)
    hv_std  = np.std(hv_arr, axis=0, ddof=min(1, len(hv_list) - 1))

    # Pico f0 (excluye el bin DC)
    search_mask = freqs > 0
    if search_mask.any():
        idx_peak = int(np.argmax(hv_mean[search_mask]))
        f0 = float(freqs[search_mask][idx_peak])
        a0 = float(hv_mean[search_mask][idx_peak])
    else:
        f0 = float(freqs[np.argmax(hv_mean)])
        a0 = float(np.max(hv_mean))

    t0 = 1.0 / f0 if f0 > 0 else float("inf")
    n_windows = len(hv_list)

    # ── Criterios SESAME básicos ──────────────────────────────────────────────
    sesame = SESAMECriteria()

    # C1: f0 * Lw * Nw ≥ 200
    cycles = f0 * window_len_s * n_windows
    sesame.c1_passed = cycles >= 200.0
    sesame.c1_detail = f"f0={f0:.2f} Hz × Lw={window_len_s:.0f} s × Nw={n_windows} = {cycles:.0f} (≥200)"

    # C2: σ_A(f0) / A(f0) < 2
    if a0 > 0:
        cv = float(hv_std[search_mask][idx_peak]) / a0 if search_mask.any() else 0.0
        sesame.c2_passed = cv < 2.0
        sesame.c2_detail = f"σ/A = {cv:.2f} (<2)"
    else:
        sesame.c2_detail = "Amplitud nula en f0"

    # C3: A(f0) ≥ 2
    sesame.c3_passed = a0 >= 2.0
    sesame.c3_detail = f"A(f0) = {a0:.2f} (≥2)"

    return HVSRResult(
        freqs=freqs,
        hv_mean=hv_mean,
        hv_std=hv_std,
        hv_plus1=hv_mean + hv_std,
        hv_minus1=np.maximum(0.0, hv_mean - hv_std),
        f0_hz=f0,
        a0=a0,
        t0_s=t0,
        n_windows=n_windows,
        window_len_s=window_len_s,
        sesame=sesame,
        hv_windows=hv_arr if store_windows else None,
    )
