from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.auth_controller import AuthController
from app.controllers.chat_history_controller import ChatHistoryController
from app.controllers.chat_quota_controller import ChatQuotaController
from app.controllers.portfolio_controller import PortfolioController
from app.database import get_db_session
from app.repositories.chat_history_repository import ChatHistoryRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.chat_history_service import ChatHistoryService
from app.services.chat_quota_service import ChatQuotaService
from app.services.portfolio_service import PortfolioService


def get_auth_controller(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthController:
    repository = UserRepository(session)
    return AuthController(AuthService(repository, session))


def get_chat_quota_controller(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChatQuotaController:
    user_repository = UserRepository(session)
    history_repository = ChatHistoryRepository(session)
    return ChatQuotaController(
        ChatQuotaService(user_repository, history_repository, session)
    )


def get_chat_history_controller(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChatHistoryController:
    user_repository = UserRepository(session)
    history_repository = ChatHistoryRepository(session)
    quota_service = ChatQuotaService(user_repository, history_repository, session)
    return ChatHistoryController(ChatHistoryService(history_repository, quota_service))


def get_portfolio_controller(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PortfolioController:
    repository = PortfolioRepository(session)
    return PortfolioController(PortfolioService(repository, session))
