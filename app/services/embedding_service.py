"""Local embedding wrapper using SentenceTransformer directly."""

import threading
import torch
from sentence_transformers import SentenceTransformer

_embed_cache = threading.local()

from app.core.config import settings

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Return the singleton SentenceTransformer model."""
    global _model
    if _model is None:
        _model = SentenceTransformer(
            settings.LOCAL_EMBEDDING_MODEL,
            device="cuda",
            model_kwargs={"torch_dtype": torch.float16},
        )
    return _model


def get_embeddings():
    """Return the model instance used by ingest and retriever services."""
    return _EmbeddingsAdapter(_get_model())


class _EmbeddingsAdapter:
    """Expose the embed_query and embed_documents interface expected by callers."""

    def __init__(self, model: SentenceTransformer):
        self._model = model

    def embed_query(self, text: str) -> list[float]:
        cached = getattr(_embed_cache, 'last', None)
        if cached is not None and cached[0] == text:
            return cached[1]
        vec = self._model.encode(
            [text],
            normalize_embeddings=True,
            batch_size=1,
            convert_to_numpy=True,
        )
        result = vec[0].tolist()
        _embed_cache.last = (text, result)
        return result

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vecs = self._model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 50,
        )
        return vecs.tolist()


def embed_query(text: str) -> list[float]:
    return get_embeddings().embed_query(text)


def embed_documents(texts: list[str]) -> list[list[float]]:
    return get_embeddings().embed_documents(texts)
