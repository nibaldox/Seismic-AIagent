"""AI agent module smoke tests."""

from __future__ import annotations

import importlib

import pytest

from src.ai_agent import seismic_interpreter as module
from src.ai_agent.seismic_interpreter import AgentSpec, _infer_provider, _resolve_task_model


@pytest.fixture(autouse=True)
def reset_agent_state():
    original_cache_enabled = module._CACHE_ENABLED
    original_cache_max = module._CACHE_MAX_ENTRIES
    original_agent = module._Agent
    module._AGENT_CACHE.clear()
    yield
    module._AGENT_CACHE.clear()
    module._CACHE_ENABLED = original_cache_enabled
    module._CACHE_MAX_ENTRIES = original_cache_max
    module._Agent = original_agent


def test_infer_provider_openrouter():
    assert _infer_provider("deepseek/deepseek-chat-v3.1:free") == "openrouter"


def test_resolve_task_model_prefers_task_model():
    config = {
        "default_model": {"provider": "openrouter", "id": "deepseek/deepseek-chat-v3.1:free"}
    }
    task_data = {"preferred": "ollama/llama3.2"}
    provider, model_id = _resolve_task_model(config, task_data)
    assert provider == "ollama"
    assert model_id == "ollama/llama3.2"


@pytest.mark.skipif(importlib.util.find_spec("agno") is None, reason="Agno not installed")
def test_create_agent_requires_agno():
    from src.ai_agent.seismic_interpreter import create_agent

    spec = AgentSpec(
        provider="openrouter",
        model_id="deepseek/deepseek-chat-v3.1:free",
        role="Test Agent",
        instructions="Return a test message.",
    )

    agent = create_agent(spec)
    assert agent is not None


class DummyAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def _install_dummy_agent(monkeypatch):
    monkeypatch.setattr(module, "_Agent", DummyAgent)
    monkeypatch.setattr(module, "_resolve_model", lambda **kwargs: object())


def test_create_agent_uses_cache(monkeypatch):
    _install_dummy_agent(monkeypatch)
    module._CACHE_ENABLED = True
    module._CACHE_MAX_ENTRIES = 2

    events = []

    def monitor(event, *, task=None, extra=None):
        events.append((event, task, extra))

    monkeypatch.setattr(module, "_monitor_event", monitor)

    spec_a = AgentSpec("openrouter", "model-a", "Role A", "Do A")
    spec_b = AgentSpec("openrouter", "model-b", "Role B", "Do B")
    spec_c = AgentSpec("openrouter", "model-c", "Role C", "Do C")

    agent_a_first = module.create_agent(spec_a)
    agent_a_second = module.create_agent(spec_a)
    assert agent_a_first is agent_a_second
    assert ("agent_cache_hit", "Role A", None) in events

    module.create_agent(spec_b)
    module.create_agent(spec_c)
    assert spec_a not in module._AGENT_CACHE
    assert any(event[0] == "agent_cache_evicted" and event[1] == "Role A" for event in events)


def test_load_agent_suite_applies_monitoring(monkeypatch):
    _install_dummy_agent(monkeypatch)
    module._AGENT_CACHE.clear()

    config = {
        "seismic_interpreter": {
            "cache": {"enable_agent_cache": True, "max_entries": 4},
            "monitoring": {"enabled": True, "log_level": "info"},
            "default_model": {"provider": "openrouter", "id": "default-model"},
            "task_models": {
                "phase_identification": {
                    "preferred": "openrouter/phase",
                    "notes": "Find P/S arrivals.",
                }
            },
        }
    }

    monkeypatch.setattr(module, "load_yaml", lambda path: config)

    events = []

    def monitor(event, *, task=None, extra=None):
        events.append((event, task, extra))

    monkeypatch.setattr(module, "_monitor_event", monitor)

    agents = module.load_agent_suite(config_path="ignored")
    assert "phase_identification" in agents
    instruction = agents["phase_identification"].kwargs["instructions"][0]
    assert "Guidance" in instruction
    assert any(event[0] == "agent_registered" and event[1] == "phase_identification" for event in events)

    module._AGENT_CACHE.clear()
