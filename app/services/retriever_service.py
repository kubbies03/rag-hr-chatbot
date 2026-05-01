"""
retriever_service.py — Retrieve relevant documents from ChromaDB.

When a user asks about company documents, this service:
1. Takes the question
2. Finds the most similar chunks in ChromaDB
3. Filters by role (access control)
4. Returns chunks with metadata
"""

import chromadb
from app.core.config import settings
from app.services.embedding_service import get_embeddings

_chroma_client = None
_collection = None


def get_collection():
    """Get ChromaDB collection (creates if not exists)."""
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        _collection = _chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
        )
    return _collection


def retrieve(
    query: str,
    user_role: str = "employee",
    top_k: int = None,
) -> list[dict]:
    """
    Find documents relevant to a query.

    Args:
        query: User question
        user_role: Role for document filtering (employee, hr, manager, admin)
        top_k: Number of results to return

    Returns:
        List of dicts with chunk content + metadata
    """
    if top_k is None:
        top_k = settings.RETRIEVER_TOP_K

    collection = get_collection()

    if collection.count() == 0:
        return []

    embeddings = get_embeddings()
    query_vector = embeddings.embed_query(query)

    # Admin sees all; other roles only see permitted documents
    where_filter = None
    if user_role != "admin":
        where_filter = {
            "$or": [
                {"access_level": "all"},
                {"access_level": user_role},
            ]
        }

    try:
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where_filter,
        )
    except Exception:
        # Fallback without filter if metadata is missing
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
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


def format_context(documents: list[dict]) -> str:
    """
    Format document list into a context string for LLM prompts.

    Example output:
        [Source 1: Company Handbook, page 5]
        Chunk content...

        [Source 2: HR Policy, page 12]
        Chunk content...
    """
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
    """Extract source list to return to the client."""
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
