import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.controllers.portfolio_controller import PortfolioController
from app.dependencies.authentication import get_current_user
from app.dependencies.services import get_portfolio_controller
from app.models.user import User
from app.schemas.portfolio import (
    PortfolioCreate,
    PortfolioResponse,
    PortfolioUpdate,
    PublicTradingWindow,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])
public_router = APIRouter(prefix="/stocks", tags=["public stocks"])


def response(portfolio, username: str) -> PortfolioResponse:
    return PortfolioResponse.model_validate(
        {
            "id": portfolio.id,
            "ticker": portfolio.ticker,
            "price": portfolio.price,
            "trading_window": portfolio.trading_window,
            "username": username,
            "created_at": portfolio.created_at,
            "updated_at": portfolio.updated_at,
        }
    )


@public_router.get("", response_model=list[str])
async def list_public_stocks(
    trading_window: PublicTradingWindow,
    controller: Annotated[PortfolioController, Depends(get_portfolio_controller)],
) -> list[str]:
    """List unique stocks for a window without requiring authentication."""
    return await controller.list_public_stocks(trading_window)


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    data: PortfolioCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    controller: Annotated[PortfolioController, Depends(get_portfolio_controller)],
) -> PortfolioResponse:
    return response(await controller.create(current_user, data), current_user.username)


@router.get("", response_model=list[PortfolioResponse])
async def list_portfolios(
    current_user: Annotated[User, Depends(get_current_user)],
    controller: Annotated[PortfolioController, Depends(get_portfolio_controller)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[PortfolioResponse]:
    items = await controller.list(current_user, offset, limit)
    return [response(item, current_user.username) for item in items]


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    controller: Annotated[PortfolioController, Depends(get_portfolio_controller)],
) -> PortfolioResponse:
    return response(await controller.retrieve(current_user, portfolio_id), current_user.username)


@router.patch("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: uuid.UUID,
    data: PortfolioUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    controller: Annotated[PortfolioController, Depends(get_portfolio_controller)],
) -> PortfolioResponse:
    return response(
        await controller.update(current_user, portfolio_id, data), current_user.username
    )


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    controller: Annotated[PortfolioController, Depends(get_portfolio_controller)],
) -> Response:
    await controller.delete(current_user, portfolio_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
