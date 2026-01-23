"""
Smart money classification and analysis.
"""

from ..polymarket.models import TraderStats


def is_smart_money(stats: TraderStats | None) -> bool:
    """
    Determine if a trader qualifies as "smart money".

    Criteria:
    - 20+ trades with 65%+ win rate, OR
    - $50,000+ portfolio value
    """
    if not stats:
        return False

    return (
        (stats.total_trades >= 20 and stats.win_rate >= 0.65)
        or stats.portfolio_value >= 50000
    )


def get_smart_money_tier(stats: TraderStats | None) -> str | None:
    """
    Get the tier of smart money classification.

    Returns:
        "elite" - Top tier (both criteria met)
        "high" - $50k+ portfolio
        "consistent" - 65%+ win rate with 20+ trades
        None - Not smart money
    """
    if not stats:
        return None

    high_portfolio = stats.portfolio_value >= 50000
    high_winrate = stats.total_trades >= 20 and stats.win_rate >= 0.65

    if high_portfolio and high_winrate:
        return "elite"
    elif high_portfolio:
        return "high"
    elif high_winrate:
        return "consistent"

    return None


def format_smart_money_badge(stats: TraderStats | None) -> str:
    """Get emoji badge for smart money tier."""
    tier = get_smart_money_tier(stats)

    badges = {
        "elite": "👑",
        "high": "💎",
        "consistent": "🧠",
    }

    return badges.get(tier, "")
