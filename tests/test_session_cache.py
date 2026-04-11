"""Tests para la lógica LRU del caché de streams en session_state.py.

Se prueban las funciones internas:
    _store_stream_in_cache, _get_stream_from_cache, _clear_stream_cache.

Los tests funcionan SIN Streamlit: se resetea `session_state._STREAM_CACHE` a
un OrderedDict vacío antes de cada test para aislar el estado compartido.
"""
from __future__ import annotations

import sys
from collections import OrderedDict
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Parche de Streamlit ANTES de importar el módulo bajo test.
# De esta forma el fallback a OrderedDict se activa automáticamente.
# ---------------------------------------------------------------------------
# Si streamlit ya fue importado por otro test, simplemente mockeamos
# cache_resource para que falle y así forzar el fallback del módulo.

_st_mock = mock.MagicMock()
_st_mock.cache_resource.side_effect = Exception("No Streamlit in tests")
_st_mock.session_state = {}

# Parchear streamlit en sys.modules para que el import del módulo use el mock
sys.modules.setdefault("streamlit", _st_mock)

import src.streamlit_utils.session_state as session_state  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture: resetear el caché antes de cada test
# ---------------------------------------------------------------------------

def _reset_cache() -> None:
    """Resetea _STREAM_CACHE a None para forzar re-inicialización."""
    session_state._STREAM_CACHE = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stream(name: str) -> dict:
    """Stream ficticio (cualquier objeto)."""
    return {"id": name, "data": list(range(10))}


# ---------------------------------------------------------------------------
# Tests de almacenamiento básico
# ---------------------------------------------------------------------------

class TestStorAndRetrieve:
    def setup_method(self):
        _reset_cache()

    def test_store_and_retrieve(self):
        stream = _make_stream("test01")
        session_state._store_stream_in_cache("test01", stream)
        retrieved = session_state._get_stream_from_cache("test01")
        assert retrieved is stream

    def test_retrieve_missing_key_returns_none(self):
        assert session_state._get_stream_from_cache("no_existe") is None

    def test_store_multiple_and_retrieve_each(self):
        for i in range(5):
            session_state._store_stream_in_cache(f"s{i}", _make_stream(f"s{i}"))
        for i in range(5):
            r = session_state._get_stream_from_cache(f"s{i}")
            assert r is not None
            assert r["id"] == f"s{i}"

    def test_overwrite_same_key(self):
        s1 = _make_stream("k1")
        s2 = {"id": "k1_v2"}
        session_state._store_stream_in_cache("k1", s1)
        session_state._store_stream_in_cache("k1", s2)
        assert session_state._get_stream_from_cache("k1") is s2


# ---------------------------------------------------------------------------
# Tests de evicción LRU
# ---------------------------------------------------------------------------

class TestLruEviction:
    def setup_method(self):
        _reset_cache()

    def test_max_size_respected(self):
        MAX = session_state._STREAM_CACHE_MAX
        for i in range(MAX + 3):
            session_state._store_stream_in_cache(f"s{i}", _make_stream(f"s{i}"))
        store = session_state._cache()
        assert len(store) <= MAX

    def test_oldest_item_evicted_first(self):
        MAX = session_state._STREAM_CACHE_MAX
        # Llenar hasta el límite
        for i in range(MAX):
            session_state._store_stream_in_cache(f"s{i}", _make_stream(f"s{i}"))
        # Añadir uno más → "s0" debe ser evictado
        session_state._store_stream_in_cache("new_entry", _make_stream("new_entry"))
        assert session_state._get_stream_from_cache("s0") is None

    def test_recently_accessed_not_evicted(self):
        MAX = session_state._STREAM_CACHE_MAX
        # Llenar hasta el límite
        for i in range(MAX):
            session_state._store_stream_in_cache(f"s{i}", _make_stream(f"s{i}"))
        # Acceder a s0 → se mueve al final (más reciente)
        session_state._get_stream_from_cache("s0")
        # Añadir nuevo → ahora s1 debería ser el más antiguo y evictado
        session_state._store_stream_in_cache("new_entry", _make_stream("new_entry"))
        assert session_state._get_stream_from_cache("s0") is not None

    def test_exactly_at_max_no_eviction(self):
        MAX = session_state._STREAM_CACHE_MAX
        for i in range(MAX):
            session_state._store_stream_in_cache(f"s{i}", _make_stream(f"s{i}"))
        store = session_state._cache()
        assert len(store) == MAX


# ---------------------------------------------------------------------------
# Tests de limpieza de caché
# ---------------------------------------------------------------------------

class TestClearCache:
    def setup_method(self):
        _reset_cache()

    def test_clear_empties_cache(self):
        for i in range(5):
            session_state._store_stream_in_cache(f"s{i}", _make_stream(f"s{i}"))
        session_state._clear_stream_cache()
        store = session_state._cache()
        assert len(store) == 0

    def test_after_clear_miss_on_previous_keys(self):
        session_state._store_stream_in_cache("x", _make_stream("x"))
        session_state._clear_stream_cache()
        assert session_state._get_stream_from_cache("x") is None

    def test_can_store_after_clear(self):
        session_state._store_stream_in_cache("a", _make_stream("a"))
        session_state._clear_stream_cache()
        session_state._store_stream_in_cache("b", _make_stream("b"))
        assert session_state._get_stream_from_cache("b") is not None


# ---------------------------------------------------------------------------
# Tests de hit / miss
# ---------------------------------------------------------------------------

class TestHitMiss:
    def setup_method(self):
        _reset_cache()

    def test_hit_returns_correct_object(self):
        obj = {"payload": 42}
        session_state._store_stream_in_cache("hit_key", obj)
        result = session_state._get_stream_from_cache("hit_key")
        assert result is obj
        assert result["payload"] == 42

    def test_miss_returns_none(self):
        assert session_state._get_stream_from_cache("miss_key") is None

    def test_hit_moves_to_end(self):
        """Verificar que un hit mueve el item al final del OrderedDict."""
        session_state._store_stream_in_cache("first", _make_stream("first"))
        session_state._store_stream_in_cache("second", _make_stream("second"))
        # Acceder a "first" → debe moverse al final
        session_state._get_stream_from_cache("first")
        store = session_state._cache()
        keys = list(store.keys())
        assert keys[-1] == "first"

    def test_stream_cache_max_constant(self):
        assert session_state._STREAM_CACHE_MAX == 10
