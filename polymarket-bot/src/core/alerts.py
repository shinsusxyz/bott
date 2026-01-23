"""
Alert detection logic including counter-signals.
"""

from ..polymarket.models import Market, Trade, CounterSignalAlert, TraderStats


def check_counter_signal(
    trade: Trade,
    market: Market,
    trader_stats: TraderStats | None = None,
    min_amount: float = 500,
) -> CounterSignalAlert | None:
    """
    Alert when a whale bets against a low-odds outcome.

    Example: If YES is at 1% and someone buys NO (99%),
    this could indicate the low odds might be a "trap".
    """
    if trade.usdc_size < min_amount:
        return None

    if len(market.outcome_prices) < 2:
        return None

    yes_price = market.outcome_prices[0]
    no_price = market.outcome_prices[1]

    # Check if YES is low odds and trade is buying NO
    if yes_price <= 0.02 and trade.outcome.lower() == "no" and trade.side == "BUY":
        return CounterSignalAlert(
            market=market,
            trade=trade,
            low_odds_outcome="Yes",
            low_odds_price=yes_price,
            trader_stats=trader_stats,
        )

    # Check if NO is low odds and trade is buying YES
    if no_price <= 0.02 and trade.outcome.lower() == "yes" and trade.side == "BUY":
        return CounterSignalAlert(
            market=market,
            trade=trade,
            low_odds_outcome="No",
            low_odds_price=no_price,
            trader_stats=trader_stats,
        )

    return None
