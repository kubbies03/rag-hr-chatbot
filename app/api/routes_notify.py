"""Push notification endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import get_current_user

router = APIRouter()

_NOTIFY_ROLES = {"hr", "admin"}


class NotifyRequest(BaseModel):
    token: str
    title: str
    body: str


@router.post("/api/notify")
async def send_notification(
    request: NotifyRequest,
    user: dict = Depends(get_current_user),
):
    """Send an FCM notification."""
    if user["role"] not in _NOTIFY_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        from app.core.config import settings

        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)

        message = messaging.Message(
            notification=messaging.Notification(
                title=request.title,
                body=request.body,
            ),
            token=request.token,
        )
        messaging.send(message)
        return {"status": "sent"}

    except Exception as e:
        return {"status": "skipped", "reason": str(e)}
