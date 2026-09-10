from typing import Annotated

from fastapi import APIRouter, Depends

from app.controllers.chat_history_controller import ChatHistoryController
from app.dependencies.authentication import get_current_user
from app.dependencies.services import get_chat_history_controller
from app.models.user import User
from app.schemas.chat_history import ChatHistoryResponse

router = APIRouter(prefix="/chat-history", tags=["chat history"])


@router.get("", response_model=ChatHistoryResponse)
async def get_chat_history(
    current_user: Annotated[User, Depends(get_current_user)],
    controller: Annotated[ChatHistoryController, Depends(get_chat_history_controller)],
) -> ChatHistoryResponse:
    """Return the authenticated user's conversation for the current Jakarta day."""
    return await controller.get(current_user)
