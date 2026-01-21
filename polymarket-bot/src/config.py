"""
Configuration settings and constants for Polymarket Low Odds Alert Bot.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Configuration
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# Scanning Configuration
SCAN_INTERVAL_SECONDS: int = int(os.getenv("SCAN_INTERVAL_SECONDS", "10"))
PRICE_THRESHOLD: float = float(os.getenv("PRICE_THRESHOLD", "0.001"))
ALERT_COOLDOWN_MINUTES: int = int(os.getenv("ALERT_COOLDOWN_MINUTES", "60"))

# API Configuration
GAMMA_API_BASE_URL: str = "https://gamma-api.polymarket.com"
CLOB_API_BASE_URL: str = "https://clob.polymarket.com"

# Request settings
REQUEST_TIMEOUT_SECONDS: int = 30
MAX_RETRIES: int = 3
RETRY_BACKOFF_BASE: float = 2.0

# Batch size for fetching markets
MARKETS_BATCH_SIZE: int = 100

# Category Keywords for filtering
POLITICS_KEYWORDS: set[str] = {
    "election", "president", "congress", "senate", "vote", "voting",
    "trump", "biden", "harris", "republican", "democrat", "democratic",
    "gop", "governor", "mayor", "legislation", "bill", "law",
    "supreme court", "scotus", "impeach", "cabinet", "secretary",
    "primary", "electoral", "ballot", "poll", "politician",
    "white house", "administration", "veto", "executive order",
    "parliamentary", "parliament", "minister", "prime minister",
    "political", "politics", "government", "federal", "state legislature",
    "house of representatives", "speaker", "majority leader", "minority leader",
    "midterm", "runoff", "recount", "certification", "inaugurate", "inauguration"
}

WEATHER_KEYWORDS: set[str] = {
    "hurricane", "temperature", "storm", "climate", "flood", "flooding",
    "tornado", "cyclone", "typhoon", "weather", "drought", "rainfall",
    "snowfall", "blizzard", "heatwave", "heat wave", "cold snap",
    "wildfire", "fire", "earthquake", "tsunami", "el nino", "la nina",
    "noaa", "national weather service", "celsius", "fahrenheit",
    "record temperature", "hottest", "coldest", "wettest", "driest",
    "atmospheric", "tropical", "category 5", "category 4", "landfall"
}

TECH_KEYWORDS: set[str] = {
    "apple", "google", "microsoft", "amazon", "meta", "facebook",
    "launch", "release", "iphone", "android", "ios", "windows",
    "macbook", "ipad", "pixel", "samsung", "nvidia", "amd", "intel",
    "spacex", "tesla", "starlink", "product launch", "software update",
    "version", "beta", "announcement", "keynote", "wwdc", "io",
    "developer conference", "acquisition", "merger", "ipo", "stock",
    "ceo", "layoff", "layoffs", "hiring", "earnings", "revenue",
    "antitrust", "regulation", "ftc", "doj", "chip", "semiconductor",
    "quantum", "computing", "data center", "cloud"
}

AI_KEYWORDS: set[str] = {
    "gpt", "gpt-4", "gpt-5", "gpt4", "gpt5", "claude", "openai", "anthropic",
    "llm", "ai model", "artificial intelligence", "machine learning", "ml",
    "chatgpt", "gemini", "bard", "llama", "mistral", "deepmind",
    "agi", "superintelligence", "neural network", "deep learning",
    "language model", "foundation model", "transformer", "diffusion",
    "stable diffusion", "midjourney", "dall-e", "dalle", "sora",
    "ai safety", "alignment", "ai regulation", "ai act", "ai bill",
    "copilot", "github copilot", "code generation", "ai assistant",
    "multimodal", "reasoning", "benchmark", "ai benchmark",
    "training", "inference", "parameter", "billion parameter",
    "trillion parameter", "context window", "token"
}

# Keywords to EXCLUDE (crypto/blockchain)
CRYPTO_KEYWORDS: set[str] = {
    "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency",
    "token", "defi", "nft", "blockchain", "web3", "solana", "sol",
    "cardano", "ada", "dogecoin", "doge", "shiba", "memecoin",
    "altcoin", "stablecoin", "usdc", "usdt", "tether", "binance",
    "coinbase", "kraken", "exchange", "wallet", "metamask",
    "polygon", "matic", "avalanche", "avax", "arbitrum", "optimism",
    "layer 2", "l2", "smart contract", "dao", "decentralized",
    "mining", "miner", "hash rate", "halving", "staking", "stake",
    "yield", "liquidity", "dex", "swap", "airdrop", "ido", "ico",
    "xrp", "ripple", "litecoin", "ltc", "chainlink", "link",
    "uniswap", "sushiswap", "pancakeswap", "curve", "aave", "compound"
}

# All included category keywords combined
ALL_INCLUDED_KEYWORDS: set[str] = (
    POLITICS_KEYWORDS | WEATHER_KEYWORDS | TECH_KEYWORDS | AI_KEYWORDS
)
