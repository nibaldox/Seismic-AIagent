"""
Golden test para waveform_analysis prompt IA.
Se salta si no hay OPENROUTER_API_KEY configurado (requiere llamada real a LLM).
"""
import os

import pytest

SKIP_IF_NO_API = pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY no configurada — test requiere llamada real a LLM",
)


@SKIP_IF_NO_API
def test_waveform_analysis_golden():
    from src.ai_agent.seismic_interpreter import load_agent_suite, run_primary_analysis

    agents = load_agent_suite()
    # Prompt de ejemplo fijo
    prompt = "Waveform: canal Z, duración 60s, fs=100Hz, sin picks."
    result = run_primary_analysis(agents, prompt)
    # Snapshot esperado (simplificado)
    expected = "canal Z: sin eventos sísmicos detectados"
    assert expected in result
