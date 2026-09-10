import uuid
from datetime import date

from sqlalchemy import case, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_username(self, username: str) -> User | None:
        return await self.session.scalar(select(User).where(User.username == username))

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def lock_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.scalar(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    async def create(self, username: str, password_hash: str) -> User:
        user = User(username=username, password_hash=password_hash)
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def consume_chat_quota(
        self, user_id: uuid.UUID, usage_date: date, daily_limit: int
    ) -> int | None:
        """Consume one chat atomically, returning today's usage or None when exhausted."""
        is_new_day = or_(User.chat_usage_date.is_(None), User.chat_usage_date != usage_date)
        statement = (
            update(User)
            .where(User.id == user_id)
            .where(or_(is_new_day, User.chat_usage_count < daily_limit))
            .values(
                chat_usage_date=usage_date,
                chat_usage_count=case(
                    (is_new_day, 1),
                    else_=User.chat_usage_count + 1,
                ),
            )
            .returning(User.chat_usage_count)
            .execution_options(synchronize_session=False)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
