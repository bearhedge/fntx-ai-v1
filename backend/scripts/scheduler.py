#!/usr/bin/env python3
"""
FNTX Trading System Scheduler
Runs scheduled tasks at specific times each day
"""
import schedule
import time
import subprocess
import logging
from datetime import datetime
import os
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/info/fntx-ai-v1/logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Change to project directory
os.chdir('/home/info/fntx-ai-v1')
sys.path.insert(0, '/home/info/fntx-ai-v1')
sys.path.insert(0, '/home/info/fntx-ai-v1/01_backend')


def run_daily_import():
    """Run daily NAV import from IBKR FlexQuery"""
    logger.info("Starting daily NAV import...")
    try:
        result = subprocess.run(
            [sys.executable, '/home/info/fntx-ai-v1/01_backend/scripts/daily_flex_import.py'],
            capture_output=True,
            text=True,
            cwd='/home/info/fntx-ai-v1'
        )
        if result.returncode == 0:
            logger.info("✅ Daily import completed successfully")
        else:
            logger.error(f"❌ Daily import failed: {result.stderr}")
    except Exception as e:
        logger.error(f"❌ Error running daily import: {e}")


def run_exercise_detection():
    """Run exercise detection and disposal"""
    logger.info("Starting exercise detection...")
    try:
        result = subprocess.run(
            [sys.executable, '/home/info/fntx-ai-v1/01_backend/scripts/exercise_detector.py'],
            capture_output=True,
            text=True,
            cwd='/home/info/fntx-ai-v1'
        )
        if result.returncode == 0:
            logger.info("✅ Exercise detection completed successfully")
        else:
            logger.error(f"❌ Exercise detection failed: {result.stderr}")
    except Exception as e:
        logger.error(f"❌ Error running exercise detection: {e}")


def run_historical_backfill():
    """Run historical data backfill (weekly)"""
    logger.info("Starting historical backfill...")
    try:
        # Check if script exists first
        script_path = '/home/info/fntx-ai-v1/01_backend/scripts/historical_backfill.py'
        if os.path.exists(script_path):
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                cwd='/home/info/fntx-ai-v1'
            )
            if result.returncode == 0:
                logger.info("✅ Historical backfill completed successfully")
            else:
                logger.error(f"❌ Historical backfill failed: {result.stderr}")
        else:
            logger.warning("⚠️  Historical backfill script not found - skipping")
    except Exception as e:
        logger.error(f"❌ Error running historical backfill: {e}")


def main():
    """Main scheduler loop"""
    logger.info("=" * 60)
    logger.info("FNTX Trading System Scheduler Started")
    logger.info("=" * 60)
    logger.info("Scheduled tasks:")
    logger.info("  - Daily NAV Import: 07:00 HKT")
    logger.info("  - Exercise Detection: 07:00 HKT")
    logger.info("  - Historical Backfill: Sundays 03:00 HKT")
    logger.info("=" * 60)
    
    # Schedule daily tasks at 7:00 AM HKT
    schedule.every().day.at("07:00").do(run_daily_import)
    schedule.every().day.at("07:00").do(run_exercise_detection)
    
    # Schedule weekly historical backfill on Sundays at 3:00 AM HKT
    schedule.every().sunday.at("03:00").do(run_historical_backfill)
    
    # Run tasks immediately on startup if within time window
    current_time = datetime.now()
    logger.info(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')} HKT")
    
    # Check if we should run tasks now (if between 7:00-7:30 AM)
    if current_time.hour == 7 and current_time.minute < 30:
        logger.info("Within daily task window - running tasks now...")
        run_daily_import()
        run_exercise_detection()
    
    # Main loop
    logger.info("Scheduler running... Press Ctrl+C to stop")
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time.sleep(60)  # Continue after errors


if __name__ == "__main__":
    main()