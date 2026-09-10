from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import DailyChatLimitExceededError
from app.models.chat_message import ChatMessage
from app.models.user import User
from app.repositories.chat_history_repository import ChatHistoryRepository
from app.repositories.user_repository import UserRepository
from app.schemas.chat_quota import (
    ChatMessageResponse,
    ChatQuotaConsumeRequest,
    ChatQuotaConsumeResponse,
    ChatQuotaResponse,
)
from app.services.chat_clock import CHAT_TIMEZONE, jakarta_business_date, jakarta_day_end


def message_response(message: ChatMessage) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        client_message_id=message.client_message_id,
        role=message.role,
        content=message.content,
        created_at=message.created_at.astimezone(CHAT_TIMEZONE),
    )


class ChatQuotaService:
    def __init__(
        self,
        repository: UserRepository,
        history_repository: ChatHistoryRepository,
        session: AsyncSession,
    ) -> None:
        self.repository = repository
        self.history_repository = history_repository
        self.session = session

    @staticmethod
    def _quota_response(
        usage: int, business_date: date, *, allowed: bool | None = None
    ) -> ChatQuotaResponse:
        return ChatQuotaResponse(
            allowed=usage < settings.chat_daily_limit if allowed is None else allowed,
            remaining=max(0, settings.chat_daily_limit - usage),
            daily_limit=settings.chat_daily_limit,
            resets_at=jakarta_day_end(business_date),
        )

    async def get(self, user: User) -> ChatQuotaResponse:
        today = jakarta_business_date()
        usage = user.chat_usage_count if user.chat_usage_date == today else 0
        return self._quota_response(usage, today)

    async def consume(
        self, user: User, data: ChatQuotaConsumeRequest
    ) -> ChatQuotaConsumeResponse:
        today = jakarta_business_date()
        try:
            locked_user = await self.repository.lock_by_id(user.id)
            if locked_user is None:
                raise RuntimeError("Authenticated user no longer exists")

            existing = await self.history_repository.get_turn_by_client_message_id(
                user.id, today, data.client_message_id
            )
            if existing is not None:
                conversation, messages = existing
                usage = (
                    locked_user.chat_usage_count
                    if locked_user.chat_usage_date == today
                    else 0
                )
                await self.session.commit()
                return ChatQuotaConsumeResponse(
                    conversation_id=conversation.id,
                    messages=[message_response(message) for message in messages],
                    quota=self._quota_response(usage, today, allowed=True),
                )

            usage = await self.repository.consume_chat_quota(
                user.id, today, settings.chat_daily_limit
            )
            if usage is None:
                await self.session.commit()
                raise DailyChatLimitExceededError

            conversation = await self.history_repository.get_conversation(user.id, today)
            if conversation is None:
                conversation = await self.history_repository.create_conversation(
                    user.id, today, jakarta_day_end(today)
                )
            next_sequence = await self.history_repository.next_sequence_number(conversation.id)
            messages = await self.history_repository.create_turn(
                conversation.id,
                next_sequence,
                data.client_message_id,
                data.query,
                data.answer,
            )
            await self.session.commit()
            return ChatQuotaConsumeResponse(
                conversation_id=conversation.id,
                messages=[message_response(message) for message in messages],
                quota=self._quota_response(usage, today, allowed=True),
            )
        except DailyChatLimitExceededError:
            raise
        except Exception:
            await self.session.rollback()
            raise
