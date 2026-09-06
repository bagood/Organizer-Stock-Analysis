from fastapi import HTTPException, status

from app.exceptions import InactiveUserError, InvalidCredentialsError, UsernameAlreadyExistsError
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService


class AuthController:
    def __init__(self, service: AuthService) -> None:
        self.service = service

    async def register(self, data: UserCreate) -> User:
        try:
            return await self.service.register(data)
        except UsernameAlreadyExistsError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
            ) from exc

    async def login(self, data: LoginRequest) -> TokenResponse:
        try:
            return await self.service.login(data)
        except InvalidCredentialsError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        except InactiveUserError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive"
            ) from exc
