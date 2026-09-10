from typing import Annotated

from fastapi import APIRouter, Depends

from app.controllers.chat_quota_controller import ChatQuotaController
from app.dependencies.authentication import get_current_user
from app.dependencies.services import get_chat_quota_controller
from app.models.user import User
from app.schemas.chat_quota import (
    ChatQuotaConsumeRequest,
    ChatQuotaConsumeResponse,
    ChatQuotaResponse,
)

router = APIRouter(prefix="/chat-quota", tags=["chat quota"])


@router.get("", response_model=ChatQuotaResponse)
async def get_chat_quota(
    current_user: Annotated[User, Depends(get_current_user)],
    controller: Annotated[ChatQuotaController, Depends(get_chat_quota_controller)],
) -> ChatQuotaResponse:
    """Return the current user's daily chat allowance without consuming it."""
    return await controller.get(current_user)


@router.post("/consume", response_model=ChatQuotaConsumeResponse)
async def consume_chat_quota(
    data: ChatQuotaConsumeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    controller: Annotated[ChatQuotaController, Depends(get_chat_quota_controller)],
) -> ChatQuotaConsumeResponse:
    """Atomically consume quota and persist a completed user/assistant turn."""
    return await controller.consume(current_user, data)
