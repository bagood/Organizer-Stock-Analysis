import math
from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.config import settings
from app.exceptions import DailyChatLimitExceededError
from app.models.user import User
from app.schemas.chat_quota import ChatQuotaResponse
from app.services.chat_quota_service import ChatQuotaService


class ChatQuotaController:
    def __init__(self, service: ChatQuotaService) -> None:
        self.service = service

    async def get(self, user: User) -> ChatQuotaResponse:
        return await self.service.get(user)

    async def consume(self, user: User) -> ChatQuotaResponse:
        try:
            return await self.service.consume(user)
        except DailyChatLimitExceededError as exc:
            quota = await self.service.get(user)
            retry_after = max(1, math.ceil((quota.resets_at - datetime.now(UTC)).total_seconds()))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Daily chat limit reached",
                    "remaining": 0,
                    "daily_limit": settings.chat_daily_limit,
                    "resets_at": quota.resets_at.isoformat().replace("+00:00", "Z"),
                },
                headers={"Retry-After": str(retry_after)},
            ) from exc
