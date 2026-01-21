#!/usr/bin/env python3
"""
Polymarket Low Odds Alert Bot

Monitors Polymarket for markets where any outcome has odds ≤ 0.1% (≤ $0.001)
and sends instant alerts via Telegram.
"""

import asyncio
import logging
import signal
import sys
import time
from typing import Any

from .alert_cache import AlertCache
from .config import (
    SCAN_INTERVAL_SECONDS,
    PRICE_THRESHOLD,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from .filters import filter_markets, FilterResult
from .polymarket_client import PolymarketClient, Market
from .telegram_bot import TelegramAlertBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class PolymarketAlertBot:
    """Main bot class orchestrating all components."""

    def __init__(self) -> None:
        self.polymarket = PolymarketClient()
        self.telegram = TelegramAlertBot()
        self.cache = AlertCache()

        self._running = False
        self._stats = {
            "total_scans": 0,
            "total_markets_scanned": 0,
            "total_alerts_sent": 0,
            "session_alerts_sent": 0,
            "last_scan_time_ms": 0,
            "errors": 0,
        }

    async def start(self) -> bool:
        """
        Initialize all components.

        Returns:
            True if all components initialized successfully
        """
        logger.info("Starting Polymarket Low Odds Alert Bot...")

        # Validate configuration
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.error("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
            return False

        # Initialize Polymarket client
        await self.polymarket.start()
        logger.info("Polymarket client initialized")

        # Initialize Telegram bot
        if not await self.telegram.start():
            logger.error("Failed to initialize Telegram bot")
            return False

        # Send startup message
        await self.telegram.send_startup_message()

        self._running = True
        logger.info("Bot started successfully")
        return True

    async def stop(self) -> None:
        """Gracefully stop all components."""
        logger.info("Stopping bot...")
        self._running = False

        await self.polymarket.close()
        await self.telegram.close()

        logger.info("Bot stopped")

    async def run_scan_cycle(self) -> None:
        """Execute a single scan cycle."""
        start_time = time.time()

        try:
            # Fetch all active markets
            logger.debug("Fetching active markets...")
            markets = await self.polymarket.fetch_all_active_markets()

            if not markets:
                logger.warning("No markets fetched")
                return

            self._stats["total_markets_scanned"] += len(markets)

            # Apply filters
            logger.debug(f"Filtering {len(markets)} markets...")
            filtered = filter_markets(markets)

            # Process alerts
            alerts_sent = 0
            for market, result in filtered:
                alerts_sent += await self._process_alert(market, result)

            self._stats["total_alerts_sent"] += alerts_sent
            self._stats["session_alerts_sent"] += alerts_sent
            self._stats["total_scans"] += 1

        except Exception as e:
            logger.error(f"Error in scan cycle: {e}")
            self._stats["errors"] += 1
        finally:
            elapsed_ms = int((time.time() - start_time) * 1000)
            self._stats["last_scan_time_ms"] = elapsed_ms
            logger.info(
                f"Scan completed: {len(markets) if 'markets' in dir() else 0} markets, "
                f"{alerts_sent if 'alerts_sent' in dir() else 0} alerts, "
                f"{elapsed_ms}ms"
            )

    async def _process_alert(self, market: Market, result: FilterResult) -> int:
        """
        Process a market that passed filters and send alerts.

        Args:
            market: The market to alert on
            result: Filter result with low odds outcomes

        Returns:
            Number of alerts sent
        """
        if not result.low_odds_outcomes:
            return 0

        alerts_sent = 0

        for outcome in result.low_odds_outcomes:
            # Check deduplication cache
            if self.cache.was_recently_alerted(market.id, outcome.name):
                logger.debug(
                    f"Skipping duplicate alert for {market.id}:{outcome.name}"
                )
                continue

            # Send alert
            logger.info(
                f"Sending alert: {market.question[:50]}... "
                f"- {outcome.name} @ {outcome.price:.4f}"
            )

            success = await self.telegram.send_alert(
                market=market,
                outcome=outcome,
                category=result.category
            )

            if success:
                # Record in cache
                self.cache.record_alert(
                    market_id=market.id,
                    outcome_name=outcome.name,
                    price=outcome.price
                )
                alerts_sent += 1
            else:
                logger.warning(f"Failed to send alert for {market.id}")

        return alerts_sent

    async def run_forever(self) -> None:
        """Run the bot continuously."""
        logger.info(
            f"Starting continuous monitoring "
            f"(interval: {SCAN_INTERVAL_SECONDS}s, threshold: {PRICE_THRESHOLD})"
        )

        while self._running:
            await self.run_scan_cycle()

            # Wait for next cycle
            if self._running:
                await asyncio.sleep(SCAN_INTERVAL_SECONDS)

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics."""
        return {
            **self._stats,
            "cache_size": self.cache.size(),
            "cache_stats": self.cache.get_stats(),
        }


async def main() -> int:
    """Main entry point."""
    bot = PolymarketAlertBot()

    # Setup signal handlers for graceful shutdown (Unix only)
    if sys.platform != "win32":
        loop = asyncio.get_running_loop()

        def signal_handler() -> None:
            logger.info("Received shutdown signal")
            asyncio.create_task(bot.stop())

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

    # Start and run
    if not await bot.start():
        logger.error("Failed to start bot")
        return 1

    try:
        await bot.run_forever()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Bot cancelled")
    finally:
        await bot.stop()

    return 0


def run() -> None:
    """Entry point for console script."""
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    run()
