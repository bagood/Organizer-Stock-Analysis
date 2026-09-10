import math
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.exceptions import DailyChatLimitExceededError
from app.models.user import User
from app.schemas.chat_quota import (
    ChatQuotaConsumeRequest,
    ChatQuotaConsumeResponse,
    ChatQuotaResponse,
)
from app.services.chat_quota_service import ChatQuotaService


class ChatQuotaController:
    def __init__(self, service: ChatQuotaService) -> None:
        self.service = service

    async def get(self, user: User) -> ChatQuotaResponse:
        return await self.service.get(user)

    async def consume(
        self, user: User, data: ChatQuotaConsumeRequest
    ) -> ChatQuotaConsumeResponse:
        try:
            return await self.service.consume(user, data)
        except DailyChatLimitExceededError as exc:
            quota = await self.service.get(user)
            retry_after = max(
                1,
                math.ceil(
                    (quota.resets_at - datetime.now(quota.resets_at.tzinfo)).total_seconds()
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Daily chat limit reached",
                    "remaining": 0,
                    "daily_limit": settings.chat_daily_limit,
                    "resets_at": quota.resets_at.isoformat(),
                },
                headers={"Retry-After": str(retry_after)},
            ) from exc
        except (SQLAlchemyError, RuntimeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Chat history is temporarily unavailable",
                    "error_code": "CHAT_HISTORY_UNAVAILABLE",
                },
            ) from exc
