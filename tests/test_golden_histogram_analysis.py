"""
Golden test para histogram_analysis prompt IA
"""
from src.ai_agent.seismic_interpreter import load_agent_suite, run_histogram_analysis

def test_histogram_analysis_golden():
    agents = load_agent_suite()
    # Prompt de ejemplo fijo
    prompt = "Histograma: bins=50, normalizado, acumulado, logy. Variable=Voltage."
    result = run_histogram_analysis(agents, filename="demo.csv", meta={}, df_head="|Voltage|\n|1.0|", columns=["Voltage"], time_range="2025-09-28", notes=prompt)
    # Snapshot esperado (simplificado)
    expected = "Voltage: tendencia estable, sin anomalías."
    assert expected in result
