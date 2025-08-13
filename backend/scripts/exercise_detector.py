#!/usr/bin/env python3
"""
Exercise Detection Script - Detects option exercises and assignments
Runs daily at 7:00 AM HKT to catch exercises before market open
"""
import os
import sys
import logging
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import requests

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'backend'))

from backend.data.database.trade_db import get_trade_db_connection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/info/fntx-ai-v1/logs/exercise_detection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ExerciseDetector:
    """Detects option exercises using IBKR FlexQuery API"""
    
    def __init__(self):
        self.token = os.getenv('IBKR_FLEX_TOKEN')
        self.query_id = '1257675'  # Exercises and Expiries query ID
        self.base_url = 'https://gdcdyn.interactivebrokers.com/Universal/servlet'
        
        if not self.token:
            raise ValueError("IBKR_FLEX_TOKEN not found in environment")
    
    def request_flex_report(self):
        """Request FlexQuery report from IBKR"""
        try:
            url = f"{self.base_url}/FlexStatementService.SendRequest"
            params = {
                't': self.token,
                'q': self.query_id,
                'v': '3'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.text)
            status = root.find('.//Status').text
            
            if status == 'Success':
                reference_code = root.find('.//ReferenceCode').text
                logger.info(f"FlexQuery requested successfully. Reference: {reference_code}")
                return reference_code
            else:
                error_msg = root.find('.//ErrorMessage')
                error_text = error_msg.text if error_msg is not None else "Unknown error"
                logger.error(f"FlexQuery request failed: {error_text}")
                return None
                
        except Exception as e:
            logger.error(f"Error requesting FlexQuery report: {e}")
            return None
    
    def get_flex_report(self, reference_code):
        """Download FlexQuery report using reference code"""
        try:
            url = f"{self.base_url}/FlexStatementService.GetStatement"
            params = {
                't': self.token,
                'q': reference_code,
                'v': '3'
            }
            
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            
            # Check if report is ready
            if 'Statement generation in progress' in response.text:
                logger.info("Report still generating, please wait...")
                return None
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error downloading FlexQuery report: {e}")
            return None
    
    def parse_exercises(self, xml_data):
        """Parse XML data to find exercises and assignments"""
        exercises = []
        
        try:
            root = ET.fromstring(xml_data)
            
            # Look for OptionEAE (Exercises and Assignments) elements
            for statement in root.findall('.//FlexStatement'):
                statement_date = statement.get('fromDate')
                
                for exercise in statement.findall('.//OptionEAE'):
                    transaction_type = exercise.get('transactionType')
                    
                    # Only process Assignment transactions
                    if transaction_type == 'Assignment':
                        exercise_data = {
                            'date': statement_date,
                            'symbol': exercise.get('symbol'),
                            'strike': float(exercise.get('strike', 0)),
                            'option_type': exercise.get('putCall'),
                            'quantity': int(exercise.get('quantity', 0)),
                            'underlying_symbol': exercise.get('underlyingSymbol'),
                            'trade_id': exercise.get('tradeID')
                        }
                        exercises.append(exercise_data)
                        logger.info(f"Found assignment: {exercise_data['symbol']} on {statement_date}")
            
            return exercises
            
        except Exception as e:
            logger.error(f"Error parsing XML data: {e}")
            return []
    
    def save_exercise_to_db(self, exercise_data):
        """Save detected exercise to database"""
        conn = get_trade_db_connection()
        if not conn:
            logger.error("Failed to connect to database")
            return False
        
        try:
            with conn.cursor() as cursor:
                # Check if exercise already exists
                cursor.execute("""
                    SELECT exercise_id FROM portfolio.option_exercises
                    WHERE option_symbol = %s AND exercise_date = %s
                """, (exercise_data['symbol'], exercise_data['date']))
                
                if cursor.fetchone():
                    logger.info(f"Exercise already recorded: {exercise_data['symbol']}")
                    return True
                
                # Insert new exercise
                cursor.execute("""
                    INSERT INTO portfolio.option_exercises (
                        exercise_date, option_symbol, strike_price, option_type,
                        contracts, shares_received, detection_time, disposal_status,
                        trade_id, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING exercise_id
                """, (
                    exercise_data['date'],
                    exercise_data['symbol'],
                    exercise_data['strike'],
                    exercise_data['option_type'],
                    abs(exercise_data['quantity']),
                    abs(exercise_data['quantity']) * 100,  # 100 shares per contract
                    datetime.now(),
                    'PENDING',
                    exercise_data['trade_id'],
                    f"Auto-detected on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} HKT"
                ))
                
                exercise_id = cursor.fetchone()[0]
                conn.commit()
                
                logger.info(f"Exercise saved to database: ID {exercise_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving exercise to database: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def check_for_exercises(self):
        """Main method to check for exercises"""
        logger.info("=" * 60)
        logger.info("FNTX Exercise Detection - Starting")
        logger.info("=" * 60)
        logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} HKT")
        
        # Step 1: Request FlexQuery report
        logger.info("Step 1: Requesting FlexQuery report...")
        reference_code = self.request_flex_report()
        if not reference_code:
            logger.error("Failed to request FlexQuery report")
            return False
        
        # Step 2: Wait and download report
        logger.info("Step 2: Waiting for report generation...")
        import time
        for attempt in range(6):  # Wait up to 60 seconds
            time.sleep(10)
            xml_data = self.get_flex_report(reference_code)
            if xml_data:
                break
            logger.info(f"Attempt {attempt + 1}/6: Report not ready yet...")
        
        if not xml_data:
            logger.error("Failed to download FlexQuery report")
            return False
        
        # Step 3: Parse exercises
        logger.info("Step 3: Parsing exercises from report...")
        exercises = self.parse_exercises(xml_data)
        
        if not exercises:
            logger.info("No new exercises detected")
            return True
        
        # Step 4: Save exercises to database
        logger.info(f"Step 4: Processing {len(exercises)} exercise(s)...")
        success_count = 0
        
        for exercise in exercises:
            if self.save_exercise_to_db(exercise):
                success_count += 1
        
        logger.info(f"Successfully processed {success_count}/{len(exercises)} exercises")
        
        # Step 5: Trigger disposal (if needed)
        if success_count > 0:
            logger.info("Step 5: Exercises detected - disposal may be needed")
            logger.info("Check pending exercises with: python3 backend/scripts/check_exercises.py")
        
        logger.info("=" * 60)
        logger.info("FNTX Exercise Detection - Completed")
        logger.info("=" * 60)
        
        return True


def main():
    """Main entry point"""
    try:
        detector = ExerciseDetector()
        success = detector.check_for_exercises()
        
        if success:
            logger.info("Exercise detection completed successfully")
            sys.exit(0)
        else:
            logger.error("Exercise detection failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error in exercise detection: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()