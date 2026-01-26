"""
Configuration settings loaded from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_ID: int = int(os.getenv("TELEGRAM_ADMIN_ID", "0"))

# API Base URLs
GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"
DATA_API_URL = "https://data-api.polymarket.com"

# Goldsky Subgraph URLs
SUBGRAPH_ORDERBOOK = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/0.0.1/gn"
SUBGRAPH_POSITIONS = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/positions-subgraph/0.0.7/gn"
SUBGRAPH_ACTIVITY = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/activity-subgraph/0.0.4/gn"
SUBGRAPH_OI = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/oi-subgraph/0.0.6/gn"
SUBGRAPH_PNL = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/pnl-subgraph/0.0.14/gn"

# WebSocket URLs
WS_CLOB_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/"
WS_RTDS_URL = "wss://ws-live-data.polymarket.com"

# Defaults (users can change via /settings)
DEFAULT_PRICE_THRESHOLD: float = float(os.getenv("DEFAULT_PRICE_THRESHOLD", "0.01"))
DEFAULT_MIN_VOLUME: float = float(os.getenv("DEFAULT_MIN_VOLUME", "1000"))
DEFAULT_MIN_LIQUIDITY: float = float(os.getenv("DEFAULT_MIN_LIQUIDITY", "5000"))
DEFAULT_MAX_SPREAD: float = float(os.getenv("DEFAULT_MAX_SPREAD", "0.03"))
DEFAULT_SCAN_INTERVAL: int = int(os.getenv("DEFAULT_SCAN_INTERVAL", "60"))
DEFAULT_WHALE_THRESHOLD: float = float(os.getenv("DEFAULT_WHALE_THRESHOLD", "30"))
DEFAULT_ALERT_COOLDOWN: int = int(os.getenv("DEFAULT_ALERT_COOLDOWN", "60"))

# Digest
DIGEST_ENABLED: bool = os.getenv("DIGEST_ENABLED", "false").lower() == "true"
DIGEST_TIME_UTC: str = os.getenv("DIGEST_TIME_UTC", "09:00")

# System
DATABASE_PATH: Path = Path(os.getenv("DATABASE_PATH", "./data/bot.db"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
HEALTH_PORT: int = int(os.getenv("HEALTH_PORT", "8080"))

# Request settings
REQUEST_TIMEOUT: int = 30
MAX_RETRIES: int = 3
RETRY_BACKOFF_BASE: float = 2.0

# Category keywords
POLITICS_KEYWORDS: set[str] = {
    "election", "president", "congress", "senate", "vote", "voting",
    "trump", "biden", "harris", "republican", "democrat", "democratic",
    "gop", "governor", "mayor", "legislation", "bill", "law",
    "supreme court", "scotus", "impeach", "cabinet", "secretary",
    "primary", "electoral", "ballot", "poll", "politician",
    "white house", "administration", "veto", "executive order",
    "parliamentary", "parliament", "minister", "prime minister",
    "political", "politics", "government", "federal"
}

WEATHER_KEYWORDS: set[str] = {
    "hurricane", "temperature", "storm", "climate", "flood", "flooding",
    "tornado", "cyclone", "typhoon", "weather", "drought", "rainfall",
    "snowfall", "blizzard", "heatwave", "heat wave", "cold snap",
    "wildfire", "fire", "earthquake", "tsunami", "el nino", "la nina",
    "noaa", "celsius", "fahrenheit", "record temperature"
}

TECH_KEYWORDS: set[str] = {
    "apple", "google", "microsoft", "amazon", "meta", "facebook",
    "launch", "release", "iphone", "android", "ios", "windows",
    "macbook", "ipad", "pixel", "samsung", "nvidia", "amd", "intel",
    "spacex", "tesla", "starlink", "product launch", "software update",
    "acquisition", "merger", "ipo", "ceo", "layoff", "earnings"
}

AI_KEYWORDS: set[str] = {
    "gpt", "gpt-4", "gpt-5", "gpt4", "gpt5", "claude", "openai", "anthropic",
    "llm", "ai model", "artificial intelligence", "machine learning",
    "chatgpt", "gemini", "bard", "llama", "mistral", "deepmind",
    "agi", "superintelligence", "neural network", "deep learning",
    "language model", "foundation model", "stable diffusion", "midjourney",
    "dall-e", "dalle", "sora", "ai safety", "alignment", "ai regulation"
}

CRYPTO_KEYWORDS: set[str] = {
    "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency",
    "token", "defi", "nft", "blockchain", "web3", "solana", "sol",
    "cardano", "ada", "dogecoin", "doge", "shiba", "memecoin",
    "altcoin", "stablecoin", "usdc", "usdt", "tether", "binance",
    "coinbase", "polygon", "matic", "avalanche", "avax", "arbitrum"
}

ALL_INCLUDED_KEYWORDS: set[str] = (
    POLITICS_KEYWORDS | WEATHER_KEYWORDS | TECH_KEYWORDS | AI_KEYWORDS
)
