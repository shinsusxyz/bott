"""
Data API client for trades, positions, and activity.
"""

import asyncio
from typing import Any

import aiohttp

from ..utils.config import DATA_API_URL, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_BACKOFF_BASE
from ..utils.logger import logger
from .models import Trade, Position


class DataClient:
    """Async client for Polymarket Data API."""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

    async def start(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Make GET request with retry logic."""
        if self._session is None:
            await self.start()

        url = f"{DATA_API_URL}{endpoint}"

        for attempt in range(MAX_RETRIES):
            try:
                async with self._session.get(url, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 429:
                        wait = RETRY_BACKOFF_BASE ** (attempt + 2)
                        logger.warning(f"Data API rate limited, waiting {wait}s")
                        await asyncio.sleep(wait)
                    else:
                        text = await resp.text()
                        logger.debug(f"Data API error {resp.status}: {text}")
            except asyncio.TimeoutError:
                logger.warning(f"Data API timeout (attempt {attempt + 1})")
            except aiohttp.ClientError as e:
                logger.warning(f"Data API error (attempt {attempt + 1}): {e}")

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)

        return None

    async def get_user_activity(
        self,
        wallet_address: str,
        limit: int = 100,
        offset: int = 0,
        side: str | None = None,
    ) -> list[Trade]:
        """
        Get user's trading activity.

        Args:
            wallet_address: User's wallet address
            limit: Number of results
            offset: Pagination offset
            side: Optional filter (BUY or SELL)

        Returns:
            List of Trade objects
        """
        params: dict[str, Any] = {
            "user": wallet_address,
            "limit": limit,
            "offset": offset,
        }
        if side:
            params["side"] = side

        data = await self._get("/activity", params)

        if not data or not isinstance(data, list):
            return []

        trades = []
        for item in data:
            try:
                trade = Trade.model_validate(item)
                trades.append(trade)
            except Exception as e:
                logger.debug(f"Failed to parse trade: {e}")

        return trades

    async def get_user_positions(self, wallet_address: str) -> list[Position]:
        """Get user's current positions."""
        data = await self._get("/positions", {"user": wallet_address})

        if not data or not isinstance(data, list):
            return []

        positions = []
        for item in data:
            try:
                position = Position.model_validate(item)
                positions.append(position)
            except Exception as e:
                logger.debug(f"Failed to parse position: {e}")

        return positions

    async def get_recent_trades(
        self,
        limit: int = 100,
        condition_id: str | None = None,
    ) -> list[Trade]:
        """
        Get recent trades across all markets.

        Args:
            limit: Number of trades
            condition_id: Optional market filter

        Returns:
            List of Trade objects
        """
        params: dict[str, Any] = {"limit": limit}
        if condition_id:
            params["market"] = condition_id

        data = await self._get("/trades", params)

        if not data or not isinstance(data, list):
            return []

        trades = []
        for item in data:
            try:
                trade = Trade.model_validate(item)
                trades.append(trade)
            except Exception as e:
                logger.debug(f"Failed to parse trade: {e}")

        return trades

    async def get_leaderboard(self) -> list[dict[str, Any]]:
        """Get the trading leaderboard."""
        data = await self._get("/v1/leaderboard")
        return data if isinstance(data, list) else []

    async def calculate_trader_stats(self, wallet_address: str) -> dict[str, Any]:
        """
        Calculate trading statistics for a user.

        Returns dict with:
            - total_trades
            - win_rate
            - portfolio_value
            - realized_pnl
        """
        stats = {
            "address": wallet_address,
            "total_trades": 0,
            "win_rate": 0.0,
            "portfolio_value": 0.0,
            "realized_pnl": 0.0,
        }

        # Get positions for portfolio value
        positions = await self.get_user_positions(wallet_address)
        if positions:
            stats["portfolio_value"] = sum(p.current_value for p in positions)
            stats["realized_pnl"] = sum(p.realized_pnl for p in positions)

        # Get activity for trade count and win rate
        trades = await self.get_user_activity(wallet_address, limit=500)
        if trades:
            stats["total_trades"] = len(trades)

            # Simple win rate: positive PnL positions / total positions
            winning_positions = sum(1 for p in positions if p.cash_pnl > 0)
            total_positions = len(positions)
            if total_positions > 0:
                stats["win_rate"] = winning_positions / total_positions

        return stats
