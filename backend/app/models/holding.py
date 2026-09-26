"""Portfolio holdings schemas.

A holding is simply "I own this company" — the personalization key for the
insights feed. No shares or cost basis: the feed only needs the company link.
"""

from pydantic import BaseModel, Field


class HoldingCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    market: str = Field(default="PH", min_length=2, max_length=4)


class Holding(BaseModel):
    id: int
    company_id: int
    ticker: str
    name: str
    sector: str | None
    currency: str
    market: str
    exchange: str | None = None
