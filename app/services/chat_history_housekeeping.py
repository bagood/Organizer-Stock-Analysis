import asyncio
import logging
from datetime import UTC, datetime, time, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import SessionFactory
from app.models.chat_conversation import ChatConversation
from app.services.chat_clock import CHAT_TIMEZONE, jakarta_now

logger = logging.getLogger(__name__)

HOUSEKEEPING_HOUR = 0
HOUSEKEEPING_MINUTE = 15


async def delete_expired_chat_history(
    session: AsyncSession, *, now: datetime | None = None
) -> int:
    """Delete conversations past the configured retention period and commit the change."""
    current = now or datetime.now(UTC)
    cutoff = current - timedelta(days=settings.chat_history_retention_days)
    result = await session.execute(
        delete(ChatConversation).where(ChatConversation.expires_at < cutoff)
    )
    await session.commit()
    return result.rowcount


def seconds_until_next_housekeeping(now: datetime | None = None) -> float:
    current = (now or jakarta_now()).astimezone(CHAT_TIMEZONE)
    next_run = datetime.combine(
        current.date(),
        time(hour=HOUSEKEEPING_HOUR, minute=HOUSEKEEPING_MINUTE),
        tzinfo=CHAT_TIMEZONE,
    )
    if next_run <= current:
        next_run += timedelta(days=1)
    return (next_run - current).total_seconds()


async def _run_housekeeping_once() -> None:
    async with SessionFactory() as session:
        try:
            deleted = await delete_expired_chat_history(session)
            logger.info("Chat history housekeeping deleted %s conversations", deleted)
        except Exception:
            await session.rollback()
            logger.exception("Chat history housekeeping failed")


async def run_chat_history_housekeeping(stop_event: asyncio.Event) -> None:
    """Run cleanup at startup and then daily at 00:15 Asia/Jakarta."""
    await _run_housekeeping_once()
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=seconds_until_next_housekeeping()
            )
        except TimeoutError:
            await _run_housekeeping_once()
