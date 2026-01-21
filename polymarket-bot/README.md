# Polymarket Low Odds Alert Bot

A high-performance Telegram bot that monitors Polymarket for markets where any outcome has odds ≤ 0.1% (≤ $0.001), sending instant alerts.

## Features

- **Real-time monitoring**: Scans Polymarket every 5-10 seconds
- **Smart filtering**: Focuses on Politics, Weather, Technology, and AI markets
- **Crypto exclusion**: Automatically filters out cryptocurrency-related markets
- **Deduplication**: Prevents spam by tracking recently alerted markets
- **Fast alerts**: Sub-second alert delivery via Telegram

## Categories Monitored

| Category | Examples |
|----------|----------|
| Politics | Elections, legislation, government events |
| Weather | Hurricanes, temperature records, climate events |
| Technology | Product launches, company announcements |
| AI | Model releases, AI milestones, regulations |

## Installation

### Prerequisites

- Python 3.11 or higher
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- Your Telegram chat ID (from [@userinfobot](https://t.me/userinfobot))

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd polymarket-bot
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create configuration:
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` with your credentials:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

## Usage

### Running the Bot

```bash
python -m src.main
```

Or run directly:
```bash
cd polymarket-bot
python -m src.main
```

### Running with Docker (Optional)

```bash
docker build -t polymarket-bot .
docker run -d --env-file .env polymarket-bot
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | (required) | Your Telegram bot token |
| `TELEGRAM_CHAT_ID` | (required) | Chat/channel ID for alerts |
| `SCAN_INTERVAL_SECONDS` | 10 | Seconds between scans |
| `PRICE_THRESHOLD` | 0.001 | Alert threshold (0.001 = 0.1%) |
| `ALERT_COOLDOWN_MINUTES` | 60 | Minutes before re-alerting same market |

## Alert Format

```
🚨 LOW ODDS ALERT

📊 Market: Will X happen by Y date?
💰 Outcome: Yes
📉 Price: 0.050% ($0.0005)
📁 Category: Politics
🔗 Link: https://polymarket.com/event/...

⏰ 2025-01-21 12:34:56 UTC
```

## Architecture

```
┌─────────────────┐
│  Main Loop      │ ← Async, runs every 5-10 seconds
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Polymarket API  │ ← Batch fetch active markets
│ (Gamma API)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Filter Engine   │ ← Category match + exclude crypto + exclude resolved
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Price Checker   │ ← Check if any outcome ≤ 0.001
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Dedup Cache     │ ← In-memory dict with TTL
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Telegram Alert  │ ← python-telegram-bot async
└─────────────────┘
```

## Project Structure

```
polymarket-bot/
├── src/
│   ├── __init__.py           # Package marker
│   ├── main.py               # Entry point, async loop
│   ├── polymarket_client.py  # API wrapper
│   ├── filters.py            # Category & resolution filters
│   ├── alert_cache.py        # Deduplication logic
│   ├── telegram_bot.py       # Telegram integration
│   └── config.py             # Settings & constants
├── requirements.txt          # Dependencies
├── .env.example              # Configuration template
└── README.md                 # This file
```

## Performance

- **Full market scan**: < 5 seconds
- **Alert delivery**: < 1 second after detection
- **Memory usage**: < 100MB

## API References

This bot uses the following Polymarket APIs:
- **Gamma API** (`gamma-api.polymarket.com`): Market metadata, categories, resolution status
- **CLOB API** (`clob.polymarket.com`): Real-time prices and order book data

## Troubleshooting

### Bot not sending alerts

1. Verify `TELEGRAM_BOT_TOKEN` is correct
2. Ensure the bot has been started by messaging it on Telegram
3. Check that `TELEGRAM_CHAT_ID` is correct (use @userinfobot)
4. Review logs for error messages

### Rate limiting

The bot includes automatic retry with exponential backoff. If you're hitting rate limits frequently:
- Increase `SCAN_INTERVAL_SECONDS`
- The bot will automatically wait when rate limited

### No markets found

- Polymarket may have temporary API issues
- Check if the API endpoints are accessible
- The bot will continue retrying automatically

## License

MIT License
