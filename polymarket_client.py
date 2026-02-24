"""Polymarket CLOB client wrapper with fee-aware signing."""
import requests
import time
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from config import Config
from logger import logger

class PolymarketClient:
    """Wrapper for Polymarket CLOB API with fee-aware order signing."""
    
    def __init__(self, private_key=None):
        """
        Initialize Polymarket client.
        
        Args:
            private_key: Wallet private key (0x...). If None, runs in dry-run mode.
        """
        self.private_key = private_key
        self.client = None
        
        if private_key:
            try:
                self.client = ClobClient(
                    host=Config.CLOB_URL,
                    key=private_key,
                    chain_id=137,  # Polygon mainnet
                    signature_type=0,  # EOA/MetaMask signatures
                )
                # Set API credentials
                self.client.set_api_creds(self.client.create_or_derive_api_creds())
                logger.info("✅ Polymarket client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Polymarket client: {e}")
                raise
        else:
            logger.warning("Running in dry-run mode (no Polymarket client)")
    
    def get_markets(self, active=True):
        """
        Fetch available markets.
        
        Args:
            active: If True, only return active markets
            
        Returns:
            List of market dictionaries
        """
        try:
            # Use Gamma Markets API (CLOB API doesn't have /markets endpoint)
            url = "https://gamma-api.polymarket.com/markets"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            markets = response.json()
            
            if active:
                markets = [m for m in markets if m.get("active", False)]
            
            logger.debug(f"Fetched {len(markets)} markets")
            return markets
            
        except Exception as e:
            logger.error(f"Failed to fetch markets: {e}")
            return []
    
    def get_crypto_markets(self, duration="15m"):
        """
        Get crypto markets (BTC, ETH, etc.) by duration.
        
        Args:
            duration: "5m", "15m", or "1h"
            
        Returns:
            List of crypto market dictionaries
        """
        markets = self.get_markets(active=True)
        
        # Filter for crypto markets with specified duration
        crypto_markets = []
        for market in markets:
            question = market.get("question", "").lower()
            if "btc" in question or "bitcoin" in question:
                if duration in question or duration.replace("m", " minute") in question:
                    crypto_markets.append(market)
        
        return crypto_markets
    
    def get_fee_rate(self, token_id):
        """
        Query current fee rate for a token/market.
        
        CRITICAL: feeRateBps MUST be included in order signing for fee-enabled markets.
        
        Args:
            token_id: Token ID to query
            
        Returns:
            Fee rate in basis points (int) or 0 if no fees
        """
        try:
            url = f"{Config.CLOB_URL}/fee-rate"
            params = {"tokenID": token_id}
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            fee_bps = int(data.get("base_fee", 0))
            
            logger.debug(f"Token {token_id[:8]}...: {fee_bps} bps fee")
            return fee_bps
            
        except Exception as e:
            logger.warning(f"Failed to get fee rate: {e}, assuming 0")
            return 0
    
    def create_maker_order(self, token_id, side, price, size):
        """
        Create a maker order with fee-aware signing.
        
        Args:
            token_id: Token ID to trade
            side: "BUY" or "SELL"
            price: Price in $ (0.01 to 0.99)
            size: Order size in shares
            
        Returns:
            Order ID if successful, None otherwise
        """
        if not self.client:
            logger.info(f"[DRY-RUN] Would create {side} order: {size} shares @ ${price:.3f}")
            return f"dry-run-order-{int(time.time())}"
        
        try:
            # STEP 1: Query current fee rate (REQUIRED for fee-enabled markets)
            fee_rate_bps = self.get_fee_rate(token_id)
            
            # STEP 2: Create order with feeRateBps
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=side,
                fee_rate_bps=fee_rate_bps,  # CRITICAL: Must include this
            )
            
            # STEP 3: Create and sign order
            signed_order = self.client.create_order(order_args)
            
            # STEP 4: Post order (make sure it's post-only for maker rebate)
            order_id = self.client.post_order(signed_order, OrderType.GTC)
            
            logger.info(f"✅ Created {side} order {order_id[:8]}: {size} @ ${price:.3f}")
            return order_id
            
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            return None
    
    def cancel_order(self, order_id):
        """
        Cancel an existing order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if successful
        """
        if not self.client:
            logger.info(f"[DRY-RUN] Would cancel order {order_id}")
            return True
        
        try:
            self.client.cancel(order_id)
            logger.debug(f"Cancelled order {order_id[:8]}")
            return True
        except Exception as e:
            logger.warning(f"Failed to cancel order {order_id[:8]}: {e}")
            return False
    
    def cancel_all_orders(self):
        """Cancel all open orders."""
        if not self.client:
            logger.info("[DRY-RUN] Would cancel all orders")
            return
        
        try:
            open_orders = self.client.get_orders()
            for order in open_orders:
                self.cancel_order(order["id"])
            logger.info(f"Cancelled {len(open_orders)} orders")
        except Exception as e:
            logger.error(f"Failed to cancel all orders: {e}")
    
    def get_positions(self):
        """Get current positions."""
        if not self.client:
            return []
        
        try:
            return self.client.get_positions()
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    def get_balance(self):
        """Get USDC balance."""
        if not self.client:
            return Config.INITIAL_CAPITAL
        
        try:
            balances = self.client.get_balances()
            usdc_balance = float(balances.get("USDC", 0))
            return usdc_balance
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return 0.0
