"""Chat API endpoints."""

import asyncio
import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import QueryLog
from app.db.session import get_db
from app.services.rag_service import process_chat

router = APIRouter()

REQUEST_TIMEOUT = 45


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
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
    start_ms = time.monotonic()
    intent = None

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
        intent = result.get("intent")
        return ChatResponse(**result)

    except asyncio.TimeoutError:
        intent = "timeout"
        return ChatResponse(
            answer="Xin loi, yeu cau mat qua nhieu thoi gian. Vui long thu lai.",
            intent=None,
            sources=[],
            error={"code": "TIMEOUT", "message": "Request timeout"},
        )
    except Exception as e:
        intent = "error"
        return ChatResponse(
            answer=None,
            intent=None,
            sources=[],
            error={"code": "INTERNAL_ERROR", "message": str(e)},
        )
    finally:
        elapsed_ms = int((time.monotonic() - start_ms) * 1000)
        try:
            db.add(QueryLog(
                user_id=user["user_id"],
                user_name=user["name"],
                role=user["role"],
                department=user.get("department"),
                session_id=request.session_id,
                question=request.message,
                intent=intent,
                response_time_ms=elapsed_ms,
            ))
            db.commit()
        except Exception:
            pass
