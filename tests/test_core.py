"""Pruebas rápidas de los componentes del núcleo."""

from __future__ import annotations

import importlib
from io import BytesIO

import numpy as np
import pytest

from src.core.data_reader import (
    DataReader,
    UnsupportedFormatError,
    _get_obspy_module,
    _resolve_descriptor,
)
from src.core.kelunji_metadata import load_kelunji_metadata


@pytest.mark.skipif(importlib.util.find_spec("obspy") is not None, reason="ObsPy instalado")
def test_data_reader_requires_obspy():
    reader = DataReader()
    with pytest.raises(ImportError):
        reader.load_bytes(buffer=BytesIO(b""))


def test_resolve_descriptor_unknown_extension():
    with pytest.raises(UnsupportedFormatError):
        _resolve_descriptor(name="evento.xyz")


def test_resolve_descriptor_hint_miniseed():
    descriptor = _resolve_descriptor(format_hint="mseed")
    assert descriptor.format_argument == "MSEED"
    assert "MiniSEED" in descriptor.description


def test_resolve_descriptor_ms_extension():
    descriptor = _resolve_descriptor(name="trace.ms")
    assert descriptor.format_argument == "MSEED"
    assert "MiniSEED" in descriptor.description


@pytest.mark.skipif(importlib.util.find_spec("obspy") is None, reason="ObsPy no instalado")
def test_get_obspy_module_returns_module():
    module = _get_obspy_module()
    assert hasattr(module, "Stream")


@pytest.mark.skipif(importlib.util.find_spec("obspy") is None, reason="ObsPy no instalado")
def test_load_gecko_histogram_from_bytes():
    reader = DataReader()
    data = np.array([0.1, 0.2, 0.3, 0.4], dtype="<f4")
    buffer = BytesIO(data.tobytes())
    stream = reader.load_bytes(buffer=buffer, format_hint="gecko").stream
    assert len(stream) == 1
    assert np.isclose(stream[0].data[0], 0.1)


def test_load_bytes_without_hint_raises():
    reader = DataReader()
    buffer = BytesIO(b"test")
    with pytest.raises(UnsupportedFormatError):
        reader.load_bytes(buffer=buffer)


def test_load_kelunji_metadata_parses_sections():
    sample = (
        '"lat"=-24.173498\n'
        '"long"=-69.045128\n'
        '"sensor_name"="Gecko SMA-2G"\n'
        '"custom_sensitivity_A_0"=0.203943\n'
    )
    metadata = load_kelunji_metadata(BytesIO(sample.encode("utf-8")))
    assert metadata.raw["lat"] == "-24.173498"

    sections = metadata.to_sections()
    assert sections["Position"]["lat"] == "-24.173498"
    assert sections["Sensor"]["sensor_name"] == "Gecko SMA-2G"
