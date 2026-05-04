"""Application configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = str(Path(__file__).resolve().parent.parent.parent)


class Settings:
    """Central app settings."""

    BASE_DIR: str = BASE_DIR
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_CHAT_MODEL: str = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")
    GEMINI_TEMPERATURE: float = 0.3

    LOCAL_EMBEDDING_MODEL: str = os.getenv("LOCAL_EMBEDDING_MODEL", "BAAI/bge-m3")
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_CREDENTIALS_PATH: str = os.getenv(
        "FIREBASE_CREDENTIALS_PATH",
        os.path.join(BASE_DIR, "firebase-service-account.json"),
    )

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "data", "sqlite", "hr.db"),
    )

    CHROMA_PERSIST_DIR: str = os.getenv(
        "CHROMA_PERSIST_DIR",
        os.path.join(BASE_DIR, "data", "chroma"),
    )
    CHROMA_COLLECTION_NAME: str = "hr_documents"

    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 75
    RETRIEVER_TOP_K: int = 2
    RETRIEVAL_CANDIDATE_K: int = 5
    MAX_CONVERSATION_HISTORY: int = 1

    RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    RERANKER_MIN_SCORE: float = float(os.getenv("RERANKER_MIN_SCORE", "0.3"))
    USE_RERANKER: bool = os.getenv("USE_RERANKER", "true").lower() == "true"

    DOCS_DIR: str = os.getenv(
        "DOCS_DIR",
        os.path.join(BASE_DIR, "data", "docs"),
    )

    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "true").lower() == "true"


settings = Settings()
