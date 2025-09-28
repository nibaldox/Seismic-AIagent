"""
Pruebas básicas para src/ai_agent
"""
from src.ai_agent.earthquake_search import EarthquakeQuery
from src.ai_agent.seismic_interpreter import load_agent_suite

def test_earthquake_query():
    q = EarthquakeQuery(latitude=10.0, longitude=20.0, radius_km=100)
    assert q.latitude == 10.0
    assert q.radius_km == 100

def test_load_agent_suite():
    agents = load_agent_suite()
    assert isinstance(agents, dict)
