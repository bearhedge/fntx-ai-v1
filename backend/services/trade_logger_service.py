#!/usr/bin/env python3
"""
24/7 IBKR Trade Logger Service
Runs continuously to capture all trades automatically
"""

import os
import sys
import asyncio
import logging
import signal
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ibkr_trade_logger import IBKRTradeLogger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/info/fntx-ai-v1/08_logs/trade_logger_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_flag = False

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global shutdown_flag
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_flag = True

async def create_trade_table_if_not_exists():
    """Ensure trade tables exist"""
    try:
        from 01_backend.database.trade_db import get_trade_db_connection
        conn = get_trade_db_connection()
        
        with conn.cursor() as cur:
            # Check if trading schema exists
            cur.execute("""
                SELECT schema_name FROM information_schema.schemata 
                WHERE schema_name = 'trading'
            """)
            if not cur.fetchone():
                logger.info("Creating trading schema and tables...")
                with open('/home/info/fntx-ai-v1/database/trades_schema.sql', 'r') as f:
                    cur.execute(f.read())
                conn.commit()
                logger.info("Trade tables created successfully")
            else:
                logger.info("Trade tables already exist")
                
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to create trade tables: {e}")
        raise

async def main():
    """Main service loop"""
    logger.info("FNTX 24/7 Trade Logger Service starting...")
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Ensure database tables exist
    await create_trade_table_if_not_exists()
    
    # Database configuration - use existing connection module
    from 01_backend.database.trade_db import get_trade_db_connection
    db_config = None  # Will use get_trade_db_connection() instead
    
    # Create trade logger instance
    trade_logger = IBKRTradeLogger(db_config)
    
    # Start logger
    logger.info("Starting IBKR Trade Logger...")
    logger.info(f"IBKR connection: {trade_logger.host}:{trade_logger.port}")
    
    try:
        # Run until shutdown signal
        await trade_logger.start()
        
    except Exception as e:
        logger.error(f"Trade logger error: {e}")
    finally:
        trade_logger.stop()
        logger.info("Trade logger service stopped")

if __name__ == "__main__":
    asyncio.run(main())