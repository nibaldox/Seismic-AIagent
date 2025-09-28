"""
Golden test para waveform_analysis prompt IA
"""
from src.ai_agent.seismic_interpreter import load_agent_suite, run_primary_analysis

def test_waveform_analysis_golden():
    agents = load_agent_suite()
    # Prompt de ejemplo fijo
    prompt = "Waveform: canal Z, duración 60s, fs=100Hz, sin picks."
    result = run_primary_analysis(agents, prompt)
    # Snapshot esperado (simplificado)
    expected = "canal Z: sin eventos sísmicos detectados"
    assert expected in result
