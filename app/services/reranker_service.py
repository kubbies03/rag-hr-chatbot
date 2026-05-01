"""Cross-encoder reranking for retrieved chunks."""

import logging
import math

from sentence_transformers import CrossEncoder

from app.core.config import settings

logger = logging.getLogger(__name__)

_reranker = None


def get_reranker() -> CrossEncoder:
    """Return the singleton reranker."""
    global _reranker
    if _reranker is None:
        logger.info("Loading reranker model: %s", settings.RERANKER_MODEL)
        _reranker = CrossEncoder(
            settings.RERANKER_MODEL,
            device="cuda",
            automodel_args={"torch_dtype": "auto"},
        )
        logger.info("Reranker loaded.")
    return _reranker


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def rerank(query: str, documents: list[dict], top_k: int = None) -> list[dict]:
    """Rerank candidate documents by relevance."""
    if not documents:
        return []

    if top_k is None:
        top_k = settings.RETRIEVER_TOP_K

    reranker = get_reranker()
    pairs = [(query, doc["content"]) for doc in documents]
    raw_scores = reranker.predict(pairs)

    for i, doc in enumerate(documents):
        doc["reranker_score"] = _sigmoid(float(raw_scores[i]))

    ranked = sorted(documents, key=lambda d: d["reranker_score"], reverse=True)

    logger.debug(
        "Reranker scores (top %d of %d candidates): %s",
        min(top_k, len(ranked)),
        len(ranked),
        [
            (round(d["reranker_score"], 3), d["metadata"].get("section_title", "")[:40])
            for d in ranked[:top_k]
        ],
    )

    filtered = [d for d in ranked if d["reranker_score"] >= settings.RERANKER_MIN_SCORE]

    if not filtered:
        logger.info(
            "Reranker: all %d candidates below threshold %.2f, falling back to vector top-%d.",
            len(ranked),
            settings.RERANKER_MIN_SCORE,
            top_k,
        )
        return documents[:top_k]

    return filtered[:top_k]
