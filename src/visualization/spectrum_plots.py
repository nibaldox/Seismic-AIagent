"""Spectral analysis plotting helpers."""

from __future__ import annotations

from typing import Any

import numpy as np
import plotly.graph_objects as go


def create_spectrogram(trace: Any, *, nfft: int = 256, overlap: float = 0.5) -> go.Figure:
    """Create a simple spectrogram plot for a single trace."""

    if not hasattr(trace, "data"):
        raise ValueError("Trace must expose a 'data' attribute.")

    data = np.asarray(trace.data)
    sample_rate = float(trace.stats.sampling_rate) if hasattr(trace, "stats") else 1.0
    window = np.hanning(nfft)
    step = int(nfft * (1 - overlap)) or 1

    segments = [data[i : i + nfft] * window for i in range(0, len(data) - nfft, step)]
    if not segments:
        raise ValueError("Trace too short for spectrogram with the given parameters.")

    spectra = np.abs(np.fft.rfft(segments, axis=1))
    freqs = np.fft.rfftfreq(nfft, d=1.0 / sample_rate)
    times = np.arange(len(segments)) * (step / sample_rate)

    fig = go.Figure(
        data=go.Heatmap(
            z=20 * np.log10(spectra + 1e-6),
            x=times,
            y=freqs,
            colorscale="Viridis",
            colorbar_title="Power (dB)",
        )
    )
    fig.update_layout(xaxis_title="Time (s)", yaxis_title="Frequency (Hz)", title="Spectrogram")
    
    # Calculate automatic X-axis range based on data
    if times.size > 0:
        x_min = float(np.min(times))
        x_max = float(np.max(times))
        if x_min == x_max:
            x_max = x_min + 1.0
        fig.update_xaxes(range=[x_min, x_max])
    
    return fig
