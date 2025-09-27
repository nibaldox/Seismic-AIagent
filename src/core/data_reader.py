"""Utilidades de carga de datos sísmicos basadas en ObsPy."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from src.utils.logger import setup_logger

LOGGER = setup_logger(__name__)


class UnsupportedFormatError(ValueError):
    """Se lanza cuando el formato de archivo no es reconocido."""


class DataReadError(RuntimeError):
    """Se lanza cuando la lectura del archivo sísmico falla."""


@dataclass(frozen=True)
class FormatDescriptor:
    """Describe cómo debe cargarse un archivo determinado."""

    description: str
    format_argument: Optional[str]
    custom_loader: Optional[str] = None

    @property
    def uses_custom_loader(self) -> bool:
        return self.custom_loader is not None


FORMAT_REGISTRY: Dict[str, FormatDescriptor] = {
    ".mseed": FormatDescriptor("MiniSEED", "MSEED"),
    ".miniseed": FormatDescriptor("MiniSEED", "MSEED"),
    ".ms": FormatDescriptor("MiniSEED", "MSEED"),
    ".sac": FormatDescriptor("SAC", "SAC"),
    ".seg2": FormatDescriptor("SEG-2", "SEG2"),
    ".sg2": FormatDescriptor("SEG-2", "SEG2"),
    ".suds": FormatDescriptor("PC-SUDS", "SUDS"),
    ".bin": FormatDescriptor("Gecko Histogram", None, custom_loader="_load_gecko_histogram"),
}

FORMAT_ALIASES: Dict[str, str] = {
    "mseed": ".mseed",
    "miniseed": ".mseed",
    "ms": ".ms",
    "sac": ".sac",
    "seg2": ".seg2",
    "suds": ".suds",
    "gecko": ".bin",
}


_OBSPY_MODULE = None


@dataclass
class LoadedStream:
    """Wrapper containing an ObsPy stream and source metadata."""

    stream: Any
    source_path: Optional[Path]
    format_description: Optional[str] = None

    @property
    def summary(self) -> str:
        """Return a human-readable summary of the stream."""

        header = f"{len(self.stream)} traces"
        if self.format_description:
            header = f"{self.format_description} | {header}"
        summary_lines = [header, *(tr.stats.__str__() for tr in self.stream)]
        return "\n".join(summary_lines)


class DataReader:
    """Load seismic files from disk or in-memory bytes."""

    def load_files(self, files: Iterable[Path]) -> List[LoadedStream]:
        """Load multiple seismic files into ObsPy streams."""

        loaded: List[LoadedStream] = []
        for path in files:
            loaded.append(self._load_single(path))
        return loaded

    def _load_single(self, file_path: Path) -> LoadedStream:
        LOGGER.info("Loading seismic file: %s", file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"No se encuentra el archivo: {file_path}")

        descriptor = _resolve_descriptor(path=file_path)
        try:
            stream = self._load_with_descriptor(descriptor, source=file_path, is_bytes=False)
        except Exception as exc:
            raise DataReadError(f"Error al leer {file_path.name}: {exc}") from exc

        return LoadedStream(stream=stream, source_path=file_path, format_description=descriptor.description)

    def load_bytes(self, *, buffer, format_hint: Optional[str] = None) -> LoadedStream:
        """Load a seismic stream from an in-memory buffer."""

        descriptor = _resolve_descriptor(
            name=getattr(buffer, "name", None),
            format_hint=format_hint,
        )

        try:
            stream = self._load_with_descriptor(descriptor, source=buffer, is_bytes=True)
        except Exception as exc:
            raise DataReadError(f"Error al leer flujo en memoria: {exc}") from exc

        return LoadedStream(stream=stream, source_path=None, format_description=descriptor.description)

    def _load_with_descriptor(self, descriptor: FormatDescriptor, *, source, is_bytes: bool):
        if descriptor.uses_custom_loader:
            loader = getattr(self, descriptor.custom_loader)
            return loader(source, is_bytes=is_bytes)

        module = _get_obspy_module()
        read = module.read
        kwargs = {"format": descriptor.format_argument} if descriptor.format_argument else {}

        if is_bytes:
            if hasattr(source, "seek"):
                source.seek(0)
            return read(source, **kwargs)

        return read(str(source), **kwargs)

    def _load_gecko_histogram(self, source, *, is_bytes: bool):
        module = _get_obspy_module()
        Trace = module.Trace
        Stream = module.Stream
        UTCDateTime = module.UTCDateTime

        raw = _read_binary(source, expect_reset=is_bytes)
        if not raw:
            raise ValueError("El archivo Gecko está vacío.")

        data = np.frombuffer(raw, dtype="<f4")
        if data.size == 0:
            data = np.frombuffer(raw, dtype="<i4")
        if data.size == 0:
            raise ValueError("No se pudieron extraer muestras del archivo Gecko.")

        trace = Trace(data=data.astype(float))
        trace.stats.channel = "HGE"
        trace.stats.delta = 1.0
        trace.stats.starttime = UTCDateTime(0)

        return Stream([trace])


def _get_obspy_module():
    """Devuelve el módulo de ObsPy, asegurando un único import."""

    global _OBSPY_MODULE
    if _OBSPY_MODULE is not None:
        return _OBSPY_MODULE

    try:
        _OBSPY_MODULE = importlib.import_module("obspy")
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ImportError(
            "ObsPy es requerido para cargar datos sísmicos. Instálalo con `pip install obspy`."
        ) from exc
    return _OBSPY_MODULE


def _resolve_descriptor(
    *, path: Optional[Path] = None, name: Optional[str] = None, format_hint: Optional[str] = None
) -> FormatDescriptor:
    """Determina el descriptor adecuado en base a hint, nombre o ruta."""

    if format_hint:
        alias = FORMAT_ALIASES.get(format_hint.lower())
        if alias and alias in FORMAT_REGISTRY:
            return FORMAT_REGISTRY[alias]

    candidates: List[str] = []
    if name:
        candidates.append(name)
    if path:
        candidates.append(path.name)

    for candidate in candidates:
        ext = Path(candidate).suffix.lower()
        if ext in FORMAT_REGISTRY:
            return FORMAT_REGISTRY[ext]
        lowered = candidate.lower()
        if lowered in FORMAT_REGISTRY:
            return FORMAT_REGISTRY[lowered]

    raise UnsupportedFormatError(
        "Formato no soportado. Usa archivos MiniSEED, SAC, SEG-2, SUDS o histogramas Gecko."
    )


def _read_binary(source, *, expect_reset: bool) -> bytes:
    """Lee bytes desde un path o un buffer en memoria."""

    if hasattr(source, "read"):
        data = source.read()
        if expect_reset and hasattr(source, "seek"):
            source.seek(0)
        return data

    path = Path(source)
    with path.open("rb") as handle:
        return handle.read()
