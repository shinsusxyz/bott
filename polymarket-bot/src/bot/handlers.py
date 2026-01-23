"""
Telegram command and message handlers.
"""

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from ..data.database import Database
from ..utils.logger import logger
from .keyboards import start_keyboard, main_menu_keyboard, export_keyboard
from .formatters import format_welcome, format_status, format_settings
from .callbacks import CallbackHandler


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    logger.info(f"User {user.id} started the bot")

    # Ensure user has settings
    db: Database = context.bot_data.get("database")
    if db:
        await db.get_settings(user.id)

    await update.message.reply_text(
        format_welcome(),
        reply_markup=start_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = """📚 HELP

**Commands:**
/start - Start the bot
/settings - Configure alerts
/watchlist - View tracked markets
/traders - View tracked traders
/status - Bot status
/export - Export your data

**How it works:**
1. Bot scans Polymarket every minute
2. Alerts are batched together
3. You get one clean message with all alerts

**Alert types:**
📉 Low odds - Markets below your threshold
🐋 Whale trades - Big trades above $30
⚖️ Arbitrage - Price discrepancies
⚠️ Counter signals - Whales betting against low odds

**Tips:**
• Use 📌 Track to watch specific markets
• Use 🔇 Mute to hide annoying markets
• Track whale traders to follow smart money"""

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settings command."""
    user_id = update.effective_user.id
    db: Database = context.bot_data.get("database")

    if not db:
        await update.message.reply_text("Database not available")
        return

    settings = await db.get_settings(user_id)
    from .keyboards import settings_keyboard
    await update.message.reply_text(
        format_settings(settings),
        reply_markup=settings_keyboard(settings),
    )


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /watchlist command."""
    user_id = update.effective_user.id
    db: Database = context.bot_data.get("database")

    if not db:
        await update.message.reply_text("Database not available")
        return

    watchlist = await db.get_watchlist(user_id)
    from .keyboards import watchlist_keyboard

    text = f"📋 YOUR WATCHLIST ({len(watchlist)} markets)"
    if not watchlist:
        text = "📋 YOUR WATCHLIST\n\nNo markets tracked yet."

    await update.message.reply_text(text, reply_markup=watchlist_keyboard(watchlist))


async def traders_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /traders command."""
    user_id = update.effective_user.id
    db: Database = context.bot_data.get("database")

    if not db:
        await update.message.reply_text("Database not available")
        return

    traders = await db.get_tracked_traders(user_id)
    from .keyboards import traders_keyboard

    text = f"👥 TRACKED TRADERS ({len(traders)})"
    if not traders:
        text = "👥 TRACKED TRADERS\n\nNo traders tracked yet."

    await update.message.reply_text(text, reply_markup=traders_keyboard(traders))


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    bot_instance = context.bot_data.get("bot_instance")
    stats = bot_instance.get_stats() if bot_instance else {}

    await update.message.reply_text(
        format_status(stats),
        reply_markup=main_menu_keyboard(),
    )


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /export command."""
    await update.message.reply_text(
        "📁 EXPORT DATA\n\nSelect format and data type:",
        reply_markup=export_keyboard(),
    )


async def markets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /markets command."""
    await update.message.reply_text(
        "🔍 BROWSE MARKETS\n\n"
        "Feature coming soon!\n\n"
        "For now, markets are discovered automatically during scans.",
        reply_markup=main_menu_keyboard(),
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages (wallet addresses, URLs)."""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    db: Database = context.bot_data.get("database")

    # Check if it's a wallet address
    if text.startswith("0x") and len(text) == 42:
        if db:
            await db.add_tracked_trader(user_id, text)
            await update.message.reply_text(
                f"✅ Added trader to tracking:\n`{text}`",
                parse_mode="Markdown",
            )
        return

    # Check if it's a Polymarket URL
    if "polymarket.com" in text:
        await update.message.reply_text(
            "🔍 URL detected!\n\nMarket tracking from URL coming soon."
        )
        return

    # Unknown text
    await update.message.reply_text(
        "I didn't understand that.\n\n"
        "Try:\n"
        "• A wallet address (0x...)\n"
        "• A Polymarket URL\n"
        "• /help for commands"
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Error: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "An error occurred. Please try again."
        )


def setup_handlers(app: Application, database: Database, bot_instance) -> None:
    """Set up all handlers."""
    # Store in bot_data for access in handlers
    app.bot_data["database"] = database
    app.bot_data["bot_instance"] = bot_instance

    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("watchlist", watchlist_command))
    app.add_handler(CommandHandler("traders", traders_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("markets", markets_command))

    # Callback handler
    callback_handler = CallbackHandler(database, bot_instance)
    app.add_handler(CallbackQueryHandler(callback_handler.handle))

    # Text handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Error handler
    app.add_error_handler(error_handler)
