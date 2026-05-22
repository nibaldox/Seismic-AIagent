"""Synthetic seismic data generator for testing and demos."""

from __future__ import annotations

import io
import struct
from pathlib import Path
from typing import Optional

import numpy as np


def generate_synthetic_waveform(
    duration_s: float = 60.0,
    sampling_rate: float = 100.0,
    p_arrival_s: float = 10.0,
    s_arrival_s: float = 17.0,
    noise_level: float = 0.05,
    amplitude: float = 1.0,
    dominant_freq_hz: float = 5.0,
) -> np.ndarray:
    """Generate a synthetic 3-component accelerogram with P and S phases.

    Args:
        duration_s: Total duration in seconds.
        sampling_rate: Samples per second.
        p_arrival_s: P-wave arrival time.
        s_arrival_s: S-wave arrival time.
        noise_level: Background noise amplitude (fraction of amplitude).
        amplitude: Peak amplitude of the signal.
        dominant_freq_hz: Dominant frequency of the seismic signal.

    Returns:
        Array of shape (3, n_samples) with [vertical, north, east] components.
    """
    n = int(duration_s * sampling_rate)
    t = np.arange(n) / sampling_rate

    # Generate synthetic source signal (Ricker wavelet at dominant frequency)
    fc = dominant_freq_hz
    tau = t - p_arrival_s
    source = (1 - 2 * (np.pi * fc * tau) ** 2) * np.exp(-(np.pi * fc * tau) ** 2)
    source[t < p_arrival_s] = 0

    # P-wave on vertical component
    p_amp = amplitude
    vertical = source * p_amp

    # S-wave on horizontal components (arrives later, lower freq)
    s_tau = t - s_arrival_s
    s_fc = fc * 0.6
    s_wavelet = (1 - 2 * (np.pi * s_fc * s_tau) ** 2) * np.exp(-(np.pi * s_fc * s_tau) ** 2)
    s_wavelet[t < s_arrival_s] = 0
    s_amp = amplitude * 1.5

    north = s_wavelet * s_amp * 0.7
    east = s_wavelet * s_amp * 0.9

    # Add noise
    noise = np.random.randn(3, n) * noise_level * amplitude
    vertical += noise[0]
    north += noise[1]
    east += noise[2]

    # Apply exponential decay envelope
    envelope = np.exp(-np.maximum(t - p_arrival_s, 0) / (duration_s * 0.3))
    vertical *= envelope
    north *= envelope
    east *= envelope

    return np.stack([vertical, north, east])


def generate_mseed_bytes(
    waveform: np.ndarray,
    sampling_rate: float = 100.0,
    station: str = "ACE01",
    network: str = "XX",
    channels: Optional[list[str]] = None,
) -> bytes:
    """Convert synthetic waveform to MiniSEED-like byte stream.

    This creates a minimal valid MiniSEED blob for testing.
    For production use, use ObsPy's write() method.
    """
    if channels is None:
        channels = ["HHZ", "HHN", "HHE"]

    # Use ObsPy if available for proper MiniSEED writing
    try:
        from obspy import Trace, Stream, UTCDateTime
        traces = []
        for i, ch in enumerate(channels[:waveform.shape[0]]):
            tr = Trace(data=waveform[i].astype(np.float32))
            tr.stats.station = station
            tr.stats.network = network
            tr.stats.channel = ch
            tr.stats.sampling_rate = sampling_rate
            tr.stats.starttime = UTCDateTime.now()
            traces.append(tr)
        stream = Stream(traces=traces)
        buf = io.BytesIO()
        stream.write(buf, format="MSEED")
        return buf.getvalue()
    except ImportError:
        # Fallback: write raw float32 bytes (unreadable by ObsPy but keeps data)
        buf = io.BytesIO()
        for i in range(min(3, waveform.shape[0])):
            buf.write(waveform[i].astype(np.float32).tobytes())
        return buf.getvalue()


def generate_histogram_bytes(
    n_samples: int = 3600,
    seed: int = 42,
) -> bytes:
    """Generate synthetic Gecko histogram binary data."""
    rng = np.random.default_rng(seed)
    data = rng.exponential(scale=1.0, size=n_samples).astype(np.float32)
    return data.tobytes()


def save_demo_dataset(
    output_dir: str | Path = "data/synthetic",
    n_files: int = 24,
    duration_s: float = 60.0,
    sampling_rate: float = 100.0,
) -> Path:
    """Generate a full demo dataset of MiniSEED files."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for i in range(n_files):
        hour = i
        amp = 0.5 + abs(np.sin(hour * 0.3)) * 2.0
        wf = generate_synthetic_waveform(
            duration_s=duration_s,
            sampling_rate=sampling_rate,
            p_arrival_s=10.0 + np.random.uniform(-2, 2),
            amplitude=amp,
        )
        data = generate_mseed_bytes(wf, sampling_rate=sampling_rate)
        fname = output_dir / f"2025-01-01 {hour:04d} 00 ACE01.ms"
        fname.write_bytes(data)

    return output_dir



