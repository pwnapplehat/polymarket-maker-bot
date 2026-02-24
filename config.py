"""Configuration management for Polymarket bot."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Bot configuration from environment variables."""
    
    # Polymarket
    PRIVATE_KEY = os.getenv("POLYMARKET_PRIVATE_KEY", "")
    POLYGON_RPC = os.getenv("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com")
    CLOB_URL = os.getenv("POLYMARKET_CLOB_URL", "https://clob.polymarket.com")
    WS_URL = os.getenv("POLYMARKET_WS_URL", "wss://ws-subscriptions-clob.polymarket.com/ws/market")
    
    # Binance
    BINANCE_WS = os.getenv("BINANCE_WS_URL", "wss://stream.binance.com:9443/ws/btcusdt@ticker")
    BINANCE_API = os.getenv("BINANCE_API_URL", "https://api.binance.com")
    
    # Trading
    INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "100.0"))
    MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "20.0"))
    SPREAD_BPS = int(os.getenv("SPREAD_BPS", "50"))
    CANCEL_REPLACE_INTERVAL = int(os.getenv("CANCEL_REPLACE_INTERVAL", "2"))  # 2 seconds for 15-min markets
    MIN_PROFIT_BPS = int(os.getenv("MIN_PROFIT_BPS", "10"))
    
    # Advanced Strategy (15-min markets)
    MIN_EDGE_BPS = int(os.getenv("MIN_EDGE_BPS", "200"))  # Minimum 2% edge to overcome fees
    QUOTE_REFRESH_ON_PRICE_CHANGE = float(os.getenv("QUOTE_REFRESH_ON_PRICE_CHANGE", "0.001"))  # 0.1% price change triggers requote
    
    # Safety
    MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "20.0"))
    MAX_DAILY_TRADES = int(os.getenv("MAX_DAILY_TRADES", "500"))
    ENABLE_DRY_RUN = os.getenv("ENABLE_DRY_RUN", "true").lower() == "true"
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/polymarket_bot.log")
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.ENABLE_DRY_RUN and not cls.PRIVATE_KEY:
            raise ValueError("POLYMARKET_PRIVATE_KEY required when ENABLE_DRY_RUN=false")
        
        if cls.MAX_POSITION_SIZE > cls.INITIAL_CAPITAL:
            raise ValueError("MAX_POSITION_SIZE cannot exceed INITIAL_CAPITAL")
        
        if cls.SPREAD_BPS < 10:
            raise ValueError("SPREAD_BPS too low (minimum 10 = 0.1%)")
        
        if cls.CANCEL_REPLACE_INTERVAL < 1:
            raise ValueError("CANCEL_REPLACE_INTERVAL too low (minimum 1 second)")
        
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration (masks sensitive data)."""
        print("=" * 60)
        print("Bot Configuration")
        print("=" * 60)
        print(f"Mode:              {'DRY-RUN' if cls.ENABLE_DRY_RUN else 'LIVE'}")
        print(f"Initial Capital:   ${cls.INITIAL_CAPITAL:.2f}")
        print(f"Max Position:      ${cls.MAX_POSITION_SIZE:.2f}")
        print(f"Spread:            {cls.SPREAD_BPS / 100:.2f}%")
        print(f"Cancel/Replace:    {cls.CANCEL_REPLACE_INTERVAL}s")
        print(f"Min Edge:          {cls.MIN_EDGE_BPS / 100:.2f}%")
        print(f"Max Daily Loss:    ${cls.MAX_DAILY_LOSS:.2f}")
        print(f"Max Daily Trades:  {cls.MAX_DAILY_TRADES}")
        if cls.PRIVATE_KEY:
            print(f"Wallet:            {cls.PRIVATE_KEY[:6]}...{cls.PRIVATE_KEY[-4:]}")
        else:
            print(f"Wallet:            Not configured")
        print("=" * 60)

# Validate on import
try:
    Config.validate()
except ValueError as e:
    print(f"❌ Configuration error: {e}")
    print("   Please check your .env file")
