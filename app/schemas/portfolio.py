import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.portfolio import TradingWindow


class PublicTradingWindow(StrEnum):
    FIVE_DD = "5dd"
    TEN_DD = "10dd"

    def to_portfolio_window(self) -> TradingWindow:
        return {
            self.FIVE_DD: TradingWindow.FIVE_TO_TEN_DD,
            self.TEN_DD: TradingWindow.TEN_TO_TWENTY_DD,
        }[self]


class PortfolioFields(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    price: Decimal = Field(ge=0, max_digits=18, decimal_places=4)
    trading_window: TradingWindow

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("ticker cannot be blank")
        return normalized


class PortfolioCreate(PortfolioFields):
    pass


class PortfolioUpdate(BaseModel):
    ticker: str | None = Field(default=None, min_length=1, max_length=20)
    price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=4)
    trading_window: TradingWindow | None = None

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("ticker cannot be blank")
        return normalized

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> "PortfolioUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class PortfolioResponse(PortfolioFields):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    created_at: datetime
    updated_at: datetime
