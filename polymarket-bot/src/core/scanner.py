"""
Main scanning loop for monitoring markets.
"""

import asyncio
import time
from typing import Any

from ..polymarket.gamma_client import GammaClient
from ..polymarket.clob_client import CLOBClient
from ..polymarket.data_client import DataClient
from ..polymarket.models import Market, PriceAlert, WhaleAlert, ArbitrageAlert, Trade
from ..data.cache import AlertCache, PriceCache, MarketCache
from ..data.database import Database
from ..utils.logger import logger
from .filters import filter_market, check_arbitrage, detect_category


class MarketScanner:
    """Scans markets for low odds and other alerts."""

    def __init__(
        self,
        gamma: GammaClient,
        clob: CLOBClient,
        data_client: DataClient,
        database: Database,
    ) -> None:
        self.gamma = gamma
        self.clob = clob
        self.data_client = data_client
        self.db = database

        self.alert_cache = AlertCache()
        self.price_cache = PriceCache()
        self.market_cache = MarketCache()

        self._stats = {
            "total_scans": 0,
            "markets_scanned": 0,
            "alerts_generated": 0,
            "last_scan_ms": 0,
        }

    async def scan_markets(
        self,
        user_id: int,
        settings: dict[str, Any],
    ) -> list[PriceAlert | ArbitrageAlert]:
        """
        Scan all markets for alerts based on user settings.

        Returns list of alerts to send.
        """
        start = time.time()
        alerts: list[PriceAlert | ArbitrageAlert] = []

        try:
            # Fetch markets
            markets = await self.gamma.get_all_active_markets()
            self._stats["markets_scanned"] = len(markets)

            if not markets:
                logger.warning("No markets fetched")
                return alerts

            # Get muted markets
            muted = set(await self.db.get_muted_markets(user_id))

            # Get user settings
            price_threshold = settings.get("price_threshold", 0.01)
            min_volume = settings.get("min_volume", 1000)
            min_liquidity = settings.get("min_liquidity", 5000)
            max_spread = settings.get("max_spread", 0.03)
            categories = settings.get("categories", ["politics", "weather", "tech", "ai"])
            check_arb = settings.get("arbitrage_alerts", True)

            for market in markets:
                # Skip muted
                if market.id in muted:
                    continue

                # Check for arbitrage
                if check_arb:
                    arb = check_arbitrage(market)
                    if arb and not self.alert_cache.was_recently_alerted(
                        market.id, "arbitrage", "arbitrage"
                    ):
                        yes_price, no_price, total = arb
                        alerts.append(ArbitrageAlert(
                            market=market,
                            yes_price=yes_price,
                            no_price=no_price,
                            total=total,
                        ))
                        self.alert_cache.record_alert(market.id, "arbitrage", "arbitrage")

                # Apply filters
                passed, reason, category = filter_market(
                    market,
                    price_threshold=price_threshold,
                    min_volume=min_volume,
                    min_liquidity=min_liquidity,
                    max_spread=max_spread,
                    enabled_categories=categories,
                )

                if not passed:
                    continue

                # Generate alerts for low odds outcomes
                for outcome in market.get_outcomes():
                    if outcome.price <= 0 or outcome.price > price_threshold:
                        continue

                    # Check dedup
                    if self.alert_cache.was_recently_alerted(market.id, outcome.name):
                        continue

                    # Get historical prices
                    price_1h = await self._get_price_n_hours_ago(market.id, outcome.token_id, 1)
                    price_24h = await self._get_price_n_hours_ago(market.id, outcome.token_id, 24)

                    alerts.append(PriceAlert(
                        market=market,
                        outcome=outcome,
                        category=category or "Unknown",
                        price_1h_ago=price_1h,
                        price_24h_ago=price_24h,
                    ))

                    self.alert_cache.record_alert(market.id, outcome.name)

            self._stats["alerts_generated"] += len(alerts)
            self._stats["total_scans"] += 1

        except Exception as e:
            logger.error(f"Error during market scan: {e}")
        finally:
            self._stats["last_scan_ms"] = int((time.time() - start) * 1000)
            logger.info(
                f"Scan complete: {self._stats['markets_scanned']} markets, "
                f"{len(alerts)} alerts, {self._stats['last_scan_ms']}ms"
            )

        return alerts

    async def _get_price_n_hours_ago(
        self, market_id: str, token_id: str, hours: int
    ) -> float | None:
        """Get historical price from database."""
        if not token_id:
            return None

        history = await self.db.get_price_history(market_id, hours)
        if history:
            return history[-1].get("price")
        return None

    async def record_current_prices(self, markets: list[Market]) -> None:
        """Record current prices for history."""
        for market in markets:
            for outcome in market.get_outcomes():
                if outcome.token_id and outcome.price > 0:
                    await self.db.record_price(
                        market.id, outcome.token_id, outcome.price
                    )

    def get_stats(self) -> dict[str, Any]:
        """Get scanner statistics."""
        return {
            **self._stats,
            "cache_size": self.alert_cache.size(),
        }


class WhaleScanner:
    """Scans for whale trades."""

    def __init__(
        self,
        data_client: DataClient,
        gamma: GammaClient,
        database: Database,
    ) -> None:
        self.data_client = data_client
        self.gamma = gamma
        self.db = database
        self.alert_cache = AlertCache()
        self._last_seen_trades: set[str] = set()

    async def scan_whale_trades(
        self,
        user_id: int,
        settings: dict[str, Any],
    ) -> list[WhaleAlert]:
        """Scan for whale trades above threshold."""
        if not settings.get("whale_alerts_enabled", True):
            return []

        alerts: list[WhaleAlert] = []
        threshold = settings.get("whale_threshold", 30)
        smart_only = settings.get("smart_money_only", False)

        try:
            # Get recent trades
            trades = await self.data_client.get_recent_trades(limit=100)

            for trade in trades:
                # Skip already seen
                if trade.id in self._last_seen_trades:
                    continue

                # Check threshold (USD amount)
                if trade.usdc_size < threshold:
                    continue

                # Check dedup
                cache_key = f"{trade.trader_address}:{trade.slug}:{trade.outcome}"
                if self.alert_cache.was_recently_alerted(cache_key, "whale", "whale"):
                    continue

                # Get trader profile and stats
                profile = await self.gamma.get_public_profile(trade.trader_address)
                stats_dict = await self.data_client.calculate_trader_stats(trade.trader_address)

                from ..polymarket.models import TraderStats, TraderProfile
                stats = TraderStats.model_validate(stats_dict)

                # Filter smart money only
                if smart_only and not stats.is_smart_money:
                    continue

                # Get market for URL
                market = await self.gamma.get_market_by_slug(trade.slug) if trade.slug else None

                alerts.append(WhaleAlert(
                    trade=trade,
                    trader_profile=profile,
                    trader_stats=stats,
                    market=market,
                ))

                self.alert_cache.record_alert(cache_key, "whale", "whale")
                self._last_seen_trades.add(trade.id)

            # Limit memory usage
            if len(self._last_seen_trades) > 10000:
                self._last_seen_trades = set(list(self._last_seen_trades)[-5000:])

        except Exception as e:
            logger.error(f"Error scanning whale trades: {e}")

        return alerts
