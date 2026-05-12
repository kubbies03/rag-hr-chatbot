"""Retrieve relevant documents from ChromaDB."""

import logging
import threading

import chromadb

from app.core.config import settings
from app.services.embedding_service import get_embeddings

logger = logging.getLogger(__name__)

_chroma_client = None
_collection = None
_collection_lock = threading.Lock()  # Fix 6: thread-safe singleton init


def get_collection():
    """Return the ChromaDB collection."""
    global _chroma_client, _collection
    if _collection is None:
        with _collection_lock:
            if _collection is None:  # double-checked locking
                _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
                _collection = _chroma_client.get_or_create_collection(
                    name=settings.CHROMA_COLLECTION_NAME,
                )
    return _collection


def _query_chroma(
    query_vector: list[float],
    user_role: str,
    top_k: int,
) -> list[dict]:
    """Run one ChromaDB query and return document records."""
    collection = get_collection()

    where_filter = None
    if user_role != "admin":
        where_filter = {
            "$or": [
                {"access_level": "all"},
                {"access_level": user_role},
            ]
        }

    # Fix 1: removed silent fallback that dropped access control on error.
    # If the filter query fails, let the exception propagate rather than
    # leaking restricted documents to lower-privileged users.
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        where=where_filter,
    )

    documents = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else None
            documents.append({
                "content": doc,
                "metadata": metadata,
                "distance": distance,
            })
    return documents


def retrieve(
    query: str,
    user_role: str = "employee",
    top_k: int = None,
) -> list[dict]:
    """Retrieve documents using vector similarity only."""
    if top_k is None:
        top_k = settings.RETRIEVER_TOP_K

    if get_collection().count() == 0:
        return []

    query_vector = get_embeddings().embed_query(query)
    documents = _query_chroma(query_vector, user_role, top_k)

    logger.debug(
        "Vector retrieval: top-%d distances = %s",
        top_k,
        [round(d["distance"], 3) for d in documents if d["distance"] is not None],
    )
    return documents


def retrieve_and_rerank(
    query: str,
    user_role: str = "employee",
) -> list[dict]:
    """Retrieve documents, then rerank the candidates."""
    from app.services.reranker_service import rerank

    if get_collection().count() == 0:
        return []

    query_vector = get_embeddings().embed_query(query)
    candidates = _query_chroma(query_vector, user_role, settings.RETRIEVAL_CANDIDATE_K)

    if not candidates:
        return []

    logger.debug(
        "Candidate pool (%d chunks) distances: %s",
        len(candidates),
        [round(d["distance"], 3) for d in candidates if d["distance"] is not None],
    )

    return rerank(query, candidates, top_k=settings.RETRIEVER_TOP_K)


def format_context(documents: list[dict]) -> str:
    """Format documents into an LLM context string."""
    if not documents:
        return "No relevant documents found."

    context_parts = []
    for i, doc in enumerate(documents, 1):
        meta = doc["metadata"]
        source = meta.get("title", "Unknown source")
        page = meta.get("page", "")
        page_str = f", page {page}" if page else ""

        context_parts.append(f"[Source {i}: {source}{page_str}]\n{doc['content']}")

    return "\n\n".join(context_parts)


def get_sources(documents: list[dict]) -> list[dict]:
    """Extract source metadata for the API response."""
    sources = []
    for doc in documents:
        meta = doc["metadata"]
        sources.append({
            "title": meta.get("title", "Unknown"),
            "page": meta.get("page", None),
            "file": meta.get("source_file", None),
            "category": meta.get("category", None),
        })
    return sources
