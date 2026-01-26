"""
SQLite database operations using aiosqlite.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from ..utils.config import DATABASE_PATH
from ..utils.logger import logger


SCHEMA = """
-- User settings
CREATE TABLE IF NOT EXISTS settings (
    user_id INTEGER PRIMARY KEY,
    price_threshold REAL DEFAULT 0.01,
    min_volume REAL DEFAULT 1000,
    min_liquidity REAL DEFAULT 5000,
    max_spread REAL DEFAULT 0.03,
    scan_interval INTEGER DEFAULT 60,
    whale_threshold REAL DEFAULT 30,
    categories TEXT DEFAULT '["politics","weather","tech","ai"]',
    whale_alerts_enabled INTEGER DEFAULT 1,
    smart_money_only INTEGER DEFAULT 0,
    arbitrage_alerts INTEGER DEFAULT 1,
    counter_signals INTEGER DEFAULT 1,
    resolution_alerts INTEGER DEFAULT 1,
    digest_enabled INTEGER DEFAULT 0,
    digest_time TEXT DEFAULT '09:00',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Watchlist
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    market_id TEXT,
    condition_id TEXT,
    event_slug TEXT,
    market_slug TEXT,
    title TEXT,
    alert_threshold REAL,
    alert_on_any_movement INTEGER DEFAULT 0,
    muted INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, market_id)
);

-- Tracked traders
CREATE TABLE IF NOT EXISTS tracked_traders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    trader_address TEXT,
    trader_name TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, trader_address)
);

-- Alert history
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    alert_type TEXT,
    market_id TEXT,
    condition_id TEXT,
    event_slug TEXT,
    market_slug TEXT,
    title TEXT,
    price_at_alert REAL,
    data_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Muted markets
CREATE TABLE IF NOT EXISTS muted_markets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    market_id TEXT,
    muted_until DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, market_id)
);

-- Price history cache
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT,
    token_id TEXT,
    price REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_price_history_market ON price_history(market_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_tracked_traders_user ON tracked_traders(user_id);
"""


class Database:
    """Async SQLite database wrapper."""

    def __init__(self, db_path: Path = DATABASE_PATH) -> None:
        self.db_path = db_path
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Connect to the database and initialize schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row

        await self._connection.executescript(SCHEMA)
        await self._connection.commit()

        logger.info(f"Database connected: {self.db_path}")

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def execute(self, query: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Execute a query."""
        if not self._connection:
            await self.connect()
        return await self._connection.execute(query, params)

    async def executemany(self, query: str, params: list[tuple]) -> None:
        """Execute a query with multiple parameter sets."""
        if not self._connection:
            await self.connect()
        await self._connection.executemany(query, params)
        await self._connection.commit()

    async def fetchone(self, query: str, params: tuple = ()) -> dict[str, Any] | None:
        """Fetch a single row as dict."""
        cursor = await self.execute(query, params)
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def fetchall(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Fetch all rows as list of dicts."""
        cursor = await self.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def commit(self) -> None:
        """Commit the current transaction."""
        if self._connection:
            await self._connection.commit()

    # Settings operations

    async def get_settings(self, user_id: int) -> dict[str, Any]:
        """Get user settings, creating defaults if needed."""
        row = await self.fetchone(
            "SELECT * FROM settings WHERE user_id = ?", (user_id,)
        )

        if row:
            if isinstance(row.get("categories"), str):
                row["categories"] = json.loads(row["categories"])
            return row

        # Create default settings
        await self.execute(
            "INSERT INTO settings (user_id) VALUES (?)", (user_id,)
        )
        await self.commit()

        return await self.get_settings(user_id)

    async def update_settings(self, user_id: int, **kwargs: Any) -> None:
        """Update user settings."""
        if "categories" in kwargs and isinstance(kwargs["categories"], list):
            kwargs["categories"] = json.dumps(kwargs["categories"])

        kwargs["updated_at"] = datetime.utcnow().isoformat()

        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = tuple(kwargs.values()) + (user_id,)

        await self.execute(
            f"UPDATE settings SET {fields} WHERE user_id = ?", values
        )
        await self.commit()

    # Watchlist operations

    async def get_watchlist(self, user_id: int) -> list[dict[str, Any]]:
        """Get user's watchlist."""
        return await self.fetchall(
            "SELECT * FROM watchlist WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )

    async def add_to_watchlist(
        self,
        user_id: int,
        market_id: str,
        condition_id: str,
        event_slug: str,
        market_slug: str,
        title: str,
        alert_threshold: float | None = None,
    ) -> bool:
        """Add a market to the watchlist."""
        try:
            await self.execute(
                """
                INSERT OR REPLACE INTO watchlist
                (user_id, market_id, condition_id, event_slug, market_slug, title, alert_threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, market_id, condition_id, event_slug, market_slug, title, alert_threshold),
            )
            await self.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to add to watchlist: {e}")
            return False

    async def remove_from_watchlist(self, user_id: int, market_id: str) -> bool:
        """Remove a market from the watchlist."""
        try:
            await self.execute(
                "DELETE FROM watchlist WHERE user_id = ? AND market_id = ?",
                (user_id, market_id),
            )
            await self.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to remove from watchlist: {e}")
            return False

    # Tracked traders operations

    async def get_tracked_traders(self, user_id: int) -> list[dict[str, Any]]:
        """Get user's tracked traders."""
        return await self.fetchall(
            "SELECT * FROM tracked_traders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )

    async def add_tracked_trader(
        self,
        user_id: int,
        trader_address: str,
        trader_name: str | None = None,
        notes: str | None = None,
    ) -> bool:
        """Add a trader to track."""
        try:
            await self.execute(
                """
                INSERT OR REPLACE INTO tracked_traders
                (user_id, trader_address, trader_name, notes)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, trader_address, trader_name, notes),
            )
            await self.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to add tracked trader: {e}")
            return False

    async def remove_tracked_trader(self, user_id: int, trader_address: str) -> bool:
        """Remove a tracked trader."""
        try:
            await self.execute(
                "DELETE FROM tracked_traders WHERE user_id = ? AND trader_address = ?",
                (user_id, trader_address),
            )
            await self.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to remove tracked trader: {e}")
            return False

    # Alert history operations

    async def record_alert(
        self,
        user_id: int,
        alert_type: str,
        market_id: str,
        condition_id: str,
        event_slug: str,
        market_slug: str,
        title: str,
        price_at_alert: float,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Record an alert in history."""
        await self.execute(
            """
            INSERT INTO alerts
            (user_id, alert_type, market_id, condition_id, event_slug, market_slug, title, price_at_alert, data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                alert_type,
                market_id,
                condition_id,
                event_slug,
                market_slug,
                title,
                price_at_alert,
                json.dumps(data) if data else None,
            ),
        )
        await self.commit()

    async def get_alert_history(
        self, user_id: int, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get user's alert history."""
        return await self.fetchall(
            """
            SELECT * FROM alerts
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )

    async def get_alerts_count_24h(self, user_id: int) -> int:
        """Get count of alerts sent in last 24 hours."""
        row = await self.fetchone(
            """
            SELECT COUNT(*) as count FROM alerts
            WHERE user_id = ?
            AND created_at > datetime('now', '-1 day')
            """,
            (user_id,),
        )
        return row["count"] if row else 0

    # Muted markets operations

    async def is_market_muted(self, user_id: int, market_id: str) -> bool:
        """Check if a market is muted for a user."""
        row = await self.fetchone(
            """
            SELECT 1 FROM muted_markets
            WHERE user_id = ? AND market_id = ?
            AND (muted_until IS NULL OR muted_until > datetime('now'))
            """,
            (user_id, market_id),
        )
        return row is not None

    async def mute_market(
        self, user_id: int, market_id: str, until: datetime | None = None
    ) -> None:
        """Mute a market for a user."""
        await self.execute(
            """
            INSERT OR REPLACE INTO muted_markets (user_id, market_id, muted_until)
            VALUES (?, ?, ?)
            """,
            (user_id, market_id, until.isoformat() if until else None),
        )
        await self.commit()

    async def unmute_market(self, user_id: int, market_id: str) -> None:
        """Unmute a market for a user."""
        await self.execute(
            "DELETE FROM muted_markets WHERE user_id = ? AND market_id = ?",
            (user_id, market_id),
        )
        await self.commit()

    async def get_muted_markets(self, user_id: int) -> list[str]:
        """Get list of muted market IDs for a user."""
        rows = await self.fetchall(
            """
            SELECT market_id FROM muted_markets
            WHERE user_id = ?
            AND (muted_until IS NULL OR muted_until > datetime('now'))
            """,
            (user_id,),
        )
        return [row["market_id"] for row in rows]

    # Price history operations

    async def record_price(
        self, market_id: str, token_id: str, price: float
    ) -> None:
        """Record a price point."""
        await self.execute(
            "INSERT INTO price_history (market_id, token_id, price) VALUES (?, ?, ?)",
            (market_id, token_id, price),
        )
        await self.commit()

    async def get_price_history(
        self, market_id: str, hours: int = 24
    ) -> list[dict[str, Any]]:
        """Get price history for a market."""
        return await self.fetchall(
            """
            SELECT * FROM price_history
            WHERE market_id = ?
            AND timestamp > datetime('now', ?)
            ORDER BY timestamp DESC
            """,
            (market_id, f"-{hours} hours"),
        )

    async def cleanup_old_prices(self, days: int = 7) -> None:
        """Delete price history older than specified days."""
        await self.execute(
            "DELETE FROM price_history WHERE timestamp < datetime('now', ?)",
            (f"-{days} days",),
        )
        await self.commit()

    # Stats

    async def get_all_users(self) -> list[int]:
        """Get all user IDs with settings."""
        rows = await self.fetchall("SELECT user_id FROM settings")
        return [row["user_id"] for row in rows]

    async def get_stats(self) -> dict[str, int]:
        """Get database statistics."""
        user_count = await self.fetchone("SELECT COUNT(*) as c FROM settings")
        alert_count = await self.fetchone("SELECT COUNT(*) as c FROM alerts")
        watchlist_count = await self.fetchone("SELECT COUNT(*) as c FROM watchlist")

        return {
            "users": user_count["c"] if user_count else 0,
            "alerts": alert_count["c"] if alert_count else 0,
            "watchlist_items": watchlist_count["c"] if watchlist_count else 0,
        }
