#!/usr/bin/env python3
"""
Start the IBKR Trade Logger Service
Automatically captures and logs all trades executed through Interactive Brokers
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ibkr_trade_logger import IBKRTradeLogger

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the trade logger service"""
    
    # Database configuration
    db_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "database": os.getenv("DB_NAME", "fntx_trading"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "postgres")
    }
    
    # Create trade logger instance
    trade_logger = IBKRTradeLogger(db_config)
    
    logger.info("Starting IBKR Trade Logger Service...")
    logger.info(f"Connecting to database: {db_config['database']}@{db_config['host']}")
    logger.info(f"IBKR connection: {trade_logger.host}:{trade_logger.port}")
    
    try:
        # Start the service
        await trade_logger.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
    except Exception as e:
        logger.error(f"Trade logger service error: {e}")
    finally:
        trade_logger.stop()
        logger.info("Trade logger service stopped")

if __name__ == "__main__":
    asyncio.run(main())