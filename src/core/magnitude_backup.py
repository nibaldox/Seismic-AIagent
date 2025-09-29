"""Local Magnitude (ML) estimation helpers.

This module now provides two tiers:

1. ``estimate_local_magnitude_placeholder`` (antiguo enfoque)
    - Mantiene compatibilidad pero NO es fisicamente riguroso.

2. ``estimate_local_magnitude_wa`` (mejorado Wood-Anderson aproximado)
    - Pre-procesa la senal (detrend, demean, taper, filtro banda).
    - Intenta simular una respuesta Wood-Anderson (si ObsPy disponible) o aplica integracion heuristica.
    - Utiliza la formulacion estandar ML = log10(A_mm) - log10 A0(R) con A0(R) piecewise (Hutton & Boore 1987).
    - Distancia R estimada aun con DeltaP-S de una sola estacion (gran incertidumbre).

IMPORTANTE: Sin remover la respuesta instrumental real ni una localizacion multi-estacion, el resultado sigue siendo preliminar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Dict, Any, List, Tuple
import math
import numpy as np

try:  # pragma: no cover - optional path
    from obspy.signal.invsim import simulate_seismometer, corn_freq_2_paz  # type: ignore
    from obspy.core.inventory import Inventory  # type: ignore
    from obspy import read_inventory  # type: ignore
except Exception:  # pragma: no cover
    simulate_seismometer = None  # type: ignore
    corn_freq_2_paz = None  # type: ignore
    Inventory = None  # type: ignore
    read_inventory = None  # type: ignore
try:  # pragma: no cover
    from obspy.signal.filter import bandpass as obspy_bandpass  # type: ignore
except Exception:  # pragma: no cover
    obspy_bandpass = None  # type: ignore

DEFAULT_BAND = (1.0, 20.0)  # Hz para limpieza basica antes de amplitud ML


@dataclass
class MagnitudeResult:
    ml: Optional[float]
    amplitude_mm: Optional[float]
    delta_ps: Optional[float]
    distance_km: Optional[float]
    notes: str
    method: str = "placeholder"
    warnings: List[str] = None  # type: ignore
    instrument_response_removed: bool = False
    sensor_type: Optional[str] = None
    units_assumed: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:  # helper for potential JSON export
        return {
            "ml": self.ml,
            "amplitude_mm": self.amplitude_mm,
            "delta_ps": self.delta_ps,
            "distance_km": self.distance_km,
            "notes": self.notes,
            "method": self.method,
            "warnings": self.warnings or [],
            "instrument_response_removed": self.instrument_response_removed,
            "sensor_type": self.sensor_type,
            "units_assumed": self.units_assumed,
        }


def _estimate_distance_from_ps(delta_ps: float) -> float:
    """Very crude distance estimate (km) from P-S time difference.

    Using typical average Vp=6.0 km/s, Vs=3.5 km/s -> (1/Vs - 1/Vp)^-1 ~= 8.4 factor.
    distance ~= delta_ps * 8.4 km
    """
    return delta_ps * 8.4


def _log10_a0_hutton_boore(distance_km: float) -> float:
    """Piecewise log10 A0(R) approximation (Hutton & Boore 1987, California).

    log10 A0(R) = 0.018 R + 2.17            (R <= 60 km)
                   0.0038 R + 3.02          (60 < R <= 700 km)
    Para R > 700 km se mantiene extrapolacion lineal segunda rama.
    """
    if distance_km <= 60.0:
        return 0.018 * distance_km + 2.17
    if distance_km <= 700.0:
        return 0.0038 * distance_km + 3.02
    return 0.0038 * distance_km + 3.02  # extrapolacion simple


def _compute_ml_hutton_boore(amplitude_mm: float, distance_km: float) -> float:
    if amplitude_mm <= 0 or distance_km <= 0:
        raise ValueError("Amplitud o distancia invalida para ML")
    log10_a = math.log10(amplitude_mm)
    log10_a0 = _log10_a0_hutton_boore(distance_km)
    return log10_a - log10_a0


def estimate_local_magnitude_placeholder(*, picks: Sequence[Dict[str, Any]], trace_data: np.ndarray, trace_sampling_rate: float, station: str) -> MagnitudeResult:
    """Version previa (no rigurosa). Conservada para comparacion."""
    station_picks = [p for p in picks if p.get("station") == station]
    p_pick = next((p for p in station_picks if p.get("phase") == "P"), None)
    s_pick = next((p for p in station_picks if p.get("phase") == "S"), None)
    if not p_pick or not s_pick:
        return MagnitudeResult(None, None, None, None, "P y S no disponibles", method="placeholder", warnings=["Faltan picks P/S"]) 
    delta_ps = float(s_pick["time_rel"]) - float(p_pick["time_rel"])
    if delta_ps <= 0:
        return MagnitudeResult(None, None, None, None, "Delta P-S invalida", method="placeholder", warnings=["DeltaP-S <= 0"]) 
    distance_km = _estimate_distance_from_ps(delta_ps)
    start_idx = int(float(p_pick["time_rel"]) * trace_sampling_rate)
    end_idx = int((float(p_pick["time_rel"]) + 3.0) * trace_sampling_rate)
    end_idx = min(end_idx, trace_data.size)
    if end_idx <= start_idx:
        return MagnitudeResult(None, None, delta_ps, distance_km, "Ventana invalida", method="placeholder", warnings=["Ventana vacia"]) 
    window = trace_data[start_idx:end_idx]
    if window.size == 0:
        return MagnitudeResult(None, None, delta_ps, distance_km, "Sin datos", method="placeholder", warnings=["Ventana sin muestras"]) 
    peak = float(np.max(np.abs(window)))
    amplitude_mm = peak * 0.01  # Escala ficticia
    try:
        # Usamos la misma formula antigua solo para mantener comparabilidad: reformulada como log10A - log10A0*
        # donde A0* = 10^{-(1.11 log10 R + 0.00189 R - 2.09)}
        ml = math.log10(amplitude_mm) + 1.11 * math.log10(distance_km) + 0.00189 * distance_km - 2.09
    except Exception as exc:  # pragma: no cover
        return MagnitudeResult(None, amplitude_mm, delta_ps, distance_km, f"Error ML: {exc}", method="placeholder", warnings=["Excepcion computo ML"]) 
    return MagnitudeResult(ml, amplitude_mm, delta_ps, distance_km, "OK (no riguroso)", method="placeholder", warnings=["No Wood-Anderson", "Factor escala ficticio"]) 


def _preprocess_array(data: np.ndarray) -> np.ndarray:
    if data.size == 0:
        return data
    # Detrend lineal simple
    x = np.arange(data.size, dtype=float)
    # Ajuste lineal y sustraccion
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
    if obspy_bandpass:
        try:
            return obspy_bandpass(data, freqmin, freqmax, sr, corners=4, zerophase=True)
        except Exception:  # pragma: no cover
            pass
    # FFT fallback con ventana suave
    n = data.size
    if n == 0:
        return data
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    spec = np.fft.rfft(data)
    mask = (freqs >= freqmin) & (freqs <= freqmax)
    # Aplicar transicion suave 10% banda
    bw = freqmax - freqmin
    if bw > 0:
        edge = bw * 0.1
        low_ramp = (freqs >= freqmin) & (freqs < freqmin + edge)
        high_ramp = (freqs <= freqmax) & (freqs > freqmax - edge)
        # Cosine ramps
        spec[~mask] = 0
        if low_ramp.any():
            w = 0.5 * (1 - np.cos(math.pi * (freqs[low_ramp] - freqmin) / edge))
            spec[low_ramp] *= w
        if high_ramp.any():
            w = 0.5 * (1 - np.cos(math.pi * (freqs[high_ramp] - (freqmax - edge)) / edge))
            spec[high_ramp] *= w
    return np.fft.irfft(spec, n=n).astype(data.dtype)


def _integrate(data: np.ndarray, sr: float) -> np.ndarray:
    if data.size == 0:
        return data
    # Simple cumulative integration (trapezoidal) in time domain
    dt = 1.0 / sr
    return np.cumsum((data[:-1] + data[1:]) * 0.5) * dt


def _remove_instrument_response(data: np.ndarray, sr: float, inventory_path: Optional[str] = None, 
                               station: str = "UNK", channel: str = "CH", network: str = "XX") -> Tuple[np.ndarray, List[str]]:
    """
    Intenta remover la respuesta instrumental usando un archivo de inventario.
    
    Returns:
        Tuple[data_corrected, warnings_list]
    """
    warnings_list = []
    
    if not inventory_path or not read_inventory:
        warnings_list.append("Sin inventario instrumental - usando datos sin corregir")
        return data, warnings_list
    
    try:
        # Intentar cargar inventario
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
    """
    Detecta las unidades probables basándose en los metadatos de la traza.
    
    Returns:
        Tuple[units_detected, warnings_list]
    """
    warnings_list = []
    
    if not trace_stats:
        warnings_list.append("Sin metadatos de traza - asumiendo cm/s²")
        return "cm/s²", warnings_list
    
    # Buscar información de unidades en los metadatos
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
    """Estimacion ML aproximada estilo Wood-Anderson con respuesta instrumental.

    Pasos mejorados:
      1. Verifica picks P y S.
      2. Detecta unidades probables de los metadatos.
      3. Intenta remover respuesta instrumental si hay inventario disponible.
      4. Preprocesa senal (detrend, taper, banda 1-20 Hz).
      5. Convierte a desplazamiento y simula Wood-Anderson.
      6. Obtiene pico mm en ventana amplia.
      7. ML = log10(A_mm) - log10 A0(R).
    """
    warnings: List[str] = []
    station_picks = [p for p in picks if p.get("station") == station]
    p_pick = next((p for p in station_picks if p.get("phase") == "P"), None)
    s_pick = next((p for p in station_picks if p.get("phase") == "S"), None)
    if not p_pick or not s_pick:
        return MagnitudeResult(None, None, None, None, "Faltan picks P/S", method="wood_anderson_inst", 
                              warnings=["Se requieren picks P y S"],
                              instrument_response_removed=False, sensor_type=None, units_assumed=None)
    
    delta_ps = float(s_pick["time_rel"]) - float(p_pick["time_rel"])
    if delta_ps <= 0:
        return MagnitudeResult(None, None, None, None, "DeltaP-S invalida", method="wood_anderson_inst", 
                              warnings=["DeltaP-S <= 0"],
                              instrument_response_removed=False, sensor_type=None, units_assumed=None) 
    
    distance_km = _estimate_distance_from_ps(delta_ps)
    sr = float(trace_sampling_rate)
    if sr <= 0:
        return MagnitudeResult(None, None, delta_ps, distance_km, "SR invalido", method="wood_anderson_inst", 
                              warnings=["Sampling rate <=0"],
                              instrument_response_removed=False, sensor_type=None, units_assumed=None) 
    
    data = np.asarray(trace_data, dtype=float)
    if data.size < 10:
        return MagnitudeResult(None, None, delta_ps, distance_km, "Pocas muestras", method="wood_anderson_inst", 
                              warnings=["Longitud traza insuficiente"],
                              instrument_response_removed=False, sensor_type=None, units_assumed=None) 

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
        # Aceleración -> velocidad -> desplazamiento
        vel = _integrate(data_bp, sr)
        disp = _integrate(vel, sr)
        disp_mm = disp * 1000.0  # m -> mm
    elif units_detected == "cm/s²":
        # Aceleración cm/s² -> m/s² -> velocidad -> desplazamiento
        acc_ms2 = data_bp / 100.0
        vel = _integrate(acc_ms2, sr)
        disp = _integrate(vel, sr)
        disp_mm = disp * 1000.0  # m -> mm
    elif units_detected == "m/s":
        # Velocidad -> desplazamiento
        disp = _integrate(data_bp, sr)
        disp_mm = disp * 1000.0  # m -> mm
    elif units_detected == "m":
        # Ya es desplazamiento
        disp_mm = data_bp * 1000.0  # m -> mm
    else:
        # Fallback: asumir aceleración cm/s²
        warnings.append("Unidades desconocidas - asumiendo cm/s²")
        acc_ms2 = data_bp / 100.0
        vel = _integrate(acc_ms2, sr)
        disp = _integrate(vel, sr)
        disp_mm = disp * 1000.0

    # Simulación Wood-Anderson aproximada
    if simulate_seismometer and corn_freq_2_paz:
        try:
            # Aplicar filtro que simule respuesta WA (bandpass alrededor de 1 Hz)
            wa_mm = _bandpass(disp_mm, sr, 0.5, 8.0)
        except Exception:
            warnings.append("Fallo simulacion WA -> usando desplazamiento directo")
            wa_mm = disp_mm
    else:
        warnings.append("simulate_seismometer no disponible -> usando desplazamiento directo")
        wa_mm = disp_mm

    if wa_mm.size == 0:
        return MagnitudeResult(None, None, delta_ps, distance_km, "Sin datos WA", method="wood_anderson_inst", 
                              warnings=warnings + ["Vector vacio"],
                              instrument_response_removed=response_removed, sensor_type=sensor_type, 
                              units_assumed=units_detected)

    # Ventana de amplitud: desde P hasta P + min(DeltaPS*2, 15s)
    p_time = float(p_pick["time_rel"])
    win_len = min(delta_ps * 2.0, 15.0)
    start_idx = int(p_time * sr)
    end_idx = int((p_time + win_len) * sr)
    end_idx = min(end_idx, wa_mm.size)
    if end_idx <= start_idx:
        return MagnitudeResult(None, None, delta_ps, distance_km, "Ventana amplitud vacia", method="wood_anderson_inst", 
                              warnings=warnings + ["Indices invertidos"],
                              instrument_response_removed=response_removed, sensor_type=sensor_type, 
                              units_assumed=units_detected) 
    
    window = wa_mm[start_idx:end_idx]
    peak_mm = float(np.max(np.abs(window))) if window.size else 0.0
    if peak_mm <= 0:
        return MagnitudeResult(None, peak_mm, delta_ps, distance_km, "Amplitud nula", method="wood_anderson_inst", 
                              warnings=warnings + ["Pico=0"],
                              instrument_response_removed=response_removed, sensor_type=sensor_type, 
                              units_assumed=units_detected) 

    try:
        ml = _compute_ml_hutton_boore(peak_mm, distance_km)
    except Exception as exc:  # pragma: no cover
        return MagnitudeResult(None, peak_mm, delta_ps, distance_km, f"Error ML: {exc}", method="wood_anderson_inst", 
                              warnings=warnings + ["Excepcion computo ML"],
                              instrument_response_removed=response_removed, sensor_type=sensor_type, 
                              units_assumed=units_detected) 

    # Advertencias metodológicas adicionales
    if not response_removed:
        warnings.append("IMPORTANTE: Respuesta instrumental no removida - resultado aproximado")
    warnings.append("Distancia basada en DeltaP-S una estacion (incertidumbre alta)")
    warnings.append("Magnitud preliminar - se requiere calibración regional")

    notes = f"ML preliminar WA (respuesta={'SI' if response_removed else 'NO'})"
    
    return MagnitudeResult(ml, peak_mm, delta_ps, distance_km, notes, method="wood_anderson_inst", 
                          warnings=warnings, instrument_response_removed=response_removed, 
                          sensor_type=sensor_type, units_assumed=units_detected)


def estimate_local_magnitude_wa(*, picks: Sequence[Dict[str, Any]], trace_data: np.ndarray, trace_sampling_rate: float, station: str) -> MagnitudeResult:
    """
    warnings: List[str] = []
    station_picks = [p for p in picks if p.get("station") == station]
    p_pick = next((p for p in station_picks if p.get("phase") == "P"), None)
    s_pick = next((p for p in station_picks if p.get("phase") == "S"), None)
    if not p_pick or not s_pick:
        return MagnitudeResult(None, None, None, None, "Faltan picks P/S", method="wood_anderson", warnings=["Se requieren picks P y S"])
    delta_ps = float(s_pick["time_rel"]) - float(p_pick["time_rel"])
    if delta_ps <= 0:
        return MagnitudeResult(None, None, None, None, "DeltaP-S invalida", method="wood_anderson", warnings=["DeltaP-S <= 0"]) 
    distance_km = _estimate_distance_from_ps(delta_ps)
    sr = float(trace_sampling_rate)
    if sr <= 0:
        return MagnitudeResult(None, None, delta_ps, distance_km, "SR invalido", method="wood_anderson", warnings=["Sampling rate <=0"]) 
    data = np.asarray(trace_data, dtype=float)
    if data.size < 10:
        return MagnitudeResult(None, None, delta_ps, distance_km, "Pocas muestras", method="wood_anderson", warnings=["Longitud traza insuficiente"]) 

    # Preproceso
    data_pp = _preprocess_array(data)
    fmin, fmax = DEFAULT_BAND
    if sr * 0.5 < fmax:
        fmax = sr * 0.45
        warnings.append("fmax recortado a Nyquist*0.45")
    data_bp = _bandpass(data_pp, sr, fmin, fmax)

    # Intento de simulacion Wood-Anderson
    # Simplificacion: si tenemos simulate_seismometer, usamos paz WA sobre desplazamiento aproximado.
    if simulate_seismometer and corn_freq_2_paz:
        try:
            # Heuristica: si asumimos datos originales en aceleracion (cm/s^2), convertimos a m/s^2, integramos dos veces.
            acc = data_bp / 100.0  # cm/s^2 -> m/s^2
            vel = _integrate(acc, sr)
            disp = _integrate(vel, sr)
            # Simular WA (usa frecuencia de esquina 1 Hz y amortiguamiento 0.707 ~ doc)
            paz_wa = corn_freq_2_paz(1.0, damp=0.707)
            # simulate_seismometer espera un Stream; evitamos dependencia creando wrapper minimo
            # Dado que no tenemos Trace aqui sin modificar interfaz, simplemente aplicamos otro filtrado aproxima.
            # Para mantener compatibilidad, aplicamos un segundo bandpass estrecho alrededor 1 Hz como aproximacion.
            disp_wa = _bandpass(disp, sr, 0.5, 8.0)
            wa_mm = disp_wa * 1000.0  # m -> mm
        except Exception:
            warnings.append("Fallo simulacion WA -> fallback integracion simple")
            wa_mm = data_bp * 0.0  # se corregira mas abajo
    else:
        warnings.append("simulate_seismometer no disponible -> integracion heuristica")
        # Asumimos aceleracion cm/s^2 -> m/s^2
        acc = data_bp / 100.0
        vel = _integrate(acc, sr)
        disp = _integrate(vel, sr)
        wa_mm = disp * 1000.0

    if wa_mm.size == 0:
        return MagnitudeResult(None, None, delta_ps, distance_km, "Sin datos WA", method="wood_anderson", warnings=warnings + ["Vector vacio"])

    # Ventana de amplitud: desde P hasta P + min(DeltaPS*2, 15s)
    p_time = float(p_pick["time_rel"])
    win_len = min(delta_ps * 2.0, 15.0)
    start_idx = int(p_time * sr)
    end_idx = int((p_time + win_len) * sr)
    end_idx = min(end_idx, wa_mm.size)
    if end_idx <= start_idx:
        return MagnitudeResult(None, None, delta_ps, distance_km, "Ventana amplitud vacia", method="wood_anderson", warnings=warnings + ["Indices invertidos"]) 
    window = wa_mm[start_idx:end_idx]
    peak_mm = float(np.max(np.abs(window))) if window.size else 0.0
    if peak_mm <= 0:
        return MagnitudeResult(None, peak_mm, delta_ps, distance_km, "Amplitud nula", method="wood_anderson", warnings=warnings + ["Pico=0"]) 

    try:
        ml = _compute_ml_hutton_boore(peak_mm, distance_km)
    except Exception as exc:  # pragma: no cover
        return MagnitudeResult(None, peak_mm, delta_ps, distance_km, f"Error ML: {exc}", method="wood_anderson", warnings=warnings + ["Excepcion computo ML"]) 

    warnings.append("Distancia basada en DeltaP-S una estacion (incertidumbre alta)")
    return MagnitudeResult(ml, peak_mm, delta_ps, distance_km, "ML preliminar WA aprox", method="wood_anderson", warnings=warnings)


# Backwards-compatible alias (mantener nombre antiguo si era importado)
estimate_local_magnitude = estimate_local_magnitude_placeholder

