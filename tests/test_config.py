import pytest

from telos.config import DEFAULT_DATABASE_URL, Settings, database_url_from_env


def test_settings_reads_ollama_and_database_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "cloud-model")
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://ollama.com")
    monkeypatch.setenv("OLLAMA_API_KEY", "secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db:5432/telos")

    settings = Settings.from_env()

    assert settings.ollama_model == "cloud-model"
    assert settings.ollama_base_url == "https://ollama.com"
    assert settings.ollama_api_key == "secret"
    assert settings.checkpoint_database_url == "postgresql://user:pass@db:5432/telos"


def test_settings_defaults_and_requires_a_model(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert database_url_from_env() == DEFAULT_DATABASE_URL
    with pytest.raises(RuntimeError, match="OLLAMA_MODEL"):
        Settings.from_env()
