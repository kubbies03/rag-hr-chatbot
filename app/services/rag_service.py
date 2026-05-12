"""Main chat orchestration layer."""

import logging
import os
import threading
import time
import unicodedata
from functools import lru_cache

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.gemini_service import chat
from app.services.intent_service import classify_intent
from app.services.retriever_service import (
    format_context,
    get_sources,
    retrieve,
    retrieve_and_rerank,
)

logger = logging.getLogger(__name__)


def _get_history(session_id: str, db: Session) -> list[dict]:
    """Load the last MAX_CONVERSATION_HISTORY exchanges from the database."""
    from app.db.models import ConversationMessage
    rows = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(settings.MAX_CONVERSATION_HISTORY * 2)  # Fix 4: use settings value
        .all()
    )
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]


def _save_history(session_id: str, question: str, answer: str, db: Session):
    """Persist a question/answer pair to the database."""
    from app.db.models import ConversationMessage
    db.add(ConversationMessage(session_id=session_id, role="user", content=question))
    db.add(ConversationMessage(session_id=session_id, role="assistant", content=answer))
    db.commit()


def _save_history_async(session_id: str, question: str, answer: str):
    """Fire-and-forget history save — uses its own session so the request isn't blocked."""
    def _run():
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            _save_history(session_id, question, answer, db)
        except Exception:
            logger.warning("Failed to save conversation history for session %s", session_id)
        finally:
            db.close()

    threading.Thread(target=_run, daemon=True).start()


@lru_cache(maxsize=1)
def _load_system_prompt() -> str:
    prompt_path = os.path.join(
        os.path.dirname(__file__), "..", "prompts", "system_prompt.txt"
    )
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


@lru_cache(maxsize=1)
def _load_answer_prompt() -> str:
    prompt_path = os.path.join(
        os.path.dirname(__file__), "..", "prompts", "answer_prompt.txt"
    )
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


_response_cache: dict[str, dict] = {}
_cache_timestamps: dict[str, float] = {}
_cache_lock = threading.Lock()  # Fix 2: protect shared dicts from concurrent writes
CACHE_MAX_SIZE = 50
CACHE_TTL_SECONDS = 300


def _get_cached(cache_key: str) -> dict | None:
    with _cache_lock:  # Fix 2
        if cache_key not in _response_cache:
            return None
        if time.time() - _cache_timestamps.get(cache_key, 0) > CACHE_TTL_SECONDS:
            _response_cache.pop(cache_key, None)
            _cache_timestamps.pop(cache_key, None)
            return None
        return _response_cache[cache_key]


def _set_cache(cache_key: str, response: dict):
    with _cache_lock:  # Fix 2
        if len(_response_cache) >= CACHE_MAX_SIZE:
            oldest_key = next(iter(_response_cache))
            _response_cache.pop(oldest_key, None)
            _cache_timestamps.pop(oldest_key, None)
        _response_cache[cache_key] = response
        _cache_timestamps[cache_key] = time.time()


def _strip_accents(text: str) -> str:
    """Normalize Vietnamese text to ASCII for keyword matching."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _use_firestore() -> bool:
    """Check whether Firestore employee queries are available."""
    try:
        from app.core.security import _ensure_firebase

        return _ensure_firebase()
    except Exception:
        return False


def _handle_employee_query_firestore(question: str) -> str:
    """Query employee data from Firestore."""
    from app.services import firestore_employee_service as fs

    q = _strip_accents(question)  # Fix 5: normalize diacritics before matching

    if any(kw in q for kw in ["nghi phep", "dang nghi", "ai nghi"]):
        data = fs.get_approved_leaves_today()
        if not data:
            users = fs.get_employees_by_status("on_leave")
            return fs.format_employee_data(users) if users else "Hom nay khong co ai nghi phep."
        return fs.format_employee_data(data)

    if any(kw in q for kw in ["di muon", "di tre", "muon"]):
        data = fs.get_late_employees()
        return fs.format_employee_data(data) if data else "Hom nay khong co ai di muon."

    if any(kw in q for kw in ["cham cong", "check in", "co mat", "vang"]):
        data = fs.get_today_attendance()
        return fs.format_employee_data(data) if data else "Chua co ai cham cong hom nay."

    if any(kw in q for kw in ["don", "cho duyet", "pending"]):
        data = fs.get_pending_leave_requests()
        return fs.format_employee_data(data) if data else "Khong co don nghi phep cho duyet."

    if any(kw in q for kw in ["thong ke", "tong quan", "bao nhieu"]):
        data = fs.get_all_stats()
        return fs.format_employee_data(data)

    if any(kw in q for kw in ["task", "nhiem vu", "cong viec"]):
        data = fs.get_all_tasks()
        return fs.format_employee_data(data) if data else "Khong co task nao."

    import re

    words = question.split()
    name_parts = []
    for w in words:
        clean = re.sub(r"[?.!,]", "", w)
        if clean and clean[0].isupper() and clean.isalpha():
            name_parts.append(clean)

    if name_parts:
        name_query = " ".join(name_parts)
        data = fs.get_employee_by_name(name_query)
        if data:
            return fs.format_employee_data(data)

    data = fs.get_all_stats()
    return fs.format_employee_data(data)


def _handle_employee_query_sqlite(question: str, db: Session) -> str:
    """Query employee data from SQLite."""
    from app.services import employee_service

    q = _strip_accents(question)  # Fix 5: normalize diacritics before matching

    if any(kw in q for kw in ["nghi phep", "dang nghi", "ai nghi"]):
        data = employee_service.get_employees_on_leave(db)
        return employee_service.format_employee_data(data)

    if any(kw in q for kw in ["di muon", "di tre", "muon"]):
        data = employee_service.get_late_employees(db)
        return employee_service.format_employee_data(data)

    if any(kw in q for kw in ["cham cong", "check in", "co mat", "vang"]):
        data = employee_service.get_today_attendance(db)
        return employee_service.format_employee_data(data)

    if any(kw in q for kw in ["don", "cho duyet", "pending"]):
        data = employee_service.get_pending_leave_requests(db)
        return employee_service.format_employee_data(data)

    if any(kw in q for kw in ["thong ke", "tong quan", "bao nhieu"]):
        data = employee_service.get_all_stats(db)
        return employee_service.format_employee_data(data)

    import re

    words = question.split()
    name_parts = []
    for w in words:
        clean = re.sub(r"[?.!,]", "", w)
        if clean and clean[0].isupper() and clean.isalpha():
            name_parts.append(clean)

    if name_parts:
        name_query = " ".join(name_parts)
        data = employee_service.get_employee_by_name(db, name_query)
        if data:
            return employee_service.format_employee_data(data)

    data = employee_service.get_all_stats(db)
    return employee_service.format_employee_data(data)


def process_chat(
    question: str,
    user_role: str,
    session_id: str,
    db: Session,
) -> dict:
    """Run the full chat pipeline and return a JSON-ready response."""
    t0 = time.time()

    intent = classify_intent(question)
    logger.info("[TIMING] intent_classify=%.2fs intent=%s", time.time() - t0, intent)
    t1 = time.time()

    history = _get_history(session_id, db)

    context = ""
    employee_data = ""
    sources = []
    cache_key = ""

    if intent == "employee_status":
        if _use_firestore():
            logger.info("Querying employee data from Firestore")
            employee_data = _handle_employee_query_firestore(question)
        else:
            logger.info("Fallback: querying employee data from SQLite")
            employee_data = _handle_employee_query_sqlite(question, db)
        logger.info("[TIMING] employee_query=%.2fs", time.time() - t1)

    elif intent == "document_qa":
        retrieval_query = question
        cache_key = f"{user_role}:{retrieval_query.lower().strip()}"
        cached = _get_cached(cache_key)
        if cached:
            return cached

        if settings.USE_RERANKER:
            documents = retrieve_and_rerank(query=retrieval_query, user_role=user_role)
        else:
            documents = retrieve(query=retrieval_query, user_role=user_role)
        context = format_context(documents)
        sources = get_sources(documents)
        logger.info("[TIMING] retrieval=%.2fs", time.time() - t1)

    elif intent == "out_of_scope":
        response = {
            "answer": "Xin loi, cau hoi nay nam ngoai pham vi ho tro cua chatbot. "
                      "Toi chi co the tra loi ve trang thai nhan vien va tai lieu noi bo cong ty.",
            "intent": "out_of_scope",
            "sources": [],
            "error": None,
        }
        _save_history_async(session_id, question, response["answer"])
        return response

    system_prompt = _load_system_prompt()

    answer_template = _load_answer_prompt()
    full_context = answer_template.format(
        role=user_role,
        intent=intent,
        context=context or "Khong co",
        employee_data=employee_data or "Khong co",
        question=question,
    )

    t2 = time.time()
    answer = chat(
        question=full_context,
        system_prompt=system_prompt,
        conversation_history=history or None,  # Fix 3: pass as structured messages
    )
    logger.info("[TIMING] gemini=%.2fs", time.time() - t2)
    logger.info("[TIMING] total_pipeline=%.2fs", time.time() - t0)

    response = {
        "answer": answer,
        "intent": intent,
        "sources": sources,
        "error": None,
    }

    _save_history_async(session_id, question, answer)

    if intent == "document_qa" and cache_key:
        _set_cache(cache_key, response)

    return response
