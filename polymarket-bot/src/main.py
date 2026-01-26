#!/usr/bin/env python3
"""
Polymarket Smart Alert Bot

A powerful Telegram bot that monitors Polymarket for:
- Low odds markets (< 1%)
- Whale trades (> $30)
- Arbitrage opportunities
- Counter-signals
"""

import asyncio
import signal
import sys
from datetime import datetime, timezone
from typing import Any

from telegram import Bot
from telegram.ext import Application

from .polymarket.gamma_client import GammaClient
from .polymarket.clob_client import CLOBClient
from .polymarket.data_client import DataClient
from .core.scanner import MarketScanner, WhaleScanner
from .core.aggregator import AlertAggregator
from .data.database import Database
from .bot.handlers import setup_handlers
from .bot.formatters import format_batch
from .bot.keyboards import alert_actions_keyboard, whale_alert_keyboard
from .utils.config import (
    TELEGRAM_BOT_TOKEN,
    DEFAULT_SCAN_INTERVAL,
)
from .utils.logger import logger


class PolymarketBot:
    """Main bot orchestrator."""

    def __init__(self) -> None:
        # API clients
        self.gamma = GammaClient()
        self.clob = CLOBClient()
        self.data_client = DataClient()

        # Database
        self.db = Database()

        # Scanners
        self.market_scanner: MarketScanner | None = None
        self.whale_scanner: WhaleScanner | None = None

        # Alert aggregator
        self.aggregator = AlertAggregator(batch_interval_seconds=60)

        # Telegram
        self.app: Application | None = None
        self.bot: Bot | None = None

        # State
        self._running = False
        self._stats = {
            "start_time": None,
            "total_scans": 0,
            "total_alerts": 0,
        }

    async def start(self) -> bool:
        """Initialize all components."""
        logger.info("Starting Polymarket Smart Alert Bot...")

        if not TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not set")
            return False

        try:
            # Initialize database
            await self.db.connect()

            # Initialize API clients
            await self.gamma.start()
            await self.clob.start()
            await self.data_client.start()

            # Initialize scanners
            self.market_scanner = MarketScanner(
                self.gamma, self.clob, self.data_client, self.db
            )
            self.whale_scanner = WhaleScanner(
                self.data_client, self.gamma, self.db
            )

            # Initialize Telegram bot
            self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
            self.bot = self.app.bot

            # Setup handlers
            setup_handlers(self.app, self.db, self)

            # Initialize the application
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(drop_pending_updates=True)

            self._running = True
            self._stats["start_time"] = datetime.now(timezone.utc)

            logger.info("Bot started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            return False

    async def stop(self) -> None:
        """Gracefully stop all components."""
        logger.info("Stopping bot...")
        self._running = False

        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

        await self.gamma.close()
        await self.clob.close()
        await self.data_client.close()
        await self.db.close()

        logger.info("Bot stopped")

    async def run_scan_loop(self) -> None:
        """Main scanning loop."""
        logger.info(f"Starting scan loop (interval: {DEFAULT_SCAN_INTERVAL}s)")

        while self._running:
            try:
                await self._run_scan_cycle()
            except Exception as e:
                logger.error(f"Scan cycle error: {e}")

            if self._running:
                await asyncio.sleep(DEFAULT_SCAN_INTERVAL)

    async def _run_scan_cycle(self) -> None:
        """Execute one scan cycle for all users."""
        users = await self.db.get_all_users()

        if not users:
            logger.debug("No users to scan for")
            return

        for user_id in users:
            try:
                settings = await self.db.get_settings(user_id)

                # Scan for price alerts
                price_alerts = await self.market_scanner.scan_markets(user_id, settings)
                for alert in price_alerts:
                    if hasattr(alert, 'market'):  # PriceAlert
                        await self.aggregator.add_price_alert(user_id, alert)
                    elif hasattr(alert, 'yes_price'):  # ArbitrageAlert
                        await self.aggregator.add_arbitrage_alert(user_id, alert)

                # Scan for whale alerts
                if settings.get("whale_alerts_enabled", True):
                    whale_alerts = await self.whale_scanner.check_whale_trades(
                        user_id,
                        whale_threshold=settings.get("whale_threshold", 30),
                        smart_money_only=settings.get("smart_money_only", False),
                    )
                    for alert in whale_alerts:
                        await self.aggregator.add_whale_alert(user_id, alert)

            except Exception as e:
                logger.error(f"Error scanning for user {user_id}: {e}")

        # Send ready batches
        await self._send_ready_batches()

        self._stats["total_scans"] += 1

    async def _send_ready_batches(self) -> None:
        """Send batched alerts to users."""
        batches = await self.aggregator.get_ready_batches()

        for user_id, batch in batches.items():
            if batch.is_empty:
                continue

            try:
                # Format the batch
                message = format_batch(batch)

                # Get keyboard for first alert (if any)
                keyboard = None
                if batch.price_alerts:
                    market_id = batch.price_alerts[0].market.id
                    keyboard = alert_actions_keyboard(market_id)
                elif batch.whale_alerts:
                    alert = batch.whale_alerts[0]
                    keyboard = whale_alert_keyboard(
                        alert.market.id if alert.market else "",
                        alert.trade.trader_address,
                    )

                # Send
                await self.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=keyboard,
                    disable_web_page_preview=True,
                )

                self._stats["total_alerts"] += batch.total_count

                # Record alerts in database
                for alert in batch.price_alerts:
                    await self.db.record_alert(
                        user_id=user_id,
                        alert_type="low_odds",
                        market_id=alert.market.id,
                        condition_id=alert.market.condition_id,
                        event_slug=alert.market.event_slug,
                        market_slug=alert.market.slug,
                        title=alert.market.question,
                        price_at_alert=alert.outcome.price,
                    )

            except Exception as e:
                logger.error(f"Failed to send batch to {user_id}: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get bot statistics."""
        scanner_stats = self.market_scanner.get_stats() if self.market_scanner else {}

        uptime = 0
        if self._stats["start_time"]:
            uptime = (datetime.now(timezone.utc) - self._stats["start_time"]).total_seconds()

        return {
            **self._stats,
            **scanner_stats,
            "uptime_seconds": int(uptime),
            "aggregator_pending": self.aggregator.get_pending_count(),
        }


async def main() -> int:
    """Main entry point."""
    bot = PolymarketBot()

    # Signal handlers (Unix only)
    if sys.platform != "win32":
        loop = asyncio.get_running_loop()

        def signal_handler() -> None:
            logger.info("Received shutdown signal")
            asyncio.create_task(bot.stop())

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

    # Start
    if not await bot.start():
        logger.error("Failed to start bot")
        return 1

    try:
        await bot.run_scan_loop()
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
