"""
routes_docs.py — Document management endpoints.

POST /api/documents/ingest — upload and ingest a document into RAG
POST /api/documents/ingest-all — ingest all files in the docs directory
GET  /api/documents/stats — view vector DB statistics
"""

import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from app.core.config import settings
from app.core.security import get_current_user
from app.services.ingest_service import ingest_file, ingest_directory, get_collection_stats

router = APIRouter()


@router.post("/api/documents/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    title: str = Form(default=None),
    category: str = Form(default="general"),
    access_level: str = Form(default="all"),
    department: str = Form(default="general"),
    user: dict = Depends(get_current_user),
):
    """Upload and ingest a single document into the RAG system."""
    if user["role"] not in ["admin", "hr"]:
        raise HTTPException(status_code=403, detail="Only admin/hr can upload documents")

    allowed_exts = {".pdf", ".docx", ".txt"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format {ext}. Allowed: {', '.join(allowed_exts)}",
        )

    os.makedirs(settings.DOCS_DIR, exist_ok=True)
    file_path = os.path.join(settings.DOCS_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        result = ingest_file(
            file_path=file_path,
            title=title,
            category=category,
            access_level=access_level,
            department=department,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/documents/ingest-all")
async def ingest_all_documents(
    user: dict = Depends(get_current_user),
):
    """Ingest all documents in the data/docs directory."""
    if user["role"] not in ["admin", "hr"]:
        raise HTTPException(status_code=403, detail="Only admin/hr can perform this action")

    results = ingest_directory()
    return {"results": results}


@router.get("/api/documents/stats")
async def document_stats(
    user: dict = Depends(get_current_user),
):
    """View vector DB statistics."""
    stats = get_collection_stats()
    return stats
