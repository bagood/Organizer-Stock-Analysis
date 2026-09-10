import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.chat_quota import ChatMessageResponse, ChatQuotaResponse


class ChatConversationResponse(BaseModel):
    id: uuid.UUID | None
    business_date: date
    timezone: str
    expires_at: datetime
    messages: list[ChatMessageResponse]


class ChatHistoryResponse(BaseModel):
    conversation: ChatConversationResponse
    quota: ChatQuotaResponse
