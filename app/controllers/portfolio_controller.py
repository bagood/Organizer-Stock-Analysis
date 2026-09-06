from __future__ import annotations

import uuid

from fastapi import HTTPException, status

from app.exceptions import DuplicateTickerError, PortfolioNotFoundError
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate, PublicTradingWindow
from app.services.portfolio_service import PortfolioService


class PortfolioController:
    def __init__(self, service: PortfolioService) -> None:
        self.service = service

    async def create(self, user: User, data: PortfolioCreate) -> Portfolio:
        try:
            return await self.service.create(user, data)
        except DuplicateTickerError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This ticker already exists in your portfolio",
            ) from exc

    async def list(self, user: User, offset: int, limit: int) -> list[Portfolio]:
        return await self.service.list(user, offset, limit)

    async def retrieve(self, user: User, portfolio_id: uuid.UUID) -> Portfolio:
        try:
            return await self.service.get(user, portfolio_id)
        except PortfolioNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
            ) from exc

    async def update(self, user: User, portfolio_id: uuid.UUID, data: PortfolioUpdate) -> Portfolio:
        try:
            return await self.service.update(user, portfolio_id, data)
        except PortfolioNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
            ) from exc
        except DuplicateTickerError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This ticker already exists in your portfolio",
            ) from exc

    async def delete(self, user: User, portfolio_id: uuid.UUID) -> None:
        try:
            await self.service.delete(user, portfolio_id)
        except PortfolioNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
            ) from exc

    async def list_public_stocks(self, trading_window: PublicTradingWindow) -> list[str]:
        return await self.service.list_public_stocks(trading_window)
