"""
Gamma API client for market and event metadata.
"""

import asyncio
from typing import Any

import aiohttp

from ..utils.config import GAMMA_API_URL, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_BACKOFF_BASE
from ..utils.logger import logger
from .models import Market, Event, TraderProfile


class GammaClient:
    """Async client for Polymarket Gamma API."""

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

    async def _request(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Make HTTP request with retry logic."""
        if self._session is None:
            await self.start()

        url = f"{GAMMA_API_URL}{endpoint}"

        for attempt in range(MAX_RETRIES):
            try:
                async with self._session.get(url, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 429:
                        wait = RETRY_BACKOFF_BASE ** (attempt + 2)
                        logger.warning(f"Rate limited, waiting {wait}s")
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"Gamma API error {resp.status}: {await resp.text()}")
            except asyncio.TimeoutError:
                logger.warning(f"Gamma request timeout (attempt {attempt + 1})")
            except aiohttp.ClientError as e:
                logger.warning(f"Gamma client error (attempt {attempt + 1}): {e}")

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)

        return None

    async def get_markets(
        self,
        closed: bool = False,
        limit: int = 100,
        offset: int = 0,
        order: str = "volume24hr",
        ascending: bool = False,
    ) -> list[Market]:
        """
        Fetch markets from Gamma API.

        Args:
            closed: Include closed markets
            limit: Number of results
            offset: Pagination offset
            order: Sort field
            ascending: Sort direction

        Returns:
            List of Market objects
        """
        params = {
            "closed": str(closed).lower(),
            "limit": limit,
            "offset": offset,
            "order": order,
            "ascending": str(ascending).lower(),
        }

        data = await self._request("/markets", params)

        if not data or not isinstance(data, list):
            return []

        markets = []
        for item in data:
            try:
                market = Market.model_validate(item)
                markets.append(market)
            except Exception as e:
                logger.debug(f"Failed to parse market: {e}")

        return markets

    async def get_all_active_markets(self, max_markets: int = 5000) -> list[Market]:
        """Fetch all active markets using pagination."""
        all_markets: list[Market] = []
        offset = 0
        batch_size = 100

        while offset < max_markets:
            markets = await self.get_markets(
                closed=False,
                limit=batch_size,
                offset=offset,
            )

            if not markets:
                break

            all_markets.extend(markets)
            offset += batch_size

            if len(markets) < batch_size:
                break

        logger.info(f"Fetched {len(all_markets)} active markets")
        return all_markets

    async def get_market_by_slug(self, slug: str) -> Market | None:
        """Fetch a single market by slug."""
        data = await self._request(f"/markets/{slug}")

        if not data:
            return None

        try:
            return Market.model_validate(data)
        except Exception as e:
            logger.error(f"Failed to parse market {slug}: {e}")
            return None

    async def get_events(
        self,
        closed: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Event]:
        """Fetch events from Gamma API."""
        params = {
            "closed": str(closed).lower(),
            "limit": limit,
            "offset": offset,
        }

        data = await self._request("/events", params)

        if not data or not isinstance(data, list):
            return []

        events = []
        for item in data:
            try:
                event = Event.model_validate(item)
                events.append(event)
            except Exception as e:
                logger.debug(f"Failed to parse event: {e}")

        return events

    async def get_event_by_slug(self, slug: str) -> Event | None:
        """Fetch a single event by slug."""
        data = await self._request(f"/events/{slug}")

        if not data:
            return None

        try:
            return Event.model_validate(data)
        except Exception as e:
            logger.error(f"Failed to parse event {slug}: {e}")
            return None

    async def get_public_profile(self, address: str) -> TraderProfile | None:
        """Fetch a trader's public profile."""
        data = await self._request("/public-profile", {"address": address})

        if not data:
            return None

        try:
            return TraderProfile.model_validate(data)
        except Exception as e:
            logger.debug(f"Failed to parse profile {address}: {e}")
            return None
