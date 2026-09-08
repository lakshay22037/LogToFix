import os
from abc import ABC, abstractmethod

import anthropic

from llm_core.schemas import FixSuggestion

DEFAULT_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-5")


class LLMSuggestionError(Exception):
    """Raised for any provider-call failure, so callers handle one exception
    type regardless of which provider is behind LLMClient."""


class LLMClient(ABC):
    """Provider-agnostic interface (see DECISIONS.md: "LLM provider — Claude
    / OpenAI (pluggable)"). Only ClaudeClient exists so far; an OpenAI
    implementation can be added behind this same interface later without
    touching callers."""

    @abstractmethod
    def suggest_fix(self, system_prompt: str, user_prompt: str) -> FixSuggestion:
        raise NotImplementedError


class ClaudeClient(LLMClient):
    def __init__(self, model: str = DEFAULT_MODEL):
        self._client = anthropic.Anthropic()  # resolves ANTHROPIC_API_KEY from env
        self._model = model

    def suggest_fix(self, system_prompt: str, user_prompt: str) -> FixSuggestion:
        try:
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                output_format=FixSuggestion,
            )
        except anthropic.AuthenticationError as e:
            raise LLMSuggestionError(f"Authentication failed: {e}") from e
        except anthropic.RateLimitError as e:
            raise LLMSuggestionError(f"Rate limited: {e}") from e
        except anthropic.APIConnectionError as e:
            raise LLMSuggestionError(f"Connection error: {e}") from e
        except anthropic.APIStatusError as e:
            raise LLMSuggestionError(f"API error ({e.status_code}): {e}") from e
        except TypeError as e:
            # The SDK raises a bare TypeError (not an anthropic.* exception)
            # when no credentials are resolvable at all (no API key, auth
            # token, or CLI profile) — this is a config error, not a bug.
            raise LLMSuggestionError(f"Client configuration error: {e}") from e

        return response.parsed_output


class FakeClient(LLMClient):
    """Returns a canned suggestion instead of calling a real provider — for
    developing/testing the pipeline without spending API credits on every
    run. Never used unless explicitly selected (see get_default_client)."""

    def suggest_fix(self, system_prompt: str, user_prompt: str) -> FixSuggestion:
        return FixSuggestion(
            explanation=(
                "[FAKE CLIENT — no real LLM call made] This is a canned response "
                "for local development. Set LLM_PROVIDER=claude (and a valid "
                "ANTHROPIC_API_KEY) to get a real suggestion."
            ),
            diff="--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-# placeholder\n+# placeholder (fake fix)",
            confidence=0.0,
        )


def get_default_client() -> LLMClient:
    """Selects the provider via LLM_PROVIDER ("claude" | "fake"), defaulting
    to "fake" — real API calls are opt-in, not accidental, so running the
    pipeline locally never silently spends credits."""
    provider = os.environ.get("LLM_PROVIDER", "fake").lower()
    if provider == "claude":
        return ClaudeClient()
    if provider == "fake":
        return FakeClient()
    raise LLMSuggestionError(f"Unknown LLM_PROVIDER: {provider!r} (expected 'claude' or 'fake')")
