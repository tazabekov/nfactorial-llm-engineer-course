import importlib

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


def test_dotenv_values_reach_module_constants_at_import(tmp_path, monkeypatch):
    """I4: значения из .env должны доходить до констант модуля при импорте,
    а не только через форму PREFIX=value python app.py.

    Раньше config.py читал os.getenv() для FAL_MOCK/AGENT_MODEL/... на
    верхнем уровне модуля, а load_dotenv() вызывался только внутри
    load_environment() — функции, которую никто не зовёт при обычном
    импорте (её вызывает только app.main(), и то уже ПОСЛЕ того, как
    константы были прочитаны). Поэтому FAL_MOCK=0 и AGENT_MODEL из .env.
    example тихо игнорировались.

    Тест подменяет dotenv.load_dotenv на версию, которая всегда грузит наш
    временный .env (сам путь REPO_ROOT/.env config.py пересчитывает заново
    при каждом импорте от расположения файла, поэтому просто monkeypatch
    config.REPO_ROOT здесь бесполезен), затем перезагружает модуль config и
    проверяет, что значения из файла долетели до констант.
    """
    import dotenv

    env_file = tmp_path / ".env"
    env_file.write_text(
        "FAL_MOCK=0\nAGENT_MODEL=test-model-from-dotenv\n", encoding="utf-8"
    )

    monkeypatch.delenv("FAL_MOCK", raising=False)
    monkeypatch.delenv("AGENT_MODEL", raising=False)

    real_load_dotenv = dotenv.load_dotenv
    monkeypatch.setattr(
        dotenv, "load_dotenv", lambda *args, **kwargs: real_load_dotenv(env_file)
    )

    importlib.reload(config)
    try:
        assert config.FAL_MOCK is False
        assert config.AGENT_MODEL == "test-model-from-dotenv"
    finally:
        # Возвращаем окружение и dotenv.load_dotenv в исходное состояние ДО
        # финальной перезагрузки — иначе модуль снова подхватил бы наш
        # временный .env и константы остались бы испорченными для всех
        # тестов, которые запустятся после этого.
        monkeypatch.undo()
        importlib.reload(config)
