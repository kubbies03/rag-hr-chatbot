"""
Authentication and caller identity resolution.

The module supports two modes behind the same dependency:

1. Demo mode
   - Reads `X-API-Key`
   - Maps directly to in-memory demo users
   - Used for local development, demos, and API smoke tests

2. Firebase mode
   - Reads `Authorization: Bearer <token>`
   - Verifies the Firebase ID token
   - Loads role and profile information from Firestore `Users`

The exported dependency returns a normalized user dictionary so route handlers
do not need to know which auth backend was used.
"""

import os
import time
from fastapi import Header, HTTPException
from app.core.config import settings

DEMO_USERS = {
    "demo_employee_001": {
        "user_id": "emp_001",
        "name": "Nguyen Van An",
        "role": "employee",
        "department": "engineering",
    },
    "demo_hr_001": {
        "user_id": "hr_001",
        "name": "Tran Thi Binh",
        "role": "hr",
        "department": "hr",
    },
    "demo_manager_001": {
        "user_id": "mgr_001",
        "name": "Le Van Cuong",
        "role": "manager",
        "department": "engineering",
    },
    "demo_admin_001": {
        "user_id": "admin_001",
        "name": "Pham Thi Dung",
        "role": "admin",
        "department": "management",
    },
}

# Small in-memory cache to avoid a Firestore role lookup on every request.
# This is process-local only; it is a latency optimization, not a source of truth.
_role_cache: dict[str, dict] = {}
_role_cache_ts: dict[str, float] = {}
CACHE_TTL = 300  # 5 minutes


def _get_cached_role(uid: str) -> dict | None:
    if uid in _role_cache:
        if time.time() - _role_cache_ts.get(uid, 0) < CACHE_TTL:
            return _role_cache[uid]
        del _role_cache[uid]
        del _role_cache_ts[uid]
    return None


def _set_cached_role(uid: str, user_info: dict):
    _role_cache[uid] = user_info
    _role_cache_ts[uid] = time.time()


# Firebase Admin initialization is lazy so demo mode can run without requiring
# service-account setup. The function returns `False` instead of throwing so
# callers can gracefully fall back to demo or SQLite paths when appropriate.
_firebase_initialized = False


def _ensure_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return True

    try:
        import firebase_admin
        from firebase_admin import credentials

        if firebase_admin._apps:
            _firebase_initialized = True
            return True

        cred_path = settings.FIREBASE_CREDENTIALS_PATH
        if not os.path.exists(cred_path):
            return False

        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        return True
    except Exception:
        return False


async def get_current_user(
    x_api_key: str = Header(default=None, alias="X-API-Key"),
    authorization: str = Header(default=None),
) -> dict:
    """
    Resolve the caller into a normalized application user object.

    Return shape:
        {
            "user_id": "...",
            "name": "...",
            "role": "employee|hr|manager|admin",
            "department": "..."
        }
    """
    if x_api_key and x_api_key in DEMO_USERS:
        return DEMO_USERS[x_api_key]

    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        return await _verify_firebase_token(token)

    raise HTTPException(
        status_code=401,
        detail="Missing authentication. Provide X-API-Key or Authorization: Bearer <token>",
    )


async def _verify_firebase_token(token: str) -> dict:
    if not _ensure_firebase():
        raise HTTPException(
            status_code=401,
            detail="Firebase not configured. Use X-API-Key for testing.",
        )

    try:
        from firebase_admin import auth as firebase_auth, firestore

        decoded_token = firebase_auth.verify_id_token(token)
        uid = decoded_token["uid"]

        cached = _get_cached_role(uid)
        if cached:
            return cached

        db = firestore.client()
        user_doc = db.collection("Users").document(uid).get()

        if user_doc.exists:
            data = user_doc.to_dict()
            result = {
                "user_id": uid,
                "name": data.get("fullName", decoded_token.get("name", "Unknown")),
                "role": data.get("role", "employee"),
                "department": data.get("department", "general"),
            }
        else:
            result = {
                "user_id": uid,
                "name": decoded_token.get("name", "Unknown"),
                "role": "employee",
                "department": "general",
            }

        _set_cached_role(uid, result)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid Firebase token: {str(e)}",
        )
