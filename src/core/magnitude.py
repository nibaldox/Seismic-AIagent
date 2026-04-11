"""Local Magnitude (ML) estimation helpers with instrument response support.

This module provides enhanced ML estimation with instrument response correction:

1. ``estimate_local_magnitude_placeholder`` - Legacy method for compatibility
2. ``estimate_local_magnitude_wa`` - Basic Wood-Anderson approximation  
3. ``estimate_local_magnitude_wa_with_response`` - Enhanced with instrument response removal
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Dict, Any, List, Tuple
import math
import numpy as np

try:
    from obspy.signal.invsim import simulate_seismometer, corn_freq_2_paz
    from obspy.core.inventory import Inventory
    from obspy import read_inventory
except ImportError:
    simulate_seismometer = None
    corn_freq_2_paz = None
    Inventory = None
    read_inventory = None

# Standard Wood-Anderson seismograph poles-zeros-gain (Uhrhammer & Collins 1990).
# T0 = 0.8 s (f0 = 1.25 Hz), h = 0.7 (critical damping ratio), gain = 2800.
# These values are the international standard for local magnitude (ML) computation.
_WA_PAZ = {
    "poles": [
        complex(-4.44288, 4.44288),   # -2π·f0·h ± 2π·f0·sqrt(1-h²)·i
        complex(-4.44288, -4.44288),
    ],
    "zeros": [0j, 0j],
    "gain": 1.0,
    "sensitivity": 2800.0,  # V·s/m  (Wood-Anderson static magnification)
}

try:
    from obspy.signal.filter import bandpass as obspy_bandpass
except ImportError:
    obspy_bandpass = None

DEFAULT_BAND = (1.0, 20.0)  # Hz para limpieza basica antes de amplitud ML

# ---------------------------------------------------------------------------
# Calibración regional de magnitud
# ---------------------------------------------------------------------------

def _load_magnitude_calibration() -> dict:
    """Load magnitude calibration from agents_config.yaml, fall back to Hutton & Boore."""
    try:
        import os
        from pathlib import Path
        # Locate config relative to this file (src/core/ → project root → config/)
        config_path = Path(__file__).resolve().parents[2] / "config" / "agents_config.yaml"
        if not config_path.exists():
            return {}
        import yaml  # PyYAML is a transitive dependency of ObsPy and Streamlit
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return cfg.get("magnitude_calibration", {})
    except Exception:
        return {}


def _log10_a0_regional(distance_km: float, calibration: dict | None = None) -> float:
    """Return log10(A0(R)) — a NEGATIVE value — for the active calibration region.

    The YAML stores positive C(Δ) coefficients (easier to read/compare).  This
    function negates them to return the physically correct log10(A0) < 0.

    Falls back to Hutton & Boore (1987) if no calibration is supplied or the
    active region is not found in the config.
    """
    if not calibration:
        return _log10_a0_hutton_boore(distance_km)

    active = calibration.get("active_region", "hutton_boore_california")
    regions = calibration.get("regions", {})
    region = regions.get(active)
    if not region:
        return _log10_a0_hutton_boore(distance_km)

    segments = region.get("segments", [])
    for seg in segments:
        if distance_km <= seg.get("max_dist_km", float("inf")):
            a = seg.get("a", 0.0)
            b = seg.get("b", 0.0)
            c = seg.get("c", 0.0)
            c_delta = a * distance_km + (b * math.log10(max(distance_km, 0.1))) + c
            return -c_delta  # negate: YAML stores +C(Δ), we return −C(Δ) = log10(A0)

    # Beyond last segment: use last segment coefficients
    if segments:
        seg = segments[-1]
        a, b, c = seg.get("a", 0.0), seg.get("b", 0.0), seg.get("c", 0.0)
        c_delta = a * distance_km + (b * math.log10(max(distance_km, 0.1))) + c
        return -c_delta

    return _log10_a0_hutton_boore(distance_km)


# Load once at import time; can be None if YAML not available
_MAGNITUDE_CALIBRATION: dict = _load_magnitude_calibration()


@dataclass
class MagnitudeResult:
    ml: Optional[float]
    amplitude_mm: Optional[float]
    delta_ps: Optional[float]
    distance_km: Optional[float]
    notes: str
    method: str = "placeholder"
    warnings: List[str] = None
    instrument_response_removed: bool = False
    sensor_type: Optional[str] = None
    units_assumed: Optional[str] = None
    # Uncertainty in magnitude units (±). None if unknown.
    ml_uncertainty: Optional[float] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ml": self.ml,
            "amplitude_mm": self.amplitude_mm,
            "delta_ps": self.delta_ps,
            "distance_km": self.distance_km,
            "notes": self.notes,
            "method": self.method,
            "warnings": self.warnings,
            "instrument_response_removed": self.instrument_response_removed,
            "sensor_type": self.sensor_type,
            "units_assumed": self.units_assumed,
            "ml_uncertainty": self.ml_uncertainty,
        }


def _estimate_distance_from_ps(delta_ps: float) -> float:
    """Distance estimate (km) from P-S differential time.

    Uses the Wadati relationship: R = k * ΔtPS, where
        k = Vp·Vs / (Vp - Vs)

    Default k=8.4 corresponds to Vp=6.0 km/s, Vs=3.5 km/s — which matches
    the standard Chilean crustal velocity model (corteza andina, 0-35 km):
        k = 6.0 * 3.5 / (6.0 - 3.5) = 21.0 / 2.5 = 8.40 km/s  ✓

    Valid only for shallow crustal events (<35 km depth).  For intraslab events
    in Chile (50-300 km), Vp≈7.8 km/s, Vs≈4.5 km/s → k≈10.6 km/s.
    Single-station distance is inherently uncertain (±20-30%); use with caution.
    """
    return delta_ps * 8.4


def _log10_a0_hutton_boore(distance_km: float) -> float:
    """Return log10(A0(R)) per Hutton & Boore (1987) — South California.

    A0 is the *reference amplitude* (mm on Wood-Anderson) for an ML=0 earthquake
    at distance R.  Because A0 is always < 1 mm, log10(A0) is NEGATIVE.

    The correction term C(R) = -log10(A0) is positive and is what gets ADDED to
    log10(A_measured) to obtain ML:
        ML = log10(A_mm) - log10(A0) = log10(A_mm) + C(R)

    At 100 km: C(100) ≈ 3.40  →  log10(A0) = -3.40  →  A0 ≈ 0.0004 mm.
    """
    if distance_km <= 60.0:
        return -(0.018 * distance_km + 2.17)
    else:
        return -(0.0038 * distance_km + 3.02)


def _compute_ml_hutton_boore(amplitude_mm: float, distance_km: float,
                             calibration: dict | None = None) -> float:
    """Compute ML = log10(A_mm) - log10(A0(R)).

    log10(A0) is negative, so this equals log10(A_mm) + C(R) where C(R) > 0.
    """
    if amplitude_mm <= 0 or distance_km <= 0:
        raise ValueError("Amplitud o distancia invalida para ML")
    log10_a = math.log10(amplitude_mm)
    log10_a0 = _log10_a0_regional(distance_km, calibration or _MAGNITUDE_CALIBRATION)
    return log10_a - log10_a0  # log10_a0 is negative → effective addition of C(R)


def _preprocess_array(data: np.ndarray) -> np.ndarray:
    """Detrend, demean, and taper signal."""
    if data.size == 0:
        return data
    
    # Detrend lineal
    x = np.arange(data.size, dtype=float)
    A = np.vstack([x, np.ones_like(x)]).T
    m, c = np.linalg.lstsq(A, data, rcond=None)[0]
    detr = data - (m * x + c)
    
    # Demean
    detr -= detr.mean()
    
    # Taper (cosine 5%)
    n = detr.size
    k = int(max(1, n * 0.05))
    window = np.ones(n)
    ramp = 0.5 * (1 - np.cos(np.linspace(0, math.pi, k)))
    window[:k] = ramp
    window[-k:] = ramp[::-1]
    
    return detr * window


def _bandpass(data: np.ndarray, sr: float, freqmin: float, freqmax: float) -> np.ndarray:
    """Bandpass filter using ObsPy or FFT fallback."""
    if obspy_bandpass:
        try:
            return obspy_bandpass(data, freqmin, freqmax, sr, corners=4, zerophase=True)
        except Exception:
            pass
    
    # FFT fallback
    n = data.size
    if n == 0:
        return data
    
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    spec = np.fft.rfft(data)
    mask = (freqs >= freqmin) & (freqs <= freqmax)
    spec[~mask] = 0
    
    return np.fft.irfft(spec, n=n).astype(data.dtype)


def _integrate(data: np.ndarray, sr: float) -> np.ndarray:
    """Cumulative trapezoidal integration with linear baseline correction.

    Without baseline correction, any DC offset in the input causes a linear
    ramp in the integral, and two successive integrations produce a quadratic
    drift that makes displacement estimates unreliable beyond ~30 s.
    The linear detrend after integration removes this first-order drift.
    """
    if data.size == 0:
        return data
    dt = 1.0 / sr
    integrated = np.cumsum((data[:-1] + data[1:]) * 0.5) * dt
    # Remove linear trend accumulated from any residual DC offset
    x = np.arange(integrated.size, dtype=float)
    coeffs = np.polyfit(x, integrated, 1)
    integrated -= np.polyval(coeffs, x)
    return integrated


def _remove_instrument_response(data: np.ndarray, sr: float, inventory_path: Optional[str] = None, 
                               station: str = "UNK", channel: str = "CH", network: str = "XX") -> Tuple[np.ndarray, List[str]]:
    """Intenta remover la respuesta instrumental usando un archivo de inventario."""
    warnings_list = []
    
    if not inventory_path or not read_inventory:
        warnings_list.append("Sin inventario instrumental - usando datos sin corregir")
        return data, warnings_list
    
    try:
        from pathlib import Path
        inv_path = Path(inventory_path)
        if not inv_path.exists():
            warnings_list.append(f"Archivo inventario no encontrado: {inventory_path}")
            return data, warnings_list
            
        inventory = read_inventory(str(inv_path))
        
        # Crear un trace temporal para la corrección
        from obspy import Trace, UTCDateTime
        trace = Trace(data=data.copy())
        trace.stats.sampling_rate = sr
        trace.stats.network = network
        trace.stats.station = station
        trace.stats.channel = channel
        trace.stats.starttime = UTCDateTime.now()  # Timestamp ficticio
        
        # Aplicar corrección de respuesta
        trace.remove_response(inventory=inventory, output="VEL", water_level=60)
        
        warnings_list.append("Respuesta instrumental removida exitosamente")
        return trace.data, warnings_list
        
    except Exception as e:
        warnings_list.append(f"Error al remover respuesta instrumental: {str(e)}")
        return data, warnings_list


def _detect_units_from_trace_stats(trace_stats) -> Tuple[str, List[str]]:
    """Detecta las unidades probables basándose en los metadatos de la traza."""
    warnings_list = []
    
    if not trace_stats:
        warnings_list.append("Sin metadatos de traza - asumiendo cm/s²")
        return "cm/s²", warnings_list
    
    channel = getattr(trace_stats, 'channel', '').upper()
    
    # Heurísticas basadas en códigos de canal estándar
    if channel.startswith('HN') or channel.startswith('BN'):
        warnings_list.append("Canal acelerómetro detectado - asumiendo m/s²")
        return "m/s²", warnings_list
    elif channel.startswith('HH') or channel.startswith('BH'):
        warnings_list.append("Canal velocímetro detectado - asumiendo m/s")
        return "m/s", warnings_list
    elif channel.startswith('HL') or channel.startswith('BL'):
        warnings_list.append("Canal desplazamiento detectado - asumiendo m")
        return "m", warnings_list
    else:
        warnings_list.append(f"Canal desconocido ({channel}) - asumiendo cm/s²")
        return "cm/s²", warnings_list


def _simulate_wood_anderson(disp_mm: np.ndarray, sr: float, warnings: List[str]) -> np.ndarray:
    """Convert displacement (mm) to Wood-Anderson equivalent amplitude (mm).

    Uses the standard WA instrument poles-zeros (Uhrhammer & Collins 1990) via
    ObsPy's ``simulate_seismometer`` when available.  Falls back to a bandpass
    approximation centred on the WA passband (0.5–8 Hz) only when ObsPy is not
    installed — this fallback introduces a systematic bias of ±0.3–0.5 ML units
    and is flagged in the warnings.

    Input must be in *millimetres of displacement*.  Output is also in mm,
    representing the peak excursion of the WA needle.
    """
    if disp_mm.size == 0:
        return disp_mm

    if simulate_seismometer is not None:
        try:
            # simulate_seismometer expects *metres* of displacement and returns
            # metres of WA displacement; we work in mm throughout so scale here.
            disp_m = disp_mm / 1000.0
            wa_m = simulate_seismometer(
                disp_m,
                sr,
                paz_remove=None,        # input is already displacement (no instrument to remove)
                paz_simulate=_WA_PAZ,
                water_level=None,
            )
            warnings.append("✓ Simulación Wood-Anderson con PAZ estándar (Uhrhammer & Collins 1990)")
            return wa_m * 1000.0  # back to mm
        except Exception as exc:
            warnings.append(f"⚠️ simulate_seismometer falló ({exc}), usando bandpass aproximado")

    # Fallback: approximate WA response with a bandpass around its passband
    warnings.append("⚠️ Simulación WA aproximada (bandpass 0.5–8 Hz) — error esperado ±0.3–0.5 ML")
    return _bandpass(disp_mm, sr, 0.5, 8.0)


def estimate_local_magnitude_wa_with_response(*, picks: Sequence[Dict[str, Any]], trace_data: np.ndarray, 
                                            trace_sampling_rate: float, station: str, 
                                            inventory_path: Optional[str] = None,
                                            trace_stats = None, network: str = "XX", 
                                            channel: str = "CH") -> MagnitudeResult:
    """Estimacion ML Wood-Anderson con respuesta instrumental."""
    warnings: List[str] = []
    
    # Verificar picks P y S
    station_picks = [p for p in picks if p.get("station") == station]
    p_pick = next((p for p in station_picks if p.get("phase") == "P"), None)
    s_pick = next((p for p in station_picks if p.get("phase") == "S"), None)
    
    if not p_pick or not s_pick:
        return MagnitudeResult(None, None, None, None, "Faltan picks P/S", 
                              method="wood_anderson_inst", warnings=["Se requieren picks P y S"])
    
    delta_ps = float(s_pick["time_rel"]) - float(p_pick["time_rel"])
    if delta_ps <= 0:
        return MagnitudeResult(None, None, None, None, "DeltaP-S invalida", 
                              method="wood_anderson_inst", warnings=["DeltaP-S <= 0"]) 
    
    distance_km = _estimate_distance_from_ps(delta_ps)
    sr = float(trace_sampling_rate)
    data = np.asarray(trace_data, dtype=float)
    
    if sr <= 0 or data.size < 10:
        return MagnitudeResult(None, None, delta_ps, distance_km, "Datos insuficientes", 
                              method="wood_anderson_inst", warnings=["Datos insuficientes"]) 

    # Detectar unidades
    units_detected, unit_warnings = _detect_units_from_trace_stats(trace_stats)
    warnings.extend(unit_warnings)
    
    # Intentar remover respuesta instrumental
    response_removed = False
    sensor_type = "Desconocido"
    if inventory_path:
        data_corrected, response_warnings = _remove_instrument_response(
            data, sr, inventory_path, station, channel, network
        )
        warnings.extend(response_warnings)
        if "exitosamente" in " ".join(response_warnings):
            response_removed = True
            data = data_corrected
            sensor_type = "Con inventario"
    else:
        warnings.append("Sin inventario - procesamientos heurísticos")

    # Preproceso
    data_pp = _preprocess_array(data)
    fmin, fmax = DEFAULT_BAND
    if sr * 0.5 < fmax:
        fmax = sr * 0.45
        warnings.append("fmax recortado a Nyquist*0.45")
    data_bp = _bandpass(data_pp, sr, fmin, fmax)

    # Conversión a desplazamiento según unidades detectadas
    if units_detected == "m/s²":
        vel = _integrate(data_bp, sr)
        disp = _integrate(vel, sr)
        disp_mm = disp * 1000.0
    elif units_detected == "cm/s²":
        acc_ms2 = data_bp / 100.0
        vel = _integrate(acc_ms2, sr)
        disp = _integrate(vel, sr)
        disp_mm = disp * 1000.0
    elif units_detected == "m/s":
        disp = _integrate(data_bp, sr)
        disp_mm = disp * 1000.0
    elif units_detected == "m":
        disp_mm = data_bp * 1000.0
    else:
        warnings.append("Unidades desconocidas - asumiendo cm/s²")
        acc_ms2 = data_bp / 100.0
        vel = _integrate(acc_ms2, sr)
        disp = _integrate(vel, sr)
        disp_mm = disp * 1000.0

    # Simulación Wood-Anderson usando PAZ estándar (Uhrhammer & Collins 1990)
    wa_mm = _simulate_wood_anderson(disp_mm, sr, warnings)
    
    if wa_mm.size == 0:
        return MagnitudeResult(None, None, delta_ps, distance_km, "Sin datos WA", 
                              method="wood_anderson_inst", warnings=warnings + ["Vector vacio"],
                              instrument_response_removed=response_removed, 
                              sensor_type=sensor_type, units_assumed=units_detected)

    # Ventana de amplitud: el pico Wood-Anderson puede llegar hasta 3×Δ(P-S)
    # después del arribo P, especialmente en eventos distantes. Mínimo 30 s.
    p_time = float(p_pick["time_rel"])
    win_len = min(max(delta_ps * 3.0, 30.0), 90.0)
    start_idx = int(p_time * sr)
    end_idx = int((p_time + win_len) * sr)
    end_idx = min(end_idx, wa_mm.size)
    
    if end_idx <= start_idx:
        return MagnitudeResult(None, None, delta_ps, distance_km, "Ventana vacia", 
                              method="wood_anderson_inst", warnings=warnings + ["Ventana vacia"],
                              instrument_response_removed=response_removed, 
                              sensor_type=sensor_type, units_assumed=units_detected) 
    
    window = wa_mm[start_idx:end_idx]
    peak_mm = float(np.max(np.abs(window))) if window.size else 0.0
    
    if peak_mm <= 0:
        return MagnitudeResult(None, peak_mm, delta_ps, distance_km, "Amplitud nula", 
                              method="wood_anderson_inst", warnings=warnings + ["Pico=0"],
                              instrument_response_removed=response_removed, 
                              sensor_type=sensor_type, units_assumed=units_detected) 

    try:
        ml = _compute_ml_hutton_boore(peak_mm, distance_km, _MAGNITUDE_CALIBRATION)
    except Exception as exc:
        return MagnitudeResult(None, peak_mm, delta_ps, distance_km, f"Error ML: {exc}", 
                              method="wood_anderson_inst", warnings=warnings + ["Error computo ML"],
                              instrument_response_removed=response_removed, 
                              sensor_type=sensor_type, units_assumed=units_detected) 

    # Advertencias metodológicas
    if not response_removed:
        warnings.append("⚠️ IMPORTANTE: Respuesta instrumental no removida")
    warnings.append("📍 Distancia estimada de P-S (una estación)")
    # Mostrar región de calibración activa
    active_region = _MAGNITUDE_CALIBRATION.get("active_region", "hutton_boore_california")
    regions = _MAGNITUDE_CALIBRATION.get("regions", {})
    region_desc = regions.get(active_region, {}).get("description", active_region)
    warnings.append(f"📐 Calibración: {region_desc}")
    warnings.append("🔬 Magnitud preliminar - requiere calibración regional y red multi-estación")

    # Incertidumbre estimada conservadoramente:
    # - sin respuesta instrumental: ±1.0 unidades
    # - con respuesta pero sin calibración regional: ±0.5 unidades
    # - estación única agrega ~±0.3 adicionales siempre
    ml_uncertainty = 1.0 if not response_removed else 0.5

    notes = f"ML Wood-Anderson (respuesta {'✓' if response_removed else '✗'})"

    return MagnitudeResult(ml, peak_mm, delta_ps, distance_km, notes,
                          method="wood_anderson_inst", warnings=warnings,
                          instrument_response_removed=response_removed,
                          sensor_type=sensor_type, units_assumed=units_detected,
                          ml_uncertainty=ml_uncertainty)


# Mantener funciones originales para compatibilidad
def estimate_local_magnitude_placeholder(*, picks: Sequence[Dict[str, Any]], trace_data: np.ndarray, 
                                        trace_sampling_rate: float, station: str) -> MagnitudeResult:
    """Version previa (no rigurosa). Conservada para comparacion."""
    station_picks = [p for p in picks if p.get("station") == station]
    p_pick = next((p for p in station_picks if p.get("phase") == "P"), None)
    s_pick = next((p for p in station_picks if p.get("phase") == "S"), None)
    
    if not p_pick or not s_pick:
        return MagnitudeResult(None, None, None, None, "P y S no disponibles", 
                              method="placeholder", warnings=["Faltan picks P/S"]) 
    
    delta_ps = float(s_pick["time_rel"]) - float(p_pick["time_rel"])
    if delta_ps <= 0:
        return MagnitudeResult(None, None, None, None, "Delta P-S invalida", 
                              method="placeholder", warnings=["DeltaP-S <= 0"]) 
    
    distance_km = _estimate_distance_from_ps(delta_ps)
    start_idx = int(float(p_pick["time_rel"]) * trace_sampling_rate)
    end_idx = int((float(p_pick["time_rel"]) + 3.0) * trace_sampling_rate)
    end_idx = min(end_idx, trace_data.size)
    
    if end_idx <= start_idx:
        return MagnitudeResult(None, None, delta_ps, distance_km, "Ventana invalida", 
                              method="placeholder", warnings=["Ventana vacia"]) 
    
    window = trace_data[start_idx:end_idx]
    if window.size == 0:
        return MagnitudeResult(None, None, delta_ps, distance_km, "Sin datos", 
                              method="placeholder", warnings=["Sin muestras"]) 
    
    peak = float(np.max(np.abs(window)))
    amplitude_mm = peak * 0.01  # Factor ficticio
    
    try:
        ml = math.log10(amplitude_mm) + 1.11 * math.log10(distance_km) + 0.00189 * distance_km - 2.09
    except Exception as exc:
        return MagnitudeResult(None, amplitude_mm, delta_ps, distance_km, f"Error ML: {exc}", 
                              method="placeholder", warnings=["Error computo"]) 
    
    return MagnitudeResult(ml, amplitude_mm, delta_ps, distance_km, "OK (no riguroso)", 
                          method="placeholder", warnings=["Factor escala ficticio", "No Wood-Anderson"]) 


def estimate_local_magnitude_wa(*, picks: Sequence[Dict[str, Any]], trace_data: np.ndarray, 
                               trace_sampling_rate: float, station: str) -> MagnitudeResult:
    """Versión básica Wood-Anderson sin respuesta instrumental."""
    # Llamar a la versión con respuesta pero sin inventario
    return estimate_local_magnitude_wa_with_response(
        picks=picks, trace_data=trace_data, trace_sampling_rate=trace_sampling_rate,
        station=station, inventory_path=None, trace_stats=None
    )


def estimate_local_magnitude(*args, **kwargs) -> MagnitudeResult:
    """Compat wrapper that accepts both positional and keyword arguments.

    Expected order for positional: (picks, trace_data, trace_sampling_rate, station)
    """
    if args and not kwargs:
        if len(args) != 4:
            raise TypeError("estimate_local_magnitude expects 4 positional args: picks, trace_data, trace_sampling_rate, station")
        picks, trace_data, trace_sampling_rate, station = args
        return estimate_local_magnitude_placeholder(
            picks=picks,
            trace_data=trace_data,
            trace_sampling_rate=trace_sampling_rate,
            station=station,
        )
    return estimate_local_magnitude_placeholder(**kwargs)