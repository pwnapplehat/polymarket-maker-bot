# Polymarket Maker Bot

Automated market maker bot for Polymarket following Feb 2026 rules (500ms delay removed).

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
nano .env  # Add your MetaMask private key
```

### 3. Test Connection

```bash
python test_connection.py
```

### 4. Run Bot

```bash
# Dry-run mode (no real trades)
python bot.py

# Live mode (requires wallet + USDC)
python bot.py --live
```

## Features

- ✅ **WebSocket-based execution** - Real-time orderbook data
- ✅ **Fee-aware maker orders** - Zero fees + daily rebates
- ✅ **<220ms cancel/replace loop** - Competitive execution speed
- ✅ **Binance price feed** - BTC price monitoring for 5-min/15-min markets
- ✅ **Safety limits** - Max daily loss, position limits, emergency stop
- ✅ **Dry-run mode** - Test without risking funds

## Architecture

Based on Polymarket changes in Feb 2026:

1. **500ms taker delay REMOVED** (Feb 18, 2026)
2. **Dynamic taker fees** on crypto markets (up to 1.56% at 50% odds)
3. **Maker orders = ZERO fees** + 20% daily rebates
4. **feeRateBps required** in order signing

## Configuration

Edit `.env` file:

```env
POLYMARKET_PRIVATE_KEY=0xYOUR_METAMASK_PRIVATE_KEY
INITIAL_CAPITAL=100.0
MAX_POSITION_SIZE=20.0
SPREAD_BPS=50           # 0.5% spread
ENABLE_DRY_RUN=true     # Start in safe mode
```

## Safety Features

- **Max daily loss**: Auto-stop if losses exceed threshold
- **Position limits**: Prevents over-exposure
- **Emergency stop**: `bash emergency_stop.sh`
- **Dry-run mode**: Test strategy without real money

## Deployment to CloudClaw

```bash
# Upload to your CloudClaw instance
scp -r . node@YOUR_CLOUDCLAW_IP:~/polymarket-bot/

# SSH into CloudClaw
ssh node@YOUR_CLOUDCLAW_IP

# Run setup
cd ~/polymarket-bot
bash deploy.sh
```

## Performance

Expected latency from Hetzner Nuremberg:

| Metric | Latency | Grade |
|--------|---------|-------|
| Polygon RPC | ~109ms | ✅ Good |
| Polymarket CLOB | ~110ms | ✅ Good |
| Cancel/Replace Loop | ~220ms | ✅ Competitive |

## Supported Markets

- ✅ **15-minute crypto** (recommended, good competition balance)
- ✅ **1-hour markets** (lower competition, higher success rate)
- ⚠️ **5-minute markets** (very competitive, requires <100ms)
- ✅ **Weather markets** (high profit, low speed requirement)

## Troubleshooting

**Bot won't start:**
- Check `.env` has correct PRIVATE_KEY
- Verify Python 3.10+ installed
- Run `python test_connection.py`

**Orders rejected:**
- Insufficient USDC balance
- Wrong network (must be Polygon mainnet)
- feeRateBps mismatch (bot handles this automatically)

**Losses exceeding profits:**
- Increase SPREAD_BPS (wider spreads = less fills but safer)
- Reduce MAX_POSITION_SIZE (smaller positions = less risk)
- Target longer-duration markets (less competition)

## License

MIT License - Use at your own risk.

## Disclaimer

This bot is for educational purposes. Trading involves substantial risk of loss. Only trade with capital you can afford to lose. The authors assume no liability for your trading results.

## Architecture Details

### Core Components

1. **polymarket_client.py** - Handles CLOB API, order signing with feeRateBps
2. **binance_feed.py** - WebSocket connection to Binance for BTC price
3. **maker_strategy.py** - Core market making logic
4. **bot.py** - Main orchestrator, handles lifecycle

### Strategy

1. Monitor Binance BTC price via WebSocket
2. Calculate optimal bid/ask prices (target spread)
3. Query current feeRateBps from Polymarket
4. Sign and post maker orders on both YES/NO sides
5. When price moves >0.5%, cancel stale orders and replace
6. Track fills and daily maker rebates

### Cancel/Replace Loop

```
1. Binance price update received (WebSocket push)
2. Calculate new bid/ask prices
3. Cancel existing orders → Polymarket CLOB API (~110ms)
4. Create new orders → Polymarket CLOB API (~110ms)
Total: ~220ms ✅
```

## Credits

Built following the Feb 2026 Polymarket rule changes analysis.
