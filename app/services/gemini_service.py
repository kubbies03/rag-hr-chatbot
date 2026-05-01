"""Gemini chat client."""

import json
import re
import threading

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings

_llm = None

GEMINI_TIMEOUT = 30


def get_llm() -> ChatGoogleGenerativeAI:
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_CHAT_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=settings.GEMINI_TEMPERATURE,
            timeout=GEMINI_TIMEOUT,
        )
    return _llm


def _invoke_with_timeout(llm, messages, timeout=GEMINI_TIMEOUT):
    result = [None]
    error = [None]

    def target():
        try:
            result[0] = llm.invoke(messages)
        except Exception as e:
            error[0] = e

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        raise TimeoutError(f"Gemini API did not respond within {timeout}s")
    if error[0]:
        raise error[0]
    return result[0]


def chat(
    question: str,
    system_prompt: str = "",
    context: str = "",
    conversation_history: list[dict] = None,
) -> str:
    llm = get_llm()
    messages = []

    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))

    if conversation_history:
        for msg in conversation_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

    full_question = f"{context}\n\n[Cau hoi]: {question}" if context else question
    messages.append(HumanMessage(content=full_question))

    try:
        response = _invoke_with_timeout(llm, messages)
        return response.content
    except TimeoutError:
        return "Xin loi, he thong mat qua nhieu thoi gian de xu ly. Vui long thu lai."
    except Exception as e:
        return f"Loi khi goi Gemini API: {str(e)}"


def classify(question: str, prompt_template: str) -> str:
    llm = get_llm()
    prompt = prompt_template.format(question=question)
    try:
        response = _invoke_with_timeout(llm, [HumanMessage(content=prompt)], timeout=10)
        return response.content.strip().lower()
    except Exception:
        return "out_of_scope"


def classify_with_keywords(question: str, prompt_template: str) -> tuple[str, str]:
    """Classify intent and extract retrieval keywords in a single LLM call."""
    valid_intents = {"employee_status", "document_qa", "out_of_scope"}
    llm = get_llm()
    prompt = prompt_template.format(question=question)
    try:
        response = _invoke_with_timeout(llm, [HumanMessage(content=prompt)], timeout=10)
        raw = response.content.strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()
        match = re.search(r"\{[^{}]+\}", raw, re.DOTALL)
        if not match:
            return "out_of_scope", question
        data = json.loads(match.group(0))
        intent = (data.get("intent") or "").strip().lower()
        keywords = (data.get("keywords") or "").strip()
        if intent not in valid_intents:
            intent = "out_of_scope"
        return intent, keywords or question
    except Exception:
        return "out_of_scope", question
