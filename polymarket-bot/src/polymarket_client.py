"""
Polymarket API client for fetching markets and prices.
Uses both Gamma API (market metadata) and CLOB API (real-time prices).
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

from .config import (
    GAMMA_API_BASE_URL,
    CLOB_API_BASE_URL,
    REQUEST_TIMEOUT_SECONDS,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
    MARKETS_BATCH_SIZE,
)

logger = logging.getLogger(__name__)


@dataclass
class Outcome:
    """Represents a market outcome with its price."""
    name: str
    token_id: str
    price: float


@dataclass
class Market:
    """Represents a Polymarket market."""
    id: str
    condition_id: str
    question: str
    description: str
    outcomes: list[Outcome]
    tags: list[str]
    slug: str
    active: bool
    closed: bool
    archived: bool
    resolved: bool
    url: str

    @property
    def is_tradeable(self) -> bool:
        """Check if market is currently tradeable (not resolved/closed)."""
        return self.active and not self.closed and not self.archived and not self.resolved


class PolymarketClient:
    """Async client for interacting with Polymarket APIs."""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)

    async def __aenter__(self) -> "PolymarketClient":
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def start(self) -> None:
        """Initialize the HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _request_with_retry(
        self,
        url: str,
        params: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[Any]:
        """Make HTTP request with exponential backoff retry."""
        if self._session is None:
            await self.start()

        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                async with self._session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        # Rate limited - wait longer
                        wait_time = RETRY_BACKOFF_BASE ** (attempt + 2)
                        logger.warning(f"Rate limited, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                    else:
                        text = await response.text()
                        logger.error(f"API error {response.status}: {text}")
                        last_error = Exception(f"API error: {response.status}")
            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(f"Request timeout (attempt {attempt + 1})")
            except aiohttp.ClientError as e:
                last_error = e
                logger.warning(f"Client error (attempt {attempt + 1}): {e}")

            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF_BASE ** attempt
                await asyncio.sleep(wait_time)

        raise last_error or Exception("Request failed after retries")

    async def fetch_active_markets(self, limit: int = MARKETS_BATCH_SIZE, offset: int = 0) -> list[Market]:
        """
        Fetch active, non-closed markets from Gamma API.

        Args:
            limit: Number of markets to fetch per request
            offset: Pagination offset

        Returns:
            List of Market objects
        """
        url = f"{GAMMA_API_BASE_URL}/markets"
        params = {
            "active": "true",
            "closed": "false",
            "archived": "false",
            "limit": limit,
            "offset": offset,
        }

        try:
            data = await self._request_with_retry(url, params)

            if not isinstance(data, list):
                logger.error(f"Unexpected response format: {type(data)}")
                return []

            markets = []
            for item in data:
                market = self._parse_market(item)
                if market:
                    markets.append(market)

            return markets

        except Exception as e:
            logger.error(f"Failed to fetch markets: {e}")
            return []

    async def fetch_all_active_markets(self) -> list[Market]:
        """
        Fetch all active markets using pagination.

        Returns:
            List of all active Market objects
        """
        all_markets: list[Market] = []
        offset = 0

        while True:
            markets = await self.fetch_active_markets(
                limit=MARKETS_BATCH_SIZE,
                offset=offset
            )

            if not markets:
                break

            all_markets.extend(markets)
            offset += MARKETS_BATCH_SIZE

            # Safety limit to prevent infinite loops
            if offset > 10000:
                logger.warning("Reached safety limit of 10000 markets")
                break

        logger.info(f"Fetched {len(all_markets)} active markets")
        return all_markets

    async def get_market_prices(self, token_ids: list[str]) -> dict[str, float]:
        """
        Fetch current prices for multiple tokens from CLOB API.

        Args:
            token_ids: List of token IDs to fetch prices for

        Returns:
            Dict mapping token_id to current price
        """
        if not token_ids:
            return {}

        prices: dict[str, float] = {}

        # CLOB API supports batch price fetching
        url = f"{CLOB_API_BASE_URL}/prices"

        try:
            # Fetch prices in batches to avoid URL length limits
            batch_size = 50
            for i in range(0, len(token_ids), batch_size):
                batch = token_ids[i:i + batch_size]
                params = {"token_ids": ",".join(batch)}

                data = await self._request_with_retry(url, params)

                if isinstance(data, dict):
                    for token_id, price_data in data.items():
                        if isinstance(price_data, (int, float)):
                            prices[token_id] = float(price_data)
                        elif isinstance(price_data, dict) and "price" in price_data:
                            prices[token_id] = float(price_data["price"])

        except Exception as e:
            logger.warning(f"Failed to fetch prices from CLOB API: {e}")
            # Prices might already be in the Gamma response

        return prices

    async def get_single_price(self, token_id: str) -> float | None:
        """
        Fetch price for a single token.

        Args:
            token_id: The token ID to fetch price for

        Returns:
            Current price or None if unavailable
        """
        url = f"{CLOB_API_BASE_URL}/price"
        params = {"token_id": token_id, "side": "BUY"}

        try:
            data = await self._request_with_retry(url, params)
            if isinstance(data, dict) and "price" in data:
                return float(data["price"])
        except Exception as e:
            logger.debug(f"Failed to get price for {token_id}: {e}")

        return None

    def _parse_market(self, data: dict[str, Any]) -> Market | None:
        """
        Parse raw API response into Market object.

        Args:
            data: Raw market data from API

        Returns:
            Market object or None if parsing fails
        """
        try:
            market_id = data.get("id", "")
            condition_id = data.get("conditionId", data.get("condition_id", ""))
            question = data.get("question", "")
            description = data.get("description", "")
            slug = data.get("slug", "")

            # Parse outcomes and prices
            outcomes: list[Outcome] = []

            # Parse outcome names
            outcome_names = data.get("outcomes", [])
            if isinstance(outcome_names, str):
                try:
                    outcome_names = json.loads(outcome_names)
                except json.JSONDecodeError:
                    outcome_names = outcome_names.split(",")

            # Parse token IDs
            token_ids = data.get("clobTokenIds", [])
            if isinstance(token_ids, str):
                try:
                    token_ids = json.loads(token_ids)
                except json.JSONDecodeError:
                    token_ids = []

            # Parse prices
            outcome_prices = data.get("outcomePrices", [])
            if isinstance(outcome_prices, str):
                try:
                    outcome_prices = json.loads(outcome_prices)
                except json.JSONDecodeError:
                    outcome_prices = []

            # Build outcomes list
            for i, name in enumerate(outcome_names):
                token_id = token_ids[i] if i < len(token_ids) else ""
                price = float(outcome_prices[i]) if i < len(outcome_prices) else 0.0
                outcomes.append(Outcome(
                    name=str(name).strip(),
                    token_id=token_id,
                    price=price
                ))

            # Parse tags
            tags: list[str] = []
            raw_tags = data.get("tags", [])
            if isinstance(raw_tags, list):
                for tag in raw_tags:
                    if isinstance(tag, dict):
                        tags.append(tag.get("label", tag.get("slug", "")))
                    elif isinstance(tag, str):
                        tags.append(tag)

            # Determine market status
            active = data.get("active", True)
            closed = data.get("closed", False)
            archived = data.get("archived", False)

            # Check for resolved status from multiple possible fields
            resolved = data.get("resolved", False)
            if not resolved:
                resolution = data.get("resolution", data.get("resolutionSource", ""))
                resolved = bool(resolution)

            # Build URL
            url = f"https://polymarket.com/event/{slug}" if slug else ""

            return Market(
                id=market_id,
                condition_id=condition_id,
                question=question,
                description=description,
                outcomes=outcomes,
                tags=tags,
                slug=slug,
                active=active,
                closed=closed,
                archived=archived,
                resolved=resolved,
                url=url
            )

        except Exception as e:
            logger.debug(f"Failed to parse market: {e}")
            return None
