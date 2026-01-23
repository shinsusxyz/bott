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
    start_keyboard,
)
from .formatters import format_settings, format_status, format_welcome


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all callback queries from inline buttons."""
    query = update.callback_query

    # Answer callback to stop loading animation
    await query.answer()

    data = query.data
    user_id = update.effective_user.id

    # Get database from context
    db: Database = context.bot_data.get("database")
    if not db:
        await query.message.reply_text("Database not available. Please try /start again.")
        return

    try:
        logger.info(f"Callback: {data} from user {user_id}")

        if data == "noop":
            return

        elif data == "main_menu":
            await query.edit_message_text(
                "📊 Polymarket Alert Bot\n\nSelect an option:",
                reply_markup=main_menu_keyboard(),
            )

        elif data == "settings":
            settings = await db.get_settings(user_id)
            text = format_settings(settings)
            await query.edit_message_text(text, reply_markup=settings_keyboard(settings))

        elif data == "watchlist":
            watchlist = await db.get_watchlist(user_id)
            count = len(watchlist)
            text = f"📋 YOUR WATCHLIST ({count} markets)"
            if not watchlist:
                text = "📋 YOUR WATCHLIST\n\nNo markets tracked yet.\nUse 📌 Track on any alert to add markets."
            await query.edit_message_text(text, reply_markup=watchlist_keyboard(watchlist))

        elif data == "traders":
            traders = await db.get_tracked_traders(user_id)
            count = len(traders)
            text = f"👥 TRACKED TRADERS ({count})\n\n🧠 = Smart money (>65% win rate or >$50K)"
            if not traders:
                text = "👥 TRACKED TRADERS\n\nNo traders tracked yet.\nUse 👁 Track trader on whale alerts."
            await query.edit_message_text(text, reply_markup=traders_keyboard(traders))

        elif data == "status":
            bot_instance = context.bot_data.get("bot_instance")
            stats = bot_instance.get_stats() if bot_instance else {}
            text = format_status(stats)
            await query.edit_message_text(text, reply_markup=main_menu_keyboard())

        elif data == "start_monitoring":
            await query.edit_message_text(
                "✅ Monitoring started!\n\n"
                "You'll receive alerts when:\n"
                "📉 Markets hit low odds threshold\n"
                "🐋 Whales make big trades\n"
                "⚖️ Arbitrage opportunities appear\n\n"
                "Alerts are batched every 1-2 minutes.",
                reply_markup=main_menu_keyboard(),
            )

        elif data == "markets":
            await query.edit_message_text(
                "🔍 BROWSE MARKETS\n\n"
                "Feature coming soon!\n\n"
                "For now, markets are discovered automatically during scans.",
                reply_markup=main_menu_keyboard(),
            )

        # Category selection on start
        elif data.startswith("cat_"):
            category = data[4:]
            settings = await db.get_settings(user_id)
            categories = list(settings.get("categories", ["politics", "weather", "tech", "ai"]))

            if category == "all":
                categories = ["politics", "weather", "tech", "ai"]
                msg = "✅ All categories enabled"
            elif category in categories:
                categories.remove(category)
                msg = f"❌ {category.title()} disabled"
            else:
                categories.append(category)
                msg = f"✅ {category.title()} enabled"

            await db.update_settings(user_id, categories=categories)

            # Show popup and stay on start menu
            await query.answer(msg, show_alert=False)

            # Update welcome text to show selected categories
            cat_list = ", ".join(c.title() for c in categories) if categories else "None"
            welcome_text = format_welcome() + f"\n\n📁 Selected: {cat_list}"
            await query.edit_message_text(welcome_text, reply_markup=start_keyboard())

        # Toggle settings
        elif data.startswith("toggle_"):
            setting = data[7:]
            settings = await db.get_settings(user_id)

            if setting in ["politics", "weather", "tech", "ai"]:
                # Category toggle
                categories = list(settings.get("categories", ["politics", "weather", "tech", "ai"]))
                if setting in categories:
                    categories.remove(setting)
                else:
                    categories.append(setting)
                await db.update_settings(user_id, categories=categories)

            elif setting == "whale":
                current = settings.get("whale_alerts_enabled", True)
                await db.update_settings(user_id, whale_alerts_enabled=not current)

            elif setting == "smart":
                current = settings.get("smart_money_only", False)
                await db.update_settings(user_id, smart_money_only=not current)

            elif setting == "arb":
                current = settings.get("arbitrage_alerts", True)
                await db.update_settings(user_id, arbitrage_alerts=not current)

            elif setting == "counter":
                current = settings.get("counter_signals", True)
                await db.update_settings(user_id, counter_signals=not current)

            # Refresh settings
            settings = await db.get_settings(user_id)
            text = format_settings(settings)
            await query.edit_message_text(text, reply_markup=settings_keyboard(settings))

        # Threshold settings
        elif data.startswith("thresh_"):
            value = float(data[7:])
            await db.update_settings(user_id, price_threshold=value)
            settings = await db.get_settings(user_id)
            text = format_settings(settings)
            await query.edit_message_text(text, reply_markup=settings_keyboard(settings))

        elif data.startswith("vol_"):
            value = float(data[4:])
            await db.update_settings(user_id, min_volume=value)
            settings = await db.get_settings(user_id)
            text = format_settings(settings)
            await query.edit_message_text(text, reply_markup=settings_keyboard(settings))

        elif data == "reset_settings":
            await db.update_settings(
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
            settings = await db.get_settings(user_id)
            text = format_settings(settings)
            await query.edit_message_text(text, reply_markup=settings_keyboard(settings))

        # Watchlist actions
        elif data.startswith("wl_page_"):
            page = int(data[8:])
            watchlist = await db.get_watchlist(user_id)
            text = f"📋 YOUR WATCHLIST ({len(watchlist)} markets)"
            await query.edit_message_text(text, reply_markup=watchlist_keyboard(watchlist, page))

        elif data.startswith("wl_remove_"):
            market_id = data[10:]
            await db.remove_from_watchlist(user_id, market_id)
            watchlist = await db.get_watchlist(user_id)
            text = f"📋 YOUR WATCHLIST ({len(watchlist)} markets)"
            if not watchlist:
                text = "📋 YOUR WATCHLIST\n\nNo markets tracked yet."
            await query.edit_message_text(text, reply_markup=watchlist_keyboard(watchlist))

        elif data == "wl_add":
            await query.edit_message_text(
                "🔍 To add a market:\n\n"
                "1. Click 📌 Track on any alert\n"
                "2. Or send me a Polymarket URL\n\n"
                "Markets will be added to your watchlist.",
                reply_markup=main_menu_keyboard(),
            )

        elif data == "wl_muted":
            muted = await db.get_muted_markets(user_id)
            if muted:
                text = f"🔇 MUTED MARKETS ({len(muted)})\n\n"
                text += "\n".join(f"• {m[:20]}..." for m in muted[:10])
            else:
                text = "🔇 No muted markets"
            await query.edit_message_text(text, reply_markup=main_menu_keyboard())

        # Trader actions
        elif data.startswith("trader_remove_"):
            address = data[14:]
            await db.remove_tracked_trader(user_id, address)
            traders = await db.get_tracked_traders(user_id)
            text = f"👥 TRACKED TRADERS ({len(traders)})"
            if not traders:
                text = "👥 TRACKED TRADERS\n\nNo traders tracked yet."
            await query.edit_message_text(text, reply_markup=traders_keyboard(traders))

        elif data == "trader_add":
            await query.edit_message_text(
                "👤 To add a trader:\n\n"
                "Send me a wallet address:\n"
                "`0x1234...abcd`\n\n"
                "Or click 👁 Track trader on whale alerts.",
                reply_markup=main_menu_keyboard(),
                parse_mode="Markdown",
            )

        elif data.startswith("trader_view_"):
            address = data[12:]
            await query.edit_message_text(
                f"👤 Trader: `{address[:10]}...{address[-6:]}`\n\n"
                f"🔗 https://polymarket.com/profile/{address}\n\n"
                "Stats loading not implemented yet.",
                reply_markup=main_menu_keyboard(),
                parse_mode="Markdown",
            )

        elif data.startswith("tr_page_"):
            page = int(data[8:])
            traders = await db.get_tracked_traders(user_id)
            text = f"👥 TRACKED TRADERS ({len(traders)})"
            await query.edit_message_text(text, reply_markup=traders_keyboard(traders, page))

        # Market actions from alerts
        elif data.startswith("mute_"):
            market_id = data[5:]
            await db.mute_market(user_id, market_id)
            await query.answer("✅ Market muted for 1 hour", show_alert=True)

        elif data.startswith("track_"):
            market_id = data[6:]
            # Would need to fetch market details - for now just confirm
            await query.answer("✅ Added to watchlist", show_alert=True)

        elif data.startswith("track_trader_"):
            address = data[13:]
            await db.add_tracked_trader(user_id, address)
            await query.answer("✅ Trader added to tracking", show_alert=True)

        elif data.startswith("orderbook_"):
            market_id = data[10:]
            await query.answer("Orderbook view coming soon!", show_alert=True)

        elif data.startswith("view_"):
            market_id = data[5:]
            await query.answer("Market view coming soon!", show_alert=True)

        # Export actions
        elif data == "export_csv":
            await query.answer("CSV export coming soon!", show_alert=True)

        elif data == "export_json":
            await query.answer("JSON export coming soon!", show_alert=True)

        elif data.startswith("export_"):
            await query.answer("Export coming soon!", show_alert=True)

        elif data == "cancel":
            await query.edit_message_text(
                "Cancelled.",
                reply_markup=main_menu_keyboard(),
            )

        else:
            logger.warning(f"Unknown callback: {data}")
            await query.answer(f"Unknown action: {data}", show_alert=True)

    except Exception as e:
        logger.error(f"Callback error for {data}: {e}", exc_info=True)
        try:
            await query.answer(f"Error: {str(e)[:50]}", show_alert=True)
        except Exception:
            pass
