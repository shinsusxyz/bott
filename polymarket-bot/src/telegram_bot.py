"""
Telegram bot integration for sending low odds alerts.
Uses python-telegram-bot in async mode for high performance.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from telegram import Bot
from telegram.error import NetworkError, RetryAfter, TelegramError

from .config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
)
from .filters import Category
from .polymarket_client import Market, Outcome

logger = logging.getLogger(__name__)


def format_alert_message(
    market: Market,
    outcome: Outcome,
    category: Category | None
) -> str:
    """
    Format a low odds alert message.

    Args:
        market: The market with low odds
        outcome: The specific outcome with low odds
        category: Detected category (if any)

    Returns:
        Formatted Telegram message
    """
    # Format price as percentage and decimal
    price_percent = f"{outcome.price * 100:.3f}%"
    price_decimal = f"${outcome.price:.4f}"

    # Category display
    category_name = category.name if category else "Unknown"

    # Timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    message = f"""🚨 LOW ODDS ALERT

📊 Market: {market.question}
💰 Outcome: {outcome.name}
📉 Price: {price_percent} ({price_decimal})
📁 Category: {category_name}
🔗 Link: {market.url}

⏰ {timestamp}"""

    return message


class TelegramAlertBot:
    """Async Telegram bot for sending low odds alerts."""

    def __init__(
        self,
        token: str = TELEGRAM_BOT_TOKEN,
        chat_id: str = TELEGRAM_CHAT_ID
    ) -> None:
        """
        Initialize the Telegram bot.

        Args:
            token: Bot token from BotFather
            chat_id: Chat ID to send alerts to
        """
        self.token = token
        self.chat_id = chat_id
        self._bot: Bot | None = None
        self._initialized = False

    async def start(self) -> bool:
        """
        Initialize the bot connection.

        Returns:
            True if initialization successful
        """
        if not self.token or not self.chat_id:
            logger.error("Telegram bot token or chat ID not configured")
            return False

        try:
            self._bot = Bot(token=self.token)
            # Verify bot is working
            me = await self._bot.get_me()
            logger.info(f"Telegram bot initialized: @{me.username}")
            self._initialized = True
            return True
        except TelegramError as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            return False

    async def close(self) -> None:
        """Close the bot connection."""
        if self._bot:
            await self._bot.close()
            self._bot = None
            self._initialized = False

    async def send_alert(
        self,
        market: Market,
        outcome: Outcome,
        category: Category | None
    ) -> bool:
        """
        Send a low odds alert to Telegram.

        Args:
            market: The market with low odds
            outcome: The specific outcome
            category: Detected category

        Returns:
            True if alert was sent successfully
        """
        if not self._initialized or not self._bot:
            logger.error("Telegram bot not initialized")
            return False

        message = format_alert_message(market, outcome, category)

        return await self._send_message_with_retry(message)

    async def send_startup_message(self) -> bool:
        """Send a message indicating the bot has started."""
        if not self._initialized or not self._bot:
            return False

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        message = f"""✅ Polymarket Low Odds Alert Bot Started

🔍 Monitoring for outcomes ≤ 0.1%
📁 Categories: Politics, Weather, Tech, AI
🚫 Excluding: Crypto markets

⏰ Started at: {timestamp}"""

        return await self._send_message_with_retry(message)

    async def send_status_message(self, stats: dict[str, Any]) -> bool:
        """
        Send a status update message.

        Args:
            stats: Dictionary of statistics to report

        Returns:
            True if message was sent successfully
        """
        if not self._initialized or not self._bot:
            return False

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        markets_scanned = stats.get("markets_scanned", 0)
        alerts_sent = stats.get("alerts_sent", 0)
        scan_time = stats.get("scan_time_ms", 0)
        cache_size = stats.get("cache_size", 0)

        message = f"""📊 Bot Status Update

📈 Markets scanned: {markets_scanned}
🔔 Alerts sent (session): {alerts_sent}
⚡ Last scan time: {scan_time}ms
💾 Cache entries: {cache_size}

⏰ {timestamp}"""

        return await self._send_message_with_retry(message)

    async def send_error_message(self, error: str) -> bool:
        """
        Send an error notification.

        Args:
            error: Error description

        Returns:
            True if message was sent successfully
        """
        if not self._initialized or not self._bot:
            return False

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        message = f"""⚠️ Bot Error

❌ {error}

⏰ {timestamp}"""

        return await self._send_message_with_retry(message)

    async def _send_message_with_retry(self, text: str) -> bool:
        """
        Send a message with exponential backoff retry.

        Args:
            text: Message text to send

        Returns:
            True if message was sent successfully
        """
        if not self._bot:
            return False

        for attempt in range(MAX_RETRIES):
            try:
                await self._bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode=None,  # Plain text for reliability
                    disable_web_page_preview=False
                )
                return True

            except RetryAfter as e:
                # Telegram rate limit - wait the specified time
                wait_time = e.retry_after + 1
                logger.warning(f"Rate limited, waiting {wait_time}s")
                await asyncio.sleep(wait_time)

            except NetworkError as e:
                # Network issue - retry with backoff
                logger.warning(f"Network error (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF_BASE ** attempt
                    await asyncio.sleep(wait_time)

            except TelegramError as e:
                # Other Telegram error
                logger.error(f"Telegram error: {e}")
                return False

        logger.error("Failed to send message after all retries")
        return False

    @property
    def is_ready(self) -> bool:
        """Check if bot is ready to send messages."""
        return self._initialized and self._bot is not None
