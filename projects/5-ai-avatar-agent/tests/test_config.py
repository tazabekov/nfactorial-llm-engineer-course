import pytest

import config


def test_require_keys_reports_all_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FAL_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        config.require_keys(need_fal=True)
    message = str(exc.value)
    assert "OPENAI_API_KEY" in message
    assert "FAL_KEY" in message


def test_require_keys_passes_when_present(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("FAL_KEY", "y")
    config.require_keys(need_fal=True)


def test_require_keys_ignores_fal_when_not_needed(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.delenv("FAL_KEY", raising=False)
    config.require_keys(need_fal=False)


def test_directories_are_absolute_and_exist():
    for path in (config.CACHE_DIR, config.OUTPUT_DIR, config.ASSETS_PRIVATE_DIR):
        assert path.is_absolute()
        assert path.exists()
