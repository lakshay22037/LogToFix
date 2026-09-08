import pytest

from llm_core.client import ClaudeClient, FakeClient, LLMSuggestionError, get_default_client
from llm_core.schemas import FixSuggestion


def test_fake_client_returns_valid_fix_suggestion():
    client = FakeClient()
    suggestion = client.suggest_fix("system prompt", "user prompt")

    assert isinstance(suggestion, FixSuggestion)
    assert suggestion.confidence == 0.0
    assert "FAKE CLIENT" in suggestion.explanation


def test_get_default_client_defaults_to_fake(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert isinstance(get_default_client(), FakeClient)


def test_get_default_client_selects_claude(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    assert isinstance(get_default_client(), ClaudeClient)


def test_get_default_client_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "not-a-real-provider")
    with pytest.raises(LLMSuggestionError):
        get_default_client()


def test_claude_client_wraps_missing_credentials_as_llm_suggestion_error(monkeypatch):
    # anthropic.Anthropic() validates credentials lazily (only when a request
    # is actually attempted), so construction succeeds with none configured
    # and the failure surfaces — and must be wrapped — inside suggest_fix.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_PROFILE", raising=False)
    client = ClaudeClient()

    with pytest.raises(LLMSuggestionError):
        client.suggest_fix("system", "user")
