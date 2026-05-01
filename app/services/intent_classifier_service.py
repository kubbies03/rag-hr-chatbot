"""Embedding-based k-NN intent classifier using BGE-M3."""

import json
import os
import threading
from collections import Counter

import numpy as np

_EXAMPLES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "intent_examples.json")
_K = 5
_THRESHOLD = 0.55

_example_vectors: np.ndarray | None = None
_example_labels: list[str] | None = None
_initialized = False
_init_lock = threading.Lock()


def _load_examples() -> tuple[list[str], list[str]]:
    with open(_EXAMPLES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    texts: list[str] = []
    labels: list[str] = []
    for intent, examples in data.items():
        for ex in examples:
            texts.append(ex)
            labels.append(intent)
    return texts, labels


def _initialize() -> None:
    global _example_vectors, _example_labels, _initialized
    with _init_lock:
        if _initialized:
            return
        from app.services.embedding_service import get_embeddings

        texts, labels = _load_examples()
        vecs = get_embeddings().embed_documents(texts)
        _example_vectors = np.array(vecs, dtype=np.float32)
        _example_labels = labels
        _initialized = True


def warmup() -> None:
    """Pre-embed all examples at startup so first inference is fast."""
    _initialize()


def classify_by_embedding(
    question: str,
    k: int = _K,
    threshold: float = _THRESHOLD,
) -> str | None:
    """Return the predicted intent, or None if confidence is below threshold.

    Vectors are L2-normalized by BGE-M3, so the dot product equals cosine similarity.
    """
    if not _initialized:
        _initialize()

    from app.services.embedding_service import get_embeddings

    q_vec = np.array(get_embeddings().embed_query(question), dtype=np.float32)
    sims = _example_vectors @ q_vec  # shape: (N,)
    top_k_idx = np.argsort(sims)[-k:][::-1]

    if sims[top_k_idx[0]] < threshold:
        return None

    votes = Counter(_example_labels[i] for i in top_k_idx)
    return votes.most_common(1)[0][0]
