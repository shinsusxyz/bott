"""
Alert deduplication cache with TTL support.
Uses simple in-memory dict with timestamps for speed.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import NamedTuple

from .config import ALERT_COOLDOWN_MINUTES

logger = logging.getLogger(__name__)


class CacheKey(NamedTuple):
    """Unique identifier for a market alert."""
    market_id: str
    outcome_name: str


@dataclass
class CacheEntry:
    """Entry in the alert cache."""
    key: CacheKey
    alerted_at: float
    price_at_alert: float


@dataclass
class AlertCache:
    """
    In-memory cache for tracking recently alerted markets.
    Prevents duplicate alerts for the same market within the cooldown period.
    """

    cooldown_seconds: float = field(default_factory=lambda: ALERT_COOLDOWN_MINUTES * 60)
    _cache: dict[CacheKey, CacheEntry] = field(default_factory=dict)
    _last_cleanup: float = field(default_factory=time.time)
    _cleanup_interval: float = 300.0  # Clean up every 5 minutes

    def was_recently_alerted(self, market_id: str, outcome_name: str) -> bool:
        """
        Check if an alert was recently sent for this market/outcome.

        Args:
            market_id: The market ID
            outcome_name: The outcome name (e.g., "Yes", "No")

        Returns:
            True if an alert was sent within the cooldown period
        """
        self._maybe_cleanup()

        key = CacheKey(market_id=market_id, outcome_name=outcome_name)
        entry = self._cache.get(key)

        if entry is None:
            return False

        # Check if the cooldown has expired
        elapsed = time.time() - entry.alerted_at
        if elapsed >= self.cooldown_seconds:
            # Cooldown expired, remove entry
            del self._cache[key]
            return False

        return True

    def record_alert(self, market_id: str, outcome_name: str, price: float) -> None:
        """
        Record that an alert was sent for a market/outcome.

        Args:
            market_id: The market ID
            outcome_name: The outcome name
            price: The price at the time of alert
        """
        key = CacheKey(market_id=market_id, outcome_name=outcome_name)
        self._cache[key] = CacheEntry(
            key=key,
            alerted_at=time.time(),
            price_at_alert=price
        )
        logger.debug(f"Recorded alert for {market_id}:{outcome_name} at price {price}")

    def get_last_alert_time(self, market_id: str, outcome_name: str) -> float | None:
        """
        Get the timestamp of the last alert for a market/outcome.

        Args:
            market_id: The market ID
            outcome_name: The outcome name

        Returns:
            Timestamp of last alert, or None if never alerted
        """
        key = CacheKey(market_id=market_id, outcome_name=outcome_name)
        entry = self._cache.get(key)
        return entry.alerted_at if entry else None

    def get_time_until_can_alert(self, market_id: str, outcome_name: str) -> float:
        """
        Get remaining cooldown time in seconds.

        Args:
            market_id: The market ID
            outcome_name: The outcome name

        Returns:
            Seconds until can alert again (0 if ready)
        """
        key = CacheKey(market_id=market_id, outcome_name=outcome_name)
        entry = self._cache.get(key)

        if entry is None:
            return 0.0

        elapsed = time.time() - entry.alerted_at
        remaining = self.cooldown_seconds - elapsed

        return max(0.0, remaining)

    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._cache.clear()
        logger.info("Alert cache cleared")

    def size(self) -> int:
        """Get the number of entries in the cache."""
        return len(self._cache)

    def _maybe_cleanup(self) -> None:
        """Periodically clean up expired entries to prevent memory growth."""
        now = time.time()

        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        expired_keys: list[CacheKey] = []

        for key, entry in self._cache.items():
            if now - entry.alerted_at >= self.cooldown_seconds:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def get_stats(self) -> dict[str, int | float]:
        """
        Get cache statistics.

        Returns:
            Dict with cache statistics
        """
        now = time.time()
        active_count = 0
        expired_count = 0

        for entry in self._cache.values():
            if now - entry.alerted_at < self.cooldown_seconds:
                active_count += 1
            else:
                expired_count += 1

        return {
            "total_entries": len(self._cache),
            "active_entries": active_count,
            "expired_entries": expired_count,
            "cooldown_seconds": self.cooldown_seconds,
        }
