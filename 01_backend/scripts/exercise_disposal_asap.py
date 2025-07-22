#!/usr/bin/env python3
"""
ASAP Exercise Disposal Script
Places extended hours limit orders to dispose of exercised stock positions
Runs immediately after exercise detection (7:30 AM HKT)
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from ib_insync import *

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '01_backend'))

from database.trade_db import get_trade_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/info/fntx-ai-v1/logs/exercise_disposal.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ExerciseDisposal:
    """Handle immediate disposal of exercised stock positions"""
    
    def __init__(self, host='127.0.0.1', port=4001, client_id=20):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = None
        self.pending_exercises = []
        
    def connect(self) -> bool:
        """Connect to IB Gateway"""
        try:
            self.ib = IB()
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            logger.info(f"Connected to IB Gateway at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IB Gateway: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from IB Gateway"""
        if self.ib:
            self.ib.disconnect()
            logger.info("Disconnected from IB Gateway")
            
    def get_pending_exercises(self):
        """Get exercises pending disposal from database"""
        conn = get_trade_db_connection()
        if not conn:
            logger.error("Failed to connect to database")
            return []
            
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT exercise_id, option_symbol, strike_price, 
                           option_type, shares_received, exercise_date
                    FROM portfolio.option_exercises
                    WHERE disposal_status = 'PENDING'
                    ORDER BY exercise_date DESC
                """)
                
                for row in cursor.fetchall():
                    self.pending_exercises.append({
                        'exercise_id': row[0],
                        'option_symbol': row[1],
                        'strike_price': float(row[2]),
                        'option_type': row[3],
                        'shares': row[4],
                        'exercise_date': row[5]
                    })
                    
            logger.info(f"Found {len(self.pending_exercises)} pending exercises")
            return self.pending_exercises
            
        except Exception as e:
            logger.error(f"Error fetching pending exercises: {e}")
            return []
        finally:
            conn.close()
            
    def get_last_close_price(self, symbol='SPY') -> float:
        """Get previous close price for limit order calculation"""
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            
            # Request historical data for last close
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr='2 D',
                barSizeSetting='1 day',
                whatToShow='TRADES',
                useRTH=True
            )
            
            if bars and len(bars) > 0:
                last_close = bars[-1].close
                logger.info(f"{symbol} last close: ${last_close:.2f}")
                return last_close
            else:
                logger.warning(f"No historical data for {symbol}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error getting last close: {e}")
            return 0.0
            
    def calculate_aggressive_limit(self, last_close: float, discount_pct: float = 0.001) -> float:
        """Calculate aggressive limit price for quick fill"""
        # Default 0.1% below last close for SPY liquidity
        limit_price = last_close * (1 - discount_pct)
        return round(limit_price, 2)
        
    def create_extended_hours_order(self, shares: int, limit_price: float, symbol='SPY'):
        """Create extended hours limit order"""
        contract = Stock(symbol, 'SMART', 'USD')
        
        # Calculate good till date/time (8 PM ET today)
        now = datetime.now()
        today_8pm_et = now.replace(hour=20, minute=0, second=0)  # 8 PM ET
        gtd_string = today_8pm_et.strftime('%Y%m%d %H:%M:%S')
        
        order = LimitOrder(
            action='SELL',
            totalQuantity=shares,
            lmtPrice=limit_price,
            tif='GTD',  # Good till date/time
            goodTillDate=gtd_string,
            outsideRth=True,  # Allow outside regular trading hours
            transmit=True
        )
        
        return contract, order
        
    def place_disposal_order(self, exercise: dict) -> bool:
        """Place disposal order for exercised shares"""
        try:
            # Get last close price
            last_close = self.get_last_close_price('SPY')
            if last_close == 0:
                logger.error("Cannot get last close price")
                return False
                
            # Calculate limit price
            limit_price = self.calculate_aggressive_limit(last_close)
            
            # Create order
            contract, order = self.create_extended_hours_order(
                shares=exercise['shares'],
                limit_price=limit_price
            )
            
            # Place order
            trade = self.ib.placeOrder(contract, order)
            
            # Wait for order acknowledgment
            self.ib.sleep(2)
            
            if trade.orderStatus.status in ['PreSubmitted', 'Submitted']:
                logger.info(f"✅ Disposal order placed: {exercise['shares']} shares @ ${limit_price:.2f}")
                logger.info(f"   Order ID: {trade.order.orderId}")
                logger.info(f"   Good till: 8 PM ET today")
                logger.info(f"   Extended hours: ENABLED")
                
                # Update database
                self._update_disposal_status(
                    exercise['exercise_id'],
                    'ORDER_PLACED',
                    trade.order.orderId,
                    limit_price
                )
                return True
            else:
                logger.error(f"Order failed: {trade.orderStatus.status}")
                return False
                
        except Exception as e:
            logger.error(f"Error placing disposal order: {e}")
            return False
            
    def _update_disposal_status(self, exercise_id: int, status: str, 
                               order_id: int = None, disposal_price: float = None):
        """Update disposal status in database"""
        conn = get_trade_db_connection()
        if not conn:
            return
            
        try:
            with conn.cursor() as cursor:
                if order_id and disposal_price:
                    cursor.execute("""
                        UPDATE portfolio.option_exercises
                        SET disposal_status = %s,
                            disposal_order_id = %s,
                            disposal_price = %s,
                            disposal_time = %s
                        WHERE exercise_id = %s
                    """, (status, str(order_id), disposal_price, datetime.now(), exercise_id))
                else:
                    cursor.execute("""
                        UPDATE portfolio.option_exercises
                        SET disposal_status = %s
                        WHERE exercise_id = %s
                    """, (status, exercise_id))
                    
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating disposal status: {e}")
            conn.rollback()
        finally:
            conn.close()
            
    def run_disposal(self):
        """Main disposal process"""
        # Get pending exercises
        exercises = self.get_pending_exercises()
        if not exercises:
            logger.info("No exercises pending disposal")
            return
            
        # Connect to IB
        if not self.connect():
            logger.error("Cannot connect to IB Gateway")
            return
            
        try:
            # Process each exercise
            successful = 0
            for exercise in exercises:
                logger.info(f"\nProcessing exercise: {exercise['option_symbol']}")
                logger.info(f"  Strike: ${exercise['strike_price']:.2f}")
                logger.info(f"  Type: {exercise['option_type']}")
                logger.info(f"  Shares to dispose: {exercise['shares']}")
                
                if self.place_disposal_order(exercise):
                    successful += 1
                else:
                    logger.error(f"Failed to place disposal order for {exercise['option_symbol']}")
                    
                # Small delay between orders
                self.ib.sleep(1)
                
            logger.info(f"\n✅ Disposal orders placed: {successful}/{len(exercises)}")
            
            # Show order summary
            if successful > 0:
                print("\n" + "="*60)
                print("EXTENDED HOURS DISPOSAL ORDERS PLACED")
                print("="*60)
                print(f"Orders placed: {successful}")
                print("Trading window: 4:00 PM - 8:00 PM HKT (Pre-market)")
                print("Order type: Limit (0.1% below last close)")
                print("Time in force: Good till 8 PM ET")
                print("\nMonitor fills at 4:00 PM HKT when pre-market opens")
                print("="*60)
                
        finally:
            self.disconnect()


def main():
    """Main entry point"""
    disposal = ExerciseDisposal()
    disposal.run_disposal()


if __name__ == "__main__":
    main()