import hashlib
import os
from abc import ABC, abstractmethod
from typing import List

import openai

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "1536"))


class EmbeddingError(Exception):
    """Raised for any embedding-provider failure, mirroring
    LLMSuggestionError in client.py — callers handle one exception type
    regardless of which provider is behind Embedder."""


class Embedder(ABC):
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        raise NotImplementedError


class OpenAIEmbedder(Embedder):
    def __init__(self, model: str = EMBEDDING_MODEL):
        self._client = openai.OpenAI()  # resolves OPENAI_API_KEY from env
        self._model = model

    def embed(self, text: str) -> List[float]:
        try:
            response = self._client.embeddings.create(model=self._model, input=text)
        except openai.AuthenticationError as e:
            raise EmbeddingError(f"Authentication failed: {e}") from e
        except openai.RateLimitError as e:
            raise EmbeddingError(f"Rate limited: {e}") from e
        except openai.APIConnectionError as e:
            raise EmbeddingError(f"Connection error: {e}") from e
        except openai.APIStatusError as e:
            raise EmbeddingError(f"API error ({e.status_code}): {e}") from e
        return response.data[0].embedding


class FakeEmbedder(Embedder):
    """Deterministic hash-based pseudo-embedding — no API cost, for
    exercising the retrieval pipeline's mechanics without a real OpenAI key.
    Not meaningful for actual similarity quality (see DECISIONS.md:
    "Embedding model for RAG")."""

    def embed(self, text: str) -> List[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = (digest * (EMBEDDING_DIM // len(digest) + 1))[:EMBEDDING_DIM]
        return [(b / 127.5) - 1.0 for b in raw]


def get_default_embedder() -> Embedder:
    """Selects the provider via EMBEDDING_PROVIDER ("openai" | "fake"),
    defaulting to "fake" for the same reason as get_default_client() in
    client.py — no free tier for OpenAI's API, so real calls are opt-in."""
    provider = os.environ.get("EMBEDDING_PROVIDER", "fake").lower()
    if provider == "openai":
        return OpenAIEmbedder()
    if provider == "fake":
        return FakeEmbedder()
    raise EmbeddingError(f"Unknown EMBEDDING_PROVIDER: {provider!r} (expected 'openai' or 'fake')")
