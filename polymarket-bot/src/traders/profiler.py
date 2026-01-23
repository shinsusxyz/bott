"""
Trader profiling and statistics.
"""

from ..polymarket.gamma_client import GammaClient
from ..polymarket.data_client import DataClient
from ..polymarket.models import TraderProfile, TraderStats
from ..utils.logger import logger


class TraderProfiler:
    """Fetches and analyzes trader profiles and statistics."""

    def __init__(self, gamma: GammaClient, data_client: DataClient) -> None:
        self.gamma = gamma
        self.data_client = data_client
        self._profile_cache: dict[str, TraderProfile] = {}
        self._stats_cache: dict[str, TraderStats] = {}

    async def get_profile(self, address: str) -> TraderProfile | None:
        """Get trader profile with caching."""
        if address in self._profile_cache:
            return self._profile_cache[address]

        profile = await self.gamma.get_public_profile(address)
        if profile:
            self._profile_cache[address] = profile
            # Limit cache size
            if len(self._profile_cache) > 1000:
                oldest = list(self._profile_cache.keys())[0]
                del self._profile_cache[oldest]

        return profile

    async def get_stats(self, address: str, refresh: bool = False) -> TraderStats | None:
        """Get trader statistics with caching."""
        if not refresh and address in self._stats_cache:
            return self._stats_cache[address]

        try:
            stats_dict = await self.data_client.calculate_trader_stats(address)
            stats = TraderStats.model_validate(stats_dict)

            self._stats_cache[address] = stats
            # Limit cache size
            if len(self._stats_cache) > 1000:
                oldest = list(self._stats_cache.keys())[0]
                del self._stats_cache[oldest]

            return stats
        except Exception as e:
            logger.debug(f"Failed to get stats for {address}: {e}")
            return None

    async def get_full_profile(
        self, address: str
    ) -> tuple[TraderProfile | None, TraderStats | None]:
        """Get both profile and stats for a trader."""
        profile = await self.get_profile(address)
        stats = await self.get_stats(address)
        return profile, stats

    def is_smart_money(self, stats: TraderStats | None) -> bool:
        """Check if trader qualifies as smart money."""
        if not stats:
            return False
        return stats.is_smart_money

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._profile_cache.clear()
        self._stats_cache.clear()
