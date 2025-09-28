"""
Pruebas básicas para src/core
"""
import pytest
from src.core.data_reader import DataReader
from src.core.magnitude import estimate_local_magnitude
import numpy as np

def test_data_reader_empty():
    reader = DataReader()
    # Debe lanzar error si buffer vacío
    with pytest.raises(Exception):
        reader.load_bytes(buffer=None)

def test_magnitude_simple():
    # Magnitud local placeholder
    picks = [{"phase": "P", "time_rel": 0.0, "station": "STA", "channel": "CH", "method": "manual"}]
    data = np.ones(100)
    result = estimate_local_magnitude(picks, data, 100.0, "STA")
    assert result is not None
