"""FastAPI REST server — SeismoAnalyzer Pro API v2.2 — Unified Analysis DB.

Pipeline state per dataset:
  V0 (raw)        → loaded, original data preserved
  V1 (corrected)  → after filter / baseline correction
  V2 (analyzed)   → IMs computed for current V1
  V3 (spectral)  → spectrum/HVSR/RotD50 cached per trace+params
  V4 (located)    → location result
  V5 (magnitud)  → magnitude result

All analysis operations READ from the current active version and
WRITE results into the dataset cache so subsequent requests (from any
page) see the updated data without reprocessing from V0.
"""

from __future__ import annotations

import io
import json
import logging
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.core.data_reader import DataReader
from src.core.intensity_measures import compute_all_ims
from src.core.picking import suggest_picks_sta_lta
from src.core.signal_qc import run_qc
from src.core.signal_processing import apply_filter, remove_baseline
from src.core.rotd50 import compute_rotd
from src.core.hvsr import compute_hvsr
from src.core.design_spectra import ncch433_spectrum, asce7_spectrum
from src.core.magnitude import estimate_local_magnitude_wa
from src.core.location.one_d_location import (
    locate_event_1d, OneDVelocityModel, Station, PSObservation
)
from src.visualization.spectrum_plots import (
    create_fft_plot, create_psd_plot, create_spectrogram, create_hvsr_plot
)
from src.utils.logger import setup_logger

LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

app = FastAPI(
    title="SeismoAnalyzer Pro API",
    description="Unified seismic analysis DB — pipeline V0→V3+",
    version="2.2.0",
)

frontend_path = PROJECT_ROOT / "frontend"
if frontend_path.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_path), html=True), name="frontend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Unified Analysis Database
# ─────────────────────────────────────────────────────────────────────────────
# _datasets: Dict[dataset_name, DatasetRecord]
# DatasetRecord: Dict with 'meta', 'traces' (list of TraceRecord)
# TraceRecord: Dict with V0 (original), V1 (current active), and caches

@dataclass
class TraceRecord:
    """One trace's complete analysis history."""
    # V0 — raw data (never modified after initial load)
    station: str = "UNK"
    channel: str = "UNK"
    network: str = "XX"
    sampling_rate: float = 100.0
    n_samples: int = 0
    start_time: str = ""
    duration_s: float = 0.0
    v0_data: List[float] = field(default_factory=list)
    v0_time: List[float] = field(default_factory=list)

    # V1 — active corrected data (updated by filter / baseline)
    v1_data: Optional[List[float]] = None
    v1_filter_type: Optional[str] = None
    v1_freqmin: Optional[float] = None
    v1_freqmax: Optional[float] = None
    v1_baseline_method: Optional[str] = None
    v1_poly_order: int = 2

    # V2 — IMs (recomputed whenever V1 changes)
    ims: Optional[Dict] = None
    ims_verdict: str = "PENDIENTE"

    # QC
    qc: Optional[Dict] = None

    # V3 — Spectral caches keyed by (spectrum_type, params_hash)
    spectra: Dict[str, Any] = field(default_factory=dict)

    # Picks (list of dicts)
    picks: List[Dict] = field(default_factory=list)

    # V4 — Location
    location: Optional[Dict] = None

    # V5 — Magnitude
    magnitude: Optional[Dict] = None

    def active_data(self) -> tuple:
        """Return (data, time) of the current active version (V1 or V0)."""
        if self.v1_data is not None:
            return self.v1_data, self.v0_time
        return self.v0_data, self.v0_time

    def active_dirty(self) -> bool:
        """True if V1 changed and V2 needs recomputing."""
        return self.v1_data is not None and self.ims is None

    def to_dict(self) -> Dict:
        data, time = self.active_data()
        result = {
            "station": self.station,
            "channel": self.channel,
            "network": self.network,
            "sampling_rate": self.sampling_rate,
            "n_samples": self.n_samples,
            "start_time": self.start_time,
            "duration_s": self.duration_s,
            "data": data,
            "time": time,
            "_v0_data": self.v0_data,
            "_v0_time": self.v0_time,
            "v1_filter_type": self.v1_filter_type,
            "v1_freqmin": self.v1_freqmin,
            "v1_freqmax": self.v1_freqmax,
            "v1_baseline_method": self.v1_baseline_method,
            "v1_poly_order": self.v1_poly_order,
            "v1_dirty": self.active_dirty(),
        }
        if self.ims:
            result["ims"] = self.ims
        if self.qc:
            result["qc"] = self.qc
        if self.picks:
            result["picks"] = self.picks
        if self.location:
            result["location"] = self.location
        if self.magnitude:
            result["magnitude"] = self.magnitude
        if self.spectra:
            result["_spectra_keys"] = list(self.spectra.keys())
        return result


class UnifiedDB:
    """In-memory unified database for all analysis results."""

    def __init__(self):
        self._datasets: Dict[str, Dict] = {}

    def create_dataset(self, name: str, traces_data: List[TraceRecord],
                      filename: str, format_desc: str) -> None:
        """Create a new dataset from raw loaded traces."""
        self._datasets[name] = {
            "name": name,
            "filename": filename,
            "format": format_desc,
            "created_at": str(Path(__file__).stat().st_mtime),
            "pipeline_version": 0,
            "traces": [t.to_dict() for t in traces_data],
        }

    def get_dataset(self, name: str) -> Optional[Dict]:
        return self._datasets.get(name)

    def resolve(self, name: str) -> Optional[str]:
        if name in self._datasets:
            return name
        for key in self._datasets:
            if key.startswith(name) or name.startswith(key):
                return key
        return None

    def list(self) -> List[str]:
        return list(self._datasets.keys())

    def get_trace(self, ds_name: str, trace_idx: int) -> Optional[Dict]:
        ds = self._datasets.get(ds_name)
        if ds is None or trace_idx >= len(ds.get("traces", [])):
            return None
        return ds["traces"][trace_idx]

    def update_trace(self, ds_name: str, trace_idx: int, **updates) -> None:
        ds = self._datasets.get(ds_name)
        if ds is None:
            raise HTTPException(404, f"Dataset '{ds_name}' not found")
        if trace_idx >= len(ds["traces"]):
            raise HTTPException(404, f"Trace {trace_idx} out of range")
        ds["traces"][trace_idx].update(updates)

    def compute_im_for_trace(self, ds_name: str, trace_idx: int) -> Dict:
        """Recompute IMs for trace from its active data."""
        import numpy as np
        from src.core.intensity_measures import compute_all_ims as _compute

        trace = self.get_trace(ds_name, trace_idx)
        if trace is None:
            raise HTTPException(404, f"Trace {trace_idx} not found in '{ds_name}'")

        data = trace.get("v1_data") or trace.get("_v0_data", [])
        if not data:
            raise HTTPException(422, "No data available for IMs")

        sr = trace.get("sampling_rate", 100.0)

        class _Tr:
            def __init__(self, d, sr, station, channel, starttime):
                self.data = np.array(d, dtype=float)
                self.stats = self._S(sr, station, channel, starttime)
            class _S:
                def __init__(self, sr, station, channel, starttime):
                    self.sampling_rate = sr
                    self.station = station
                    self.channel = channel
                    self.starttime = starttime
                    self.npts = len(self.__class__.__init__.__code__.co_freevars)

        tr = _Tr(data, sr, trace.get("station", "UNK"),
                 trace.get("channel", "UNK"), trace.get("start_time", ""))

        ims = _compute(tr)
        ims_dict = {
            "pga_cms2": ims.pga_cms2, "pga_g": ims.pga_g,
            "pgv_cms": ims.pgv_cms, "pgd_cm": ims.pgd_cm,
            "arias_ms": ims.arias_ms, "cav_cms": ims.cav_cms,
            "d5_75_s": ims.d5_75_s, "d5_95_s": ims.d5_95_s,
            "dominant_period_s": ims.dominant_period_s,
            "mean_period_s": ims.mean_period_s,
            "rms_cms2": ims.rms_cms2, "duration_s": ims.duration_s,
        }

        # Auto-verdict
        verdict = "ACEPTADO"
        reasons = []
        if ims.snr_db < 3 if hasattr(ims, 'snr_db') else False:
            verdict = "RECHAZADO"
            reasons.append("SNR bajo")
        elif ims.pga_cms2 < 1.0:
            verdict = "CONDICIONADO"
            reasons.append("PGA muy bajo")

        self.update_trace(ds_name, trace_idx,
                         ims=ims_dict,
                         ims_verdict=verdict,
                         ims_reasons=reasons,
                         ims_dirty=False)
        trace = self.get_trace(ds_name, trace_idx)
        return {"ims": ims_dict, "verdict": verdict, "reasons": reasons}

    def compute_qc_for_trace(self, ds_name: str, trace_idx: int) -> Dict:
        """Run QC on trace's active data."""
        from src.core.signal_qc import run_qc as _run_qc

        trace = self.get_trace(ds_name, trace_idx)
        if trace is None:
            raise HTTPException(404, f"Trace {trace_idx} not found")

        data = np.array(trace.get("v1_data") or trace.get("_v0_data", []), dtype=float)
        if not len(data):
            raise HTTPException(422, "No data for QC")

        sr = trace.get("sampling_rate", 100)

        class _Tr:
            def __init__(self, d, sr, station, channel, starttime, npts):
                self.data = d
                self.stats = self._S(sr, station, channel, starttime, npts)
            class _S:
                def __init__(self, sr, station, channel, starttime, npts):
                    self.sampling_rate = sr
                    self.station = station
                    self.channel = channel
                    self.starttime = starttime
                    self.npts = npts

        tr = _Tr(data, sr, trace.get("station", "UNK"),
                 trace.get("channel", "UNK"),
                 trace.get("start_time", ""), len(data))

        qc = _run_qc(tr)
        qc_dict = {
            "verdict": qc.verdict,
            "snr_db": qc.snr_db,
            "clip_ratio": qc.clip_ratio,
            "baseline_drift": qc.drift_magnitude_pct,
            "has_gaps": qc.has_gaps,
            "n_gaps": qc.n_gaps,
            "reasons": qc.reasons,
        }
        self.update_trace(ds_name, trace_idx, qc=qc_dict)
        return qc_dict

    def compute_spectrum_for_trace(self, ds_name: str, trace_idx: int,
                                    spectrum_type: str, params: Dict) -> Any:
        """Get or compute spectrum for trace, caching by params_hash."""
        trace = self.get_trace(ds_name, trace_idx)
        if trace is None:
            raise HTTPException(404, f"Trace {trace_idx} not found")

        # Build cache key
        cache_key = f"{spectrum_type}:" + ";".join(
            f"{k}={v}" for k, v in sorted(params.items())
        )

        if cache_key in trace.get("spectra", {}):
            return trace["spectra"][cache_key]

        data = np.array(trace.get("v1_data") or trace.get("_v0_data", []), dtype=float)
        sr = trace.get("sampling_rate", 100)

        wrapper = TraceWrapper(
            data=data,
            station=trace.get("station", "UNK"),
            channel=trace.get("channel", "UNK"),
            network=trace.get("network", "XX"),
            sampling_rate=sr,
            starttime=trace.get("start_time", ""),
        )

        if spectrum_type == "fft":
            fig = create_fft_plot(wrapper, **params)
        elif spectrum_type == "psd":
            fig = create_psd_plot(wrapper, **params)
        elif spectrum_type == "spectro":
            fig = create_spectrogram(wrapper, **params)
        elif spectrum_type == "hvsr":
            # For HVSR we need H1, H2, Z traces — use indices from params
            # (simplified: compute H/V from first 3 traces or current)
            fig = create_hvsr_plot(wrapper, wrapper, wrapper, **params)
        else:
            raise HTTPException(422, f"Unknown spectrum type: {spectrum_type}")

        result = json.loads(fig.to_json())

        if "spectra" not in trace:
            trace["spectra"] = {}
        trace["spectra"][cache_key] = result
        return result


_db = UnifiedDB()


# ─────────────────────────────────────────────────────────────────────────────
# Trace-like wrapper for spectrum functions
# ─────────────────────────────────────────────────────────────────────────────

class TraceWrapper:
    def __init__(self, data, station, channel, network, sampling_rate, starttime):
        self.data = data
        self.stats = self._Stats(station, channel, network, sampling_rate, npts=len(data), starttime=starttime)
    class _Stats:
        def __init__(self, station, channel, network, sampling_rate, npts, starttime):
            self.station = station; self.channel = channel
            self.network = network; self.sampling_rate = sampling_rate
            self.npts = npts; self.starttime = starttime


def _process_trace(tr) -> TraceRecord:
    data_f = tr.data.astype(float)
    sr = tr.stats.sampling_rate
    step = max(1, len(data_f) // 5000)
    return TraceRecord(
        station=str(tr.stats.station),
        channel=str(tr.stats.channel),
        network=str(tr.stats.network),
        sampling_rate=float(sr),
        n_samples=int(tr.stats.npts),
        start_time=str(tr.stats.starttime),
        duration_s=float(tr.stats.npts / sr) if sr > 0 else 0.0,
        v0_data=data_f[::step].tolist(),
        v0_time=np.arange(0, len(data_f) / sr, step / sr)[:len(data_f[::step])].tolist(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _resolve(name: str) -> Optional[str]:
    return _db.resolve(name)


def _ensure_trace(name: str, idx: int) -> Dict:
    tr = _db.get_trace(name, idx)
    if tr is None:
        raise HTTPException(404, f"Trace {idx} not found in '{name}'")
    return tr


# ─────────────────────────────────────────────────────────────────────────────
# HTML Landing
# ─────────────────────────────────────────────────────────────────────────────

HTML_PAGE = """<!DOCTYPE html>
<html><head><title>SeismoAnalyzer Pro API</title>
<meta charset="utf-8"><style>
body{font-family:-apple-system,sans-serif;max-width:800px;margin:0 auto;padding:2rem;background:#0f0f23;color:#e0e0e0}
h1{color:#55efc4}a{color:#74b9ff}.ep{background:#1a1a3e;padding:1rem;border-radius:8px;margin:1rem 0}
code{background:#2d2d5e;padding:.2rem .4rem;border-radius:4px}
</style></head>
<body>
<h1>🌋 SeismoAnalyzer Pro API v2.2 — Unified DB</h1>
<p>Pipeline: V0(raw) → V1(corrected) → V2(IMs) → V3(spectra) → V4(location) → V5(magnitude)</p>
<div class="ep"><h3><code>GET /api/health</code></h3><p>Health + DB status</p></div>
<div class="ep"><h3><code>POST /api/datasets/{name}/correct</code></h3><p>Apply filter or baseline to V1</p></div>
<div class="ep"><h3><code>GET /api/datasets/{name}/trace/{idx}</code></h3><p>Get full trace record with all cached analysis</p></div>
<div class="ep"><h3><code>GET /api/datasets/{name}/ims</code></h3><p>Get (or compute) IMs for all traces</p></div>
<div class="ep"><h3><code>GET /api/datasets/{name}/qc</code></h3><p>Get (or compute) QC for all traces</p></div>
<div class="ep"><h3><code>GET /api/datasets/{name}/spectrum/{type}</code></h3><p>Get cached spectrum</p></div>
<p><a href="/docs">📚 Swagger UI</a></p>
</body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root(): return HTML_PAGE

@app.get("/api", response_class=HTMLResponse)
async def api_root(): return HTML_PAGE


@app.get("/api/health")
async def health():
    ds_list = _db.list()
    total_traces = sum(
        len((_db.get_dataset(d) or {}).get("traces", []))
        for d in ds_list
    )
    dirty = sum(
        sum(1 for t in (_db.get_dataset(d) or {}).get("traces", [])
            if t.get("ims_dirty", False))
        for d in ds_list
    )
    return {
        "status": "ok", "version": "2.2.0",
        "datasets": len(ds_list), "total_traces": total_traces,
        "dirty_traces": dirty,
        "db": list(ds_list),
    }


# ── Upload ───────────────────────────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Empty file")

    buffer = io.BytesIO(contents)
    reader = DataReader()
    ext = Path(file.filename).suffix.lower()
    fmt_hint = {
        ".ms": "mseed", ".mseed": "mseed", ".miniseed": "mseed",
        ".sac": "sac", ".seg2": "seg2", ".sg2": "seg2",
        ".suds": "suds", ".bin": "gecko",
    }.get(ext)

    try:
        loaded = reader.load_bytes(buffer=buffer, format_hint=fmt_hint)
    except Exception as exc:
        raise HTTPException(422, f"Failed to read file: {exc}")

    records = [_process_trace(tr) for tr in loaded.stream]
    _db.create_dataset(file.filename, records, file.filename, loaded.format_description)

    return {
        "filename": file.filename,
        "format": loaded.format_description,
        "n_traces": len(records),
        "dataset_name": file.filename,
        "pipeline_version": 0,
        "msg": "Loaded as V0. Apply corrections via POST /datasets/{name}/correct",
    }


# ── Dataset listing / info ───────────────────────────────────────────────────

@app.get("/api/datasets")
async def list_datasets():
    return {"datasets": _db.list(), "count": len(_db.list())}


@app.get("/api/datasets/{name}")
async def get_dataset(name: str):
    real = _resolve(name)
    if real is None:
        raise HTTPException(404, f"Dataset '{name}' not found")
    return _db.get_dataset(real)


# ── Single trace with full history ──────────────────────────────────────────

@app.get("/api/datasets/{name}/trace/{trace_idx}")
async def get_trace(name: str, trace_idx: int):
    real = _resolve(name)
    if real is None:
        raise HTTPException(404, f"Dataset '{name}' not found")
    tr = _db.get_trace(real, trace_idx)
    if tr is None:
        raise HTTPException(404, f"Trace {trace_idx} not found")
    return tr


# ── Apply filter or baseline correction (→ V1) ───────────────────────────────

@app.post("/api/datasets/{name}/correct")
async def correct_trace(name: str,
                         trace_idx: int = Query(0),
                         correction_type: str = Query("filter"),
                         filter_type: str = Query("bandpass"),
                         freqmin: float = Query(0.5),
                         freqmax: float = Query(25.0),
                         baseline_method: str = Query("linear"),
                         poly_order: int = Query(2)):
    """Apply filter or baseline to V1. Marks IMs as dirty (need recompute)."""
    real = _resolve(name)
    if real is None:
        raise HTTPException(404, f"Dataset '{name}' not found")

    tr = _db.get_trace(real, trace_idx)
    if tr is None:
        raise HTTPException(404, f"Trace {trace_idx} not found")

    v0_data = np.array(tr.get("_v0_data", []), dtype=float)
    if not len(v0_data):
        raise HTTPException(422, "No V0 data to correct")

    sr = tr.get("sampling_rate", 100)

    if correction_type == "filter":
        try:
            filtered = apply_filter(v0_data, float(sr),
                                     filter_type=filter_type,
                                     freqmin=freqmin, freqmax=freqmax)
        except Exception as exc:
            raise HTTPException(422, f"Filter failed: {exc}")
        # Downsample for storage
        step = max(1, len(filtered) // 5000)
        v1_data = filtered[::step].tolist()
        _db.update_trace(real, trace_idx,
                         v1_data=v1_data,
                         v1_filter_type=filter_type,
                         v1_freqmin=freqmin,
                         v1_freqmax=freqmax,
                         ims_dirty=True,
                         spectra={})  # clear spectra cache on new filter
        updated = _db.get_trace(real, trace_idx)
        return {
            "trace_idx": trace_idx,
            "correction": "filter",
            "filter_type": filter_type,
            "freqmin": freqmin,
            "freqmax": freqmax,
            "n_filtered": len(filtered),
            "n_stored": len(v1_data),
            "ims_dirty": True,
        }

    elif correction_type == "baseline":
        try:
            corrected = remove_baseline(v0_data, method=baseline_method,
                                       poly_order=poly_order)
        except Exception as exc:
            raise HTTPException(422, f"Baseline failed: {exc}")
        step = max(1, len(corrected) // 5000)
        v1_data = corrected[::step].tolist()
        _db.update_trace(real, trace_idx,
                         v1_data=v1_data,
                         v1_baseline_method=baseline_method,
                         v1_poly_order=poly_order,
                         ims_dirty=True,
                         spectra={})
        updated = _db.get_trace(real, trace_idx)
        return {
            "trace_idx": trace_idx,
            "correction": "baseline",
            "method": baseline_method,
            "poly_order": poly_order,
            "ims_dirty": True,
        }

    else:
        raise HTTPException(422, f"Unknown correction_type: {correction_type}")


# ── Reset to V0 ───────────────────────────────────────────────────────────────

@app.post("/api/datasets/{name}/reset")
async def reset_trace(name: str, trace_idx: int = Query(0)):
    """Reset trace to V0 (remove all corrections and cached analyses)."""
    real = _resolve(name)
    if real is None:
        raise HTTPException(404, f"Dataset '{name}' not found")
    _db.update_trace(real, trace_idx,
                     v1_data=None,
                     v1_filter_type=None, v1_freqmin=None, v1_freqmax=None,
                     v1_baseline_method=None,
                     ims=None, ims_dirty=False,
                     qc=None,
                     spectra={},
                     picks=[],
                     location=None, magnitude=None)
    return {"trace_idx": trace_idx, "reset_to": "V0"}


# ── IMs (auto-compute if dirty) ──────────────────────────────────────────────

@app.get("/api/datasets/{name}/ims")
async def get_ims(name: str, trace_idx: Optional[int] = Query(None),
                   recompute: bool = Query(False)):
    real = _resolve(name)
    if real is None:
        raise HTTPException(404, f"Dataset '{name}' not found")

    ds = _db.get_dataset(real)
    traces = ds.get("traces", [])

    if trace_idx is not None:
        if trace_idx >= len(traces):
            raise HTTPException(404, f"Trace {trace_idx} out of range")
        tr = traces[trace_idx]
        if recompute or tr.get("ims_dirty") or tr.get("ims") is None:
            result = _db.compute_im_for_trace(real, trace_idx)
            return {"trace_idx": trace_idx, "ims": tr.get("ims"), "verdict": tr.get("ims_verdict")}
        return {"trace_idx": trace_idx, "ims": tr.get("ims"), "verdict": tr.get("ims_verdict")}

    # All traces
    results = []
    for i, tr in enumerate(traces):
        if recompute or tr.get("ims_dirty") or tr.get("ims") is None:
            _db.compute_im_for_trace(real, i)
        results.append({
            "trace_idx": i,
            "station": tr.get("station"),
            "channel": tr.get("channel"),
            "ims": tr.get("ims"),
            "verdict": tr.get("ims_verdict"),
            "dirty": tr.get("ims_dirty", False),
        })
    return {"ims": results, "count": len(results)}


# ── QC ─────────────────────────────────────────────────────────────────────────

@app.get("/api/datasets/{name}/qc")
async def get_qc(name: str, trace_idx: Optional[int] = Query(None),
                  recompute: bool = Query(False)):
    real = _resolve(name)
    if real is None:
        raise HTTPException(404, f"Dataset '{name}' not found")

    ds = _db.get_dataset(real)
    traces = ds.get("traces", [])

    if trace_idx is not None:
        if trace_idx >= len(traces):
            raise HTTPException(404, f"Trace {trace_idx} out of range")
        tr = traces[trace_idx]
        if recompute or tr.get("qc") is None:
            qc = _db.compute_qc_for_trace(real, trace_idx)
        return {"trace_idx": trace_idx, "qc": tr.get("qc")}

    results = []
    for i, tr in enumerate(traces):
        if recompute or tr.get("qc") is None:
            _db.compute_qc_for_trace(real, i)
        results.append({
            "trace_idx": i, "station": tr.get("station"),
            "channel": tr.get("channel"), "qc": tr.get("qc"),
        })
    return {"qc_results": results, "count": len(results)}


# ── Picks ─────────────────────────────────────────────────────────────────────

@app.post("/api/datasets/{name}/picks")
async def compute_picks(name: str, trace_idx: int = Query(0),
                         recompute: bool = Query(False)):
    """Run STA/LTA picks on trace's active data."""
    real = _resolve(name)
    if real is None:
        raise HTTPException(404, f"Dataset '{name}' not found")

    tr = _db.get_trace(real, trace_idx)
    if tr is None:
        raise HTTPException(404, f"Trace {trace_idx} not found")

    if recompute or not tr.get("picks"):
        data = np.array(tr.get("v1_data") or tr.get("_v0_data", []), dtype=float)
        sr = tr.get("sampling_rate", 100)

        class _Tr:
            def __init__(self, d, sr, station, channel, starttime):
                self.data = d; self.stats = self._S(sr, station, channel, starttime)
            class _S:
                def __init__(self, sr, station, channel, starttime):
                    self.sampling_rate = sr; self.station = station
                    self.channel = channel; self.starttime = starttime
                    self.npts = len(self.__class__.__init__.__code__.co_freevars)

        wrapper = _Tr(data, sr, tr.get("station", "UNK"),
                      tr.get("channel", "UNK"), tr.get("start_time", ""))

        picks = suggest_picks_sta_lta(wrapper)
        picks_list = [
            {"time_rel": p.get("time_rel"), "phase": p.get("phase"),
             "score": p.get("score"), "snr_db": p.get("snr_db"),
             "uncertainty_s": p.get("uncertainty_s"),
             "method": "STA/LTA"}
            for p in picks
        ]
        _db.update_trace(real, trace_idx, picks=picks_list)
        tr = _db.get_trace(real, trace_idx)

    return {"trace_idx": trace_idx, "picks": tr.get("picks", []),
            "count": len(tr.get("picks", []))}


# ── Spectrum (cached) ─────────────────────────────────────────────────────────

@app.get("/api/datasets/{name}/spectrum/{spectrum_type}")
async def get_spectrum(name: str, spectrum_type: str,
                       trace_idx: int = Query(0),
                       # FFT params
                       log_scale: bool = Query(True),
                       freq_limit: int = Query(25),
                       window_type: str = Query("hanning"),
                       # PSD params
                       nperseg: int = Query(512),
                       overlap: float = Query(0.75),
                       freq_max: int = Query(50),
                       # Spectrogram params
                       nfft: int = Query(256),
                       colorscale: str = Query("Viridis"),
                       # HVSR params
                       h1_idx: int = Query(0), h2_idx: int = Query(1),
                       z_idx: int = Query(2),
                       freq_min: float = Query(0.1),
                       freq_max_hvsr: float = Query(20.0),
                       smooth_octaves: float = Query(0.1),
                       # RotD50
                       comp1_idx: int = Query(0), comp2_idx: int = Query(1),
                       damping: float = Query(0.05),
                       t_min: float = Query(0.01), t_max: float = Query(4.0),
                       n_periods: int = Query(100),
                       # Design spectrum
                       code: str = Query("nch433"),
                       zone: int = Query(3), soil: str = Query("B"),
                       Ss: float = Query(1.0), S1: float = Query(0.4),
                       site_class: str = Query("D")):

    real = _resolve(name)
    if real is None:
        raise HTTPException(404, f"Dataset '{name}' not found")

    ds = _db.get_dataset(real)
    traces = ds.get("traces", [])

    # Build params dict for cache key
    params = {}

    if spectrum_type == "fft":
        params = {"log_scale": log_scale, "freq_limit": freq_limit,
                  "window_type": window_type}
        result = _db.compute_spectrum_for_trace(real, trace_idx, "fft", params)
        tr = traces[trace_idx] if trace_idx < len(traces) else {}
        return {"plot": result,
                "station": tr.get("station"), "channel": tr.get("channel"),
                "type": "fft", "cache_key": f"fft:log_scale={log_scale};freq_limit={freq_limit}"}

    elif spectrum_type == "psd":
        params = {"nperseg": nperseg, "overlap": overlap,
                  "log_scale": log_scale, "freq_max": freq_max}
        result = _db.compute_spectrum_for_trace(real, trace_idx, "psd", params)
        tr = traces[trace_idx] if trace_idx < len(traces) else {}
        return {"plot": result,
                "station": tr.get("station"), "channel": tr.get("channel"),
                "type": "psd"}

    elif spectrum_type == "spectro":
        params = {"nfft": nfft, "overlap": overlap,
                  "window_type": window_type, "colorscale": colorscale}
        result = _db.compute_spectrum_for_trace(real, trace_idx, "spectro", params)
        tr = traces[trace_idx] if trace_idx < len(traces) else {}
        return {"plot": result,
                "station": tr.get("station"), "channel": tr.get("channel"),
                "type": "spectrogram"}

    elif spectrum_type == "hvsr":
        params = {"nperseg": nperseg, "overlap": overlap,
                  "freq_min": freq_min, "freq_max": freq_max_hvsr,
                  "smooth_octaves": smooth_octaves}
        # HVSR needs 3 traces — use h1_idx/h2_idx/z_idx relative to dataset
        if max(h1_idx, h2_idx, z_idx) >= len(traces):
            raise HTTPException(422, f"Need 3 trace indices, got h1={h1_idx}, h2={h2_idx}, z={z_idx}")

        # Wrap all 3 traces
        wrappers = []
        for idx in (h1_idx, h2_idx, z_idx):
            t = traces[idx]
            d = np.array(t.get("v1_data") or t.get("_v0_data", []), dtype=float)
            wrappers.append(TraceWrapper(
                data=d,
                station=t.get("station", "UNK"),
                channel=t.get("channel", "UNK"),
                network=t.get("network", "XX"),
                sampling_rate=t.get("sampling_rate", 100),
                starttime=t.get("start_time", ""),
            ))

        fig = create_hvsr_plot(wrappers[0], wrappers[1], wrappers[2], **params)
        result = json.loads(fig.to_json())
        return {
            "plot": result,
            "h1": traces[h1_idx].get("station"),
            "h2": traces[h2_idx].get("station"),
            "z": traces[z_idx].get("station"),
            "type": "hvsr",
        }

    elif spectrum_type == "rotd50":
        if max(comp1_idx, comp2_idx) >= len(traces):
            raise HTTPException(422, f"Need 2 components, got {comp1_idx} and {comp2_idx}")
        t1 = traces[comp1_idx]
        t2 = traces[comp2_idx]
        d1 = np.array(t1.get("v1_data") or t1.get("_v0_data", []), dtype=float)
        d2 = np.array(t2.get("v1_data") or t2.get("_v0_data", []), dtype=float)
        rotd = compute_rotd(d1, d2, 1.0 / t1.get("sampling_rate", 100),
                             damping=damping, t_min=t_min, t_max=t_max, n_periods=n_periods)
        return {
            "periods": rotd.periods.tolist(),
            "rotd50": rotd.rotd50.tolist(),
            "rotd100": rotd.rotd100.tolist(),
            "damping": rotd.damping,
            "comp1": t1.get("station"),
            "comp2": t2.get("station"),
            "type": "rotd50",
        }

    elif spectrum_type == "design":
        if code.lower() == "nch433":
            periods, sa = ncch433_spectrum(zone=zone, soil=soil,
                                            damping=damping, t_max=t_max)
        else:
            periods, sa = asce7_spectrum(Ss=Ss, S1=S1, site_class=site_class,
                                          damping=damping, t_max=t_max)
        return {
            "periods": periods.tolist(), "sa": sa.tolist(),
            "code": code, "damping": damping,
            "type": "design",
        }

    else:
        raise HTTPException(422, f"Unknown spectrum type: {spectrum_type}")


# ── Magnitude ─────────────────────────────────────────────────────────────────

@app.get("/api/datasets/{name}/magnitude")
async def get_magnitude(name: str, trace_idx: int = Query(0)):
    real = _resolve(name)
    if real is None:
        raise HTTPException(404, f"Dataset '{name}' not found")

    tr = _db.get_trace(real, trace_idx)
    if tr is None:
        raise HTTPException(404, f"Trace {trace_idx} not found")

    picks = tr.get("picks", [])
    if not picks:
        raise HTTPException(422, "No picks. Run POST /datasets/{name}/picks first.")

    data = np.array(tr.get("v1_data") or tr.get("_v0_data", []), dtype=float)
    try:
        result = estimate_local_magnitude_wa(
            picks=picks,
            trace_data=data,
            trace_sampling_rate=float(tr.get("sampling_rate", 100)),
            station=tr.get("station", "UNK"),
        )
        ml_dict = result.as_dict() if hasattr(result, "as_dict") else {
            "ml": result.ml, "amplitude_mm": result.amplitude_mm,
            "delta_ps": result.delta_ps, "distance_km": result.distance_km,
            "notes": getattr(result, "notes", ""),
            "warnings": getattr(result, "warnings", []),
        }
        _db.update_trace(real, trace_idx, magnitude=ml_dict)
        return ml_dict
    except Exception as exc:
        raise HTTPException(422, f"Magnitude failed: {exc}")


# ── Location ──────────────────────────────────────────────────────────────────

@app.post("/api/datasets/{name}/location")
async def locate(name: str,
                vp: float = Query(6.0), vs: float = Query(3.46),
                grid_min: float = Query(-50.0),
                grid_max: float = Query(50.0),
                grid_step: float = Query(2.0),
                grid_z_min: float = Query(-20.0),
                grid_z_max: float = Query(0.0),
                grid_z_step: float = Query(2.0)):
    real = _resolve(name)
    if real is None:
        raise HTTPException(404, f"Dataset '{name}' not found")

    ds = _db.get_dataset(real)
    traces = ds.get("traces", [])

    # Collect P/S observations with station coordinates from trace metadata
    from src.utils.geo import latlon_to_local_xy
    stations_obs = {}
    for i, tr in enumerate(traces):
        station_code = tr.get("station", f"tr{i}")
        picks = tr.get("picks", [])
        t_p = t_s = None
        for p in picks:
            ph = p.get("phase", "")
            t = p.get("time_rel")
            if t is None:
                continue
            if ph.startswith("P") and t_p is None:
                t_p = float(t)
            elif ph.startswith("S") and t_s is None:
                t_s = float(t)

        # Attempt to read lat/lon from trace metadata for real coordinates
        lat = tr.get("latitude") or tr.get("stats", {}).get("latitude")
        lon = tr.get("longitude") or tr.get("stats", {}).get("longitude")
        elev_km = 0.0  # default surface

        if t_p is not None and t_s is not None:
            if lat is not None and lon is not None:
                try:
                    x_km, y_km = latlon_to_local_xy(lat, lon, lat, lon)
                    stations_obs[station_code] = {
                        "t_p": t_p, "t_s": t_s,
                        "x": x_km, "y": y_km, "z": elev_km,
                    }
                except Exception:
                    # Fallback: synthetic grid layout based on index
                    angle = 2 * math.pi * len(stations_obs) / max(len(traces), 1)
                    r = 10.0
                    stations_obs[station_code] = {
                        "t_p": t_p, "t_s": t_s,
                        "x": r * math.cos(angle), "y": r * math.sin(angle), "z": elev_km,
                    }
            else:
                # Synthetic circular layout when no coordinates available
                angle = 2 * math.pi * len(stations_obs) / max(len(traces), 1)
                r = 10.0
                stations_obs[station_code] = {
                    "t_p": t_p, "t_s": t_s,
                    "x": r * math.cos(angle), "y": r * math.sin(angle), "z": elev_km,
                }

    if len(stations_obs) < 3:
        raise HTTPException(422, f"Need ≥3 stations with P+S picks, got {len(stations_obs)}")

    model = OneDVelocityModel(vp=vp, vs=vs)
    stations = [
        Station(code=s, x=v["x"], y=v["y"], z=v.get("z", 0.0))
        for s, v in stations_obs.items()
    ]
    observations = [
        PSObservation(station=Station(code=s, x=v["x"], y=v["y"], z=v.get("z", 0.0)),
                      t_p=v["t_p"], t_s=v["t_s"])
        for s, v in stations_obs.items()
    ]

    try:
        loc = locate_event_1d(
            stations=stations, observations=observations, model=model,
            grid_x=(grid_min, grid_max, grid_step),
            grid_y=(grid_min, grid_max, grid_step),
            grid_z=(grid_z_min, grid_z_max, grid_z_step),
        )
    except Exception as exc:
        raise HTTPException(422, f"Location failed: {exc}")

    if loc is None:
        raise HTTPException(422, "Location did not converge")

    loc_dict = {
        "latitude": loc.x, "longitude": loc.y,
        "depth_km": loc.z, "origin_time_offset_s": loc.t0,
        "rms": loc.rms, "n_stations": len(stations_obs),
        "method": "grid-search 3D" if grid_z_min != grid_z_max else "grid-search 2D",
        "stations": list(stations_obs.keys()),
        "notes": f"z={loc.z:.1f} km, {loc.notes}",
    }

    # Store in all traces that participated
    for i in range(len(traces)):
        _db.update_trace(real, i, location=loc_dict)

    return loc_dict


# ── Reports ──────────────────────────────────────────────────────────────────────

@app.get("/api/datasets/{name}/report/html")
async def report_html(name: str):
    real = _resolve(name)
    if real is None:
        raise HTTPException(404, f"Dataset '{name}' not found")

    ds = _db.get_dataset(real)
    traces = ds.get("traces", [])

    ims_rows = ""
    for i, tr in enumerate(traces):
        ims = tr.get("ims", {})
        ims_rows += f"<tr><td>{tr.get('station')}</td><td>{tr.get('channel')}</td>"
        ims_rows += f"<td>{ims.get('pga_cms2', 'N/A'):.2f if isinstance(ims.get('pga_cms2'), float) else ims.get('pga_cms2', 'N/A')}</td>"
        ims_rows += f"<td>{ims.get('pgv_cms', 'N/A'):.3f if isinstance(ims.get('pgv_cms'), float) else ims.get('pgv_cms', 'N/A')}</td>"
        ims_rows += f"<td>{ims.get('arias_ms', 'N/A'):.4f if isinstance(ims.get('arias_ms'), float) else ims.get('arias_ms', 'N/A')}</td>"
        ims_rows += f"<td>{tr.get('ims_verdict', '?')}</td></tr>"

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Reporte {name}</title>
<style>body{{font-family:system-ui;padding:2rem;background:#0f0f23;color:#e0e0e0}}
table{{border-collapse:collapse;width:100%}}td,th{{padding:8px;border:1px solid #333}}
th{{background:#1a1a3e}}tr:nth-child(even){{background:#16163a}}
.verdict-ACEPTADO{{color:#55efc4}}.verdict-CONDICIONADO{{color:#fdcb6e}}.verdict-RECHAZADO{{color:#ff6b6b}}
h1{{color:#55efc4}}h2{{color:#74b9ff}}
</style></head>
<body>
<h1>🌋 SeismoAnalyzer Pro — Reporte v2.2</h1>
<h2>Dataset: {name}</h2>
<p>Traces: {len(traces)} | Pipeline: V0→V1(corr.)→V2(IMs)→V3(espectro)→V4(loc)→V5(ML)</p>
<h2>📊 Intensity Measures</h2>
<table><thead><tr><th>Station</th><th>Channel</th><th>PGA (cm/s²)</th><th>PGV (cm/s)</th><th>Arias (m/s)</th><th>Veredicto</th></tr></thead>
<tbody>{ims_rows}</tbody></table>
<p><small>Generated by SeismoAnalyzer Pro API v2.2</small></p>
</body></html>"""
    return HTMLResponse(content=html)


@app.get("/api/datasets/{name}/report/excel")
async def report_excel(name: str):
    real = _resolve(name)
    if real is None:
        raise HTTPException(404, f"Dataset '{name}' not found")

    try:
        import openpyxl
        from io import BytesIO
    except ImportError:
        raise HTTPException(422, "openpyxl not available")

    ds = _db.get_dataset(real)
    wb = openpyxl.Workbook()

    # Sheet 1: IMs
    ws = wb.active
    ws.title = "IMs"
    ws.append(["Station", "Channel", "PGA_cm_s2", "PGV_cm_s", "PGD_cm",
               "Arias_m_s", "CAV_cm_s", "D5_75_s", "D5_95_s", "Veredicto", "Dirty"])

    for tr in ds.get("traces", []):
        ims = tr.get("ims", {})
        ws.append([
            tr.get("station"), tr.get("channel"),
            ims.get("pga_cms2", ""), ims.get("pgv_cms", ""),
            ims.get("pgd_cm", ""), ims.get("arias_ms", ""),
            ims.get("cav_cms", ""), ims.get("d5_75_s", ""),
            ims.get("d5_95_s", ""),
            tr.get("ims_verdict", ""),
            "YES" if tr.get("ims_dirty") else "NO",
        ])

    # Sheet 2: QC
    ws2 = wb.create_sheet("QC")
    ws2.append(["Station", "Channel", "Veredicto", "SNR_dB",
                "Clip_ratio", "Baseline_drift", "Has_gaps", "N_gaps", "Reasons"])
    for tr in ds.get("traces", []):
        qc = tr.get("qc", {})
        ws2.append([
            tr.get("station"), tr.get("channel"),
            qc.get("verdict", ""), qc.get("snr_db", ""),
            qc.get("clip_ratio", ""), qc.get("baseline_drift", ""),
            qc.get("has_gaps", ""), qc.get("n_gaps", ""),
            "; ".join(qc.get("reasons", [])),
        ])

    # Sheet 3: Picks
    ws3 = wb.create_sheet("Picks")
    ws3.append(["Station", "Channel", "Phase", "Time_s", "SNR_dB", "Method"])
    for tr in ds.get("traces", []):
        for pk in tr.get("picks", []):
            ws3.append([
                tr.get("station"), tr.get("channel"),
                pk.get("phase", ""), pk.get("time_rel", ""),
                pk.get("snr_db", ""), pk.get("method", ""),
            ])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        io.BytesIO(buf.read()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={name}.xlsx"},
    )


# ── Location demo ────────────────────────────────────────────────────────────

@app.get("/api/location/demo")
async def location_demo():
    return {
        "latitude": -24.173, "longitude": -69.045, "depth_km": 12.3,
        "magnitude": 3.2, "rms": 0.08,
        "summary": "Demo — grid-search 1D con 3 estaciones",
        "traces": [
            {"x": [0], "y": [0], "size": 12, "color": "#74b9ff", "symbol": "triangle-down",
             "name": "ACE01", "text": ["ACE01"]},
            {"x": [15], "y": [8], "size": 12, "color": "#74b9ff", "symbol": "triangle-down",
             "name": "ACE02", "text": ["ACE02"]},
            {"x": [-10], "y": [12], "size": 12, "color": "#74b9ff", "symbol": "triangle-down",
             "name": "ACE03", "text": ["ACE03"]},
            {"x": [2], "y": [10], "size": 20, "color": "#ff6b6b", "symbol": "star",
             "name": "Epicentro", "text": ["M3.2 @ 12.3 km"]},
        ],
        "stations": [{"name": "ACE01"}, {"name": "ACE02"}, {"name": "ACE03"}],
        "epicenter": {"lat": -24.173, "lon": -69.045, "depth_km": 12.3},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("src.server:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    main()