"""Parsing utilities for Kelunji/Gecko station setting (.ss) files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Tuple

_SECTION_RULES: Tuple[Tuple[str, str], ...] = (
    ("format", "Device"),
    ("settings_time", "Device"),
    ("serial", "Device"),
    ("cpv", "Device"),
    ("board_id", "Device"),
    ("channel_config", "Device"),
    ("firmware_version", "Device"),
    ("build_number", "Device"),
    ("log_level", "Device"),
    ("settings_version", "Device"),
    ("sitename", "Station"),
    ("network_code", "Station"),
    ("location_id", "Station"),
    ("sampling_rate", "Station"),
    ("storing_chan", "Channels"),
    ("storing_vsum", "Channels"),
    ("tele_chan", "Channels"),
    ("tele_vsum", "Channels"),
    ("current_gain", "Gain"),
    ("gain", "Gain"),
    ("sensor_power", "Gain"),
    ("gain_A_", "Gain"),
    ("stalta", "Triggers"),
    ("level_trigger", "Triggers"),
    ("sensor_name", "Sensor"),
    ("sensor_sn", "Sensor"),
    ("sens", "Sensor"),
    ("unit", "Sensor"),
    ("custom_", "Sensor"),
    ("input_", "Sensor"),
    ("connection_", "Telemetry"),
    ("socket_port", "Telemetry"),
    ("data_server", "Telemetry"),
    ("send_mode", "Telemetry"),
    ("server_timeout", "Telemetry"),
    ("alarm_", "Safety"),
    ("low_voltage", "Safety"),
    ("high_temperature", "Safety"),
    ("output_", "Safety"),
    ("long", "Position"),
    ("lat", "Position"),
    ("alt", "Position"),
    ("sats", "Position"),
    ("leap_seconds", "Position"),
    ("v_supply", "Environment"),
    ("temperature", "Environment"),
    ("card_", "Storage"),
    ("zero_offset", "Calibration"),
)


def _classify_key(key: str) -> str:
    for prefix, section in _SECTION_RULES:
        if key.startswith(prefix):
            return section
    return "Other"


@dataclass(frozen=True)
class KelunjiMetadata:
    raw: Dict[str, str]

    def to_sections(self) -> Dict[str, Dict[str, str]]:
        sections: Dict[str, Dict[str, str]] = {}
        for key, value in self.raw.items():
            section = _classify_key(key)
            section_dict = sections.setdefault(section, {})
            section_dict[key] = value
        return sections

    def __getitem__(self, item: str) -> str:
        return self.raw[item]


def _normalize_value(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) >= 2:
        cleaned = cleaned[1:-1]
    cleaned = cleaned.replace("\x00", "").strip()
    return cleaned


def _parse_lines(lines: Iterable[str]) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    for original in lines:
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().strip('"')
        metadata[key] = _normalize_value(value)
    return metadata


def loads_kelunji_metadata(content: str) -> KelunjiMetadata:
    return KelunjiMetadata(raw=_parse_lines(content.splitlines()))


def load_kelunji_metadata(source) -> KelunjiMetadata:
    if hasattr(source, "read"):
        raw_bytes = source.read()
        if hasattr(source, "seek"):
            source.seek(0)
    else:
        path = Path(source)
        raw_bytes = path.read_bytes()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = raw_bytes.decode("latin-1", errors="ignore")
    return loads_kelunji_metadata(text)


__all__ = ["KelunjiMetadata", "load_kelunji_metadata", "loads_kelunji_metadata"]
