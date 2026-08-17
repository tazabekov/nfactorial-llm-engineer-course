"""Общие фикстуры pytest для проекта ai-avatar-agent.

Изолируют тесты от диска, чтобы запуск набора тестов был герметичным:
результат прогона не должен зависеть от файлов, оставленных предыдущим
прогоном, и тесты не должны писать в боевой каталог кэша проекта.
"""

from __future__ import annotations

import pytest

from mcp_servers.common import cache


@pytest.fixture(autouse=True)
def _isolated_cache_dir(monkeypatch, tmp_path):
    """Подменяет каталог TTL-кэша на временный для каждого теста.

    ``mcp_servers.common.cache`` читает каталог кэша как модульную
    переменную ``CACHE_DIR`` в момент вызова, поэтому патчим именно её —
    так это подхватывают и сам модуль кэша, и любой сервер, который
    импортирует функции ``cache_get``/``cache_set`` (они разделяют
    глобальное пространство имён модуля ``cache``).

    Если тест сам патчит ``cache.CACHE_DIR`` (см. ``tests/test_cache.py``),
    его собственный ``monkeypatch.setattr`` выполняется позже и просто
    перекрывает значение, установленное здесь, — конфликта нет.
    """
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / "cache")
