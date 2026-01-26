"""
Telegram inline keyboard builders.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def start_keyboard() -> InlineKeyboardMarkup:
    """Build the start menu keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏛 Politics", callback_data="cat_politics"),
            InlineKeyboardButton("🌪 Weather", callback_data="cat_weather"),
        ],
        [
            InlineKeyboardButton("💻 Tech", callback_data="cat_tech"),
            InlineKeyboardButton("🤖 AI", callback_data="cat_ai"),
        ],
        [InlineKeyboardButton("✓ All categories", callback_data="cat_all")],
        [
            InlineKeyboardButton("▶️ Start monitoring", callback_data="start_monitoring"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
        ],
    ])


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Build the main menu keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
            InlineKeyboardButton("📋 Watchlist", callback_data="watchlist"),
        ],
        [
            InlineKeyboardButton("👥 Traders", callback_data="traders"),
            InlineKeyboardButton("📊 Status", callback_data="status"),
        ],
        [InlineKeyboardButton("🔍 Browse Markets", callback_data="markets")],
    ])


def settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    """Build the settings keyboard."""
    # Helper for checkmark
    def check(val: bool) -> str:
        return "✓" if val else ""

    # Categories
    cats = settings.get("categories", ["politics", "weather", "tech", "ai"])
    pol = "politics" in cats
    wea = "weather" in cats
    tec = "tech" in cats
    ai_ = "ai" in cats

    # Thresholds
    thresh = settings.get("price_threshold", 0.01)
    vol = settings.get("min_volume", 1000)

    # Whale
    whale_on = settings.get("whale_alerts_enabled", True)
    smart_only = settings.get("smart_money_only", False)

    # Other
    arb = settings.get("arbitrage_alerts", True)
    counter = settings.get("counter_signals", True)

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 MONITORING", callback_data="noop")],
        [
            InlineKeyboardButton(f"0.5%{check(thresh==0.005)}", callback_data="thresh_0.005"),
            InlineKeyboardButton(f"1%{check(thresh==0.01)}", callback_data="thresh_0.01"),
            InlineKeyboardButton(f"2%{check(thresh==0.02)}", callback_data="thresh_0.02"),
            InlineKeyboardButton(f"5%{check(thresh==0.05)}", callback_data="thresh_0.05"),
        ],
        [InlineKeyboardButton("─ Min Volume (24h) ─", callback_data="noop")],
        [
            InlineKeyboardButton(f"$500{check(vol==500)}", callback_data="vol_500"),
            InlineKeyboardButton(f"$1K{check(vol==1000)}", callback_data="vol_1000"),
            InlineKeyboardButton(f"$5K{check(vol==5000)}", callback_data="vol_5000"),
            InlineKeyboardButton(f"$10K{check(vol==10000)}", callback_data="vol_10000"),
        ],
        [InlineKeyboardButton("📁 CATEGORIES", callback_data="noop")],
        [
            InlineKeyboardButton(f"Politics {check(pol)}", callback_data="toggle_politics"),
            InlineKeyboardButton(f"Weather {check(wea)}", callback_data="toggle_weather"),
        ],
        [
            InlineKeyboardButton(f"Tech {check(tec)}", callback_data="toggle_tech"),
            InlineKeyboardButton(f"AI {check(ai_)}", callback_data="toggle_ai"),
        ],
        [InlineKeyboardButton("🐋 WHALE ALERTS", callback_data="noop")],
        [
            InlineKeyboardButton(f"Enabled: {'ON' if whale_on else 'OFF'}", callback_data="toggle_whale"),
            InlineKeyboardButton(f"Smart only: {'ON' if smart_only else 'OFF'}", callback_data="toggle_smart"),
        ],
        [InlineKeyboardButton("📋 OTHER ALERTS", callback_data="noop")],
        [
            InlineKeyboardButton(f"Arbitrage: {'ON' if arb else 'OFF'}", callback_data="toggle_arb"),
            InlineKeyboardButton(f"Counter signals: {'ON' if counter else 'OFF'}", callback_data="toggle_counter"),
        ],
        [InlineKeyboardButton("🔄 Reset to defaults", callback_data="reset_settings")],
        [InlineKeyboardButton("« Back", callback_data="main_menu")],
    ])


def watchlist_keyboard(watchlist: list, page: int = 0) -> InlineKeyboardMarkup:
    """Build watchlist keyboard with pagination."""
    buttons = []
    page_size = 5
    start = page * page_size
    items = watchlist[start:start + page_size]

    for i, item in enumerate(items, start=1):
        title = item.get("title", "Unknown")[:30]
        muted = item.get("muted", False)
        market_id = item.get("market_id", "")

        buttons.append([
            InlineKeyboardButton(
                f"{'🔇 ' if muted else ''}{i}. {title}",
                callback_data=f"wl_view_{market_id}"
            ),
            InlineKeyboardButton("❌", callback_data=f"wl_remove_{market_id}"),
        ])

    # Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("← Prev", callback_data=f"wl_page_{page-1}"))
    total_pages = (len(watchlist) + page_size - 1) // page_size
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next →", callback_data=f"wl_page_{page+1}"))
    if nav:
        buttons.append(nav)

    buttons.append([
        InlineKeyboardButton("➕ Add market", callback_data="wl_add"),
        InlineKeyboardButton(f"🔇 Muted ({sum(1 for w in watchlist if w.get('muted'))})", callback_data="wl_muted"),
    ])
    buttons.append([InlineKeyboardButton("« Back", callback_data="main_menu")])

    return InlineKeyboardMarkup(buttons)


def traders_keyboard(traders: list, page: int = 0) -> InlineKeyboardMarkup:
    """Build tracked traders keyboard."""
    buttons = []
    page_size = 5
    start = page * page_size
    items = traders[start:start + page_size]

    for item in items:
        name = item.get("trader_name") or item.get("trader_address", "")[:10] + "..."
        addr = item.get("trader_address", "")

        buttons.append([
            InlineKeyboardButton(f"👤 {name}", callback_data=f"trader_view_{addr}"),
            InlineKeyboardButton("❌", callback_data=f"trader_remove_{addr}"),
        ])

    # Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("← Prev", callback_data=f"tr_page_{page-1}"))
    total_pages = max(1, (len(traders) + page_size - 1) // page_size)
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next →", callback_data=f"tr_page_{page+1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("➕ Add by address", callback_data="trader_add")])
    buttons.append([InlineKeyboardButton("« Back", callback_data="main_menu")])

    return InlineKeyboardMarkup(buttons)


def market_actions_keyboard(market_id: str, is_tracked: bool = False) -> InlineKeyboardMarkup:
    """Build action buttons for a market."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔇 Mute", callback_data=f"mute_{market_id}"),
            InlineKeyboardButton(
                "📌 Untrack" if is_tracked else "📌 Track",
                callback_data=f"{'untrack' if is_tracked else 'track'}_{market_id}"
            ),
        ],
        [InlineKeyboardButton("📊 Orderbook", callback_data=f"orderbook_{market_id}")],
    ])


def alert_actions_keyboard(market_id: str) -> InlineKeyboardMarkup:
    """Build action buttons for an alert message."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔇 Mute", callback_data=f"mute_{market_id}"),
            InlineKeyboardButton("📌 Track", callback_data=f"track_{market_id}"),
            InlineKeyboardButton("📊 Orderbook", callback_data=f"orderbook_{market_id}"),
        ],
    ])


def whale_alert_keyboard(market_id: str, trader_address: str) -> InlineKeyboardMarkup:
    """Build action buttons for a whale alert."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👁 Track trader", callback_data=f"track_trader_{trader_address}"),
            InlineKeyboardButton("📊 View market", callback_data=f"view_{market_id}"),
        ],
    ])


def confirm_keyboard(action: str, target: str) -> InlineKeyboardMarkup:
    """Build a confirmation keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✓ Confirm", callback_data=f"confirm_{action}_{target}"),
            InlineKeyboardButton("✗ Cancel", callback_data="cancel"),
        ],
    ])


def export_keyboard() -> InlineKeyboardMarkup:
    """Build export options keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Format:", callback_data="noop")],
        [
            InlineKeyboardButton("CSV", callback_data="export_csv"),
            InlineKeyboardButton("JSON", callback_data="export_json"),
        ],
        [InlineKeyboardButton("Data:", callback_data="noop")],
        [
            InlineKeyboardButton("Alerts", callback_data="export_alerts"),
            InlineKeyboardButton("Trades", callback_data="export_trades"),
            InlineKeyboardButton("Watchlist", callback_data="export_watchlist"),
        ],
        [InlineKeyboardButton("📥 Generate & Download", callback_data="export_generate")],
        [InlineKeyboardButton("« Back", callback_data="main_menu")],
    ])
