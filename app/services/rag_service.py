"""
Central chat orchestration layer.

This module is the decision point that turns a user message into one of the
backend's supported execution paths:

1. Classify the intent
2. For `employee_status`, query Firestore when available, otherwise SQLite
3. For `document_qa`, retrieve relevant chunks from ChromaDB
4. Assemble prompt context, recent conversation state, and role information
5. Call Gemini to generate the final answer
6. Return answer metadata in a stable API-friendly structure

It also maintains small in-process stores for conversation history and
document-answer caching.
"""

import os
import logging
from functools import lru_cache
from sqlalchemy.orm import Session

from app.services.intent_service import classify_intent
from app.services.gemini_service import chat
from app.services.retriever_service import retrieve, format_context, get_sources

logger = logging.getLogger(__name__)

# Conversation state is deliberately process-local and short-lived.
# It improves follow-up questions in dev/demo flows but should not be treated
# as durable chat storage.
_conversation_store: dict[str, list[dict]] = {}
MAX_HISTORY = 3


def _get_history(session_id: str) -> list[dict]:
    return _conversation_store.get(session_id, [])


def _save_history(session_id: str, question: str, answer: str):
    if session_id not in _conversation_store:
        _conversation_store[session_id] = []

    _conversation_store[session_id].append({"role": "user", "content": question})
    _conversation_store[session_id].append({"role": "assistant", "content": answer})

    max_messages = MAX_HISTORY * 2
    if len(_conversation_store[session_id]) > max_messages:
        _conversation_store[session_id] = _conversation_store[session_id][-max_messages:]


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


# This cache only applies to document QA because retrieval + generation is the
# most expensive path and repeated policy questions are common during demos.
_response_cache: dict[str, dict] = {}
CACHE_MAX_SIZE = 50


def _get_cached(cache_key: str) -> dict | None:
    return _response_cache.get(cache_key)


def _set_cache(cache_key: str, response: dict):
    if len(_response_cache) >= CACHE_MAX_SIZE:
        oldest_key = next(iter(_response_cache))
        del _response_cache[oldest_key]
    _response_cache[cache_key] = response


def _use_firestore() -> bool:
    """Return whether Firestore-backed employee queries are available."""
    try:
        from app.core.security import _ensure_firebase
        return _ensure_firebase()
    except Exception:
        return False


def _handle_employee_query_firestore(question: str) -> str:
    """Query employee data from Firestore."""
    from app.services import firestore_employee_service as fs

    q = question.lower()

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
    """Fallback employee query path backed by local SQLite."""
    from app.services import employee_service

    q = question.lower()

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
    """
    Execute the full chat pipeline and return a JSON-serializable response.

    The function is synchronous by design because most downstream helpers are
    synchronous. The FastAPI layer runs it in a worker thread.
    """
    intent = classify_intent(question)

    context = ""
    employee_data = ""
    sources = []

    if intent == "employee_status":
        if _use_firestore():
            logger.info("Querying employee data from Firestore")
            employee_data = _handle_employee_query_firestore(question)
        else:
            logger.info("Fallback: querying employee data from SQLite")
            employee_data = _handle_employee_query_sqlite(question, db)

    elif intent == "document_qa":
        cache_key = f"{user_role}:{question.lower().strip()}"
        cached = _get_cached(cache_key)
        if cached:
            return cached

        documents = retrieve(query=question, user_role=user_role)
        context = format_context(documents)
        sources = get_sources(documents)

    elif intent == "out_of_scope":
        response = {
            "answer": "Xin loi, cau hoi nay nam ngoai pham vi ho tro cua chatbot. "
                      "Toi chi co the tra loi ve trang thai nhan vien va tai lieu noi bo cong ty.",
            "intent": "out_of_scope",
            "sources": [],
            "error": None,
        }
        _save_history(session_id, question, response["answer"])
        return response

    system_prompt = _load_system_prompt()
    history = _get_history(session_id)

    history_text = ""
    if history:
        history_parts = []
        for msg in history:
            prefix = "Nguoi dung" if msg["role"] == "user" else "Tro ly"
            history_parts.append(f"{prefix}: {msg['content']}")
        history_text = "\n".join(history_parts)

    answer_template = _load_answer_prompt()
    full_context = answer_template.format(
        role=user_role,
        intent=intent,
        context=context or "Khong co",
        employee_data=employee_data or "Khong co",
        conversation_history=history_text or "Khong co",
        question=question,
    )

    answer = chat(
        question=full_context,
        system_prompt=system_prompt,
    )

    response = {
        "answer": answer,
        "intent": intent,
        "sources": sources,
        "error": None,
    }

    _save_history(session_id, question, answer)

    if intent == "document_qa":
        cache_key = f"{user_role}:{question.lower().strip()}"
        _set_cache(cache_key, response)

    return response
