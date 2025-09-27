"""Tests for session state utilities."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.streamlit_utils import session_state as session_module
from src.streamlit_utils.session_state import (
    get_current_stream_name,
    get_selected_trace_label,
    get_session,
    get_stream_summary,
    list_dataset_names,
    register_stream,
    set_current_stream,
    set_selected_trace,
)


class DummyTrace:
    def __init__(self, label: str) -> None:
        self.id = label


@pytest.fixture(autouse=True)
def fake_streamlit(monkeypatch):
    stub = SimpleNamespace(session_state={})
    monkeypatch.setattr(session_module, "st", stub)
    yield
    stub.session_state.clear()
    session_module._apply_current_stream  # keep module available


def _make_stream(prefix: str, count: int = 3):
    return [DummyTrace(f"{prefix}-{idx}") for idx in range(count)]


def test_register_stream_tracks_multiple_datasets():
    register_stream(stream=_make_stream("A"), name="alpha.ms", summary="Alpha summary")
    session = get_session()
    session.ai_results["analysis"] = "to be cleared"

    register_stream(stream=_make_stream("B"), name="beta.ms", summary="Beta summary")

    assert list_dataset_names(session) == ["alpha.ms", "beta.ms"]
    assert get_current_stream_name(session) == "beta.ms"
    assert session.ai_results == {}
    assert get_stream_summary("alpha.ms", session=session) == "Alpha summary"

    set_current_stream("alpha.ms", session=session)
    assert get_current_stream_name(session) == "alpha.ms"
    assert get_stream_summary(session=session) == "Alpha summary"
    assert get_selected_trace_label(session) == "A-0"


def test_set_current_stream_preserves_selection_when_reusing_dataset():
    register_stream(stream=_make_stream("C"), name="gamma.ms", summary="Gamma")
    labels = list_dataset_names()
    assert labels == ["gamma.ms"]

    labels_for_stream = [trace.id for trace in _make_stream("C")]
    set_selected_trace(labels_for_stream[1])
    assert get_selected_trace_label() == labels_for_stream[1]

    set_current_stream("gamma.ms")
    assert get_selected_trace_label() == labels_for_stream[1]