"""
config.py — Application configuration.

All file paths use absolute paths resolved from the project root (BASE_DIR).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Resolve project root: config.py -> core -> app -> hr-rag-chatbot
BASE_DIR = str(Path(__file__).resolve().parent.parent.parent)


class Settings:
    """Central application settings."""

    # --- Base path ---
    BASE_DIR: str = BASE_DIR

    # --- Gemini API ---
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_CHAT_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    GEMINI_TEMPERATURE: float = 0.3

    # --- Firebase ---
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

    # --- RAG Settings ---
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    RETRIEVER_TOP_K: int = 3
    MAX_CONVERSATION_HISTORY: int = 3

    # --- Document directory (absolute path) ---
    DOCS_DIR: str = os.getenv(
        "DOCS_DIR",
        os.path.join(BASE_DIR, "data", "docs"),
    )

    # --- App ---
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "true").lower() == "true"


settings = Settings()
