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

try:
    from obspy.signal.filter import bandpass as obspy_bandpass
except ImportError:
    obspy_bandpass = None

DEFAULT_BAND = (1.0, 20.0)  # Hz para limpieza basica antes de amplitud ML


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
        }


def _estimate_distance_from_ps(delta_ps: float) -> float:
    """Crude distance estimate (km) from P-S time difference."""
    return delta_ps * 8.4


def _log10_a0_hutton_boore(distance_km: float) -> float:
    """Piecewise log10 A0(R) approximation (Hutton & Boore 1987)."""
    if distance_km <= 60.0:
        return 0.018 * distance_km + 2.17
    else:
        return 0.0038 * distance_km + 3.02


def _compute_ml_hutton_boore(amplitude_mm: float, distance_km: float) -> float:
    if amplitude_mm <= 0 or distance_km <= 0:
        raise ValueError("Amplitud o distancia invalida para ML")
    log10_a = math.log10(amplitude_mm)
    log10_a0 = _log10_a0_hutton_boore(distance_km)
    return log10_a - log10_a0


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
    """Simple cumulative integration (trapezoidal)."""
    if data.size == 0:
        return data
    dt = 1.0 / sr
    return np.cumsum((data[:-1] + data[1:]) * 0.5) * dt


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

    # Simulación Wood-Anderson aproximada
    wa_mm = _bandpass(disp_mm, sr, 0.5, 8.0) if simulate_seismometer else disp_mm
    
    if wa_mm.size == 0:
        return MagnitudeResult(None, None, delta_ps, distance_km, "Sin datos WA", 
                              method="wood_anderson_inst", warnings=warnings + ["Vector vacio"],
                              instrument_response_removed=response_removed, 
                              sensor_type=sensor_type, units_assumed=units_detected)

    # Ventana de amplitud
    p_time = float(p_pick["time_rel"])
    win_len = min(delta_ps * 2.0, 15.0)
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
        ml = _compute_ml_hutton_boore(peak_mm, distance_km)
    except Exception as exc:
        return MagnitudeResult(None, peak_mm, delta_ps, distance_km, f"Error ML: {exc}", 
                              method="wood_anderson_inst", warnings=warnings + ["Error computo ML"],
                              instrument_response_removed=response_removed, 
                              sensor_type=sensor_type, units_assumed=units_detected) 

    # Advertencias metodológicas
    if not response_removed:
        warnings.append("⚠️ IMPORTANTE: Respuesta instrumental no removida")
    warnings.append("📍 Distancia estimada de P-S (una estación)")
    warnings.append("🔬 Magnitud preliminar - requiere calibración regional")

    notes = f"ML Wood-Anderson (respuesta {'✓' if response_removed else '✗'})"
    
    return MagnitudeResult(ml, peak_mm, delta_ps, distance_km, notes, 
                          method="wood_anderson_inst", warnings=warnings, 
                          instrument_response_removed=response_removed, 
                          sensor_type=sensor_type, units_assumed=units_detected)


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


# Alias para compatibilidad
estimate_local_magnitude = estimate_local_magnitude_placeholder