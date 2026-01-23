"""
Message formatting for Telegram alerts.
"""

from datetime import datetime, timezone
from typing import Any

from ..polymarket.models import (
    PriceAlert,
    WhaleAlert,
    ArbitrageAlert,
    CounterSignalAlert,
    Market,
    TraderStats,
)
from ..core.aggregator import AlertBatch
from ..traders.smart_money import format_smart_money_badge


def format_price(price: float) -> str:
    """Format price as percentage."""
    return f"{price * 100:.2f}%"


def format_usd(amount: float) -> str:
    """Format USD amount."""
    if amount >= 1000000:
        return f"${amount/1000000:.1f}M"
    elif amount >= 1000:
        return f"${amount/1000:.1f}K"
    return f"${amount:.0f}"


def format_change(change: float | None) -> str:
    """Format percentage change with arrow."""
    if change is None:
        return ""
    arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
    return f"{arrow}{abs(change):.0f}%"


def format_timestamp(dt: datetime | None = None) -> str:
    """Format timestamp for display."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%H:%M UTC")


def format_date(dt: datetime | None) -> str:
    """Format date for display."""
    if dt is None:
        return "TBD"
    now = datetime.now(timezone.utc)
    delta = dt - now
    days = delta.days
    if days < 0:
        return "Ended"
    elif days == 0:
        return "Today"
    elif days == 1:
        return "Tomorrow"
    else:
        return f"{dt.strftime('%b %d')} ({days} days)"


def format_price_alert(alert: PriceAlert) -> str:
    """Format a single price alert."""
    market = alert.market
    outcome = alert.outcome

    # Price change
    change_1h = format_change(alert.price_change_1h) if alert.price_1h_ago else ""
    change_text = f" (was {format_price(alert.price_1h_ago)} 1h ago) {change_1h}" if alert.price_1h_ago else ""

    # End date
    end_date = format_date(market.end_date)

    lines = [
        f"🔴 LOW ODDS DETECTED",
        "",
        f"{market.question}",
        f"├ {outcome.name}: {format_price(outcome.price)}{change_text}",
        f"├ Vol: {format_usd(market.volume_24hr)} | Liq: {format_usd(market.liquidity)} | Spread: {format_price(market.spread)}",
        f"├ Ends: {end_date}",
        f"└ 🔗 {market.url}",
    ]

    return "\n".join(lines)


def format_whale_alert(alert: WhaleAlert) -> str:
    """Format a whale trade alert."""
    trade = alert.trade
    profile = alert.trader_profile
    stats = alert.trader_stats

    # Trader name
    name = profile.display_name if profile else trade.trader_address[:10] + "..."
    badge = format_smart_money_badge(stats)

    # Stats line
    stats_line = ""
    if stats:
        stats_line = f"├ Stats: {stats.win_rate*100:.0f}% win rate ({stats.total_trades} trades)"
        stats_line += f"\n├ Portfolio: {format_usd(stats.portfolio_value)} | PnL: {'+' if stats.realized_pnl >= 0 else ''}{format_usd(stats.realized_pnl)}"

    lines = [
        f"🐋 WHALE {trade.side} • {format_usd(trade.usdc_size)}",
        "",
        f"@{name} {badge} bought {trade.outcome}",
        f"├ Market: \"{trade.market_title}\"",
        f"├ Price: ${trade.price:.2f} | Shares: {trade.size:,.0f}",
    ]

    if stats_line:
        lines.append(stats_line)

    lines.extend([
        f"├ 👤 {profile.url if profile else trade.trader_url}",
        f"└ 🔗 {trade.market_url}",
    ])

    return "\n".join(lines)


def format_arbitrage_alert(alert: ArbitrageAlert) -> str:
    """Format an arbitrage alert."""
    market = alert.market
    profit = alert.potential_profit_percent

    lines = [
        f"⚖️ ARBITRAGE • ~{profit:.1f}% profit",
        "",
        f"\"{market.question}\"",
        f"├ YES: {format_price(alert.yes_price)} + NO: {format_price(alert.no_price)} = {alert.total*100:.1f}%",
        f"└ 🔗 {market.url}",
    ]

    return "\n".join(lines)


def format_counter_signal(alert: CounterSignalAlert) -> str:
    """Format a counter-signal alert."""
    market = alert.market
    trade = alert.trade
    stats = alert.trader_stats

    stats_info = ""
    if stats:
        stats_info = f"├ Trader: {stats.win_rate*100:.0f}% win rate, {format_usd(stats.portfolio_value)} portfolio"

    lines = [
        f"⚠️ COUNTER SIGNAL",
        "",
        f"\"{market.question}\" — {alert.low_odds_outcome} at {format_price(alert.low_odds_price)}",
        f"├ Whale bought {format_usd(trade.usdc_size)} of {trade.outcome} ({format_price(1 - alert.low_odds_price)})",
    ]

    if stats_info:
        lines.append(stats_info)

    lines.append(f"└ ⚡ Low odds might be a trap")

    return "\n".join(lines)


def format_batch(batch: AlertBatch, next_scan_time: str | None = None) -> str:
    """Format a batch of alerts into a single message."""
    timestamp = format_timestamp(batch.timestamp)

    lines = [
        f"📊 POLYMARKET ALERTS • {timestamp}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]

    # Price alerts
    for alert in batch.price_alerts:
        lines.append("")
        lines.append(format_price_alert(alert))
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    # Whale alerts
    for alert in batch.whale_alerts:
        lines.append("")
        lines.append(format_whale_alert(alert))
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    # Arbitrage alerts
    for alert in batch.arbitrage_alerts:
        lines.append("")
        lines.append(format_arbitrage_alert(alert))
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    # Counter signals
    for alert in batch.counter_signals:
        lines.append("")
        lines.append(format_counter_signal(alert))
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    # Footer
    lines.append("")
    footer = f"📈 {batch.total_count} alert{'s' if batch.total_count != 1 else ''}"
    if next_scan_time:
        footer += f" | Next scan: {next_scan_time}"
    lines.append(footer)

    return "\n".join(lines)


def format_welcome() -> str:
    """Format the welcome message."""
    return """👋 Welcome to Polymarket Alerts!

I find opportunities others miss:
📉 Low odds markets (< 1%)
🐋 Whale trades (> $30)
⚖️ Arbitrage opportunities
⚠️ Counter-signals

✨ Everything works out of the box.

━━━━━━━━━━━━━━━━━━━━━━

Quick setup (optional):
Select categories below, then start monitoring."""


def format_status(stats: dict[str, Any]) -> str:
    """Format bot status message."""
    timestamp = format_timestamp()

    return f"""📊 Bot Status

📈 Markets monitored: {stats.get('markets_scanned', 0)}
🔔 Alerts sent (session): {stats.get('alerts_generated', 0)}
⚡ Last scan: {stats.get('last_scan_ms', 0)}ms
💾 Cache entries: {stats.get('cache_size', 0)}

⏰ {timestamp}"""


def format_settings(settings: dict[str, Any]) -> str:
    """Format current settings summary."""
    cats = settings.get("categories", [])
    cat_str = ", ".join(c.title() for c in cats) if cats else "None"

    return f"""⚙️ SETTINGS

📊 Price threshold: {settings.get('price_threshold', 0.01) * 100}%
💰 Min volume: {format_usd(settings.get('min_volume', 1000))}
💧 Min liquidity: {format_usd(settings.get('min_liquidity', 5000))}

📁 Categories: {cat_str}

🐋 Whale alerts: {'ON' if settings.get('whale_alerts_enabled', True) else 'OFF'}
⚖️ Arbitrage: {'ON' if settings.get('arbitrage_alerts', True) else 'OFF'}"""
