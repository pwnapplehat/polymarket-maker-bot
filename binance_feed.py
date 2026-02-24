"""Binance WebSocket price feed for BTC/USDT."""
import json
import threading
import time
import websocket
from config import Config
from logger import logger

class BinanceFeed:
    """Binance WebSocket price feed."""
    
    def __init__(self, symbol="BTCUSDT"):
        """
        Initialize Binance feed.
        
        Args:
            symbol: Trading pair (default: BTCUSDT)
        """
        self.symbol = symbol
        self.ws = None
        self.price = None
        self.last_update = 0
        self.running = False
        self.thread = None
        self.callbacks = []
        
        logger.info(f"Binance feed initialized for {symbol}")
    
    def on_message(self, ws, message):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            
            # Binance ticker format: {"e":"24hrTicker","E":1234567890,"s":"BTCUSDT","c":"50000.00",...}
            if data.get("e") == "24hrTicker":
                price = float(data.get("c", 0))  # 'c' = current close price
                
                if price > 0:
                    self.price = price
                    self.last_update = time.time()
                    
                    # Call registered callbacks
                    for callback in self.callbacks:
                        try:
                            callback(price)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
            
        except Exception as e:
            logger.error(f"Error processing Binance message: {e}")
    
    def on_error(self, ws, error):
        """Handle WebSocket error."""
        logger.error(f"Binance WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        logger.warning("Binance WebSocket closed")
        
        # Auto-reconnect if still running
        if self.running:
            logger.info("Reconnecting to Binance in 5 seconds...")
            time.sleep(5)
            self._connect()
    
    def on_open(self, ws):
        """Handle WebSocket open."""
        logger.info("✅ Connected to Binance WebSocket")
    
    def _connect(self):
        """Create WebSocket connection."""
        # Binance WebSocket URL format: wss://stream.binance.com:9443/ws/btcusdt@ticker
        ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol.lower()}@ticker"
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
    
    def _run(self):
        """Run WebSocket in thread."""
        while self.running:
            try:
                self._connect()
                self.ws.run_forever()
            except Exception as e:
                logger.error(f"Binance WebSocket error: {e}")
                if self.running:
                    time.sleep(5)
    
    def start(self):
        """Start the WebSocket feed."""
        if self.running:
            logger.warning("Binance feed already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
        # Wait for first price update
        timeout = 10
        start = time.time()
        while self.price is None and (time.time() - start) < timeout:
            time.sleep(0.1)
        
        if self.price:
            logger.info(f"✅ Binance feed started: BTC ${self.price:,.2f}")
        else:
            logger.warning("Binance feed started but no price received yet")
    
    def stop(self):
        """Stop the WebSocket feed."""
        logger.info("Stopping Binance feed...")
        self.running = False
        
        if self.ws:
            self.ws.close()
        
        if self.thread:
            self.thread.join(timeout=5)
    
    def register_callback(self, callback):
        """
        Register a callback function to be called on price updates.
        
        Args:
            callback: Function that accepts price as argument
        """
        self.callbacks.append(callback)
    
    def get_price(self):
        """
        Get current BTC price.
        
        Returns:
            Current price or None if not available
        """
        return self.price
    
    def is_connected(self):
        """Check if feed is connected and receiving data."""
        if not self.running:
            return False
        
        # Check if we received data in last 10 seconds
        if self.last_update and (time.time() - self.last_update) < 10:
            return True
        
        return False
