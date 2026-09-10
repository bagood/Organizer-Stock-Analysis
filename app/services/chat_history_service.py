from app.models.user import User
from app.repositories.chat_history_repository import ChatHistoryRepository
from app.schemas.chat_history import ChatConversationResponse, ChatHistoryResponse
from app.services.chat_clock import (
    CHAT_TIMEZONE,
    CHAT_TIMEZONE_NAME,
    jakarta_business_date,
    jakarta_day_end,
)
from app.services.chat_quota_service import ChatQuotaService, message_response


class ChatHistoryService:
    def __init__(
        self,
        repository: ChatHistoryRepository,
        quota_service: ChatQuotaService,
    ) -> None:
        self.repository = repository
        self.quota_service = quota_service

    async def get(self, user: User) -> ChatHistoryResponse:
        today = jakarta_business_date()
        conversation = await self.repository.get_conversation(user.id, today)
        messages = (
            await self.repository.list_messages(conversation.id) if conversation is not None else []
        )
        expires_at = conversation.expires_at if conversation else jakarta_day_end(today)
        return ChatHistoryResponse(
            conversation=ChatConversationResponse(
                id=conversation.id if conversation is not None else None,
                business_date=today,
                timezone=CHAT_TIMEZONE_NAME,
                expires_at=expires_at.astimezone(CHAT_TIMEZONE),
                messages=[message_response(message) for message in messages],
            ),
            quota=await self.quota_service.get(user),
        )
