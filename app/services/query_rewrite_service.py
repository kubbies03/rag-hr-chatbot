"""Query rewriting — converts conversational questions into retrieval-optimized keywords."""

import logging
from app.services.gemini_service import _invoke_with_timeout, get_llm
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

_REWRITE_PROMPT = """Bạn là công cụ tối ưu hóa truy vấn tài liệu HR.

Nhiệm vụ: Rút gọn câu hỏi thành cụm từ khóa ngắn (3-8 từ) để tìm kiếm trong tài liệu nội bộ công ty.

Quy tắc:
- Giữ nguyên các thuật ngữ quan trọng: OT, KPI, PIP, HRBP, C&B, remote, hybrid, onboard, resign
- Bỏ các từ đệm: "làm thế nào", "như thế nào", "là gì", "tôi muốn biết", "cho tôi hỏi", "ở đâu"
- Trả về DUY NHẤT cụm từ khóa, không giải thích
- Giữ nguyên tiếng Việt

Ví dụ:
Câu hỏi: làm thế nào để xin nghỉ phép?
Từ khóa: quy trình xin nghỉ phép

Câu hỏi: tôi muốn biết lương làm thêm giờ OT tính như thế nào
Từ khóa: chính sách lương OT làm thêm giờ

Câu hỏi: quy định về đi muộn là gì
Từ khóa: quy định đi muộn kỷ luật

Câu hỏi: {question}
Từ khóa:"""


def rewrite_query(question: str) -> str:
    """
    Rewrite a conversational question into retrieval-optimized keywords.

    Falls back to the original question if rewriting fails or adds latency.
    """
    if len(question.strip()) < 30:
        return question

    try:
        llm = get_llm()
        prompt = _REWRITE_PROMPT.format(question=question.strip())
        response = _invoke_with_timeout(llm, [HumanMessage(content=prompt)], timeout=8)
        rewritten = response.content.strip()

        if not rewritten or len(rewritten) > 120:
            return question

        logger.debug("Query rewrite: '%s' → '%s'", question[:60], rewritten)
        return rewritten

    except Exception as e:
        logger.warning("Query rewrite failed, using original: %s", e)
        return question
