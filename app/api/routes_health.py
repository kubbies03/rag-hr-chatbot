"""
routes_health.py — Health check endpoint.

GET /health — verify server is running. Used for monitoring and quick demo checks.
"""

from fastapi import APIRouter
from app.core.config import settings
from app.services.ingest_service import get_collection_stats

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Check system health status.

    Returns:
    - status: ok / degraded
    - services: status of each component
    """
    services = {}

    services["gemini"] = "configured" if settings.GOOGLE_API_KEY else "missing_api_key"

    try:
        stats = get_collection_stats()
        services["chromadb"] = f"ok ({stats['total_chunks']} chunks)"
    except Exception as e:
        services["chromadb"] = f"error: {str(e)}"

    try:
        from app.db.session import engine
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        services["sqlite"] = "ok"
    except Exception as e:
        services["sqlite"] = f"error: {str(e)}"

    all_ok = all(
        v.startswith("ok") or v == "configured"
        for v in services.values()
    )

    return {
        "status": "ok" if all_ok else "degraded",
        "environment": settings.APP_ENV,
        "services": services,
    }
