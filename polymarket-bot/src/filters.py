"""
Market filtering logic for category matching and exclusion rules.
"""

import logging
from typing import NamedTuple

from .config import (
    POLITICS_KEYWORDS,
    WEATHER_KEYWORDS,
    TECH_KEYWORDS,
    AI_KEYWORDS,
    CRYPTO_KEYWORDS,
    ALL_INCLUDED_KEYWORDS,
    PRICE_THRESHOLD,
)
from .polymarket_client import Market, Outcome

logger = logging.getLogger(__name__)


class Category(NamedTuple):
    """Represents a detected market category."""
    name: str
    confidence: float  # 0.0 to 1.0 based on keyword matches


def get_searchable_text(market: Market) -> str:
    """
    Extract all searchable text from a market for keyword matching.

    Args:
        market: The market to extract text from

    Returns:
        Lowercase combined text for searching
    """
    parts = [
        market.question,
        market.description,
        " ".join(market.tags),
        market.slug.replace("-", " "),
    ]

    # Include outcome names
    for outcome in market.outcomes:
        parts.append(outcome.name)

    return " ".join(parts).lower()


def is_crypto_market(market: Market) -> bool:
    """
    Check if a market is crypto-related (should be excluded).

    Args:
        market: The market to check

    Returns:
        True if the market is crypto-related
    """
    text = get_searchable_text(market)

    # Check for crypto keywords
    matches = sum(1 for keyword in CRYPTO_KEYWORDS if keyword in text)

    # Strong signal if multiple crypto keywords match
    if matches >= 2:
        return True

    # Single match but it's a strong indicator
    strong_indicators = {"bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency", "blockchain", "defi", "nft"}
    for indicator in strong_indicators:
        if indicator in text:
            return True

    return False


def detect_category(market: Market) -> Category | None:
    """
    Detect which category a market belongs to.

    Args:
        market: The market to categorize

    Returns:
        Category with name and confidence, or None if no match
    """
    text = get_searchable_text(market)

    categories = {
        "Politics": POLITICS_KEYWORDS,
        "Weather": WEATHER_KEYWORDS,
        "Technology": TECH_KEYWORDS,
        "AI": AI_KEYWORDS,
    }

    best_category: str | None = None
    best_score = 0
    best_matches = 0

    for category_name, keywords in categories.items():
        matches = sum(1 for keyword in keywords if keyword in text)

        if matches > best_matches:
            best_matches = matches
            best_category = category_name
            # Confidence based on number of matches
            best_score = min(1.0, matches / 3.0)  # 3+ matches = full confidence

    if best_category and best_matches >= 1:
        return Category(name=best_category, confidence=best_score)

    return None


def matches_categories(market: Market) -> bool:
    """
    Check if market matches any of our target categories.

    Args:
        market: The market to check

    Returns:
        True if market matches at least one category
    """
    text = get_searchable_text(market)

    # Check if any included keyword matches
    for keyword in ALL_INCLUDED_KEYWORDS:
        if keyword in text:
            return True

    return False


def is_market_resolved(market: Market) -> bool:
    """
    Check if a market has been resolved/closed.

    Args:
        market: The market to check

    Returns:
        True if the market is no longer active
    """
    return not market.is_tradeable


def get_low_odds_outcomes(
    market: Market,
    threshold: float = PRICE_THRESHOLD
) -> list[Outcome]:
    """
    Find all outcomes with prices at or below the threshold.

    Args:
        market: The market to check
        threshold: Price threshold (default 0.001 = 0.1%)

    Returns:
        List of outcomes with low odds
    """
    return [
        outcome for outcome in market.outcomes
        if outcome.price <= threshold and outcome.price > 0
    ]


class FilterResult(NamedTuple):
    """Result of market filtering."""
    passed: bool
    reason: str
    category: Category | None = None
    low_odds_outcomes: list[Outcome] | None = None


def filter_market(market: Market) -> FilterResult:
    """
    Apply all filters to determine if a market should trigger an alert.

    Args:
        market: The market to filter

    Returns:
        FilterResult with pass/fail status and reason
    """
    # 1. Check if resolved/closed
    if is_market_resolved(market):
        return FilterResult(
            passed=False,
            reason="Market is resolved or closed"
        )

    # 2. Check if crypto (exclude)
    if is_crypto_market(market):
        return FilterResult(
            passed=False,
            reason="Market is crypto-related"
        )

    # 3. Check category match
    if not matches_categories(market):
        return FilterResult(
            passed=False,
            reason="Market does not match any target category"
        )

    # 4. Check for low odds outcomes
    low_odds = get_low_odds_outcomes(market)
    if not low_odds:
        return FilterResult(
            passed=False,
            reason="No outcomes at or below price threshold"
        )

    # 5. All checks passed - detect category for alert
    category = detect_category(market)

    return FilterResult(
        passed=True,
        reason="Market passed all filters",
        category=category,
        low_odds_outcomes=low_odds
    )


def filter_markets(markets: list[Market]) -> list[tuple[Market, FilterResult]]:
    """
    Apply filters to a list of markets.

    Args:
        markets: List of markets to filter

    Returns:
        List of (market, filter_result) tuples that passed all filters
    """
    results: list[tuple[Market, FilterResult]] = []

    for market in markets:
        result = filter_market(market)
        if result.passed:
            results.append((market, result))

    logger.debug(f"Filtered {len(results)} markets from {len(markets)} total")
    return results
