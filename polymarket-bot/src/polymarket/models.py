"""
Pydantic models for Polymarket data structures.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator
import json


class Outcome(BaseModel):
    """Represents a market outcome with its price."""
    name: str
    token_id: str = ""
    price: float = 0.0


class Market(BaseModel):
    """Represents a Polymarket market."""
    id: str = ""
    slug: str = ""
    question: str = ""
    description: str = ""
    condition_id: str = Field(default="", alias="conditionId")
    event_slug: str = Field(default="", alias="eventSlug")
    outcomes: list[str] = []
    outcome_prices: list[float] = Field(default=[], alias="outcomePrices")
    clob_token_ids: list[str] = Field(default=[], alias="clobTokenIds")
    volume: float = 0.0
    volume_24hr: float = Field(default=0.0, alias="volume24hr")
    liquidity: float = 0.0
    best_bid: float = Field(default=0.0, alias="bestBid")
    best_ask: float = Field(default=0.0, alias="bestAsk")
    spread: float = 0.0
    active: bool = True
    closed: bool = False
    archived: bool = False
    resolved: bool = False
    end_date: datetime | None = Field(default=None, alias="endDate")
    tags: list[str] = []

    model_config = {"populate_by_name": True}

    @field_validator("outcome_prices", "clob_token_ids", mode="before")
    @classmethod
    def parse_json_list(cls, v: Any) -> list:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v if v else []

    @field_validator("outcome_prices", mode="after")
    @classmethod
    def convert_prices_to_float(cls, v: list) -> list[float]:
        return [float(p) for p in v]

    @field_validator("end_date", mode="before")
    @classmethod
    def parse_end_date(cls, v: Any) -> datetime | None:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    @property
    def is_tradeable(self) -> bool:
        return self.active and not self.closed and not self.archived and not self.resolved

    @property
    def url(self) -> str:
        if self.event_slug and self.slug:
            return f"https://polymarket.com/event/{self.event_slug}/{self.slug}"
        elif self.event_slug:
            return f"https://polymarket.com/event/{self.event_slug}"
        return ""

    def get_outcomes(self) -> list[Outcome]:
        """Get structured outcome objects."""
        result = []
        for i, name in enumerate(self.outcomes):
            token_id = self.clob_token_ids[i] if i < len(self.clob_token_ids) else ""
            price = self.outcome_prices[i] if i < len(self.outcome_prices) else 0.0
            result.append(Outcome(name=name, token_id=token_id, price=price))
        return result


class Event(BaseModel):
    """Represents a Polymarket event (group of markets)."""
    id: str = ""
    slug: str = ""
    title: str = ""
    description: str = ""
    markets: list[Market] = []
    volume: float = 0.0
    liquidity: float = 0.0
    active: bool = True
    closed: bool = False

    model_config = {"populate_by_name": True}

    @property
    def url(self) -> str:
        return f"https://polymarket.com/event/{self.slug}" if self.slug else ""


class TraderProfile(BaseModel):
    """Represents a trader's public profile."""
    address: str = Field(default="", alias="proxyWallet")
    name: str | None = None
    pseudonym: str | None = None
    bio: str | None = None
    profile_image: str | None = Field(default=None, alias="profileImage")
    x_username: str | None = Field(default=None, alias="xUsername")
    verified_badge: bool = Field(default=False, alias="verifiedBadge")

    model_config = {"populate_by_name": True}

    @property
    def display_name(self) -> str:
        return self.name or self.pseudonym or self.address[:10] + "..."

    @property
    def url(self) -> str:
        return f"https://polymarket.com/profile/{self.address}" if self.address else ""


class TraderStats(BaseModel):
    """Trader statistics from portfolio analysis."""
    address: str = ""
    total_trades: int = 0
    win_rate: float = 0.0
    portfolio_value: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    @property
    def is_smart_money(self) -> bool:
        return (
            (self.total_trades >= 20 and self.win_rate >= 0.65)
            or self.portfolio_value >= 50000
        )


class Trade(BaseModel):
    """Represents a single trade."""
    id: str = ""
    trader_address: str = Field(default="", alias="proxyWallet")
    market_title: str = Field(default="", alias="title")
    slug: str = ""
    event_slug: str = Field(default="", alias="eventSlug")
    outcome: str = ""
    side: str = ""  # BUY or SELL
    size: float = 0.0  # shares
    usdc_size: float = Field(default=0.0, alias="usdcSize")  # USD amount
    price: float = 0.0
    timestamp: datetime | None = None
    transaction_hash: str = Field(default="", alias="transactionHash")
    trader_name: str | None = Field(default=None, alias="name")
    trader_pseudonym: str | None = Field(default=None, alias="pseudonym")
    trader_image: str | None = Field(default=None, alias="profileImage")

    model_config = {"populate_by_name": True}

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime | None:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v)
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    @property
    def market_url(self) -> str:
        if self.event_slug and self.slug:
            return f"https://polymarket.com/event/{self.event_slug}/{self.slug}"
        elif self.event_slug:
            return f"https://polymarket.com/event/{self.event_slug}"
        return ""

    @property
    def trader_url(self) -> str:
        return f"https://polymarket.com/profile/{self.trader_address}" if self.trader_address else ""


class Position(BaseModel):
    """Represents a user's position in a market."""
    market_title: str = Field(default="", alias="title")
    slug: str = ""
    event_slug: str = Field(default="", alias="eventSlug")
    outcome: str = ""
    size: float = 0.0
    avg_price: float = Field(default=0.0, alias="avgPrice")
    initial_value: float = Field(default=0.0, alias="initialValue")
    current_value: float = Field(default=0.0, alias="currentValue")
    cash_pnl: float = Field(default=0.0, alias="cashPnl")
    percent_pnl: float = Field(default=0.0, alias="percentPnl")
    realized_pnl: float = Field(default=0.0, alias="realizedPnl")

    model_config = {"populate_by_name": True}


class PriceAlert(BaseModel):
    """Alert for low odds detection."""
    market: Market
    outcome: Outcome
    category: str = "Unknown"
    price_1h_ago: float | None = None
    price_24h_ago: float | None = None

    @property
    def price_change_1h(self) -> float | None:
        if self.price_1h_ago and self.price_1h_ago > 0:
            return ((self.outcome.price - self.price_1h_ago) / self.price_1h_ago) * 100
        return None

    @property
    def price_change_24h(self) -> float | None:
        if self.price_24h_ago and self.price_24h_ago > 0:
            return ((self.outcome.price - self.price_24h_ago) / self.price_24h_ago) * 100
        return None


class WhaleAlert(BaseModel):
    """Alert for whale trades."""
    trade: Trade
    trader_profile: TraderProfile | None = None
    trader_stats: TraderStats | None = None
    market: Market | None = None

    @property
    def is_smart_money(self) -> bool:
        return self.trader_stats.is_smart_money if self.trader_stats else False


class ArbitrageAlert(BaseModel):
    """Alert for arbitrage opportunities."""
    market: Market
    yes_price: float
    no_price: float
    total: float

    @property
    def potential_profit_percent(self) -> float:
        return (self.total - 1) * 100


class CounterSignalAlert(BaseModel):
    """Alert when whale bets against low-odds outcome."""
    market: Market
    trade: Trade
    low_odds_outcome: str
    low_odds_price: float
    trader_stats: TraderStats | None = None
