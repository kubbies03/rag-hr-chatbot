"""
Chat API surface.

`POST /api/chat` is the single entrypoint used by clients. The endpoint itself
is intentionally small:
- validate payload
- authenticate caller
- open a database session
- run the synchronous orchestration pipeline in a worker thread
- map timeout and unexpected failures into a stable API shape

The heavy business logic lives in `app.services.rag_service.process_chat`.
"""

import asyncio
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.services.rag_service import process_chat

router = APIRouter()

REQUEST_TIMEOUT = 45  # seconds


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Ai dang nghi phep tuan nay?",
                "session_id": "sess_001",
            }
        }


class SourceInfo(BaseModel):
    title: str | None = None
    page: int | None = None
    file: str | None = None
    category: str | None = None


class ChatResponse(BaseModel):
    answer: str | None = None
    intent: str | None = None
    sources: list[SourceInfo] = []
    error: dict | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Hien tai co 2 nhan vien dang nghi phep...",
                "intent": "employee_status",
                "sources": [],
                "error": None,
            }
        }


@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # `process_chat` mixes database access, vector retrieval, and LLM calls.
    # Running it in `asyncio.to_thread(...)` prevents blocking the event loop
    # while keeping the existing synchronous service layer unchanged.
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                process_chat,
                question=request.message,
                user_role=user["role"],
                session_id=request.session_id,
                db=db,
            ),
            timeout=REQUEST_TIMEOUT,
        )
        return ChatResponse(**result)

    except asyncio.TimeoutError:
        return ChatResponse(
            answer="Xin loi, yeu cau mat qua nhieu thoi gian. Vui long thu lai.",
            intent=None,
            sources=[],
            error={"code": "TIMEOUT", "message": "Request timeout"},
        )
    except Exception as e:
        return ChatResponse(
            answer=None,
            intent=None,
            sources=[],
            error={"code": "INTERNAL_ERROR", "message": str(e)},
        )
