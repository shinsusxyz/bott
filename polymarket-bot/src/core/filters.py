"""
Market filtering logic for categories and quality checks.
"""

from ..polymarket.models import Market
from ..utils.config import (
    POLITICS_KEYWORDS,
    WEATHER_KEYWORDS,
    TECH_KEYWORDS,
    AI_KEYWORDS,
    CRYPTO_KEYWORDS,
    ALL_INCLUDED_KEYWORDS,
)


def get_searchable_text(market: Market) -> str:
    """Extract all searchable text from a market."""
    parts = [
        market.question,
        market.description,
        " ".join(market.tags),
        market.slug.replace("-", " "),
    ]
    for outcome in market.outcomes:
        parts.append(outcome)
    return " ".join(parts).lower()


def is_crypto_market(market: Market) -> bool:
    """Check if a market is crypto-related (should be excluded)."""
    text = get_searchable_text(market)

    # Strong indicators
    strong = {"bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency", "blockchain", "defi", "nft"}
    for keyword in strong:
        if keyword in text:
            return True

    # Multiple weak indicators
    matches = sum(1 for kw in CRYPTO_KEYWORDS if kw in text)
    return matches >= 2


def detect_category(market: Market) -> str | None:
    """Detect which category a market belongs to."""
    text = get_searchable_text(market)

    categories = {
        "Politics": POLITICS_KEYWORDS,
        "Weather": WEATHER_KEYWORDS,
        "Technology": TECH_KEYWORDS,
        "AI": AI_KEYWORDS,
    }

    best_category = None
    best_matches = 0

    for name, keywords in categories.items():
        matches = sum(1 for kw in keywords if kw in text)
        if matches > best_matches:
            best_matches = matches
            best_category = name

    return best_category if best_matches >= 1 else None


def matches_categories(market: Market, enabled_categories: list[str] | None = None) -> bool:
    """Check if market matches enabled categories."""
    text = get_searchable_text(market)

    if enabled_categories:
        category_map = {
            "politics": POLITICS_KEYWORDS,
            "weather": WEATHER_KEYWORDS,
            "tech": TECH_KEYWORDS,
            "ai": AI_KEYWORDS,
        }
        for cat in enabled_categories:
            keywords = category_map.get(cat.lower(), set())
            if any(kw in text for kw in keywords):
                return True
        return False

    return any(kw in text for kw in ALL_INCLUDED_KEYWORDS)


def is_quality_market(
    market: Market,
    min_volume: float = 1000,
    min_liquidity: float = 5000,
    max_spread: float = 0.03,
) -> bool:
    """Check if market meets quality criteria."""
    return (
        market.volume_24hr >= min_volume
        and market.liquidity >= min_liquidity
        and market.spread <= max_spread
        and market.is_tradeable
    )


def check_arbitrage(market: Market) -> tuple[float, float, float] | None:
    """
    Check if YES + NO prices > 100% (arbitrage opportunity).

    Returns (yes_price, no_price, total) if opportunity exists, else None.
    """
    if len(market.outcome_prices) < 2:
        return None

    yes_price = market.outcome_prices[0]
    no_price = market.outcome_prices[1]
    total = yes_price + no_price

    if total > 1.01:  # >1% opportunity
        return (yes_price, no_price, total)

    return None


def filter_market(
    market: Market,
    price_threshold: float = 0.01,
    min_volume: float = 1000,
    min_liquidity: float = 5000,
    max_spread: float = 0.03,
    enabled_categories: list[str] | None = None,
    check_quality: bool = True,
) -> tuple[bool, str, str | None]:
    """
    Apply all filters to a market.

    Returns:
        (passed, reason, category)
    """
    # Check if tradeable
    if not market.is_tradeable:
        return (False, "Market is resolved or closed", None)

    # Check crypto exclusion
    if is_crypto_market(market):
        return (False, "Market is crypto-related", None)

    # Check category match
    if not matches_categories(market, enabled_categories):
        return (False, "Does not match categories", None)

    # Check quality (optional)
    if check_quality and not is_quality_market(market, min_volume, min_liquidity, max_spread):
        return (False, "Does not meet quality criteria", None)

    # Detect category
    category = detect_category(market)

    # Check for low odds
    has_low_odds = any(
        0 < price <= price_threshold
        for price in market.outcome_prices
    )

    if not has_low_odds:
        return (False, "No low odds outcomes", category)

    return (True, "Passed all filters", category)
