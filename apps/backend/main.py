from __future__ import annotations

import base64
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.data_reader import DataReader
from src.visualization.waveform_plots import create_waveform_plot
from src.visualization.spectrum_plots import (
    create_spectrogram,
    create_fft_plot,
    create_psd_plot,
)

app = FastAPI(title="Seismic Backend", version="0.1.0")

# CORS abierto por defecto, ajustar en producción
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Health(BaseModel):
    status: str


@app.get("/health", response_model=Health)
async def health() -> Health:
    return Health(status="ok")


@app.post("/waveform/plot")
async def waveform_plot(
    file: UploadFile = File(...),
    filter_type: Literal["none", "bandpass", "highpass", "lowpass"] = Form("none"),
    freqmin: float = Form(1.0),
    freqmax: float = Form(10.0),
    unit: Literal["Raw", "m/s²", "g"] = Form("Raw"),
    amplitude_scale: Literal["Auto", "Global", "Normalized"] = Form("Auto"),
    t0: int = Form(0),
    t1: Optional[int] = Form(None),
):
    tmp = Path("./uploaded_files")
    tmp.mkdir(exist_ok=True)
    save_path = tmp / file.filename
    content = await file.read()
    save_path.write_bytes(content)

    reader = DataReader()
    loaded = reader.load_files([save_path])[0]
    stream = loaded.stream

    # ventana
    if t1 is None:
        try:
            first_trace = stream[0]
            t1 = int(first_trace.times("relative")[-1]) if first_trace.stats.npts > 0 else 0
        except Exception:
            t1 = 0
    if t1 <= t0:
        t1 = max(t0 + 1, t1 or 1)

    fig = create_waveform_plot(
        streams=stream,
        time_window=(t0, t1),
        unit=unit,
        filter_type=filter_type,
        freqmin=freqmin,
        freqmax=freqmax,
        amplitude_scale=amplitude_scale,
        title=f"Waveforms · {file.filename}",
    )
    png_bytes = fig.to_image(format="png", scale=2)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return {"image_base64": b64, "summary": loaded.summary}


@app.post("/spectrum/plot")
async def spectrum_plot(
    file: UploadFile = File(...),
    analysis_type: Literal["Spectrogram", "FFT", "PSD"] = Form("Spectrogram"),
    nfft: int = Form(256),
    overlap: float = Form(0.5),
    window_type: Literal["hanning", "hamming", "blackman"] = Form("hanning"),
    colorscale: Literal["Viridis", "Plasma", "Inferno", "Turbo"] = Form("Viridis"),
    fft_log: bool = Form(True),
    fft_lim: int = Form(25),
    psd_nperseg: int = Form(512),
    psd_overlap: float = Form(0.75),
    psd_log: bool = Form(True),
    psd_freq_max: int = Form(50),
):
    tmp = Path("./uploaded_files")
    tmp.mkdir(exist_ok=True)
    save_path = tmp / file.filename
    content = await file.read()
    save_path.write_bytes(content)

    reader = DataReader()
    loaded = reader.load_files([save_path])[0]
    trace = loaded.stream[0]

    if analysis_type == "Spectrogram":
        fig = create_spectrogram(trace, nfft=nfft, overlap=overlap, window_type=window_type, colorscale=colorscale)
    elif analysis_type == "FFT":
        fig = create_fft_plot(trace, log_scale=fft_log, freq_limit=fft_lim, window_type=window_type)
    else:
        fig = create_psd_plot(trace, nperseg=psd_nperseg, overlap=psd_overlap, log_scale=psd_log, freq_max=psd_freq_max)

    png_bytes = fig.to_image(format="png", scale=2)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return {"image_base64": b64, "summary": loaded.summary}
