"""
Utilidad para validación y sanitización de CSV
"""
import pandas as pd
from typing import List, Dict, Any

def validate_csv(df: pd.DataFrame, required_columns: List[str] = None, column_types: Dict[str, Any] = None, ranges: Dict[str, tuple] = None) -> Dict[str, Any]:
    """
    Valida un DataFrame según columnas requeridas, tipos y rangos.
    Retorna dict con errores y advertencias.
    """
    report = {"errors": [], "warnings": []}
    required_columns = required_columns or []
    column_types = column_types or {}
    ranges = ranges or {}

    # Verificar columnas requeridas
    for col in required_columns:
        if col not in df.columns:
            report["errors"].append(f"Falta columna requerida: {col}")

    # Verificar tipos
    for col, typ in column_types.items():
        if col in df.columns:
            if not pd.api.types.is_dtype_equal(df[col].dtype, typ):
                report["warnings"].append(f"Columna {col} tipo esperado {typ}, encontrado {df[col].dtype}")

    # Verificar rangos
    for col, (minv, maxv) in ranges.items():
        if col in df.columns:
            vals = df[col].dropna()
            if not vals.empty:
                if (vals < minv).any():
                    report["warnings"].append(f"Columna {col} tiene valores < {minv}")
                if (vals > maxv).any():
                    report["warnings"].append(f"Columna {col} tiene valores > {maxv}")

    # Verificar NaN
    for col in df.columns:
        n_nan = df[col].isna().sum()
        if n_nan > 0:
            report["warnings"].append(f"Columna {col} tiene {n_nan} valores NaN")

    return report
