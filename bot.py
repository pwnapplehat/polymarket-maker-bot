#!/usr/bin/env python3
"""Polymarket Maker Bot - Main Entry Point."""
import sys
import time
import signal
from config import Config
from logger import logger

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
        iteration = 0
        
        while self.running:
            iteration += 1
            
            try:
                # TODO: Implement actual trading logic
                # For now, just simulate monitoring
                
                logger.info(f"Iteration {iteration}: Monitoring markets...")
                
                # Check safety limits
                if self.daily_pnl < -Config.MAX_DAILY_LOSS:
                    logger.warning(f"Daily loss limit reached: ${-self.daily_pnl:.2f}")
                    logger.warning("Stopping bot for safety")
                    break
                
                if self.daily_trades >= Config.MAX_DAILY_TRADES:
                    logger.warning(f"Daily trade limit reached: {self.daily_trades}")
                    logger.warning("Stopping bot for safety")
                    break
                
                # Sleep until next cycle
                time.sleep(Config.CANCEL_REPLACE_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(5)  # Wait before retrying
    
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
