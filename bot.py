#!/usr/bin/env python3
"""Polymarket Maker Bot - Main Entry Point."""
import sys
import time
import signal
from config import Config
from logger import logger
from polymarket_client import PolymarketClient
from maker_strategy import MakerStrategy

class PolymarketMakerBot:
    """Main bot orchestrator."""
    
    def __init__(self, live_mode=False):
        """Initialize bot."""
        self.live_mode = live_mode
        self.running = False
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.start_time = time.time()
        
        # Override dry-run if live mode specified
        if live_mode:
            Config.ENABLE_DRY_RUN = False
        
        logger.info("Initializing Polymarket Maker Bot...")
        
        # Validate configuration
        try:
            Config.validate()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
        
        # Check wallet for live mode
        if not Config.ENABLE_DRY_RUN and not Config.PRIVATE_KEY:
            logger.error("PRIVATE_KEY required for live mode")
            logger.error("Edit .env file and add your MetaMask private key")
            sys.exit(1)
        
        # Initialize Polymarket client
        private_key = Config.PRIVATE_KEY if not Config.ENABLE_DRY_RUN else None
        self.client = PolymarketClient(private_key=private_key)
        
        # Initialize maker strategy
        self.strategy = MakerStrategy(self.client, target_market_duration="15m")
    
    def start(self):
        """Start the bot."""
        logger.info("=" * 60)
        logger.info("Polymarket Maker Bot v1.0")
        logger.info("=" * 60)
        
        Config.print_config()
        
        if Config.ENABLE_DRY_RUN:
            logger.warning("🔵 DRY-RUN MODE: No real trades will be executed")
        else:
            logger.warning("🔴 LIVE MODE: Real trades with real money!")
            time.sleep(2)  # Give user time to cancel
        
        logger.info("")
        logger.info("Starting bot... Press Ctrl+C to stop")
        logger.info("")
        
        self.running = True
        
        try:
            self._run_loop()
        except KeyboardInterrupt:
            logger.info("\nReceived stop signal...")
            self.stop()
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            self.stop()
    
    def _run_loop(self):
        """Main bot loop."""
        # Start the maker strategy
        try:
            self.strategy.run()
        except Exception as e:
            logger.error(f"Strategy error: {e}", exc_info=True)
            raise
    
    def stop(self):
        """Stop the bot gracefully."""
        logger.info("Stopping bot...")
        self.running = False
        
        # Print final statistics
        runtime = time.time() - self.start_time
        logger.info("")
        logger.info("=" * 60)
        logger.info("Bot Statistics")
        logger.info("=" * 60)
        logger.info(f"Runtime:       {runtime/60:.1f} minutes")
        logger.info(f"Daily P&L:     ${self.daily_pnl:+.2f}")
        logger.info(f"Daily Trades:  {self.daily_trades}")
        logger.info("=" * 60)
        logger.info("✅ Bot stopped safely")

def signal_handler(sig, frame):
    """Handle Ctrl+C signal."""
    print("\nReceived interrupt signal...")
    sys.exit(0)

def main():
    """Main entry point."""
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Check for live mode flag
    live_mode = "--live" in sys.argv
    
    # Create and start bot
    bot = PolymarketMakerBot(live_mode=live_mode)
    bot.start()

if __name__ == "__main__":
    main()
