#!/usr/bin/env python3
"""
Background Database Cleanup
Removes old far OTM contracts while downloader continues
"""
import sys
import psycopg2
import logging
import time
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/info/fntx-ai-v1/logs/background_cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

sys.path.append('/home/info/fntx-ai-v1')
from backend.config.theta_config import DB_CONFIG

def background_cleanup():
    """Run cleanup in background without blocking downloader"""
    
    logger.info("🧹 Starting Background Database Cleanup")
    logger.info("=" * 50)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check initial count
        cursor.execute("SELECT COUNT(*) FROM theta.options_ohlc")
        initial_count = cursor.fetchone()[0]
        logger.info(f"📊 Initial OHLC records: {initial_count:,}")
        
        # Delete in batches to avoid blocking
        logger.info("🗑️ Removing far OTM contracts in batches...")
        
        years_to_clean = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
        strike_ranges = {
            2017: (225, 275),  # ATM 250 ±25
            2018: (255, 305),  # ATM 280 ±25
            2019: (295, 345),  # ATM 320 ±25
            2020: (325, 375),  # ATM 350 ±25
            2021: (395, 445),  # ATM 420 ±25
            2022: (425, 475),  # ATM 450 ±25
            2023: (375, 425),  # ATM 400 ±25
            2024: (475, 525),  # ATM 500 ±25
            2025: (575, 625),  # ATM 600 ±25
        }
        
        total_deleted = 0
        
        for year in years_to_clean:
            min_strike, max_strike = strike_ranges[year]
            logger.info(f"🗓️ Cleaning {year}: Keeping strikes ${min_strike}-${max_strike}")
            
            # Delete in smaller batches
            batch_size = 100000
            year_deleted = 0
            
            while True:
                start_time = time.time()
                
                cursor.execute(f"""
                    DELETE FROM theta.options_ohlc 
                    WHERE id IN (
                        SELECT o.id 
                        FROM theta.options_ohlc o
                        JOIN theta.options_contracts c ON o.contract_id = c.contract_id
                        WHERE c.symbol = 'SPY'
                        AND EXTRACT(YEAR FROM c.expiration) = %s
                        AND (c.strike < %s OR c.strike > %s)
                        LIMIT %s
                    )
                """, (year, min_strike, max_strike, batch_size))
                
                deleted_count = cursor.rowcount
                if deleted_count == 0:
                    break
                
                year_deleted += deleted_count
                total_deleted += deleted_count
                
                # Commit batch
                conn.commit()
                
                elapsed = time.time() - start_time
                logger.info(f"   Batch: {deleted_count:,} records in {elapsed:.1f}s | Year total: {year_deleted:,}")
                
                # Small delay to not overwhelm database
                time.sleep(0.5)
            
            logger.info(f"✅ {year} complete: {year_deleted:,} records removed")
        
        # Clean orphaned contracts
        logger.info("🧹 Removing orphaned contracts...")
        cursor.execute("""
            DELETE FROM theta.options_contracts 
            WHERE contract_id NOT IN (
                SELECT DISTINCT contract_id FROM theta.options_ohlc
            )
        """)
        orphaned = cursor.rowcount
        conn.commit()
        
        # Update statistics
        logger.info("📊 Updating database statistics...")
        cursor.execute("ANALYZE theta.options_ohlc")
        cursor.execute("ANALYZE theta.options_contracts")
        
        # Final count
        cursor.execute("SELECT COUNT(*) FROM theta.options_ohlc")
        final_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        # Summary
        logger.info("\n✅ Background Cleanup Complete!")
        logger.info("=" * 50)
        logger.info(f"📊 Before: {initial_count:,} records")
        logger.info(f"📊 After:  {final_count:,} records")
        logger.info(f"🗑️ Removed: {total_deleted:,} OHLC records")
        logger.info(f"🗑️ Orphaned contracts: {orphaned:,}")
        logger.info(f"💾 Space freed: ~{total_deleted * 0.5 / 1024:.1f} MB")
        logger.info("🚀 Database optimized for smart filtering!")
        
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    background_cleanup()