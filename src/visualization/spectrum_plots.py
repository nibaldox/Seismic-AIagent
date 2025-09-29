"""Spectral analysis plotting helpers."""

from __future__ import annotations

from typing import Any

import numpy as np
import plotly.graph_objects as go
from scipy import signal


def create_spectrogram(trace: Any, *, nfft: int = 256, overlap: float = 0.5, 
                      window_type: str = "hanning", colorscale: str = "Viridis") -> go.Figure:
    """Create a spectrogram plot for a single trace with enhanced options."""

    if not hasattr(trace, "data"):
        raise ValueError("Trace must expose a 'data' attribute.")

    data = np.asarray(trace.data)
    sample_rate = float(trace.stats.sampling_rate) if hasattr(trace, "stats") else 1.0
    
    # Seleccionar ventana
    window_functions = {
        "hanning": np.hanning,
        "hamming": np.hamming,
        "blackman": np.blackman
    }
    window = window_functions.get(window_type, np.hanning)(nfft)
    
    step = int(nfft * (1 - overlap)) or 1
    segments = [data[i : i + nfft] * window for i in range(0, len(data) - nfft, step)]
    
    if not segments:
        raise ValueError("Trace too short for spectrogram with the given parameters.")

    spectra = np.abs(np.fft.rfft(segments, axis=1))
    freqs = np.fft.rfftfreq(nfft, d=1.0 / sample_rate)
    times = np.arange(len(segments)) * (step / sample_rate)

    # Calcular tiempo absoluto si está disponible
    if hasattr(trace, "stats") and hasattr(trace.stats, "starttime"):
        start_time = trace.stats.starttime
        times_abs = [start_time + t for t in times]
        x_label = "Tiempo (UTC)"
        x_data = times_abs
    else:
        x_label = "Tiempo (s)"
        x_data = times

    fig = go.Figure(
        data=go.Heatmap(
            z=20 * np.log10(spectra + 1e-12),  # Evitar log(0)
            x=x_data,
            y=freqs,
            colorscale=colorscale,
            colorbar=dict(title="Potencia (dB)"),
        )
    )
    
    fig.update_layout(
        title=f"Espectrograma (NFFT={nfft}, Overlap={overlap:.0%})",
        xaxis_title=x_label, 
        yaxis_title="Frecuencia (Hz)",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=50, r=80, b=50, l=70),
    )
    
    # Auto-configurar rangos
    if len(x_data) > 0:
        fig.update_xaxes(range=[x_data[0], x_data[-1]])
    if len(freqs) > 0:
        fig.update_yaxes(range=[0, np.max(freqs)])
    
    return fig


def create_fft_plot(trace: Any, *, log_scale: bool = True, freq_limit: int = 25, 
                   window_type: str = "hanning") -> go.Figure:
    """Create an FFT magnitude plot for a single trace."""
    
    if not hasattr(trace, "data"):
        raise ValueError("Trace must expose a 'data' attribute.")
    
    data = np.asarray(trace.data)
    sample_rate = float(trace.stats.sampling_rate) if hasattr(trace, "stats") else 1.0
    
    # Aplicar ventana
    window_functions = {
        "hanning": np.hanning,
        "hamming": np.hamming, 
        "blackman": np.blackman
    }
    window = window_functions.get(window_type, np.hanning)(len(data))
    windowed_data = data * window
    
    # Calcular FFT
    fft_vals = np.fft.rfft(windowed_data)
    freqs = np.fft.rfftfreq(len(data), d=1.0 / sample_rate)
    magnitudes = np.abs(fft_vals)
    
    # Aplicar límite de frecuencia
    mask = freqs <= freq_limit
    freqs_plot = freqs[mask]
    mags_plot = magnitudes[mask]
    
    # Crear gráfico
    y_data = 20 * np.log10(mags_plot + 1e-12) if log_scale else mags_plot
    y_label = "Magnitud (dB)" if log_scale else "Magnitud"
    
    fig = go.Figure(
        data=go.Scatter(
            x=freqs_plot,
            y=y_data,
            mode="lines",
            name="FFT",
            line=dict(color="#74b9ff", width=2),
        )
    )
    
    fig.update_layout(
        title=f"FFT - Ventana {window_type.capitalize()}",
        xaxis_title="Frecuencia (Hz)",
        yaxis_title=y_label,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=50, r=20, b=50, l=70),
        showlegend=False,
    )
    
    return fig


def create_psd_plot(trace: Any, *, nperseg: int = 512, overlap: float = 0.75, 
                   log_scale: bool = True, freq_max: int = 50) -> go.Figure:
    """Create a Power Spectral Density plot using Welch method."""
    
    if not hasattr(trace, "data"):
        raise ValueError("Trace must expose a 'data' attribute.")
    
    data = np.asarray(trace.data)
    sample_rate = float(trace.stats.sampling_rate) if hasattr(trace, "stats") else 1.0
    
    # Calcular PSD usando método de Welch
    noverlap = int(nperseg * overlap)
    freqs, psd = signal.welch(
        data, 
        fs=sample_rate, 
        nperseg=nperseg, 
        noverlap=noverlap,
        window='hann'  # Usar 'hann' en lugar de 'hanning' que es válido para scipy
    )
    
    # Aplicar límite de frecuencia
    mask = freqs <= freq_max
    freqs_plot = freqs[mask]
    psd_plot = psd[mask]
    
    # Configurar escala
    y_data = 10 * np.log10(psd_plot + 1e-12) if log_scale else psd_plot
    y_label = "PSD (dB/Hz)" if log_scale else "PSD"
    
    fig = go.Figure(
        data=go.Scatter(
            x=freqs_plot,
            y=y_data,
            mode="lines",
            name="PSD",
            line=dict(color="#55efc4", width=2),
            fill="tonexty" if not log_scale else None,
            fillcolor="rgba(85, 239, 196, 0.3)",
        )
    )
    
    fig.update_layout(
        title=f"Densidad Espectral - Welch (nperseg={nperseg})",
        xaxis_title="Frecuencia (Hz)",
        yaxis_title=y_label,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=50, r=20, b=50, l=70),
        showlegend=False,
    )
    
    return fig
