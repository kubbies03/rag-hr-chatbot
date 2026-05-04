"""FastAPI application entrypoint."""

import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_chat import router as chat_router
from app.api.routes_docs import router as docs_router
from app.api.routes_employee import router as employee_router
from app.api.routes_health import router as health_router
from app.api.routes_logs import router as logs_router
from app.api.routes_notify import router as notify_router
from app.core.config import settings
from app.db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="HR RAG Chatbot API",
    description="Intelligent HR assistant API with RAG-powered document Q&A.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    response.headers["ngrok-skip-browser-warning"] = "true"

    path = request.url.path
    if path.startswith("/api/") or path == "/health":
        logger.info(f"{request.method} {path} -> {response.status_code} ({duration:.2f}s)")

    return response


app.include_router(chat_router, tags=["Chat"])
app.include_router(docs_router, tags=["Documents"])
app.include_router(employee_router, tags=["Employees"])
app.include_router(health_router, tags=["Health"])
app.include_router(logs_router, tags=["Logs"])
app.include_router(notify_router, tags=["Notifications"])


@app.on_event("startup")
async def startup_event():
    import asyncio

    for folder in ["data/sqlite", "data/chroma", "data/docs"]:
        os.makedirs(os.path.join(settings.BASE_DIR, folder), exist_ok=True)

    logger.info("Initializing database...")
    init_db()
    _cleanup_old_conversations()
    logger.info("Database ready")

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _warmup_models)

    logger.info("Swagger UI:  http://localhost:8000/docs")
    logger.info("Health:      http://localhost:8000/health")


def _cleanup_old_conversations():
    """Delete conversation messages older than 30 days."""
    from datetime import datetime, timedelta
    from app.db.models import ConversationMessage
    from app.db.session import SessionLocal
    cutoff = datetime.utcnow() - timedelta(days=30)
    db = SessionLocal()
    try:
        deleted = db.query(ConversationMessage).filter(
            ConversationMessage.created_at < cutoff
        ).delete()
        db.commit()
        if deleted:
            logger.info("Cleaned up %d old conversation messages.", deleted)
    except Exception as e:
        logger.warning("Conversation cleanup failed: %s", e)
    finally:
        db.close()


def _warmup_models():
    """Download and load AI models into GPU memory at startup."""
    try:
        import torch
        if torch.cuda.is_available():
            logger.info("Device: CUDA — %s", torch.cuda.get_device_name(0))
        else:
            logger.warning("Device: CPU (CUDA not available — models will be slow)")
    except Exception:
        pass

    try:
        logger.info("Warming up embedding model...")
        from app.services.embedding_service import get_embeddings
        emb = get_embeddings()
        emb.embed_query("warmup")
        logger.info("Embedding model ready.")
    except Exception as e:
        logger.warning("Embedding warmup failed: %s", e)

    if settings.USE_RERANKER:
        try:
            logger.info("Warming up reranker model...")
            from app.services.reranker_service import get_reranker
            reranker = get_reranker()
            reranker.predict([("warmup query", "warmup document")])
            logger.info("Reranker model ready.")
        except Exception as e:
            logger.warning("Reranker warmup failed: %s", e)

    try:
        logger.info("Warming up intent classifier...")
        from app.services.intent_classifier_service import warmup as intent_warmup
        intent_warmup()
        logger.info("Intent classifier ready.")
    except Exception as e:
        logger.warning("Intent classifier warmup failed: %s", e)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "HR RAG Chatbot API",
        "docs": "/docs",
        "health": "/health",
    }
