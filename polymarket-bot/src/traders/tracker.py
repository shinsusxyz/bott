"""
Whale trade monitoring.
"""

from typing import Any

from ..polymarket.data_client import DataClient
from ..polymarket.gamma_client import GammaClient
from ..polymarket.models import Trade, WhaleAlert
from ..data.database import Database
from ..data.cache import AlertCache
from ..utils.logger import logger
from .profiler import TraderProfiler


class WhaleTracker:
    """Monitors for whale trades and tracked traders."""

    def __init__(
        self,
        data_client: DataClient,
        gamma: GammaClient,
        database: Database,
    ) -> None:
        self.data_client = data_client
        self.gamma = gamma
        self.db = database
        self.profiler = TraderProfiler(gamma, data_client)
        self.alert_cache = AlertCache()
        self._seen_trade_ids: set[str] = set()

    async def check_whale_trades(
        self,
        user_id: int,
        whale_threshold: float = 30,
        smart_money_only: bool = False,
    ) -> list[WhaleAlert]:
        """
        Check for new whale trades.

        Args:
            user_id: User to check for
            whale_threshold: Minimum USD amount
            smart_money_only: Only alert for smart money traders

        Returns:
            List of WhaleAlert objects
        """
        alerts: list[WhaleAlert] = []

        try:
            # Get tracked traders for this user
            tracked = await self.db.get_tracked_traders(user_id)
            tracked_addresses = {t["trader_address"].lower() for t in tracked}

            # Get recent trades
            trades = await self.data_client.get_recent_trades(limit=100)

            for trade in trades:
                if not self._should_alert(trade, whale_threshold, tracked_addresses):
                    continue

                # Check dedup
                key = f"{trade.trader_address}:{trade.slug}:{trade.timestamp}"
                if self.alert_cache.was_recently_alerted(key, "trade", "whale"):
                    continue

                # Get profile and stats
                profile, stats = await self.profiler.get_full_profile(trade.trader_address)

                # Filter smart money only
                if smart_money_only and not self.profiler.is_smart_money(stats):
                    continue

                # Get market for full details
                market = None
                if trade.slug:
                    market = await self.gamma.get_market_by_slug(trade.slug)

                alerts.append(WhaleAlert(
                    trade=trade,
                    trader_profile=profile,
                    trader_stats=stats,
                    market=market,
                ))

                self.alert_cache.record_alert(key, "trade", "whale")
                self._seen_trade_ids.add(trade.id)

            # Limit memory
            if len(self._seen_trade_ids) > 10000:
                self._seen_trade_ids = set(list(self._seen_trade_ids)[-5000:])

        except Exception as e:
            logger.error(f"Error checking whale trades: {e}")

        return alerts

    def _should_alert(
        self,
        trade: Trade,
        threshold: float,
        tracked_addresses: set[str],
    ) -> bool:
        """Check if a trade should trigger an alert."""
        # Already seen
        if trade.id in self._seen_trade_ids:
            return False

        # Above threshold
        if trade.usdc_size >= threshold:
            return True

        # From tracked trader (any amount)
        if trade.trader_address.lower() in tracked_addresses:
            return True

        return False

    async def get_trader_activity(
        self,
        address: str,
        limit: int = 20,
    ) -> list[Trade]:
        """Get recent activity for a specific trader."""
        return await self.data_client.get_user_activity(address, limit=limit)
