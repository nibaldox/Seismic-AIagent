"""
Golden test para histogram_analysis prompt IA.
Se salta si no hay OPENROUTER_API_KEY configurado (requiere llamada real a LLM).
"""
import os

import pytest

SKIP_IF_NO_API = pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY no configurada — test requiere llamada real a LLM",
)


@SKIP_IF_NO_API
def test_histogram_analysis_golden():
    from src.ai_agent.seismic_interpreter import load_agent_suite, run_histogram_analysis

    agents = load_agent_suite()
    # Prompt de ejemplo fijo
    prompt = "Histograma: bins=50, normalizado, acumulado, logy. Variable=Voltage."
    result = run_histogram_analysis(
        agents,
        filename="demo.csv",
        meta={},
        df_head="|Voltage|\n|1.0|",
        columns=["Voltage"],
        time_range="2025-09-28",
        notes=prompt,
    )
    # Snapshot esperado (simplificado)
    expected = "Voltage: tendencia estable, sin anomalías."
    assert expected in result
