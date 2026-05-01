"""Query employee data from Firestore."""

import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)

_firestore_client = None
_users_cache: dict[str, dict] = {}
_users_cache_time: float = 0
USERS_CACHE_TTL = 120


def _get_db():
    global _firestore_client
    if _firestore_client is None:
        from app.core.security import _ensure_firebase

        if not _ensure_firebase():
            raise RuntimeError("Firebase not configured")
        from firebase_admin import firestore

        _firestore_client = firestore.client()
    return _firestore_client


def _today_str() -> str:
    return datetime.now().strftime("%Y%m%d")


def _get_all_users_cached() -> dict[str, dict]:
    """Return all users with a short cache."""
    import time

    global _users_cache, _users_cache_time

    if _users_cache and (time.time() - _users_cache_time < USERS_CACHE_TTL):
        return _users_cache

    db = _get_db()
    docs = db.collection("Users").stream()
    result = {}
    for doc in docs:
        data = doc.to_dict()
        data["uid"] = doc.id
        result[doc.id] = data

    _users_cache = result
    _users_cache_time = time.time()
    return result


def _get_user_name(uid: str) -> str:
    users = _get_all_users_cached()
    user = users.get(uid)
    if user:
        return user.get("fullName", uid)
    return uid


def get_all_users() -> list[dict]:
    return list(_get_all_users_cached().values())


def get_employee_by_name(name: str) -> dict | None:
    users = _get_all_users_cached()
    name_lower = name.lower()
    for user in users.values():
        full_name = user.get("fullName", "")
        if full_name and name_lower in full_name.lower():
            return user
    return None


def get_employees_by_status(status: str) -> list[dict]:
    users = _get_all_users_cached()
    return [u for u in users.values() if u.get("status") == status]


def get_today_attendance() -> list[dict]:
    db = _get_db()
    today = _today_str()
    docs = db.collection("Attendance").where("date", "==", today).stream()

    records = []
    for doc in docs:
        data = doc.to_dict()
        uid = data.get("userId", "")
        data["hoTen"] = _get_user_name(uid)
        data["gioVao"] = _format_timestamp(data.get("checkIn"))
        data["gioRa"] = _format_timestamp(data.get("checkOut"))
        records.append({
            "Ho ten": data["hoTen"],
            "Gio vao": data["gioVao"],
            "Gio ra": data["gioRa"] or "Chua check-out",
        })
    return records


def get_late_employees(after_hour: int = 9) -> list[dict]:
    db = _get_db()
    today = _today_str()
    docs = db.collection("Attendance").where("date", "==", today).stream()

    late = []
    for doc in docs:
        data = doc.to_dict()
        check_in = data.get("checkIn")
        hour = _get_hour(check_in)
        if hour is not None and hour >= after_hour:
            uid = data.get("userId", "")
            late.append({
                "Ho ten": _get_user_name(uid),
                "Gio vao": _format_timestamp(check_in),
                "Tre": f"{hour - after_hour} gio" if hour > after_hour else f"Dung {after_hour}h",
            })
    return late


def get_checked_in_users() -> list[dict]:
    db = _get_db()
    today = _today_str()
    docs = db.collection("Attendance").where("date", "==", today).stream()

    result = []
    for doc in docs:
        data = doc.to_dict()
        if data.get("checkIn") and not data.get("checkOut"):
            uid = data.get("userId", "")
            result.append({
                "Ho ten": _get_user_name(uid),
                "Gio vao": _format_timestamp(data.get("checkIn")),
            })
    return result


def get_pending_leave_requests() -> list[dict]:
    db = _get_db()
    docs = db.collection("LeaveRequests").where("status", "==", "pending").stream()
    result = []
    for doc in docs:
        data = doc.to_dict()
        result.append({
            "Ho ten": data.get("userName", "Khong ro"),
            "Phong ban": data.get("department", ""),
            "Loai nghi": data.get("leaveType", ""),
            "Ly do": data.get("reason", ""),
            "Tu ngay": _format_date(data.get("startDate")),
            "Den ngay": _format_date(data.get("endDate")),
            "So ngay": data.get("totalDays", ""),
        })
    return result


def get_approved_leaves_today() -> list[dict]:
    db = _get_db()
    today = datetime.now()

    docs = db.collection("LeaveRequests").where("status", "==", "approved").stream()
    on_leave = []
    for doc in docs:
        data = doc.to_dict()
        start = data.get("startDate")
        end = data.get("endDate")

        if _is_date_in_range(today, start, end):
            on_leave.append({
                "Ho ten": data.get("userName", "Khong ro"),
                "Phong ban": data.get("department", ""),
                "Loai nghi": data.get("leaveType", ""),
                "Tu ngay": _format_date(start),
                "Den ngay": _format_date(end),
                "Ly do": data.get("reason", ""),
            })
    return on_leave


def get_all_tasks() -> list[dict]:
    db = _get_db()
    docs = db.collection("Tasks").stream()
    result = []
    for doc in docs:
        data = doc.to_dict()
        emp_id = data.get("employeeId", "")
        result.append({
            "Nhan vien": _get_user_name(emp_id),
            "Tieu de": data.get("title", ""),
            "Mo ta": data.get("description", ""),
            "Trang thai": data.get("status", ""),
        })
    return result


def get_tasks_by_employee(employee_id: str) -> list[dict]:
    db = _get_db()
    docs = db.collection("Tasks").where("employeeId", "==", employee_id).stream()
    return [_format_task(doc) for doc in docs]


def get_all_stats() -> dict:
    users = get_all_users()
    today_att = get_today_attendance()
    pending = get_pending_leave_requests()
    on_leave = get_approved_leaves_today()

    names_on_leave = [l.get("Ho ten", "") for l in on_leave]
    names_checked_in = [a.get("Ho ten", "") for a in today_att]

    result = {
        "Tong nhan vien": len(users),
        "Da cham cong hom nay": len(today_att),
        "Dang nghi phep": len(on_leave),
        "Don nghi cho duyet": len(pending),
    }

    if names_on_leave:
        result["Danh sach nghi phep"] = ", ".join(names_on_leave)
    if names_checked_in:
        result["Danh sach da cham cong"] = ", ".join(names_checked_in)

    return result


def format_employee_data(data) -> str:
    if not data:
        return "Khong tim thay du lieu."

    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            if value is not None and key not in ("uid", "fcmToken", "avatarUrl", "biometricRegistered"):
                label = _vn_key(key) if not _is_vietnamese(key) else key
                lines.append(f"- {label}: {value}")
        return "\n".join(lines)

    if isinstance(data, list):
        if not data:
            return "Danh sach trong."
        parts = []
        for i, item in enumerate(data, 1):
            if isinstance(item, dict):
                lines = []
                for key, value in item.items():
                    if value is not None:
                        label = _vn_key(key) if not _is_vietnamese(key) else key
                        lines.append(f"  {label}: {value}")
                parts.append(f"[{i}]\n" + "\n".join(lines))
        return "\n\n".join(parts)

    return str(data)


def _is_vietnamese(key: str) -> bool:
    return " " in key or any(c in key for c in "Ã Ã¡áº¡áº£Ã£Äƒáº¯áº±áº·áº³áºµÃ¢áº¥áº§áº­áº©áº«")


def _vn_key(key: str) -> str:
    mapping = {
        "fullName": "Ho ten",
        "email": "Email",
        "role": "Vai tro",
        "status": "Trang thai",
        "department": "Phong ban",
        "position": "Chuc vu",
        "baseSalary": "Luong co ban",
        "productivityScore": "Diem nang suat",
    }
    return mapping.get(key, key)


def _format_timestamp(ts) -> str:
    if ts is None:
        return ""
    if hasattr(ts, "strftime"):
        return ts.strftime("%H:%M")
    if hasattr(ts, "timestamp"):
        dt = datetime.fromtimestamp(ts.timestamp())
        return dt.strftime("%H:%M")
    return str(ts)


def _format_date(d) -> str:
    if d is None:
        return ""
    if hasattr(d, "strftime"):
        return d.strftime("%d/%m/%Y")
    return str(d)


def _get_hour(ts) -> int | None:
    if ts is None:
        return None
    if hasattr(ts, "hour"):
        return ts.hour
    if hasattr(ts, "timestamp"):
        dt = datetime.fromtimestamp(ts.timestamp())
        return dt.hour
    return None


def _is_date_in_range(today, start, end) -> bool:
    try:
        if hasattr(start, "timestamp"):
            start_dt = datetime.fromtimestamp(start.timestamp()).date()
        elif hasattr(start, "date"):
            start_dt = start.date() if callable(getattr(start, "date")) else start
        else:
            return False

        if hasattr(end, "timestamp"):
            end_dt = datetime.fromtimestamp(end.timestamp()).date()
        elif hasattr(end, "date"):
            end_dt = end.date() if callable(getattr(end, "date")) else end
        else:
            return False

        return start_dt <= today.date() <= end_dt
    except Exception:
        return False


def _format_task(doc) -> dict:
    data = doc.to_dict()
    emp_id = data.get("employeeId", "")
    return {
        "Nhan vien": _get_user_name(emp_id),
        "Tieu de": data.get("title", ""),
        "Mo ta": data.get("description", ""),
        "Trang thai": data.get("status", ""),
    }
