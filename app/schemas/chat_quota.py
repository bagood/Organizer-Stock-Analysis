import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatQuotaResponse(BaseModel):
    allowed: bool
    remaining: int = Field(ge=0)
    daily_limit: int = Field(gt=0)
    resets_at: datetime


class ChatQuotaConsumeRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10_000)
    answer: str = Field(min_length=1, max_length=100_000)
    client_message_id: uuid.UUID

    @field_validator("query", "answer")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    client_message_id: uuid.UUID | None
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ChatQuotaConsumeResponse(BaseModel):
    conversation_id: uuid.UUID
    messages: list[ChatMessageResponse]
    quota: ChatQuotaResponse
