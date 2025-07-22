#!/usr/bin/env python3
"""
Exercise Detection Script
Runs at 7:00 AM HKT to detect overnight option exercises
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import xml.etree.ElementTree as ET

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '01_backend'))

from services.ibkr_flex_query_enhanced import flex_query_enhanced
from database.trade_db import get_trade_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/info/fntx-ai-v1/logs/exercise_detector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ExerciseDetector:
    """Detect option exercises from IBKR FlexQuery data"""
    
    def __init__(self):
        self.exercises_found = []
        self.stock_positions = []
        
    def detect_exercises(self):
        """Main detection logic"""
        logger.info("Starting exercise detection...")
        
        # Request FlexQuery report
        reference_code = flex_query_enhanced.request_flex_report()
        if not reference_code:
            logger.error("Failed to request FlexQuery report")
            return False
            
        # Wait for report generation
        import time
        time.sleep(5)
        
        # Get report XML
        xml_data = flex_query_enhanced.get_flex_report(reference_code)
        if not xml_data:
            logger.error("Failed to retrieve FlexQuery report")
            return False
            
        # Parse for exercises
        self._parse_exercises(xml_data)
        
        # Save to database
        if self.exercises_found:
            self._save_exercises()
            return True
        else:
            logger.info("No exercises detected")
            return False
            
    def _parse_exercises(self, xml_data: str):
        """Parse XML for option exercises"""
        try:
            root = ET.fromstring(xml_data)
            
            # Parse OptionEAE (Option Exercise/Assignment/Expiration) section
            for exercise in root.findall(".//OptionEAE"):
                asset_category = exercise.get('assetCategory', '')
                symbol = exercise.get('symbol', '')
                trans_type = exercise.get('transactionType', '')
                
                # Only process SPY options that are assignments or exercises
                if (asset_category == 'OPT' and 
                    'SPY' in symbol.upper() and 
                    trans_type in ['Exercise', 'Assignment']):
                    
                    self._process_option_exercise(exercise)
                    
                # Also capture the stock position from assignment
                elif (asset_category == 'STK' and 
                      symbol == 'SPY' and 
                      trans_type == 'Buy'):
                    # This is the stock received from assignment
                    trade_price = float(exercise.get('tradePrice', 0))
                    quantity = int(exercise.get('quantity', 0))
                    
                    # Check if price matches a strike (indicates assignment)
                    if trade_price % 1 == 0 and quantity == 100:  
                        logger.info(f"Stock from assignment: {quantity} SPY @ ${trade_price}")
                        
        except Exception as e:
            logger.error(f"Error parsing exercises: {e}")
            
    def _process_option_exercise(self, exercise_elem):
        """Process an option exercise/assignment from OptionEAE"""
        try:
            # Extract data from OptionEAE element
            exercise_data = {
                'trade_date': exercise_elem.get('date'),  # date format: YYYYMMDD
                'symbol': exercise_elem.get('symbol'),
                'asset_category': exercise_elem.get('assetCategory'),
                'quantity': int(exercise_elem.get('quantity', 0)),
                'strike': float(exercise_elem.get('strike', 0)),
                'option_type': 'PUT' if exercise_elem.get('putCall') == 'P' else 'CALL',
                'transaction_type': exercise_elem.get('transactionType'),
                'trade_id': exercise_elem.get('tradeID', '')
            }
            
            # Quantity is positive in OptionEAE for assignments
            if exercise_data['quantity'] > 0:
                logger.info(f"Exercise detected: {exercise_data['symbol']} - "
                          f"{exercise_data['quantity']} contracts {exercise_data['transaction_type']}")
                logger.info(f"  Strike: ${exercise_data['strike']}, Type: {exercise_data['option_type']}")
                self.exercises_found.append(exercise_data)
                
        except Exception as e:
            logger.error(f"Error processing option exercise: {e}")
            
    def _process_stock_position(self, position_elem):
        """Process stock position from exercise"""
        try:
            position_data = {
                'symbol': position_elem.get('symbol'),
                'quantity': int(position_elem.get('position', 0)),
                'mark_price': float(position_elem.get('markPrice', 0)),
                'position_value': float(position_elem.get('positionValue', 0))
            }
            
            logger.info(f"Stock position from exercise: {position_data['symbol']} - {position_data['quantity']} shares")
            self.stock_positions.append(position_data)
            
        except Exception as e:
            logger.error(f"Error processing stock position: {e}")
            
        
    def _save_exercises(self):
        """Save detected exercises to database"""
        conn = get_trade_db_connection()
        if not conn:
            logger.error("Failed to connect to database")
            return
            
        try:
            with conn.cursor() as cursor:
                for exercise in self.exercises_found:
                    # Check if already recorded
                    cursor.execute("""
                        SELECT exercise_id FROM portfolio.option_exercises
                        WHERE option_symbol = %s AND exercise_date = %s
                    """, (exercise['symbol'], exercise['trade_date']))
                    
                    if cursor.fetchone():
                        logger.info(f"Exercise already recorded: {exercise['symbol']}")
                        continue
                        
                    # Insert new exercise
                    cursor.execute("""
                        INSERT INTO portfolio.option_exercises (
                            exercise_date, option_symbol, strike_price, 
                            option_type, contracts, shares_received,
                            detection_time, disposal_status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        datetime.strptime(exercise['trade_date'], '%Y%m%d').date(),
                        exercise['symbol'],
                        exercise['strike'],
                        exercise['option_type'],
                        abs(exercise['quantity']),  # Contracts exercised
                        abs(exercise['quantity']) * 100,  # Shares received
                        datetime.now(),
                        'PENDING'
                    ))
                    
                    logger.info(f"Recorded exercise: {exercise['symbol']} - {abs(exercise['quantity'])} contracts")
                    
                conn.commit()
                logger.info(f"Saved {len(self.exercises_found)} exercises to database")
                
        except Exception as e:
            logger.error(f"Error saving exercises: {e}")
            conn.rollback()
        finally:
            conn.close()


def main():
    """Main entry point"""
    detector = ExerciseDetector()
    
    # Run detection
    if detector.detect_exercises():
        print(f"\n✅ Detected {len(detector.exercises_found)} exercises")
        print(f"✅ Found {len(detector.stock_positions)} stock positions")
        
        # Trigger disposal script if exercises found
        if detector.exercises_found:
            print("\n🚀 Triggering exercise disposal...")
            os.system("python3 /home/info/fntx-ai-v1/01_backend/scripts/exercise_disposal_asap.py")
    else:
        print("\n✅ No exercises detected")


if __name__ == "__main__":
    main()