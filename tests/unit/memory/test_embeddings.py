"""Unit tests for EmbeddingGenerator without model downloads."""

from __future__ import annotations

from typing import ClassVar

import pytest

from app.memory.embeddings import EmbeddingGenerator


class _ArrayLike:
    def __init__(self, values):
        self._values = values

    def tolist(self):
        return self._values


class _StubTransformer:
    init_calls: ClassVar[list[str]] = []

    def __init__(self, model_name: str):
        self.model_name = model_name
        _StubTransformer.init_calls.append(model_name)

    def encode(self, texts, convert_to_numpy=True, show_progress_bar=False):
        _ = convert_to_numpy
        _ = show_progress_bar
        if isinstance(texts, list):
            return _ArrayLike([[1.0, 2.0] for _ in texts])
        return _ArrayLike([0.1, 0.2, 0.3])

    def get_sentence_embedding_dimension(self):
        return 3


class _StubTransformerNoDim(_StubTransformer):
    def get_sentence_embedding_dimension(self):
        return None


@pytest.mark.real_embeddings
def test_embed_text_uses_stubbed_model(monkeypatch) -> None:
    _StubTransformer.init_calls.clear()
    monkeypatch.setattr(
        "app.memory.embeddings.SentenceTransformer",
        _StubTransformer,
        raising=True,
    )

    generator = EmbeddingGenerator(model_name="stub-model")
    result = generator.embed_text("hello")

    assert result == [0.1, 0.2, 0.3]
    assert _StubTransformer.init_calls == ["stub-model"]


@pytest.mark.real_embeddings
def test_embed_batch_returns_list(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.memory.embeddings.SentenceTransformer",
        _StubTransformer,
        raising=True,
    )

    generator = EmbeddingGenerator()
    result = generator.embed_batch(["alpha", "beta"])

    assert result == [[1.0, 2.0], [1.0, 2.0]]


@pytest.mark.real_embeddings
def test_embedding_dim_falls_back_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.memory.embeddings.SentenceTransformer",
        _StubTransformerNoDim,
        raising=True,
    )

    generator = EmbeddingGenerator()
    assert generator.embedding_dim == 384
