import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Portfolio, TradingWindow


class PortfolioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user_id: uuid.UUID, data: Mapping[str, Any]) -> Portfolio:
        portfolio = Portfolio(user_id=user_id, **data)
        self.session.add(portfolio)
        await self.session.flush()
        await self.session.refresh(portfolio)
        return portfolio

    async def list_by_user(self, user_id: uuid.UUID, offset: int, limit: int) -> list[Portfolio]:
        query = (
            select(Portfolio)
            .where(Portfolio.user_id == user_id)
            .order_by(Portfolio.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list((await self.session.scalars(query)).all())

    async def get_by_id_and_user(
        self, portfolio_id: uuid.UUID, user_id: uuid.UUID
    ) -> Portfolio | None:
        query = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        return await self.session.scalar(query)

    async def update(self, portfolio: Portfolio, data: Mapping[str, Any]) -> Portfolio:
        for field_name, value in data.items():
            setattr(portfolio, field_name, value)
        await self.session.flush()
        await self.session.refresh(portfolio)
        return portfolio

    async def delete(self, portfolio: Portfolio) -> None:
        await self.session.delete(portfolio)
        await self.session.flush()

    async def list_distinct_tickers_by_trading_window(
        self, trading_window: TradingWindow
    ) -> list[str]:
        query = (
            select(Portfolio.ticker)
            .where(Portfolio.trading_window == trading_window)
            .distinct()
            .order_by(Portfolio.ticker)
        )
        return list((await self.session.scalars(query)).all())
