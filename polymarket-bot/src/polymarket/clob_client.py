"""
CLOB API client for real-time prices and orderbook data.
"""

import asyncio
from typing import Any

import aiohttp

from ..utils.config import CLOB_API_URL, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_BACKOFF_BASE
from ..utils.logger import logger


class CLOBClient:
    """Async client for Polymarket CLOB API."""

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

        url = f"{CLOB_API_URL}{endpoint}"

        for attempt in range(MAX_RETRIES):
            try:
                async with self._session.get(url, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 429:
                        wait = RETRY_BACKOFF_BASE ** (attempt + 2)
                        logger.warning(f"CLOB rate limited, waiting {wait}s")
                        await asyncio.sleep(wait)
                    else:
                        text = await resp.text()
                        logger.debug(f"CLOB API error {resp.status}: {text}")
            except asyncio.TimeoutError:
                logger.warning(f"CLOB request timeout (attempt {attempt + 1})")
            except aiohttp.ClientError as e:
                logger.warning(f"CLOB client error (attempt {attempt + 1}): {e}")

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)

        return None

    async def _post(self, endpoint: str, data: Any) -> Any:
        """Make POST request with retry logic."""
        if self._session is None:
            await self.start()

        url = f"{CLOB_API_URL}{endpoint}"

        for attempt in range(MAX_RETRIES):
            try:
                async with self._session.post(url, json=data) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 429:
                        wait = RETRY_BACKOFF_BASE ** (attempt + 2)
                        logger.warning(f"CLOB rate limited, waiting {wait}s")
                        await asyncio.sleep(wait)
            except asyncio.TimeoutError:
                logger.warning(f"CLOB POST timeout (attempt {attempt + 1})")
            except aiohttp.ClientError as e:
                logger.warning(f"CLOB POST error (attempt {attempt + 1}): {e}")

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)

        return None

    async def get_price(self, token_id: str, side: str = "BUY") -> float | None:
        """Get current price for a token."""
        data = await self._get("/price", {"token_id": token_id, "side": side})

        if data and "price" in data:
            try:
                return float(data["price"])
            except (ValueError, TypeError):
                pass
        return None

    async def get_midpoint(self, token_id: str) -> float | None:
        """Get midpoint price for a token."""
        data = await self._get("/midpoint", {"token_id": token_id})

        if data and "mid" in data:
            try:
                return float(data["mid"])
            except (ValueError, TypeError):
                pass
        return None

    async def get_orderbook(self, token_id: str) -> dict[str, Any] | None:
        """Get orderbook for a token."""
        return await self._get("/book", {"token_id": token_id})

    async def get_orderbooks_batch(self, token_ids: list[str]) -> list[dict[str, Any]]:
        """Get orderbooks for multiple tokens."""
        data = [{"token_id": tid} for tid in token_ids]
        result = await self._post("/books", data)
        return result if isinstance(result, list) else []

    async def get_prices_batch(
        self, token_ids: list[str], side: str = "BUY"
    ) -> dict[str, float]:
        """Get prices for multiple tokens."""
        data = [{"token_id": tid, "side": side} for tid in token_ids]
        result = await self._post("/prices", data)

        prices: dict[str, float] = {}
        if isinstance(result, dict):
            for token_id, price_data in result.items():
                try:
                    if isinstance(price_data, (int, float)):
                        prices[token_id] = float(price_data)
                    elif isinstance(price_data, dict) and "price" in price_data:
                        prices[token_id] = float(price_data["price"])
                except (ValueError, TypeError):
                    pass

        return prices

    async def get_spreads_batch(self, token_ids: list[str]) -> dict[str, float]:
        """Get spreads for multiple tokens."""
        data = [{"token_id": tid} for tid in token_ids]
        result = await self._post("/spreads", data)

        spreads: dict[str, float] = {}
        if isinstance(result, dict):
            for token_id, spread_data in result.items():
                try:
                    if isinstance(spread_data, (int, float)):
                        spreads[token_id] = float(spread_data)
                    elif isinstance(spread_data, dict) and "spread" in spread_data:
                        spreads[token_id] = float(spread_data["spread"])
                except (ValueError, TypeError):
                    pass

        return spreads

    async def get_price_history(
        self,
        token_id: str,
        interval: str = "1d",
        fidelity: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get price history for a token.

        Args:
            token_id: The token ID
            interval: Time interval (1m, 1h, 6h, 1d, 1w, max)
            fidelity: Resolution in minutes

        Returns:
            List of price history points
        """
        data = await self._get(
            "/prices-history",
            {"market": token_id, "interval": interval, "fidelity": fidelity},
        )
        return data.get("history", []) if isinstance(data, dict) else []
