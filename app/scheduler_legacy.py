"""
scheduler_legacy.py

This is a transitional module that imports and re-exports the refactored 
scheduler package functionality for backward compatibility.

In new code, please use app.scheduler directly instead of this module.
"""

import sys
import signal
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

try:
    # Try to import from our new package structure
    from app.scheduler import PolicyPulseScheduler, scheduler, handle_signal
    
    logger.info("Successfully imported refactored scheduler package")
except ImportError as e:
    # Fall back to original implementation if package not found
    logger.error(f"Failed to import refactored scheduler package: {e}")
    logger.error("Using original scheduler implementation")
    
    # Here we would have the original implementation or raise an error
    # For now, we'll just raise the original exception
    raise

# For backward compatibility
if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    logger.info("Starting PolicyPulse scheduler (legacy module)...")
    
    # Run seeding if requested via command line argument
    if len(sys.argv) > 1 and sys.argv[1] == '--seed':
        start_date = sys.argv[2] if len(sys.argv) > 2 else "2025-01-01"
        logger.info(f"Running historical data seeding from {start_date}...")
        scheduler.run_historical_seeding(start_date)
    else:
        # Start scheduler
        scheduler.start()
        
        # Keep main thread alive
        try:
            while scheduler.is_running:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            if scheduler.is_running:
                scheduler.stop()
    
    logger.info("PolicyPulse scheduler shutdown complete") 