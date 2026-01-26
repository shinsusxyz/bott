"""
Alert aggregation and batching.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..polymarket.models import PriceAlert, WhaleAlert, ArbitrageAlert, CounterSignalAlert
from ..utils.logger import logger


@dataclass
class AlertBatch:
    """A batch of alerts to be sent together."""
    price_alerts: list[PriceAlert] = field(default_factory=list)
    whale_alerts: list[WhaleAlert] = field(default_factory=list)
    arbitrage_alerts: list[ArbitrageAlert] = field(default_factory=list)
    counter_signals: list[CounterSignalAlert] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_count(self) -> int:
        return (
            len(self.price_alerts)
            + len(self.whale_alerts)
            + len(self.arbitrage_alerts)
            + len(self.counter_signals)
        )

    @property
    def is_empty(self) -> bool:
        return self.total_count == 0


class AlertAggregator:
    """
    Aggregates alerts and batches them for delivery.
    Prevents spam by combining alerts into single messages.
    """

    def __init__(self, batch_interval_seconds: int = 60) -> None:
        self.batch_interval = batch_interval_seconds
        self._pending: dict[int, AlertBatch] = {}  # user_id -> batch
        self._lock = asyncio.Lock()

    async def add_price_alert(self, user_id: int, alert: PriceAlert) -> None:
        """Add a price alert to the pending batch."""
        async with self._lock:
            batch = self._get_or_create_batch(user_id)
            batch.price_alerts.append(alert)

    async def add_whale_alert(self, user_id: int, alert: WhaleAlert) -> None:
        """Add a whale alert to the pending batch."""
        async with self._lock:
            batch = self._get_or_create_batch(user_id)
            batch.whale_alerts.append(alert)

    async def add_arbitrage_alert(self, user_id: int, alert: ArbitrageAlert) -> None:
        """Add an arbitrage alert to the pending batch."""
        async with self._lock:
            batch = self._get_or_create_batch(user_id)
            batch.arbitrage_alerts.append(alert)

    async def add_counter_signal(self, user_id: int, alert: CounterSignalAlert) -> None:
        """Add a counter signal to the pending batch."""
        async with self._lock:
            batch = self._get_or_create_batch(user_id)
            batch.counter_signals.append(alert)

    async def get_ready_batches(self) -> dict[int, AlertBatch]:
        """
        Get batches that are ready to be sent.
        Returns dict of user_id -> batch.
        """
        async with self._lock:
            ready: dict[int, AlertBatch] = {}
            now = datetime.now(timezone.utc)

            for user_id, batch in list(self._pending.items()):
                elapsed = (now - batch.timestamp).total_seconds()

                if elapsed >= self.batch_interval and not batch.is_empty:
                    ready[user_id] = batch
                    del self._pending[user_id]

            return ready

    async def flush_user(self, user_id: int) -> AlertBatch | None:
        """Force flush a user's pending batch."""
        async with self._lock:
            batch = self._pending.pop(user_id, None)
            return batch if batch and not batch.is_empty else None

    async def clear(self) -> None:
        """Clear all pending batches."""
        async with self._lock:
            self._pending.clear()

    def _get_or_create_batch(self, user_id: int) -> AlertBatch:
        """Get or create a batch for a user."""
        if user_id not in self._pending:
            self._pending[user_id] = AlertBatch()
        return self._pending[user_id]

    def get_pending_count(self) -> dict[str, int]:
        """Get count of pending alerts by type."""
        counts = {
            "price": 0,
            "whale": 0,
            "arbitrage": 0,
            "counter_signal": 0,
        }

        for batch in self._pending.values():
            counts["price"] += len(batch.price_alerts)
            counts["whale"] += len(batch.whale_alerts)
            counts["arbitrage"] += len(batch.arbitrage_alerts)
            counts["counter_signal"] += len(batch.counter_signals)

        return counts
