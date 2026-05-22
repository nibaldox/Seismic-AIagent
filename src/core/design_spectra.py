"""Espectros de diseño sísmico según normativas internacionales.

Normativas implementadas
------------------------
- NCh433 Of.1996 mod. DS61-2011 (Chile)
- ASCE 7-22 (USA/genérico, Capítulo 11)

Uso típico
----------
>>> periods, sa = ncch433_spectrum(zone=3, soil="B", damping=0.05)
>>> periods, sa = asce7_spectrum(Ss=1.5, S1=0.6, site_class="D", damping=0.05)
"""

from __future__ import annotations

from typing import Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Espectro de diseño NCh433 (Chile)
# ---------------------------------------------------------------------------

# Tabla de parámetros según zona y tipo de suelo (DS61/2011)
# Fuente: NCh433 Of.1996 modificada por DS61-2011, Tabla 6.4 y Tabla 6.5
_NCH433_PARAMS = {
    # (zona, suelo): (T0 [s], T'n [s], A0/g, S, Ia, p)
    # A0 = aceleración máxima del suelo en g (zona sísmica)
    # S   = factor de amplificación del suelo
    # Ia, p = parámetros de forma del espectro
    (1, "A"): (0.10, 0.30, 0.20, 0.90, 1.80, 1.50),
    (1, "B"): (0.15, 0.55, 0.20, 1.00, 2.10, 1.50),
    (1, "C"): (0.20, 0.75, 0.20, 1.10, 2.30, 1.50),
    (1, "D"): (0.25, 1.20, 0.20, 1.20, 2.50, 1.50),
    (2, "A"): (0.10, 0.30, 0.30, 0.90, 1.80, 1.50),
    (2, "B"): (0.15, 0.55, 0.30, 1.00, 2.10, 1.50),
    (2, "C"): (0.20, 0.75, 0.30, 1.10, 2.30, 1.50),
    (2, "D"): (0.25, 1.20, 0.30, 1.20, 2.50, 1.50),
    (3, "A"): (0.10, 0.30, 0.40, 0.90, 1.80, 1.50),
    (3, "B"): (0.15, 0.55, 0.40, 1.00, 2.10, 1.50),
    (3, "C"): (0.20, 0.75, 0.40, 1.10, 2.30, 1.50),
    (3, "D"): (0.25, 1.20, 0.40, 1.20, 2.50, 1.50),
}

# Descripción de zonas sísmicas chilenas
NCH433_ZONES = {
    1: "Zona 1 — A0=0.20g (p.ej. Magallanes)",
    2: "Zona 2 — A0=0.30g (p.ej. Santiago, Valparaíso)",
    3: "Zona 3 — A0=0.40g (p.ej. Antofagasta, Atacama, Coquimbo, Biobío)",
}

NCH433_SOILS = {
    "A": "Tipo A — Roca (Vs30 > 900 m/s)",
    "B": "Tipo B — Suelo firme (350–900 m/s)",
    "C": "Tipo C — Suelo medio (180–350 m/s)",
    "D": "Tipo D — Suelo blando (<180 m/s)",
}

# Nota: la zona 3 incluye la región de Antofagasta donde están los sensores
# del proyecto (lat -24.17°S, lon -69.04°O).


def ncch433_spectrum(
    zone: int = 3,
    soil: str = "B",
    damping: float = 0.05,
    n_periods: int = 200,
    t_max: float = 4.0,
    g_cms2: float = 980.665,
) -> Tuple[np.ndarray, np.ndarray]:
    """Espectro de pseudoaceleración de diseño NCh433 DS61-2011.

    El espectro elástico de referencia para ξ=5% se escala con el factor
    de reducción de amortiguamiento η si ξ ≠ 5%.

    Args:
        zone:      Zona sísmica chilena (1, 2 o 3).
        soil:      Tipo de suelo ('A', 'B', 'C' o 'D').
        damping:   Fracción de amortiguamiento crítico (0.05 = 5 %).
        n_periods: Número de puntos del espectro (resolución).
        t_max:     Período máximo en segundos.
        g_cms2:    Aceleración de gravedad en cm/s².

    Returns:
        (periods [s], Sa [cm/s²])  — ambos como arrays numpy.
    """
    key = (zone, soil.upper())
    if key not in _NCH433_PARAMS:
        raise ValueError(
            f"Zona {zone} o suelo '{soil}' no reconocidos. "
            f"Zonas: 1-3. Suelos: A, B, C, D."
        )

    T0, Tn, A0, S, Ia, p = _NCH433_PARAMS[key]

    # Factor de amortiguamiento η (NCh433 §6.3.4)
    # Para ξ=5% → η=1; para otros valores:
    eta = np.sqrt(10.0 / (5.0 + damping * 100.0))

    # Grilla de períodos
    periods = np.linspace(0.0, t_max, n_periods)
    sa = np.zeros_like(periods)

    for i, T in enumerate(periods):
        if T <= T0:
            if T <= 0:
                sa_base = A0 * S  # PGA en T=0 (sin amplificación Ia)
            else:
                # Rama ascendente lineal: A0*S → A0*S*Ia entre T=0 y T=T0
                sa_base = A0 * S + (A0 * S * Ia - A0 * S) * (T / T0)
        elif T <= Tn:
            # Zona de aceleración constante (meseta)
            sa_base = A0 * S * Ia
        else:
            # Zona descendente
            sa_base = A0 * S * Ia * (Tn / T) ** p

        # Escalar al amortiguamiento solicitado
        sa[i] = sa_base * eta * g_cms2  # convertir g → cm/s²

    return periods, sa


# ---------------------------------------------------------------------------
# Espectro de diseño ASCE 7-22
# ---------------------------------------------------------------------------

# Factores de amplificación de suelo Fa y Fv (Tabla 11.4-1 y 11.4-2, simplificado)
_ASCE7_FA = {
    # site_class: {Ss_bracket: Fa}
    "A": {0.25: 0.8, 0.5: 0.8, 0.75: 0.8, 1.0: 0.8, 1.25: 0.8},
    "B": {0.25: 0.9, 0.5: 0.9, 0.75: 0.9, 1.0: 0.9, 1.25: 0.9},
    "C": {0.25: 1.3, 0.5: 1.3, 0.75: 1.2, 1.0: 1.2, 1.25: 1.2},
    "D": {0.25: 1.6, 0.5: 1.4, 0.75: 1.2, 1.0: 1.1, 1.25: 1.0},
    "E": {0.25: 2.4, 0.5: 1.7, 0.75: 1.3, 1.0: 1.1, 1.25: 0.9},
}

_ASCE7_FV = {
    "A": {0.1: 0.8, 0.2: 0.8, 0.3: 0.8, 0.4: 0.8, 0.5: 0.8},
    "B": {0.1: 0.8, 0.2: 0.8, 0.3: 0.8, 0.4: 0.8, 0.5: 0.8},
    "C": {0.1: 1.5, 0.2: 1.5, 0.3: 1.5, 0.4: 1.5, 0.5: 1.5},
    "D": {0.1: 2.4, 0.2: 2.2, 0.3: 2.0, 0.4: 1.9, 0.5: 1.8},
    "E": {0.1: 4.2, 0.2: 3.3, 0.3: 2.8, 0.4: 2.4, 0.5: 2.2},
}

ASCE7_SITE_CLASSES = {
    "A": "Clase A — Roca dura (Vs30 > 1500 m/s)",
    "B": "Clase B — Roca (760–1500 m/s)",
    "C": "Clase C — Suelo muy denso/roca blanda (360–760 m/s)",
    "D": "Clase D — Suelo rígido (180–360 m/s)",
    "E": "Clase E — Suelo blando (<180 m/s)",
}


def _interp_fa(site_class: str, Ss: float) -> float:
    table = _ASCE7_FA.get(site_class.upper(), _ASCE7_FA["D"])
    keys = sorted(table.keys())
    vals = [table[k] for k in keys]
    return float(np.interp(Ss, keys, vals))


def _interp_fv(site_class: str, S1: float) -> float:
    table = _ASCE7_FV.get(site_class.upper(), _ASCE7_FV["D"])
    keys = sorted(table.keys())
    vals = [table[k] for k in keys]
    return float(np.interp(S1, keys, vals))


def asce7_spectrum(
    Ss: float = 1.0,
    S1: float = 0.4,
    site_class: str = "D",
    damping: float = 0.05,
    n_periods: int = 200,
    t_max: float = 4.0,
    g_cms2: float = 980.665,
) -> Tuple[np.ndarray, np.ndarray]:
    """Espectro de diseño ASCE 7-22 §11.4.

    Args:
        Ss:         Aceleración espectral corto período MCEr [g].
        S1:         Aceleración espectral 1 s MCEr [g].
        site_class: Clase de sitio NEHRP ('A'–'E').
        damping:    Fracción de amortiguamiento crítico (0.05 = 5 %).
        n_periods:  Resolución del espectro.
        t_max:      Período máximo en segundos.
        g_cms2:     Aceleración de gravedad en cm/s².

    Returns:
        (periods [s], Sa [cm/s²])
    """
    Fa = _interp_fa(site_class, Ss)
    Fv = _interp_fv(site_class, S1)

    SMS = Fa * Ss          # §11.4.3
    SM1 = Fv * S1          # §11.4.3
    SDS = (2.0 / 3.0) * SMS   # §11.4.4
    SD1 = (2.0 / 3.0) * SM1   # §11.4.4

    T0 = 0.2 * SD1 / SDS if SDS > 0 else 0.02
    Ts = SD1 / SDS if SDS > 0 else 0.2
    TL = 8.0  # período largo (simplificado; varía por región)

    # Factor de amortiguamiento BL (ASCE 7-22 §17.5.4 simplificado)
    # Para espectro elástico con ξ ≠ 5%:
    xi_pct = damping * 100.0
    if xi_pct <= 2:
        BL = 0.8
    elif xi_pct <= 5:
        BL = 1.0
    elif xi_pct <= 10:
        BL = 1.2
    elif xi_pct <= 20:
        BL = 1.5
    elif xi_pct <= 30:
        BL = 1.7
    else:
        BL = 1.9

    periods = np.linspace(0.0, t_max, n_periods)
    sa = np.zeros_like(periods)

    for i, T in enumerate(periods):
        if T <= 0:
            sa_g = SDS * (0.4 + 0.6 * T / T0) if T0 > 0 else SDS * 0.4
        elif T <= T0:
            sa_g = SDS * (0.4 + 0.6 * T / T0)
        elif T <= Ts:
            sa_g = SDS
        elif T <= TL:
            sa_g = SD1 / T if T > 0 else 0.0
        else:
            sa_g = SD1 * TL / T**2 if T > 0 else 0.0

        sa[i] = sa_g * g_cms2 / BL

    return periods, sa
