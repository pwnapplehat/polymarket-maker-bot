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
        self.last_btc_price = None  # Track last price for change detection
        
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
    
    def should_requote(self, current_btc_price):
        """
        Determine if we should cancel/replace orders.
        
        Article recommendation: Requote on significant price changes to avoid adverse selection.
        
        Args:
            current_btc_price: Current BTC price
            
        Returns:
            True if should requote
        """
        # Always requote if we haven't quoted yet
        if self.last_btc_price is None:
            return True
        
        # Check time-based interval
        elapsed = time.time() - self.last_cancel_replace
        if elapsed >= Config.CANCEL_REPLACE_INTERVAL:
            return True
        
        # Check price change threshold (article: requote on price movement)
        price_change_pct = abs(current_btc_price - self.last_btc_price) / self.last_btc_price
        if price_change_pct >= Config.QUOTE_REFRESH_ON_PRICE_CHANGE:
            logger.info(f"Price changed {price_change_pct*100:.2f}% - triggering requote")
            return True
        
        return False
    
    def calculate_fair_price(self, btc_price, strike_price, market_close_time=None):
    def calculate_fair_price(self, btc_price, strike_price, market_close_time=None):
        """
        Calculate fair probability based on BTC price vs strike.
        
        Article insight: For 15-min markets, BTC direction becomes ~85% determined at T-10 seconds.
        We use linear approximation for simplicity.
        
        Args:
            btc_price: Current BTC price (e.g., 83250)
            strike_price: Market strike price (e.g., 83000)
            market_close_time: Optional market close timestamp (for future T-10s logic)
            
        Returns:
            Fair YES price between 0.01 and 0.99
        """
        # Calculate price difference
        diff = btc_price - strike_price
        
        # For 15-min markets: Use aggressive pricing model
        # If BTC is $100 above strike → ~60% probability
        # If BTC is $500 above strike → ~90% probability
        if diff > 0:
            # Above strike - higher YES probability
            if diff >= 500:
                fair_price = 0.90
            elif diff >= 300:
                fair_price = 0.75
            elif diff >= 100:
                fair_price = 0.60
            else:
                # Small difference: linear scale from 0.50 to 0.60
                fair_price = 0.50 + (diff / 100) * 0.10
        else:
            # Below strike - lower YES probability
            abs_diff = abs(diff)
            if abs_diff >= 500:
                fair_price = 0.10
            elif abs_diff >= 300:
                fair_price = 0.25
            elif abs_diff >= 100:
                fair_price = 0.40
            else:
                # Small difference: linear scale from 0.50 to 0.40
                fair_price = 0.50 - (abs_diff / 100) * 0.10
        
        # Clamp to valid range [0.01, 0.99]
        fair_price = max(0.01, min(0.99, fair_price))
        
        return fair_price
    
    def quote_orders(self):
        """
        Quote BUY/SELL maker orders on Polymarket.
        
        Article strategy:
        1. Post maker orders on both sides (BUY + SELL)
        2. Earn 20% of taker fees as daily rebates
        3. Avoid 50% probability (1.56% max fee zone)
        4. Cancel/replace on price changes
        """
        # Get current BTC price
        btc_price = self.binance_feed.get_price()
        
        if not btc_price:
            logger.warning("No BTC price available, skipping quote")
            return
        
        # Parse strike price from market question
        question = self.active_market.get("question", "")
        strike_price = self.extract_strike_price(question)
        
        if not strike_price:
            logger.error("Could not extract strike price from market question")
            return
        
        # Calculate fair YES price
        fair_price = self.calculate_fair_price(btc_price, strike_price)
        
        # CRITICAL: Check if we have enough edge to overcome fees
        # Article: Max fee is 1.56% at p=0.50
        # We need edge > 2% to be safe (MIN_EDGE_BPS = 200)
        min_edge = Config.MIN_EDGE_BPS / 10000.0
        
        # Check distance from 50% (danger zone)
        distance_from_50 = abs(fair_price - 0.50)
        
        if distance_from_50 < (min_edge / 2):
            logger.warning(f"Fair price {fair_price:.3f} too close to 50% (high fee zone) - skipping")
            logger.warning(f"Need at least {min_edge*100:.1f}% edge, have {distance_from_50*100:.1f}%")
            # Cancel existing orders but don't place new ones
            for order_id in self.current_orders:
                self.client.cancel_order(order_id)
            self.current_orders.clear()
            return
        
        # Apply spread
        spread_bps = Config.SPREAD_BPS
        spread = spread_bps / 10000.0
        
        buy_price = fair_price - spread / 2
        sell_price = fair_price + spread / 2
        
        # Clamp to valid range
        buy_price = max(0.01, min(0.99, buy_price))
        sell_price = max(0.01, min(0.99, sell_price))
        
        # Position size
        position_size = Config.MAX_POSITION_SIZE
        
        logger.info(f"BTC: ${btc_price:,.2f} | Strike: ${strike_price:,.0f} | Fair: ${fair_price:.3f}")
        logger.info(f"Edge: {distance_from_50*100:.1f}% | Quoting: BUY ${buy_price:.3f} | SELL ${sell_price:.3f}")
        
        # STEP 1: Cancel existing orders (article: fast cancel/replace)
        cancel_start = time.time()
        for order_id in self.current_orders:
            self.client.cancel_order(order_id)
        self.current_orders.clear()
        cancel_time_ms = (time.time() - cancel_start) * 1000
        
        # STEP 2: Create new maker orders (article: post on both sides)
        create_start = time.time()
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
        create_time_ms = (time.time() - create_start) * 1000
        
        # Track new orders
        if buy_order_id:
            self.current_orders.append(buy_order_id)
        if sell_order_id:
            self.current_orders.append(sell_order_id)
        
        total_loop_ms = cancel_time_ms + create_time_ms
        logger.debug(f"Cancel/replace loop: {total_loop_ms:.0f}ms (cancel: {cancel_time_ms:.0f}ms, create: {create_time_ms:.0f}ms)")
        
        # Update tracking
        self.last_cancel_replace = time.time()
        self.last_btc_price = btc_price
    
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
        """
        Main strategy loop.
        
        Article strategy:
        - Monitor Binance WebSocket for BTC price
        - Requote on price changes OR time interval
        - Fast cancel/replace loop
        - Avoid 50% probability (high fee zone)
        """
        try:
            self.start()
            
            logger.info("Entering main loop...")
            logger.info("Strategy: Maker bot for 15-min BTC markets")
            logger.info("- Requote interval: {}s".format(Config.CANCEL_REPLACE_INTERVAL))
            logger.info("- Price change trigger: {:.1f}%".format(Config.QUOTE_REFRESH_ON_PRICE_CHANGE * 100))
            logger.info("- Min edge required: {:.1f}%".format(Config.MIN_EDGE_BPS / 100))
            
            while True:
                # Get current BTC price
                btc_price = self.binance_feed.get_price()
                
                if btc_price and self.should_requote(btc_price):
                    self.quote_orders()
                
                # Sleep briefly (article: tight loop for 15-min markets)
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            logger.info("Received stop signal")
        except Exception as e:
            logger.error(f"Strategy error: {e}", exc_info=True)
        finally:
            self.stop()
