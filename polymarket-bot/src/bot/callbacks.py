"""
Callback query handlers for inline buttons.
"""

from telegram import Update
from telegram.ext import ContextTypes

from ..data.database import Database
from ..utils.logger import logger
from .keyboards import (
    main_menu_keyboard,
    settings_keyboard,
    watchlist_keyboard,
    traders_keyboard,
)
from .formatters import format_settings, format_status


class CallbackHandler:
    """Handles all callback queries from inline buttons."""

    def __init__(self, database: Database, bot_instance: "PolymarketBot") -> None:
        self.db = database
        self.bot = bot_instance

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Route callback to appropriate handler."""
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = update.effective_user.id

        try:
            if data == "noop":
                return

            elif data == "main_menu":
                await self._show_main_menu(query)

            elif data == "settings":
                await self._show_settings(query, user_id)

            elif data == "watchlist":
                await self._show_watchlist(query, user_id)

            elif data == "traders":
                await self._show_traders(query, user_id)

            elif data == "status":
                await self._show_status(query)

            elif data == "start_monitoring":
                await self._start_monitoring(query, user_id)

            # Category toggles
            elif data.startswith("cat_"):
                await self._toggle_category(query, user_id, data[4:])

            elif data.startswith("toggle_"):
                await self._toggle_setting(query, user_id, data[7:])

            # Threshold settings
            elif data.startswith("thresh_"):
                value = float(data[7:])
                await self._update_setting(query, user_id, "price_threshold", value)

            elif data.startswith("vol_"):
                value = float(data[4:])
                await self._update_setting(query, user_id, "min_volume", value)

            # Reset
            elif data == "reset_settings":
                await self._reset_settings(query, user_id)

            # Watchlist actions
            elif data.startswith("wl_"):
                await self._handle_watchlist_action(query, user_id, data)

            # Trader actions
            elif data.startswith("trader_"):
                await self._handle_trader_action(query, user_id, data)

            # Market actions
            elif data.startswith("mute_"):
                market_id = data[5:]
                await self._mute_market(query, user_id, market_id)

            elif data.startswith("track_"):
                market_id = data[6:]
                await self._track_market(query, user_id, market_id)

            else:
                logger.warning(f"Unknown callback: {data}")

        except Exception as e:
            logger.error(f"Callback error: {e}")
            await query.message.reply_text(f"Error: {e}")

    async def _show_main_menu(self, query) -> None:
        """Show main menu."""
        await query.edit_message_text(
            "📊 Polymarket Alert Bot\n\nSelect an option:",
            reply_markup=main_menu_keyboard(),
        )

    async def _show_settings(self, query, user_id: int) -> None:
        """Show settings menu."""
        settings = await self.db.get_settings(user_id)
        text = format_settings(settings)
        await query.edit_message_text(text, reply_markup=settings_keyboard(settings))

    async def _show_watchlist(self, query, user_id: int, page: int = 0) -> None:
        """Show watchlist."""
        watchlist = await self.db.get_watchlist(user_id)
        count = len(watchlist)
        text = f"📋 YOUR WATCHLIST ({count} markets)\n\nSelect a market for details:"

        if not watchlist:
            text = "📋 YOUR WATCHLIST\n\nNo markets tracked yet.\nUse 📌 Track on any alert to add markets."

        await query.edit_message_text(text, reply_markup=watchlist_keyboard(watchlist, page))

    async def _show_traders(self, query, user_id: int, page: int = 0) -> None:
        """Show tracked traders."""
        traders = await self.db.get_tracked_traders(user_id)
        count = len(traders)
        text = f"👥 TRACKED TRADERS ({count})\n\n🧠 = Smart money (>65% win rate or >$50K)"

        if not traders:
            text = "👥 TRACKED TRADERS\n\nNo traders tracked yet.\nUse 👁 Track trader on whale alerts."

        await query.edit_message_text(text, reply_markup=traders_keyboard(traders, page))

    async def _show_status(self, query) -> None:
        """Show bot status."""
        stats = self.bot.get_stats() if hasattr(self.bot, 'get_stats') else {}
        text = format_status(stats)
        await query.edit_message_text(text, reply_markup=main_menu_keyboard())

    async def _start_monitoring(self, query, user_id: int) -> None:
        """Start monitoring for user."""
        await query.edit_message_text(
            "✅ Monitoring started!\n\n"
            "You'll receive alerts when:\n"
            "📉 Markets hit low odds threshold\n"
            "🐋 Whales make big trades\n"
            "⚖️ Arbitrage opportunities appear\n\n"
            "Alerts are batched every 1-2 minutes.",
            reply_markup=main_menu_keyboard(),
        )

    async def _toggle_category(self, query, user_id: int, category: str) -> None:
        """Toggle a category on/off."""
        settings = await self.db.get_settings(user_id)
        categories = settings.get("categories", ["politics", "weather", "tech", "ai"])

        if category == "all":
            categories = ["politics", "weather", "tech", "ai"]
        elif category in categories:
            categories.remove(category)
        else:
            categories.append(category)

        await self.db.update_settings(user_id, categories=categories)
        await self._show_settings(query, user_id)

    async def _toggle_setting(self, query, user_id: int, setting: str) -> None:
        """Toggle a boolean setting."""
        settings = await self.db.get_settings(user_id)

        mapping = {
            "politics": "categories",
            "weather": "categories",
            "tech": "categories",
            "ai": "categories",
            "whale": "whale_alerts_enabled",
            "smart": "smart_money_only",
            "arb": "arbitrage_alerts",
            "counter": "counter_signals",
        }

        if setting in ["politics", "weather", "tech", "ai"]:
            await self._toggle_category(query, user_id, setting)
            return

        key = mapping.get(setting)
        if key:
            current = settings.get(key, False)
            await self.db.update_settings(user_id, **{key: not current})

        await self._show_settings(query, user_id)

    async def _update_setting(self, query, user_id: int, key: str, value: float) -> None:
        """Update a numeric setting."""
        await self.db.update_settings(user_id, **{key: value})
        await self._show_settings(query, user_id)

    async def _reset_settings(self, query, user_id: int) -> None:
        """Reset settings to defaults."""
        await self.db.update_settings(
            user_id,
            price_threshold=0.01,
            min_volume=1000,
            min_liquidity=5000,
            max_spread=0.03,
            whale_threshold=30,
            categories=["politics", "weather", "tech", "ai"],
            whale_alerts_enabled=True,
            smart_money_only=False,
            arbitrage_alerts=True,
            counter_signals=True,
        )
        await self._show_settings(query, user_id)

    async def _handle_watchlist_action(self, query, user_id: int, data: str) -> None:
        """Handle watchlist actions."""
        if data.startswith("wl_page_"):
            page = int(data[8:])
            await self._show_watchlist(query, user_id, page)
        elif data.startswith("wl_remove_"):
            market_id = data[10:]
            await self.db.remove_from_watchlist(user_id, market_id)
            await self._show_watchlist(query, user_id)
        elif data == "wl_add":
            await query.edit_message_text(
                "🔍 To add a market:\n\n"
                "1. Browse markets with /markets\n"
                "2. Click 📌 Track on any alert\n"
                "3. Or send me a Polymarket URL",
                reply_markup=main_menu_keyboard(),
            )

    async def _handle_trader_action(self, query, user_id: int, data: str) -> None:
        """Handle trader actions."""
        if data.startswith("trader_remove_"):
            address = data[14:]
            await self.db.remove_tracked_trader(user_id, address)
            await self._show_traders(query, user_id)
        elif data == "trader_add":
            await query.edit_message_text(
                "👤 To add a trader:\n\n"
                "Send me a wallet address:\n"
                "`0x1234...`\n\n"
                "Or click 👁 Track trader on whale alerts.",
                reply_markup=main_menu_keyboard(),
                parse_mode="Markdown",
            )

    async def _mute_market(self, query, user_id: int, market_id: str) -> None:
        """Mute a market."""
        await self.db.mute_market(user_id, market_id)
        await query.answer("Market muted for 1 hour")

    async def _track_market(self, query, user_id: int, market_id: str) -> None:
        """Track a market (add to watchlist)."""
        # Would need market details - for now just acknowledge
        await query.answer("Market added to watchlist")
