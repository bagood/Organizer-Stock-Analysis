from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from app.config import settings
from app.database import SessionFactory
from app.models.chat_conversation import ChatConversation
from app.models.chat_message import ChatMessage
from app.models.user import User
from app.services.chat_clock import jakarta_business_date, jakarta_day_end
from app.services.chat_history_housekeeping import (
    delete_expired_chat_history,
    seconds_until_next_housekeeping,
)
from tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_housekeeping_deletes_only_history_beyond_retention(client, monkeypatch):
    await register_and_login(client, "alice")
    monkeypatch.setattr(settings, "chat_history_retention_days", 30)
    now = datetime(2026, 9, 10, 12, tzinfo=UTC)

    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.username == "alice"))
        assert user is not None
        expired = ChatConversation(
            user_id=user.id,
            business_date=jakarta_business_date(now) - timedelta(days=32),
            expires_at=now - timedelta(days=31),
        )
        retained = ChatConversation(
            user_id=user.id,
            business_date=jakarta_business_date(now),
            expires_at=jakarta_day_end(jakarta_business_date(now)),
        )
        session.add_all([expired, retained])
        await session.flush()
        session.add_all(
            [
                ChatMessage(
                    conversation_id=expired.id,
                    role="user",
                    content="Delete me",
                    sequence_number=1,
                ),
                ChatMessage(
                    conversation_id=retained.id,
                    role="user",
                    content="Keep me",
                    sequence_number=1,
                ),
            ]
        )
        await session.commit()

    async with SessionFactory() as session:
        deleted = await delete_expired_chat_history(session, now=now)
        assert deleted == 1
        assert await session.scalar(select(func.count()).select_from(ChatConversation)) == 1
        assert await session.scalar(select(func.count()).select_from(ChatMessage)) == 1
        remaining = await session.scalar(select(ChatMessage))
        assert remaining is not None
        assert remaining.content == "Keep me"


def test_next_housekeeping_is_0015_jakarta():
    jakarta = ZoneInfo("Asia/Jakarta")
    before_run = datetime(2026, 9, 10, 0, 10, tzinfo=jakarta)
    at_run = datetime(2026, 9, 10, 0, 15, tzinfo=jakarta)

    assert seconds_until_next_housekeeping(before_run) == 5 * 60
    assert seconds_until_next_housekeeping(at_run) == 24 * 60 * 60
