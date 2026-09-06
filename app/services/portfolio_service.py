import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DuplicateTickerError, PortfolioNotFoundError
from app.models.portfolio import Portfolio
from app.models.user import User
from app.repositories.portfolio_repository import PortfolioRepository
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate


class PortfolioService:
    def __init__(self, repository: PortfolioRepository, session: AsyncSession) -> None:
        self.repository = repository
        self.session = session

    async def create(self, user: User, data: PortfolioCreate) -> Portfolio:
        try:
            portfolio = await self.repository.create(user.id, data.model_dump())
            await self.session.commit()
            return portfolio
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateTickerError from exc

    async def list(self, user: User, offset: int, limit: int) -> list[Portfolio]:
        return await self.repository.list_by_user(user.id, offset, limit)

    async def get(self, user: User, portfolio_id: uuid.UUID) -> Portfolio:
        portfolio = await self.repository.get_by_id_and_user(portfolio_id, user.id)
        if portfolio is None:
            raise PortfolioNotFoundError
        return portfolio

    async def update(self, user: User, portfolio_id: uuid.UUID, data: PortfolioUpdate) -> Portfolio:
        portfolio = await self.get(user, portfolio_id)
        try:
            updated = await self.repository.update(portfolio, data.model_dump(exclude_unset=True))
            await self.session.commit()
            return updated
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateTickerError from exc

    async def delete(self, user: User, portfolio_id: uuid.UUID) -> None:
        portfolio = await self.get(user, portfolio_id)
        await self.repository.delete(portfolio)
        await self.session.commit()
