"""
embedding_service.py — Gemini Embedding API wrapper.

Converts text into numerical vectors for semantic similarity search.
"""

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings

_embeddings = None


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Get singleton Gemini Embedding model instance."""
    global _embeddings
    if _embeddings is None:
        _embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.GEMINI_EMBEDDING_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
        )
    return _embeddings


def embed_query(text: str) -> list[float]:
    """Embed a single query into a vector for ChromaDB similarity search."""
    embeddings = get_embeddings()
    return embeddings.embed_query(text)


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed multiple text chunks into vectors for document ingestion."""
    embeddings = get_embeddings()
    return embeddings.embed_documents(texts)
