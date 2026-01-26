"""
URL construction helpers for Polymarket.
"""


def market_url(event_slug: str, market_slug: str | None = None) -> str:
    """
    Construct a market URL.

    Args:
        event_slug: The event slug (e.g., "presidential-election-winner-2024")
        market_slug: Optional market slug for multi-market events

    Returns:
        Full Polymarket URL
    """
    if market_slug:
        return f"https://polymarket.com/event/{event_slug}/{market_slug}"
    return f"https://polymarket.com/event/{event_slug}"


def market_url_with_token(event_slug: str, token_id: str) -> str:
    """Construct market URL with token ID parameter."""
    return f"https://polymarket.com/event/{event_slug}?tid={token_id}"


def profile_url(wallet_address: str) -> str:
    """Construct a user profile URL."""
    return f"https://polymarket.com/profile/{wallet_address}"


def shorten_address(address: str, chars: int = 6) -> str:
    """Shorten a wallet address for display."""
    if len(address) <= chars * 2 + 3:
        return address
    return f"{address[:chars]}...{address[-chars:]}"
