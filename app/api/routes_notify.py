"""
routes_notify.py — Send FCM push notifications via Firebase Admin SDK.

POST /api/notify — receives token + title + body, sends FCM message.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import get_current_user

router = APIRouter()


class NotifyRequest(BaseModel):
    token: str
    title: str
    body: str


@router.post("/api/notify")
async def send_notification(
    request: NotifyRequest,
    user: dict = Depends(get_current_user),
):
    """Send FCM push notification to a specified device token."""
    try:
        import firebase_admin
        from firebase_admin import messaging, credentials
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
        # Best-effort delivery — don't raise errors to the client
        return {"status": "skipped", "reason": str(e)}
