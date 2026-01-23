# Polymarket Smart Alert Bot

A powerful Telegram bot that monitors Polymarket for low odds markets, whale trades, and arbitrage opportunities. Complex analytics under the hood, clean minimal interface for the user.

## Features

### Alert Types
- **📉 Low Odds** - Markets where outcomes are below your threshold (default 1%)
- **🐋 Whale Trades** - Large trades above $30 USD with trader profiles
- **⚖️ Arbitrage** - Price discrepancies where YES + NO > 100%
- **⚠️ Counter Signals** - When whales bet against low-odds outcomes

### Smart Filtering
- **Quality filters**: Volume, liquidity, and spread requirements
- **Category targeting**: Politics, Weather, Technology, AI
- **Crypto exclusion**: Automatically filters out blockchain markets
- **Deduplication**: No spam - alerts are batched every 1-2 minutes

### User Features
- **📋 Watchlist** - Track specific markets
- **👥 Trader Tracking** - Follow whale wallets
- **⚙️ Settings** - All configuration via inline buttons
- **📁 Export** - Download your data as CSV/JSON

## Installation

### Prerequisites

- Python 3.11+
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- Your Telegram user ID from [@userinfobot](https://t.me/userinfobot)

### Setup

```bash
# Clone and enter directory
git clone <repository-url>
cd polymarket-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your credentials
```

### Running

```bash
python -m src.main
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/settings` | Configure alert thresholds |
| `/watchlist` | View tracked markets |
| `/traders` | View tracked traders |
| `/status` | Bot status and stats |
| `/export` | Export your data |
| `/help` | Show help |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | required | Bot token from BotFather |
| `TELEGRAM_ADMIN_ID` | required | Your Telegram user ID |
| `DEFAULT_PRICE_THRESHOLD` | 0.01 | Alert threshold (1%) |
| `DEFAULT_MIN_VOLUME` | 1000 | Min 24h volume ($) |
| `DEFAULT_MIN_LIQUIDITY` | 5000 | Min liquidity ($) |
| `DEFAULT_MAX_SPREAD` | 0.03 | Max spread (3%) |
| `DEFAULT_SCAN_INTERVAL` | 60 | Scan interval (seconds) |
| `DEFAULT_WHALE_THRESHOLD` | 30 | Min whale trade ($) |

## Alert Format

```
📊 POLYMARKET ALERTS • 14:32 UTC

━━━━━━━━━━━━━━━━━━━━━━

🔴 LOW ODDS DETECTED

Will X happen before Y?
├ NO: 1.0% (was 2.3% 1h ago) ↓57%
├ Vol: $45K | Liq: $120K | Spread: 0.8%
├ Ends: Jan 15, 2025 (12 days)
└ 🔗 polymarket.com/event/xxx/yyy

━━━━━━━━━━━━━━━━━━━━━━

🐋 WHALE BUY • $500

@trader_name 🧠 bought YES
├ Market: "Will Z happen?"
├ Price: $0.34 | Shares: 1,470
├ Stats: 73% win rate (89 trades)
├ Portfolio: $12.4K | PnL: +$2.1K
└ 🔗 polymarket.com/event/xxx

━━━━━━━━━━━━━━━━━━━━━━

📈 2 alerts | Next scan: 14:34 UTC
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      TELEGRAM BOT                           │
│  Commands • Callbacks • Scheduled Jobs                      │
└─────────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                     CORE ENGINE                             │
│  Market Scanner • Whale Tracker • Alert Aggregator          │
└─────────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                   POLYMARKET LAYER                          │
│  Gamma API • CLOB API • Data API                            │
└─────────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                             │
│  SQLite DB • Memory Cache • Price History                   │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
polymarket-bot/
├── src/
│   ├── main.py                 # Entry point
│   ├── bot/                    # Telegram handlers
│   │   ├── handlers.py
│   │   ├── callbacks.py
│   │   ├── keyboards.py
│   │   └── formatters.py
│   ├── polymarket/             # API clients
│   │   ├── gamma_client.py
│   │   ├── clob_client.py
│   │   ├── data_client.py
│   │   ├── models.py
│   │   └── urls.py
│   ├── core/                   # Business logic
│   │   ├── scanner.py
│   │   ├── filters.py
│   │   ├── aggregator.py
│   │   └── alerts.py
│   ├── traders/                # Whale tracking
│   │   ├── tracker.py
│   │   ├── profiler.py
│   │   └── smart_money.py
│   ├── data/                   # Persistence
│   │   ├── database.py
│   │   └── cache.py
│   └── utils/                  # Utilities
│       ├── config.py
│       └── logger.py
├── data/                       # SQLite database
├── requirements.txt
├── .env.example
└── README.md
```

## API References

| API | Base URL | Purpose |
|-----|----------|---------|
| Gamma | `gamma-api.polymarket.com` | Markets, events, profiles |
| CLOB | `clob.polymarket.com` | Prices, orderbook |
| Data | `data-api.polymarket.com` | Trades, positions |

## Smart Money Classification

Traders are classified as "smart money" if they meet either:
- 20+ trades with 65%+ win rate
- $50,000+ portfolio value

Smart money badges:
- 👑 Elite (both criteria)
- 💎 High portfolio
- 🧠 Consistent wins

## Troubleshooting

### Bot not responding
1. Check `TELEGRAM_BOT_TOKEN` is correct
2. Start a conversation with your bot on Telegram
3. Check logs for errors

### No alerts
1. Verify markets exist with low odds
2. Check your threshold settings (`/settings`)
3. Ensure categories are enabled

### Rate limiting
The bot includes automatic retry with exponential backoff. If persistent:
- Increase `DEFAULT_SCAN_INTERVAL`
- Check API status

## License

MIT License
