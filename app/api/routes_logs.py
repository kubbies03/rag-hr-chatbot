"""Query log endpoints HR/admin only."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import QueryLog
from app.db.session import get_db

router = APIRouter()

_ALLOWED_ROLES = {"hr", "manager", "admin"}


def _require_hr(user: dict = Depends(get_current_user)):
    if user["role"] not in _ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="HR/admin access required.")
    return user


@router.get("/api/logs/queries")
def get_query_logs(
    user_id: str = Query(default=None, description="Filter by user_id"),
    intent: str = Query(default=None, description="Filter by intent"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    db: Session = Depends(get_db),
    _: dict = Depends(_require_hr),
):
    """
    List chat questions with caller identity.
    Restricted to HR, manager, and admin roles.
    """
    q = db.query(QueryLog).order_by(QueryLog.created_at.desc())

    if user_id:
        q = q.filter(QueryLog.user_id == user_id)
    if intent:
        q = q.filter(QueryLog.intent == intent)

    total = q.count()
    rows = q.offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "logs": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "user_name": r.user_name,
                "role": r.role,
                "department": r.department,
                "session_id": r.session_id,
                "question": r.question,
                "intent": r.intent,
                "response_time_ms": r.response_time_ms,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.get("/api/logs/stats")
def get_log_stats(
    db: Session = Depends(get_db),
    _: dict = Depends(_require_hr),
):
    """Aggregate stats: total questions, breakdown by user and intent."""
    from sqlalchemy import func

    total = db.query(func.count(QueryLog.id)).scalar()

    by_user = (
        db.query(QueryLog.user_name, QueryLog.role, func.count(QueryLog.id).label("count"))
        .group_by(QueryLog.user_id)
        .order_by(func.count(QueryLog.id).desc())
        .all()
    )

    by_intent = (
        db.query(QueryLog.intent, func.count(QueryLog.id).label("count"))
        .group_by(QueryLog.intent)
        .order_by(func.count(QueryLog.id).desc())
        .all()
    )

    avg_ms = db.query(func.avg(QueryLog.response_time_ms)).scalar()

    return {
        "total_questions": total,
        "avg_response_time_ms": round(avg_ms) if avg_ms else None,
        "by_user": [{"name": r[0], "role": r[1], "count": r[2]} for r in by_user],
        "by_intent": [{"intent": r[0], "count": r[1]} for r in by_intent],
    }
