"""Classify user questions by intent."""

import os
import re
from functools import lru_cache

from app.services.gemini_service import classify
from app.services.intent_classifier_service import classify_by_embedding

EMPLOYEE_KEYWORDS = [
    r"trạng thái",
    r"(có mặt|vắng mặt|đi làm|offline|online)",
    r"ai.*(đang|hiện tại)",
    r"(ai|nhân viên).*(nghỉ|vắng|phép|ốm|remote)",
    r"(đang|hôm nay).*(nghỉ|vắng)",
    r"còn phép không",
    r"bao nhiêu.*(phép|leave)",
    r"(ai|hôm nay|chưa).*(chấm công)|(chấm công).*(hôm nay|ai|chưa)",
    r"check.?in|check.?out",
    r"quên chấm công",
    r"đi (muộn|trễ|sớm)",
    r"(trễ|muộn).*bao nhiêu",
    r"(bao nhiêu|mấy).*(người|nhân viên)",
    r"danh sách.*(nhân viên|đi trễ|nghỉ|remote)",
    r"ai.*(trễ|muộn|nghỉ|remote)",
    r"phòng ban",
    r"(onsite|offsite|remote|wfh)",
    r"hợp đồng.*(còn|hết|khi nào)",
    r"tôi còn phép không",
    r"tôi quên check.?in",
    r"tôi đi trễ",
    r"hôm nay ai nghỉ",
]

DOCUMENT_KEYWORDS = [
    r"quy (định|chế|trình)",
    r"nội quy",
    r"chính sách",
    r"handbook",
    r"cơ cấu",
    r"co cau",
    r"(cấp bậc|cap bac)",
    r"(chức danh|chuc danh)",
    r"(sơ đồ|so do).*(tổ chức|to chuc)",
    r"(thăng chức|thang chuc)",
    r"(lộ trình|lo trinh).*(thăng tiến|thang tien)",
    r"(đào tạo|dao tao)",
    r"(tuyển dụng|tuyen dung)",
    r"(hợp đồng|hop dong).*(lao động|lao dong)",
    r"(phòng ban|phong ban)",
    r"(được|không được|có được).*(nghỉ|remote|phép|ot)",
    r"quyền lợi",
    r"nghĩa vụ",
    r"lương",
    r"thưởng",
    r"tăng lương",
    r"phúc lợi",
    r"bảo hiểm",
    r"thử việc|probation",
    r"kpi",
    r"pip",
    r"kỷ luật",
    r"vi phạm",
    r"bị (phạt|cảnh cáo|đuổi)",
    r"remote|wfh|hybrid",
    r"điều kiện.*remote",
    r"nghỉ.*(bao nhiêu ngày|quy định)",
    r"hết phép.*(sao|làm gì)",
    r"ot.*(bao nhiêu|tính sao)",
    r"làm thêm.*(tính|quy định)",
    r"(mức|hạn|điều kiện).*(lương|phạt|kpi|remote)",
]

PROCEDURE_KEYWORDS = [
    r"(làm sao|cách).*(xin nghỉ|nghỉ phép)",
    r"quy trình.*nghỉ",
    r"nghỉ.*(phải làm gì|bước nào)",
    r"(làm sao|cách).*(sửa|bổ sung).*(chấm công)",
    r"quên check.?in.*(làm sao|sửa)",
    r"(điều chỉnh|bổ sung).*(chấm công|công)",
    r"(làm sao|cách).*(xin|đăng ký).*ot",
    r"quy trình.*ot",
    r"onboard.*(làm gì|quy trình)",
    r"nhân viên mới.*(cần gì|làm gì)",
    r"(nghỉ việc|resign).*(làm gì|quy trình)",
    r"bàn giao.*(gì|như nào)",
    r"đề xuất tuyển.*(như nào|ra sao)",
    r"quy trình.*tuyển",
    r"(đánh giá|tính).*kpi",
    r"review kpi.*(như nào)",
    r"đề xuất tăng lương.*(ra sao|như nào)",
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

OUT_OF_SCOPE_KEYWORDS = [
    r"thời tiết",
    r"(nấu ăn|công thức|món)",
    r"(bóng đá|thể thao|kết quả.*trận)",
    r"(bitcoin|chứng khoán|giá vàng|crypto)",
    r"(đặt vé|đặt phòng|du lịch)",
    r"(viết code|lập trình|debug|javascript|python(?!.*hr|.*nhân))",
    r"(phim|nhạc|game|giải trí)",
    r"(ăn gì|uống gì|quán)",
    r"(mua.*điện thoại|laptop|máy tính(?!.*công ty))",
    r"(tin tức|thời sự|chính trị)",
    r"(dịch.*sang|translate)",
    r"(bài thơ|truyện|sáng tác)",
]


def normalize(q: str) -> str:
    q = q.lower().strip()
    q = re.sub(r"[^\w\s]", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def classify_intent(question: str) -> str:
    """Classify a question into an intent.

    Priority:
    1. k-NN embedding classifier (fast, accurate for known patterns)
    2. Regex: employee_status signals
    3. Regex: document_qa signals
    4. Regex: clearly out-of-scope signals
    5. Default → document_qa (let RAG decide if info exists)
    """
    q = normalize(question)

    try:
        result = classify_by_embedding(question)
        if result is not None:
            return result
    except Exception:
        pass

    for pattern in EMPLOYEE_KEYWORDS:
        if re.search(pattern, q):
            return "employee_status"

    for pattern in PROCEDURE_KEYWORDS:
        if re.search(pattern, q):
            return "document_qa"

    for pattern in DOCUMENT_KEYWORDS:
        if re.search(pattern, q):
            return "document_qa"

    for pattern in CASUAL_KEYWORDS:
        if re.search(pattern, q):
            return "document_qa"

    for pattern in OUT_OF_SCOPE_KEYWORDS:
        if re.search(pattern, q):
            return "out_of_scope"

    return "document_qa"
