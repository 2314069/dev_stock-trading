import pytest

from config import LLMSettings, Settings, get_settings, reset_settings, set_settings


@pytest.fixture(autouse=True)
def _reset_settings_around_each_test():
    reset_settings()
    yield
    reset_settings()


def test_defaults_when_no_env():
    s = get_settings()
    assert s.llm.default_model == "claude-sonnet-4-6"
    assert s.llm.default_max_tokens == 2048
    assert s.llm.default_temperature == 0.0


def test_settings_singleton_returns_same_instance():
    assert get_settings() is get_settings()


def test_set_settings_replaces_singleton():
    set_settings(Settings(llm=LLMSettings(default_model="claude-haiku-4-5")))
    assert get_settings().llm.default_model == "claude-haiku-4-5"


def test_reset_settings_clears_cache(monkeypatch):
    monkeypatch.setenv("LLM_DEFAULT_MODEL", "claude-opus-4-7")
    reset_settings()
    assert get_settings().llm.default_model == "claude-opus-4-7"


def test_from_env_reads_all_keys(monkeypatch):
    monkeypatch.setenv("LLM_DEFAULT_MODEL", "claude-haiku-4-5")
    monkeypatch.setenv("LLM_DEFAULT_MAX_TOKENS", "4096")
    monkeypatch.setenv("LLM_DEFAULT_TEMPERATURE", "0.3")
    s = Settings.from_env()
    assert s.llm.default_model == "claude-haiku-4-5"
    assert s.llm.default_max_tokens == 4096
    assert s.llm.default_temperature == 0.3


def test_from_env_partial_override(monkeypatch):
    monkeypatch.setenv("LLM_DEFAULT_MODEL", "claude-opus-4-7")
    monkeypatch.delenv("LLM_DEFAULT_MAX_TOKENS", raising=False)
    s = Settings.from_env()
    assert s.llm.default_model == "claude-opus-4-7"
    assert s.llm.default_max_tokens == 2048  # default kept
