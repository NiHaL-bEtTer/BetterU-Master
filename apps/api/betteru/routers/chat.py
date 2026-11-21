from datetime import UTC, datetime, time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, select

from betteru.config import get_settings
from betteru.db import SessionLocal
from betteru.deps import DB, CurrentUser
from betteru.llm.agent import run_chat, to_sse
from betteru.models import ChatMessage, User
from betteru.schemas import ChatIn, ChatMessageOut, RatingIn

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/messages", response_model=list[ChatMessageOut])
def messages(db: DB, user: CurrentUser, limit: int = 50):
    rows = db.scalars(
        select(ChatMessage).where(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(min(limit, 200))
    ).all()
    return list(reversed(rows))


@router.delete("/messages", status_code=204)
def clear(db: DB, user: CurrentUser):
    db.execute(delete(ChatMessage).where(ChatMessage.user_id == user.id))
    db.commit()


@router.post("/messages/{message_id}/rating", status_code=204)
def rate(message_id: int, body: RatingIn, db: DB, user: CurrentUser):
    """👍/👎 on an answer. 👎 answers are the best source of new eval questions."""
    msg = db.get(ChatMessage, message_id)
    if not msg or msg.user_id != user.id or msg.role != "assistant":
        raise HTTPException(404, "Message not found")
    msg.rating = body.rating or None
    db.commit()


@router.delete("/messages/{message_id}/actions/{index}", status_code=204)
def consume_action(message_id: int, index: int, db: DB, user: CurrentUser):
    """Remove an action button once used, so a reload can't log the same meal twice."""
    msg = db.get(ChatMessage, message_id)
    if not msg or msg.user_id != user.id or not (0 <= index < len(msg.actions or [])):
        raise HTTPException(404, "Action not found")
    msg.actions = [a for i, a in enumerate(msg.actions) if i != index]
    db.commit()


@router.post("", responses={200: {"content": {"text/event-stream": {}}}})
def chat(body: ChatIn, db: DB, user: CurrentUser):
    start_of_day = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
    sent_today = db.scalar(
        select(func.count()).select_from(ChatMessage)
        .where(ChatMessage.user_id == user.id, ChatMessage.role == "user", ChatMessage.created_at >= start_of_day)
    )
    if sent_today >= get_settings().llm_daily_message_limit:
        raise HTTPException(429, "You've reached today's message limit. It resets at midnight UTC.")

    user_id = user.id

    def stream():
        # The stream outlives the request's DB session, so it opens its own.
        session = SessionLocal()
        try:
            yield from to_sse(run_chat(session, session.get(User, user_id), body.message))
        finally:
            session.close()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
