"""Maker strategy implementation for Polymarket crypto markets."""
import time
from polymarket_client import PolymarketClient
from binance_feed import BinanceFeed
from config import Config
from logger import logger

class MakerStrategy:
    """
    Market maker strategy for Polymarket crypto markets.
    
    Core Logic:
    1. Monitor Binance BTC price via WebSocket
    2. Calculate YES/NO probabilities based on BTC price
    3. Quote BUY/SELL orders on Polymarket with spread
    4. Cancel/replace orders on every price update
    5. Earn maker rebates on filled orders
    """
    
    def __init__(self, client: PolymarketClient, target_market_duration="15m"):
        """
        Initialize maker strategy.
        
        Args:
            client: PolymarketClient instance
            target_market_duration: "5m", "15m", or "1h"
        """
        self.client = client
        self.target_market_duration = target_market_duration
        self.binance_feed = BinanceFeed(symbol="BTCUSDT")
        
        # Active market tracking
        self.active_market = None
        self.active_token_id = None
        self.current_orders = []
        
        # Performance tracking
        self.total_trades = 0
        self.total_pnl = 0.0
        self.last_cancel_replace = 0
        
        logger.info(f"Maker strategy initialized for {target_market_duration} markets")
    
    def start(self):
        """Start the strategy."""
        logger.info("Starting maker strategy...")
        
        # Start Binance price feed
        self.binance_feed.start()
        
        if not self.binance_feed.is_connected():
            raise RuntimeError("Failed to connect to Binance feed")
        
        # Find active market
        self.find_active_market()
        
        if not self.active_market:
            raise RuntimeError(f"No active {self.target_market_duration} BTC markets found")
        
        logger.info(f"✅ Trading market: {self.active_market.get('question', 'Unknown')}")
    
    def stop(self):
        """Stop the strategy."""
        logger.info("Stopping maker strategy...")
        
        # Cancel all open orders
        self.client.cancel_all_orders()
        
        # Stop price feed
        self.binance_feed.stop()
        
        logger.info("✅ Strategy stopped")
    
    def find_active_market(self):
        """Find an active BTC market with target duration."""
        markets = self.client.get_crypto_markets(duration=self.target_market_duration)
        
        if not markets:
            logger.error(f"No active {self.target_market_duration} BTC markets found")
            return
        
        # Pick first active market
        self.active_market = markets[0]
        
        # Extract token ID from market (usually in 'tokens' field)
        tokens = self.active_market.get("tokens", [])
        if tokens:
            # Pick YES token (index 0 usually)
            self.active_token_id = tokens[0].get("token_id")
        
        logger.info(f"Selected market: {self.active_market.get('question', 'N/A')}")
        logger.info(f"Token ID: {self.active_token_id[:16] if self.active_token_id else 'N/A'}...")
    
    def calculate_fair_price(self, btc_price, strike_price):
        """
        Calculate fair probability based on BTC price vs strike.
        
        Simple logic:
        - If BTC price is far above strike: YES probability high
        - If BTC price is far below strike: YES probability low
        
        Args:
            btc_price: Current BTC price (e.g., 83250)
            strike_price: Market strike price (e.g., 83000)
            
        Returns:
            Fair YES price between 0.01 and 0.99
        """
        # Calculate price difference ratio
        diff = btc_price - strike_price
        
        # Simple linear model (adjust based on backtesting)
        # For every $100 above/below strike, adjust probability by 1%
        prob_adjustment = diff / 100 * 0.01
        
        # Base probability = 0.5 (50/50)
        fair_price = 0.5 + prob_adjustment
        
        # Clamp to valid range [0.01, 0.99]
        fair_price = max(0.01, min(0.99, fair_price))
        
        return fair_price
    
    def quote_orders(self):
        """
        Quote BUY/SELL orders on Polymarket based on current BTC price.
        
        This is called every CANCEL_REPLACE_INTERVAL seconds.
        """
        # Get current BTC price
        btc_price = self.binance_feed.get_price()
        
        if not btc_price:
            logger.warning("No BTC price available, skipping quote")
            return
        
        # Parse strike price from market question
        # Example: "Will BTC be above $83,000 at 3:15 PM?"
        question = self.active_market.get("question", "")
        strike_price = self.extract_strike_price(question)
        
        if not strike_price:
            logger.error("Could not extract strike price from market question")
            return
        
        # Calculate fair YES price
        fair_price = self.calculate_fair_price(btc_price, strike_price)
        
        # Apply spread
        spread_bps = Config.SPREAD_BPS
        spread = spread_bps / 10000.0  # Convert basis points to decimal
        
        buy_price = fair_price - spread / 2
        sell_price = fair_price + spread / 2
        
        # Clamp to valid range
        buy_price = max(0.01, min(0.99, buy_price))
        sell_price = max(0.01, min(0.99, sell_price))
        
        # Position size
        position_size = Config.MAX_POSITION_SIZE
        
        logger.info(f"BTC: ${btc_price:,.2f} | Strike: ${strike_price:,.0f} | Fair: ${fair_price:.3f}")
        logger.info(f"Quoting: BUY ${buy_price:.3f} | SELL ${sell_price:.3f}")
        
        # STEP 1: Cancel existing orders
        for order_id in self.current_orders:
            self.client.cancel_order(order_id)
        self.current_orders.clear()
        
        # STEP 2: Create new orders
        buy_order_id = self.client.create_maker_order(
            token_id=self.active_token_id,
            side="BUY",
            price=buy_price,
            size=position_size
        )
        
        sell_order_id = self.client.create_maker_order(
            token_id=self.active_token_id,
            side="SELL",
            price=sell_price,
            size=position_size
        )
        
        # Track new orders
        if buy_order_id:
            self.current_orders.append(buy_order_id)
        if sell_order_id:
            self.current_orders.append(sell_order_id)
        
        self.last_cancel_replace = time.time()
    
    def extract_strike_price(self, question):
        """
        Extract strike price from market question.
        
        Example: "Will BTC be above $83,000 at 3:15 PM?" -> 83000
        
        Args:
            question: Market question string
            
        Returns:
            Strike price as float, or None if not found
        """
        import re
        
        # Look for patterns like "$83,000" or "$83000"
        match = re.search(r'\$([0-9,]+)', question)
        
        if match:
            price_str = match.group(1).replace(",", "")
            return float(price_str)
        
        return None
    
    def run(self):
        """Main strategy loop."""
        try:
            self.start()
            
            logger.info("Entering main loop...")
            
            while True:
                # Check if it's time to cancel/replace
                elapsed = time.time() - self.last_cancel_replace
                
                if elapsed >= Config.CANCEL_REPLACE_INTERVAL:
                    self.quote_orders()
                
                # Sleep briefly
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received stop signal")
        except Exception as e:
            logger.error(f"Strategy error: {e}", exc_info=True)
        finally:
            self.stop()
