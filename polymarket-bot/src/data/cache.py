"""
In-memory cache for deduplication and temporary data.
"""

import time
from dataclasses import dataclass, field
from typing import Any

from ..utils.config import DEFAULT_ALERT_COOLDOWN


@dataclass
class CacheEntry:
    """Entry in the cache with TTL."""
    value: Any
    expires_at: float


@dataclass
class AlertCache:
    """
    In-memory cache for tracking recently sent alerts.
    Prevents duplicate alerts within the cooldown period.
    """

    cooldown_seconds: float = field(default_factory=lambda: DEFAULT_ALERT_COOLDOWN * 60)
    _cache: dict[str, CacheEntry] = field(default_factory=dict)
    _last_cleanup: float = field(default_factory=time.time)

    def _key(self, market_id: str, outcome: str, alert_type: str = "price") -> str:
        """Generate cache key."""
        return f"{alert_type}:{market_id}:{outcome}"

    def was_recently_alerted(
        self,
        market_id: str,
        outcome: str,
        alert_type: str = "price",
    ) -> bool:
        """Check if an alert was recently sent."""
        self._maybe_cleanup()

        key = self._key(market_id, outcome, alert_type)
        entry = self._cache.get(key)

        if entry is None:
            return False

        if time.time() >= entry.expires_at:
            del self._cache[key]
            return False

        return True

    def record_alert(
        self,
        market_id: str,
        outcome: str,
        alert_type: str = "price",
        data: Any = None,
    ) -> None:
        """Record that an alert was sent."""
        key = self._key(market_id, outcome, alert_type)
        self._cache[key] = CacheEntry(
            value=data,
            expires_at=time.time() + self.cooldown_seconds,
        )

    def get_time_until_can_alert(
        self,
        market_id: str,
        outcome: str,
        alert_type: str = "price",
    ) -> float:
        """Get remaining cooldown time in seconds."""
        key = self._key(market_id, outcome, alert_type)
        entry = self._cache.get(key)

        if entry is None:
            return 0.0

        remaining = entry.expires_at - time.time()
        return max(0.0, remaining)

    def clear(self) -> None:
        """Clear all entries."""
        self._cache.clear()

    def size(self) -> int:
        """Get number of entries."""
        return len(self._cache)

    def _maybe_cleanup(self) -> None:
        """Periodically remove expired entries."""
        now = time.time()

        if now - self._last_cleanup < 300:
            return

        self._last_cleanup = now
        expired = [k for k, v in self._cache.items() if now >= v.expires_at]

        for key in expired:
            del self._cache[key]


@dataclass
class PriceCache:
    """Cache for recent price data."""

    _prices: dict[str, CacheEntry] = field(default_factory=dict)
    ttl_seconds: float = 300  # 5 minutes

    def get(self, token_id: str) -> float | None:
        """Get cached price if not expired."""
        entry = self._prices.get(token_id)

        if entry is None:
            return None

        if time.time() >= entry.expires_at:
            del self._prices[token_id]
            return None

        return entry.value

    def set(self, token_id: str, price: float) -> None:
        """Cache a price."""
        self._prices[token_id] = CacheEntry(
            value=price,
            expires_at=time.time() + self.ttl_seconds,
        )

    def set_many(self, prices: dict[str, float]) -> None:
        """Cache multiple prices."""
        expires_at = time.time() + self.ttl_seconds
        for token_id, price in prices.items():
            self._prices[token_id] = CacheEntry(value=price, expires_at=expires_at)

    def clear(self) -> None:
        """Clear all cached prices."""
        self._prices.clear()


@dataclass
class MarketCache:
    """Cache for market data."""

    _markets: dict[str, CacheEntry] = field(default_factory=dict)
    ttl_seconds: float = 60  # 1 minute

    def get(self, market_id: str) -> Any | None:
        """Get cached market if not expired."""
        entry = self._markets.get(market_id)

        if entry is None:
            return None

        if time.time() >= entry.expires_at:
            del self._markets[market_id]
            return None

        return entry.value

    def set(self, market_id: str, market: Any) -> None:
        """Cache a market."""
        self._markets[market_id] = CacheEntry(
            value=market,
            expires_at=time.time() + self.ttl_seconds,
        )

    def get_all(self) -> list[Any]:
        """Get all non-expired cached markets."""
        now = time.time()
        return [
            entry.value
            for entry in self._markets.values()
            if now < entry.expires_at
        ]

    def clear(self) -> None:
        """Clear all cached markets."""
        self._markets.clear()
