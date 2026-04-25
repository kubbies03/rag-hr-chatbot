"""
Application entrypoint.

Technical overview:
- Builds the FastAPI app and registers all route modules
- Adds permissive CORS for local/mobile integration during development
- Adds a lightweight middleware for request timing and ngrok compatibility
- Ensures the local data folders and SQLite schema exist on startup

Run locally with:
    uvicorn app.main:app --reload --port 8000
"""

import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os

from app.api.routes_chat import router as chat_router
from app.api.routes_docs import router as docs_router
from app.api.routes_employee import router as employee_router
from app.api.routes_health import router as health_router
from app.api.routes_notify import router as notify_router
from app.db.session import init_db
from app.core.config import settings

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


# This middleware intentionally stays thin because it runs on every request.
# It only adds timing/logging and the ngrok header used during demo sessions.
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
app.include_router(notify_router, tags=["Notifications"])

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/admin", include_in_schema=False)
async def admin_ui():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# Startup keeps initialization local and idempotent so the app can boot
# cleanly in both bare-metal dev mode and containerized runs.
@app.on_event("startup")
async def startup_event():
    for folder in ["data/sqlite", "data/chroma", "data/docs"]:
        os.makedirs(os.path.join(settings.BASE_DIR, folder), exist_ok=True)

    logger.info("Initializing database...")
    init_db()
    logger.info("Database ready")
    logger.info("Swagger UI:  http://localhost:8000/docs")
    logger.info("Admin UI:    http://localhost:8000/admin")
    logger.info("Health:      http://localhost:8000/health")


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "HR RAG Chatbot API",
        "admin_ui": "/admin",
        "docs": "/docs",
        "health": "/health",
    }
