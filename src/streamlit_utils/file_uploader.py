"""Reusable Streamlit file uploader components."""

from __future__ import annotations

from io import BytesIO
from typing import Iterable, List, Optional

import streamlit as st


def seismic_file_uploader(label: str, *, accept_multiple: bool = False) -> Optional[Iterable[BytesIO]]:
    """Render a Streamlit file uploader configured for seismic data."""

    files = st.file_uploader(
        label,
        type=["mseed", "sac", "sg2", "seg2", "suds", "bin"],
        accept_multiple_files=accept_multiple,
        help="Supported formats: MiniSEED, SAC, SEG-2, PC-SUDS, Gecko histograms",
    )
    if not files:
        return None

    if accept_multiple:
        return files
    return [files]
