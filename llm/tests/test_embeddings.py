import pytest

from llm_core.embeddings import EmbeddingError, FakeEmbedder, get_default_embedder


def test_fake_embedder_returns_correct_dimension(monkeypatch):
    monkeypatch.setenv("EMBEDDING_DIM", "1536")
    # EMBEDDING_DIM is read at import time in embeddings.py, so re-check
    # against FakeEmbedder's own module-level constant instead of assuming
    # the monkeypatched env var retroactively changes it.
    from llm_core import embeddings as embeddings_module

    vec = FakeEmbedder().embed("some error message")
    assert len(vec) == embeddings_module.EMBEDDING_DIM


def test_fake_embedder_is_deterministic():
    embedder = FakeEmbedder()
    assert embedder.embed("same text") == embedder.embed("same text")


def test_fake_embedder_differs_for_different_text():
    embedder = FakeEmbedder()
    assert embedder.embed("text one") != embedder.embed("a completely different text")


def test_get_default_embedder_defaults_to_fake(monkeypatch):
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
    assert isinstance(get_default_embedder(), FakeEmbedder)


def test_get_default_embedder_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "not-a-real-provider")
    with pytest.raises(EmbeddingError):
        get_default_embedder()
