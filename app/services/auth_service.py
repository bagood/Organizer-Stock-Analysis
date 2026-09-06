from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import InactiveUserError, InvalidCredentialsError, UsernameAlreadyExistsError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate
from app.security.passwords import hash_password, verify_password
from app.security.tokens import create_access_token


class AuthService:
    def __init__(self, repository: UserRepository, session: AsyncSession) -> None:
        self.repository = repository
        self.session = session

    async def register(self, data: UserCreate) -> User:
        if await self.repository.get_by_username(data.username):
            raise UsernameAlreadyExistsError
        try:
            user = await self.repository.create(data.username, hash_password(data.password))
            await self.session.commit()
            return user
        except IntegrityError as exc:
            await self.session.rollback()
            raise UsernameAlreadyExistsError from exc

    async def login(self, data: LoginRequest) -> TokenResponse:
        user = await self.repository.get_by_username(data.username)
        if user is None or not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsError
        if not user.is_active:
            raise InactiveUserError
        return TokenResponse(
            access_token=create_access_token(user.id),
            expires_in=settings.access_token_expire_minutes * 60,
        )
