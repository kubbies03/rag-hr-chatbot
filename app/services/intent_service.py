"""
intent_service.py — Classify user questions by intent.

3-layer strategy (fast -> slow):
  Layer 1: Keyword matching (0ms, high accuracy for clear questions)
  Layer 2: Gemini API fallback (when keywords don't match)
  Layer 3: Default out_of_scope (when both layers are uncertain)
"""

import re
import os
from functools import lru_cache
from app.services.gemini_service import classify

# === LAYER 1: Keyword patterns ===

# Employee questions: contain person names + HR keywords
EMPLOYEE_KEYWORDS = [
    # status / presence
    r"trạng thái",
    r"(có mặt|vắng mặt|đi làm|offline|online)",
    r"ai.*(đang|hiện tại)",

    # leave / absence
    r"(ai|nhân viên).*(nghỉ|vắng|phép|ốm|remote)",
    r"(đang|hôm nay).*(nghỉ|vắng)",
    r"còn phép không",
    r"bao nhiêu.*(phép|leave)",

    # attendance / late
    r"chấm công",
    r"check.?in|check.?out",
    r"quên chấm công",
    r"đi (muộn|trễ|sớm)",
    r"(trễ|muộn).*bao nhiêu",

    # headcount / listing
    r"(bao nhiêu|mấy).*(người|nhân viên)",
    r"danh sách.*(nhân viên|đi trễ|nghỉ|remote)",
    r"ai.*(trễ|muộn|nghỉ|remote)",

    # employee info
    r"phòng ban",
    r"(onsite|offsite|remote|wfh)",
    r"thử việc|probation",
    r"hợp đồng.*(còn|hết|khi nào)",

    # short FAQ-style questions
    r"tôi còn phép không",
    r"tôi quên check.?in",
    r"tôi đi trễ",
    r"hôm nay ai nghỉ",
]

# Document questions: keywords related to policies and regulations
DOCUMENT_KEYWORDS = [
    # policy core
    r"quy (định|chế|trình)",
    r"nội quy",
    r"chính sách",
    r"handbook",

    # rights & obligations
    r"(được|không được|có được).*(nghỉ|remote|phép|ot)",
    r"quyền lợi",
    r"nghĩa vụ",

    # compensation & benefits
    r"lương",
    r"thưởng",
    r"tăng lương",
    r"phúc lợi",
    r"bảo hiểm",

    # KPI / discipline
    r"kpi",
    r"pip",
    r"kỷ luật",
    r"vi phạm",
    r"bị (phạt|cảnh cáo|đuổi)",

    # remote policy
    r"remote|wfh|hybrid",
    r"điều kiện.*remote",

    # leave policy
    r"nghỉ.*(bao nhiêu ngày|quy định)",
    r"hết phép.*(sao|làm gì)",

    # OT policy
    r"ot.*(bao nhiêu|tính sao)",
    r"làm thêm.*(tính|quy định)",

    # semantic patterns
    r"(mức|hạn|điều kiện).*(lương|phạt|kpi|remote)",
]

PROCEDURE_KEYWORDS = [
    # requesting leave
    r"(làm sao|cách).*(xin nghỉ|nghỉ phép)",
    r"quy trình.*nghỉ",
    r"nghỉ.*(phải làm gì|bước nào)",

    # attendance correction
    r"(làm sao|cách).*(sửa|bổ sung).*(chấm công)",
    r"quên check.?in.*(làm sao|sửa)",
    r"điều chỉnh công",

    # OT
    r"(làm sao|cách).*(xin|đăng ký).*ot",
    r"quy trình.*ot",

    # onboarding
    r"onboard.*(làm gì|quy trình)",
    r"nhân viên mới.*(cần gì|làm gì)",

    # offboarding
    r"(nghỉ việc|resign).*(làm gì|quy trình)",
    r"bàn giao.*(gì|như nào)",

    # recruitment
    r"đề xuất tuyển.*(như nào|ra sao)",
    r"quy trình.*tuyển",

    # KPI
    r"(đánh giá|tính).*kpi",
    r"review kpi.*(như nào)",

    # salary raise
    r"đề xuất tăng lương.*(ra sao|như nào)",

    # generic how-to
    r"(làm thế nào|cách nào|process|workflow)",
]

CASUAL_KEYWORDS = [
    r"còn phép không",
    r"quên chấm công rồi",
    r"tôi xin nghỉ hôm nay",
    r"đi muộn có sao không",
    r"lương bao giờ review",
    r"kpi thấp có sao không",
    r"tôi muốn wfh",
    r"hết phép rồi",
    r"ot tính sao",
    r"cần nộp gì khi nghỉ việc",
]

INTENT_LAYERS = {
    "employee": EMPLOYEE_KEYWORDS,
    "policy": DOCUMENT_KEYWORDS,
    "procedure": PROCEDURE_KEYWORDS,
    "casual": CASUAL_KEYWORDS,
}


@lru_cache(maxsize=1)
def _load_router_prompt() -> str:
    prompt_path = os.path.join(
        os.path.dirname(__file__), "..", "prompts", "router_prompt.txt",
    )
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def normalize(q: str) -> str:
    q = q.lower().strip()
    q = re.sub(r"[^\w\s]", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def classify_intent(question: str) -> str:
    """
    Classify a question into one of 3 intents:
    - employee_status: queries about employee state
    - document_qa: queries about policies, procedures, company documents
    - out_of_scope: unrelated questions
    """
    q = normalize(question)

    # --- Layer 1: Rule-based keyword matching ---
    # Prioritize procedure — many how-to questions may contain generic HR terms
    for pattern in PROCEDURE_KEYWORDS:
        if re.search(pattern, q):
            return "document_qa"

    for pattern in DOCUMENT_KEYWORDS:
        if re.search(pattern, q):
            return "document_qa"

    for pattern in EMPLOYEE_KEYWORDS:
        if re.search(pattern, q):
            return "employee_status"

    # Casual HR questions still classified as document_qa
    for pattern in CASUAL_KEYWORDS:
        if re.search(pattern, q):
            return "document_qa"

    # --- Layer 2: LLM fallback ---
    try:
        prompt_template = _load_router_prompt()
        result = classify(question, prompt_template)

        valid_intents = {"employee_status", "document_qa", "out_of_scope"}
        if result in valid_intents:
            return result

    except Exception:
        pass

    # --- Layer 3: Default fallback ---
    return "out_of_scope"
