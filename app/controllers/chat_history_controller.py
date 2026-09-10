from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User
from app.schemas.chat_history import ChatHistoryResponse
from app.services.chat_history_service import ChatHistoryService


class ChatHistoryController:
    def __init__(self, service: ChatHistoryService) -> None:
        self.service = service

    async def get(self, user: User) -> ChatHistoryResponse:
        try:
            return await self.service.get(user)
        except SQLAlchemyError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Chat history is temporarily unavailable",
                    "error_code": "CHAT_HISTORY_UNAVAILABLE",
                },
            ) from exc
