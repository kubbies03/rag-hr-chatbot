"""
gemini_service.py — Gemini Chat API client with timeout and retry.
"""

import signal
import threading
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app.core.config import settings

_llm = None

GEMINI_TIMEOUT = 30  # seconds


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

    if context:
        full_question = f"{context}\n\n[Cau hoi]: {question}"
    else:
        full_question = question

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
