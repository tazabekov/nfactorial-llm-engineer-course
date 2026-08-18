import time

from mcp_servers.common import cache


def test_set_then_get_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    cache.cache_set("twogis", "суши центр", {"items": [1, 2]})
    assert cache.cache_get("twogis", "суши центр") == {"items": [1, 2]}


def test_miss_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    assert cache.cache_get("twogis", "ничего") is None


def test_expired_entry_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(cache, "CACHE_TTL_SECONDS", 0)
    cache.cache_set("twogis", "суши", {"items": []})
    time.sleep(0.01)
    assert cache.cache_get("twogis", "суши") is None


def test_key_normalisation_ignores_case_and_spaces(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    cache.cache_set("twogis", "  Суши  Центр ", {"items": [1]})
    assert cache.cache_get("twogis", "суши центр") == {"items": [1]}
