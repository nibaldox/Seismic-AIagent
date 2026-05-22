"""Spectral analysis plotting helpers."""

from __future__ import annotations

from typing import Any, Optional

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
        # Convertir UTCDateTime a strings para Plotly
        times_abs = [(start_time + t).isoformat() for t in times]
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
    """Create an FFT magnitude plot for a single trace.

    Amplitude is normalised by the window's RMS so that different window types
    produce comparable absolute values (avoids the systematic ~3 dB bias of a
    raw Hann window versus a rectangular window).
    """

    if not hasattr(trace, "data"):
        raise ValueError("Trace must expose a 'data' attribute.")

    data = np.asarray(trace.data, dtype=float)
    # Demean before transform to suppress DC spike
    data = data - data.mean()
    sample_rate = float(trace.stats.sampling_rate) if hasattr(trace, "stats") else 1.0

    # Limitar nfft para evitar FFTs de millones de puntos en registros largos.
    # 65 536 muestras dan resolución de frecuencia < 4 mHz a 200 Hz — más que
    # suficiente para análisis sísmico de campo cercano.
    _MAX_FFT = 65_536
    nfft = min(len(data), _MAX_FFT)
    data_fft = data[:nfft]

    window_functions = {
        "hanning": np.hanning,
        "hamming": np.hamming,
        "blackman": np.blackman
    }
    win = window_functions.get(window_type, np.hanning)(nfft)
    # Normalise by RMS of window so amplitude is independent of window choice
    win_rms = np.sqrt(np.mean(win ** 2))
    windowed_data = data_fft * win / (win_rms if win_rms > 0 else 1.0)

    fft_vals = np.fft.rfft(windowed_data, n=nfft)
    freqs = np.fft.rfftfreq(nfft, d=1.0 / sample_rate)
    # Single-sided amplitude spectrum (×2 for all bins except DC and Nyquist)
    magnitudes = np.abs(fft_vals) * 2.0 / nfft
    if len(magnitudes) > 1:
        magnitudes[0] /= 2.0
        magnitudes[-1] /= 2.0

    mask = freqs <= freq_limit
    freqs_plot = freqs[mask]
    mags_plot = magnitudes[mask]

    # Downsampling de seguridad: nunca enviar más de 4000 puntos al browser
    _MAX_PLOT_PTS = 4_000
    if len(freqs_plot) > _MAX_PLOT_PTS:
        step = len(freqs_plot) // _MAX_PLOT_PTS
        freqs_plot = freqs_plot[::step]
        mags_plot  = mags_plot[::step]

    y_data = 20 * np.log10(mags_plot + 1e-12) if log_scale else mags_plot
    y_label = "Amplitud (dB re 1 counts)" if log_scale else "Amplitud (counts)"

    # Frecuencia dominante (excluir DC bin)
    dominant_annotations = []
    if len(freqs_plot) > 1 and mags_plot.size > 1:
        search_start = 1  # skip DC
        dom_idx = int(np.argmax(mags_plot[search_start:])) + search_start
        dom_freq = float(freqs_plot[dom_idx])
        dom_val = float(y_data[dom_idx])
        dominant_annotations.append(dict(
            x=dom_freq, y=dom_val,
            xanchor="left", yanchor="bottom",
            text=f"<b>f={dom_freq:.2f} Hz</b>",
            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5,
            arrowcolor="#ffeaa7", font=dict(size=11, color="#ffeaa7"),
            ax=20, ay=-30,
        ))

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
        annotations=dominant_annotations,
    )

    return fig


def create_psd_plot(trace: Any, *, nperseg: int = 512, overlap: float = 0.75,
                   log_scale: bool = True, freq_max: int = 50) -> go.Figure:
    """Create a Power Spectral Density plot using Welch method.

    Uses ``detrend='linear'`` in each segment to suppress baseline drift that
    would otherwise contaminate low-frequency bins, and clips ``nperseg`` to
    the actual data length so short traces don't raise an error.
    """

    if not hasattr(trace, "data"):
        raise ValueError("Trace must expose a 'data' attribute.")

    data = np.asarray(trace.data, dtype=float)
    sample_rate = float(trace.stats.sampling_rate) if hasattr(trace, "stats") else 1.0

    # Guard: nperseg must not exceed data length
    nperseg_safe = min(nperseg, len(data))
    noverlap = int(nperseg_safe * overlap)

    freqs, psd = signal.welch(
        data,
        fs=sample_rate,
        nperseg=nperseg_safe,
        noverlap=noverlap,
        window='hann',
        detrend='linear',   # Remove linear trend per segment → cleaner low-f bins
        scaling='density',  # Units: counts²/Hz  (physical when data is in counts)
    )

    mask = freqs <= freq_max
    freqs_plot = freqs[mask]
    psd_plot = psd[mask]

    y_data = 10 * np.log10(psd_plot + 1e-30) if log_scale else psd_plot
    y_label = "PSD (dB re counts²/Hz)" if log_scale else "PSD (counts²/Hz)"

    # Frecuencia dominante (excluir DC)
    dominant_annotations = []
    if len(freqs_plot) > 1 and psd_plot.size > 1:
        dom_idx = int(np.argmax(psd_plot[1:])) + 1
        dom_freq = float(freqs_plot[dom_idx])
        dom_val = float(y_data[dom_idx])
        dominant_annotations.append(dict(
            x=dom_freq, y=dom_val,
            xanchor="left", yanchor="bottom",
            text=f"<b>f={dom_freq:.2f} Hz</b>",
            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5,
            arrowcolor="#ffeaa7", font=dict(size=11, color="#ffeaa7"),
            ax=20, ay=-30,
        ))

    fig = go.Figure(
        data=go.Scatter(
            x=freqs_plot,
            y=y_data,
            mode="lines",
            name="PSD",
            line=dict(color="#55efc4", width=2),
            fill="tozeroy" if not log_scale else None,
            fillcolor="rgba(85, 239, 196, 0.3)",
        )
    )

    fig.update_layout(
        title=f"Densidad Espectral de Potencia - Welch (nperseg={nperseg_safe}, overlap={overlap:.0%})",
        xaxis_title="Frecuencia (Hz)",
        yaxis_title=y_label,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=50, r=20, b=50, l=70),
        showlegend=False,
        annotations=dominant_annotations,
    )

    return fig


def create_hvsr_plot(
    trace_h1: Any,
    trace_h2: Any,
    trace_z: Any,
    *,
    nperseg: int = 512,
    overlap: float = 0.75,
    freq_min: float = 0.1,
    freq_max: float = 20.0,
    smooth_octaves: float = 0.1,
) -> go.Figure:
    """Compute and plot the Horizontal-to-Vertical Spectral Ratio (HVSR).

    Implements the Nakamura (1989) method:
        HVSR(f) = sqrt( [PSD_H1(f) + PSD_H2(f)] / 2 ) / PSD_Z(f)

    The H/V ratio peak frequency (f0) is a proxy for the fundamental resonance
    frequency of the soil column, widely used in site characterisation studies.

    Parameters
    ----------
    trace_h1, trace_h2 : ObsPy-like traces for the two horizontal components (E/N).
    trace_z            : ObsPy-like trace for the vertical component (Z).
    nperseg            : Welch window length in samples.
    overlap            : Welch segment overlap fraction (0–1).
    freq_min/freq_max  : Frequency range to display (Hz).
    smooth_octaves     : Konno-Ohmachi-style log-smoothing bandwidth in octaves.
                         Set to 0 to disable smoothing.
    """
    for tr, name in [(trace_h1, "H1"), (trace_h2, "H2"), (trace_z, "Z")]:
        if not hasattr(tr, "data"):
            raise ValueError(f"Trace {name} must expose a 'data' attribute.")

    sr = float(trace_z.stats.sampling_rate) if hasattr(trace_z, "stats") else 1.0
    nperseg_safe = min(nperseg, len(trace_z.data), len(trace_h1.data), len(trace_h2.data))
    noverlap = int(nperseg_safe * overlap)

    def _psd(tr: Any) -> tuple:
        d = np.asarray(tr.data, dtype=float)
        f, p = signal.welch(
            d, fs=sr, nperseg=nperseg_safe, noverlap=noverlap,
            window="hann", detrend="linear", scaling="density",
        )
        return f, p

    freqs, psd_h1 = _psd(trace_h1)
    _,     psd_h2 = _psd(trace_h2)
    _,     psd_z  = _psd(trace_z)

    # Combined horizontal PSD (geometric mean of H1 and H2)
    psd_h = np.sqrt(psd_h1 * psd_h2)

    # Avoid division by zero
    hvsr = np.sqrt(psd_h / (psd_z + 1e-30))

    # Optional log-domain smoothing (simplified octave-band boxcar)
    if smooth_octaves > 0 and len(freqs) > 10:
        hvsr_smooth = np.empty_like(hvsr)
        for i, f0 in enumerate(freqs):
            if f0 <= 0:
                hvsr_smooth[i] = hvsr[i]
                continue
            f_lo = f0 * 2 ** (-smooth_octaves / 2)
            f_hi = f0 * 2 ** (smooth_octaves / 2)
            mask = (freqs >= f_lo) & (freqs <= f_hi)
            hvsr_smooth[i] = float(np.mean(hvsr[mask])) if mask.any() else hvsr[i]
        hvsr = hvsr_smooth

    # Apply frequency limits
    mask = (freqs >= freq_min) & (freqs <= freq_max)
    freqs_plot = freqs[mask]
    hvsr_plot = hvsr[mask]

    # Find f0 (H/V peak excluding DC)
    annotations = []
    if hvsr_plot.size > 1:
        peak_idx = int(np.argmax(hvsr_plot))
        f0 = float(freqs_plot[peak_idx])
        hv0 = float(hvsr_plot[peak_idx])
        annotations.append(dict(
            x=f0, y=hv0,
            xanchor="left", yanchor="bottom",
            text=f"<b>f₀={f0:.2f} Hz</b>",
            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5,
            arrowcolor="#ffeaa7", font=dict(size=12, color="#ffeaa7"),
            ax=20, ay=-30,
        ))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=freqs_plot, y=hvsr_plot,
        mode="lines", name="H/V",
        line=dict(color="#a29bfe", width=2),
        fill="tozeroy", fillcolor="rgba(162,155,254,0.15)",
    ))
    # Reference line at H/V = 1 (no amplification)
    fig.add_hline(y=1.0, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dash"))

    fig.update_layout(
        title="Relación H/V Espectral — Método Nakamura",
        xaxis_title="Frecuencia (Hz)",
        yaxis_title="H/V",
        xaxis=dict(type="log", range=[np.log10(freq_min), np.log10(freq_max)]),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=50, r=20, b=50, l=70),
        showlegend=False,
        annotations=annotations,
    )

    return fig
