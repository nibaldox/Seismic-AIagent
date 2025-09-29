from __future__ import annotations

import base64
from pathlib import Path
from typing import Literal, Optional, List
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.data_reader import DataReader
from src.visualization.waveform_plots import create_waveform_plot
from src.visualization.spectrum_plots import (
    create_spectrogram,
    create_fft_plot,
    create_psd_plot,
)
from src.ai_agent.seismic_interpreter import (
    load_agent_suite,
    run_spectrum_analysis,
)
from src.core.location.one_d_location import (
    locate_event_1d,
    Station as OneDStation,
    PSObservation as OneDPSObservation,
    OneDVelocityModel,
)
import plotly.graph_objects as go
import pandas as pd

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
    fname = file.filename or f"upload_{uuid4().hex}"
    save_path = tmp / fname
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
    fname = file.filename or f"upload_{uuid4().hex}"
    save_path = tmp / fname
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


# ---------------------- Telemetry / Histogramas ----------------------
@app.post("/telemetry/histogram")
async def telemetry_histogram(
    file: UploadFile = File(...),
    column: Optional[str] = Form(None),
    bins: int = Form(50),
):
    """Crea un histograma de una columna numérica de un CSV subido."""
    tmp = Path("./uploaded_files"); tmp.mkdir(exist_ok=True)
    fname = file.filename or f"telemetry_{uuid4().hex}.csv"
    path = tmp / fname
    path.write_bytes(await file.read())

    df = pd.read_csv(path)
    # Elegir primera columna numérica si no se especifica
    if column is None or column not in df.columns:
        num_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if not num_cols:
            return {"error": "No hay columnas numéricas en el CSV"}
        column = num_cols[0]

    series = pd.to_numeric(df[column], errors="coerce").dropna()
    fig = go.Figure(data=go.Histogram(x=series, nbinsx=bins))
    fig.update_layout(
        title=f"Histograma · {column}", xaxis_title=column, yaxis_title="Cuenta",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    png = fig.to_image(format="png", scale=2)
    desc = df.describe(include="all").to_string()
    return {"image_base64": base64.b64encode(png).decode("ascii"), "summary": desc}


# ---------------------- Localización 1D ----------------------
class StationIn(BaseModel):
    code: str
    x_km: Optional[float] = None
    y_km: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class ObservationIn(BaseModel):
    station: str
    t_p: float
    t_s: float


class VelocityModelIn(BaseModel):
    vp: float = 6.0
    vs: float = 3.5


class GridIn(BaseModel):
    x: List[float] = [-50, 50, 2.0]
    y: List[float] = [-50, 50, 2.0]


class Location1DRequest(BaseModel):
    stations: List[StationIn]
    observations: List[ObservationIn]
    model: VelocityModelIn = VelocityModelIn()
    grid: GridIn = GridIn()
    min_stations: int = 2


@app.post("/location/one_d")
async def location_one_d(req: Location1DRequest):
    stations: List[OneDStation] = []
    # Usar XY si están disponibles, sino rechazar (o aquí podríamos proyectar si se proporciona ref)
    for s in req.stations:
        if s.x_km is not None and s.y_km is not None:
            stations.append(OneDStation(code=s.code, x=float(s.x_km), y=float(s.y_km)))
        else:
            return {"error": f"Falta x_km/y_km para la estación {s.code}"}

    observations: List[OneDPSObservation] = [
        OneDPSObservation(station=o.station, t_p=o.t_p, t_s=o.t_s) for o in req.observations
    ]
    model = OneDVelocityModel(vp=req.model.vp, vs=req.model.vs)
    gx = tuple(req.grid.x); gy = tuple(req.grid.y)

    res = locate_event_1d(
        stations=stations,
        observations=observations,
        model=model,
        grid_x=(float(gx[0]), float(gx[1]), float(gx[2])),
        grid_y=(float(gy[0]), float(gy[1]), float(gy[2])),
        min_stations=req.min_stations,
    )
    if res is None:
        return {"message": "Localización no resuelta"}
    return {
        "x_km": res.x,
        "y_km": res.y,
        "t0": res.t0,
        "rms": res.rms,
        "used_stations": res.used_stations,
        "residuals": [[st, val] for st, val in res.residuals],
    }


# ---------------------- AI: análisis espectral ----------------------
class AISpectrumRequest(BaseModel):
    trace_info: dict
    analysis_type: str
    analysis_params: dict


@app.post("/ai/spectrum")
async def ai_spectrum(req: AISpectrumRequest):
    try:
        agents = load_agent_suite("config/agents_config.yaml")
        content = run_spectrum_analysis(
            agents,
            trace_info=req.trace_info,
            analysis_type=req.analysis_type,
            analysis_params=req.analysis_params,
        )
        return {"markdown": content}
    except Exception as exc:
        return {"error": str(exc)}
