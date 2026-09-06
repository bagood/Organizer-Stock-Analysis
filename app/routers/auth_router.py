from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.controllers.auth_controller import AuthController
from app.dependencies.authentication import get_current_user
from app.dependencies.services import get_auth_controller
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    controller: Annotated[AuthController, Depends(get_auth_controller)],
) -> User:
    return await controller.register(data)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    controller: Annotated[AuthController, Depends(get_auth_controller)],
) -> TokenResponse:
    return await controller.login(data)


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
