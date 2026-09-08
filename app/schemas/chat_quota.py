from datetime import datetime

from pydantic import BaseModel, Field


class ChatQuotaResponse(BaseModel):
    allowed: bool
    remaining: int = Field(ge=0)
    daily_limit: int = Field(gt=0)
    resets_at: datetime
