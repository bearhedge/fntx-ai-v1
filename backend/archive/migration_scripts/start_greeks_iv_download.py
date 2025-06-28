#!/usr/bin/env python3
"""
Start Greeks and IV Download for Existing Data (2021-2024)
Phase 1: Enhance existing OHLC data with Greeks and IV
"""
import sys
import os
import logging
from datetime import datetime

# Add parent directory to path
sys.path.append('/home/info/fntx-ai-v1')
from backend.data.theta_downloader_enhanced import EnhancedThetaDownloader

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/info/fntx-ai-v1/logs/greeks_iv_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def start_greeks_iv_download():
    """Start downloading Greeks and IV for existing 2021-2024 data"""
    
    logger.info("🚀 Starting Greeks/IV Enhancement for 2021-2024 Data")
    logger.info("=" * 60)
    
    downloader = EnhancedThetaDownloader()
    
    try:
        # Define the periods where we already have OHLC data
        # Start with 2024 (most recent and valuable)
        periods_to_enhance = [
            ('20240101', '20240331', '2024 Q1'),
            ('20240401', '20240630', '2024 Q2'),
            ('20240701', '20240930', '2024 Q3'),
            ('20241001', '20241231', '2024 Q4'),
            ('20230101', '20230331', '2023 Q1'),
            ('20230401', '20230630', '2023 Q2'),
            ('20230701', '20230930', '2023 Q3'),
            ('20231001', '20231231', '2023 Q4'),
            ('20220101', '20220331', '2022 Q1'),
            ('20220401', '20220630', '2022 Q2'),
            ('20220701', '20220930', '2022 Q3'),
            ('20221001', '20221231', '2022 Q4'),
            ('20210101', '20210331', '2021 Q1'),
            ('20210401', '20210630', '2021 Q2'),
            ('20210701', '20210930', '2021 Q3'),
            ('20211001', '20211231', '2021 Q4'),
        ]
        
        logger.info(f"📊 Will enhance {len(periods_to_enhance)} quarterly periods")
        logger.info(f"📈 Data types: {downloader.available_data_types}")
        
        for i, (start_date, end_date, period_name) in enumerate(periods_to_enhance):
            logger.info(f"\n📅 Processing {period_name} ({i+1}/{len(periods_to_enhance)})")
            logger.info(f"🗓️  Period: {start_date} to {end_date}")
            
            try:
                # This will download Greeks and IV for this period
                # OHLC will be skipped since it already exists
                downloader.download_date_range(start_date, end_date)
                
                logger.info(f"✅ Completed {period_name}")
                
                # Log current stats
                stats = downloader.stats
                logger.info(f"📊 Progress: {stats['contracts_processed']:,} contracts, "
                          f"Greeks: {stats['greeks_records']:,}, IV: {stats['iv_records']:,}")
                
            except Exception as e:
                logger.error(f"❌ Failed {period_name}: {e}")
                continue
        
        # Final statistics
        final_stats = downloader.stats
        duration = datetime.now() - final_stats['start_time']
        
        logger.info("\n🎉 Greeks/IV Enhancement Complete!")
        logger.info("=" * 50)
        logger.info(f"⏰ Duration: {duration}")
        logger.info(f"📈 Contracts processed: {final_stats['contracts_processed']:,}")
        logger.info(f"🧮 Greeks records: {final_stats['greeks_records']:,}")
        logger.info(f"📐 IV records: {final_stats['iv_records']:,}")
        logger.info(f"❌ Errors: {final_stats['errors']:,}")
        
    except Exception as e:
        logger.error(f"💥 Critical error: {e}")
        raise
    finally:
        downloader.close()


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    os.makedirs('/home/info/fntx-ai-v1/logs', exist_ok=True)
    
    start_greeks_iv_download()