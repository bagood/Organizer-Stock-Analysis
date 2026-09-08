from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import DailyChatLimitExceededError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.chat_quota import ChatQuotaResponse


class ChatQuotaService:
    def __init__(self, repository: UserRepository, session: AsyncSession) -> None:
        self.repository = repository
        self.session = session

    @staticmethod
    def _resets_at(today: date) -> datetime:
        return datetime.combine(today + timedelta(days=1), time.min, tzinfo=UTC)

    async def get(self, user: User) -> ChatQuotaResponse:
        today = datetime.now(UTC).date()
        usage = user.chat_usage_count if user.chat_usage_date == today else 0
        return ChatQuotaResponse(
            allowed=usage < settings.chat_daily_limit,
            remaining=max(0, settings.chat_daily_limit - usage),
            daily_limit=settings.chat_daily_limit,
            resets_at=self._resets_at(today),
        )

    async def consume(self, user: User) -> ChatQuotaResponse:
        today = datetime.now(UTC).date()
        usage = await self.repository.consume_chat_quota(
            user.id, today, settings.chat_daily_limit
        )
        if usage is None:
            raise DailyChatLimitExceededError
        await self.session.commit()
        return ChatQuotaResponse(
            allowed=True,
            remaining=max(0, settings.chat_daily_limit - usage),
            daily_limit=settings.chat_daily_limit,
            resets_at=self._resets_at(today),
        )
