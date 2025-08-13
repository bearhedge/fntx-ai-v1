"""
Database-based position tracker using trading.trades table
Replaces IB Gateway dependency for position tracking
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor
import pytz

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from config import DB_CONFIG


class DatabasePositionTracker:
    """Track positions using database instead of IB Gateway"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.conn = None
        self.eastern = pytz.timezone('US/Eastern')
        self._positions_cache = {}
        self._last_update = None
        
    def connect(self) -> bool:
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port'],
                database=DB_CONFIG['database'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password']
            )
            self.logger.info("Connected to PostgreSQL database")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            return False
            
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.logger.info("Disconnected from backend.data.database")
            
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions from backend.data.database"""
        if not self.conn:
            self.logger.warning("Database not connected")
            return []
            
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Query open trades
                query = """
                    SELECT 
                        trade_id,
                        symbol,
                        strike_price,
                        option_type,
                        expiration,
                        quantity,
                        entry_time,
                        entry_price,
                        entry_commission,
                        stop_loss_price,
                        market_snapshot
                    FROM trading.trades
                    WHERE status = 'open'
                    AND symbol = 'SPY'
                    ORDER BY entry_time DESC
                """
                cursor.execute(query)
                positions = cursor.fetchall()
                
                # Convert to standard format
                formatted_positions = []
                for pos in positions:
                    formatted_positions.append({
                        'trade_id': str(pos['trade_id']),
                        'symbol': pos['symbol'],
                        'strike': float(pos['strike_price']),
                        'type': pos['option_type'],
                        'quantity': pos['quantity'],
                        'entry_time': pos['entry_time'],
                        'entry_price': float(pos['entry_price']),
                        'stop_loss': float(pos['stop_loss_price']) if pos['stop_loss_price'] else None,
                        'days_to_expiry': (pos['expiration'] - datetime.now().date()).days
                    })
                    
                self._positions_cache = {p['trade_id']: p for p in formatted_positions}
                self._last_update = datetime.now()
                
                return formatted_positions
                
        except Exception as e:
            self.logger.error(f"Error fetching positions: {e}")
            return []
            
    def calculate_position_pnl(self, position: Dict, current_price: float) -> Dict:
        """Calculate P&L for a position given current market price"""
        # For short options, P&L = (entry_price - current_price) * quantity * 100
        entry = position['entry_price']
        quantity = position['quantity']
        
        # Calculate per-contract P&L
        pnl_per_contract = (entry - current_price) * 100
        total_pnl = pnl_per_contract * quantity
        
        # Calculate percentage
        pnl_percentage = (pnl_per_contract / (entry * 100)) * 100
        
        return {
            'current_price': current_price,
            'pnl_per_contract': pnl_per_contract,
            'total_pnl': total_pnl,
            'pnl_percentage': pnl_percentage,
            'unrealized': True  # Since position is still open
        }
        
    def get_position_summary(self, options_chain: List[Dict]) -> Dict:
        """Get summary of all positions with current P&L"""
        positions = self.get_open_positions()
        
        if not positions:
            return {
                'total_positions': 0,
                'total_pnl': 0,
                'positions': []
            }
            
        # Match positions with current option prices
        position_details = []
        total_pnl = 0
        
        for pos in positions:
            # Find matching option in chain
            current_price = self._find_option_price(
                options_chain,
                pos['strike'],
                pos['type']
            )
            
            if current_price is not None:
                pnl_data = self.calculate_position_pnl(pos, current_price)
                pos_detail = {**pos, **pnl_data}
                position_details.append(pos_detail)
                total_pnl += pnl_data['total_pnl']
            else:
                # Can't find price, use entry price as fallback
                position_details.append({
                    **pos,
                    'current_price': pos['entry_price'],  # Use entry price as fallback
                    'pnl_per_contract': 0,
                    'total_pnl': 0,
                    'pnl_percentage': 0,
                    'unrealized': True
                })
                
        return {
            'total_positions': len(positions),
            'total_pnl': total_pnl,
            'positions': position_details,
            'last_update': self._last_update
        }
        
    def _find_option_price(self, 
                          options_chain: List[Dict], 
                          strike: float, 
                          option_type: str) -> Optional[float]:
        """Find current price for specific option in chain"""
        for option in options_chain:
            if (option['strike'] == strike and 
                option['type'].upper() == option_type.upper()):
                # Calculate mid price from bid/ask
                bid = option.get('bid', 0)
                ask = option.get('ask', 0)
                if bid > 0 and ask > 0:
                    return (bid + ask) / 2.0
                elif bid > 0:
                    return bid
                elif ask > 0:
                    return ask
                else:
                    return option.get('last', 0)
        return None
        
    def record_new_trade(self, trade_details: Dict) -> bool:
        """Record a new trade in the database"""
        if not self.conn:
            self.logger.warning("Database not connected")
            return False
            
        try:
            with self.conn.cursor() as cursor:
                query = """
                    INSERT INTO trading.trades (
                        symbol, strike_price, option_type, expiration,
                        quantity, entry_time, entry_price, entry_commission,
                        stop_loss_price, market_snapshot
                    ) VALUES (
                        %(symbol)s, %(strike_price)s, %(option_type)s, %(expiration)s,
                        %(quantity)s, %(entry_time)s, %(entry_price)s, %(entry_commission)s,
                        %(stop_loss_price)s, %(market_snapshot)s::jsonb
                    )
                    RETURNING trade_id
                """
                
                cursor.execute(query, {
                    'symbol': 'SPY',
                    'strike_price': trade_details['strike'],
                    'option_type': 'PUT' if trade_details['right'] == 'P' else 'CALL',
                    'expiration': datetime.now().date(),  # 0DTE
                    'quantity': trade_details.get('position_size', 1),
                    'entry_time': datetime.now(),
                    'entry_price': trade_details['entry_price'],
                    'entry_commission': 0.65,  # Standard commission
                    'stop_loss_price': trade_details.get('stop_loss'),
                    'market_snapshot': '{}'  # Could add market data here
                })
                
                trade_id = cursor.fetchone()[0]
                self.conn.commit()
                
                self.logger.info(f"Recorded new trade: {trade_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error recording trade: {e}")
            if self.conn:
                self.conn.rollback()
            return False
            
    def close_position(self, trade_id: str, exit_price: float, exit_reason: str = 'manual') -> bool:
        """Close a position in the database"""
        if not self.conn:
            self.logger.warning("Database not connected")
            return False
            
        try:
            with self.conn.cursor() as cursor:
                query = """
                    UPDATE trading.trades
                    SET 
                        exit_time = %(exit_time)s,
                        exit_price = %(exit_price)s,
                        exit_commission = %(exit_commission)s,
                        exit_reason = %(exit_reason)s,
                        status = 'closed'
                    WHERE trade_id = %(trade_id)s
                    AND status = 'open'
                """
                
                cursor.execute(query, {
                    'exit_time': datetime.now(),
                    'exit_price': exit_price,
                    'exit_commission': 0.65,
                    'exit_reason': exit_reason,
                    'trade_id': trade_id
                })
                
                self.conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.info(f"Closed position: {trade_id}")
                    return True
                else:
                    self.logger.warning(f"Position not found or already closed: {trade_id}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
            if self.conn:
                self.conn.rollback()
            return False
            
    def get_daily_stats(self) -> Dict:
        """Get today's trading statistics"""
        if not self.conn:
            return {}
            
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                    SELECT 
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_trades,
                        COUNT(CASE WHEN status = 'open' THEN 1 END) as open_trades,
                        SUM(CASE WHEN status = 'closed' THEN realized_pnl ELSE 0 END) as realized_pnl,
                        COUNT(CASE WHEN status = 'closed' AND realized_pnl > 0 THEN 1 END) as winning_trades,
                        COUNT(CASE WHEN status = 'closed' AND realized_pnl <= 0 THEN 1 END) as losing_trades
                    FROM trading.trades
                    WHERE DATE(entry_time) = CURRENT_DATE
                """
                cursor.execute(query)
                stats = cursor.fetchone()
                
                return {
                    'total_trades': stats['total_trades'],
                    'closed_trades': stats['closed_trades'],
                    'open_trades': stats['open_trades'],
                    'realized_pnl': float(stats['realized_pnl']) if stats['realized_pnl'] else 0,
                    'win_rate': (stats['winning_trades'] / stats['closed_trades'] * 100) if stats['closed_trades'] > 0 else 0,
                    'winning_trades': stats['winning_trades'],
                    'losing_trades': stats['losing_trades']
                }
                
        except Exception as e:
            self.logger.error(f"Error getting daily stats: {e}")
            return {}
            
    def get_account_balance(self, starting_capital: float = 100000) -> Dict:
        """Get current account balance based on starting capital and all trades"""
        if not self.conn:
            return {'balance': starting_capital, 'total_pnl': 0}
            
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Calculate total P&L from all closed trades
                query = """
                    SELECT 
                        COALESCE(SUM(realized_pnl), 0) as total_realized_pnl,
                        COALESCE(SUM(CASE WHEN exit_time >= CURRENT_DATE THEN realized_pnl ELSE 0 END), 0) as today_pnl,
                        COUNT(CASE WHEN status = 'closed' THEN 1 END) as total_closed_trades
                    FROM trading.trades
                    WHERE status = 'closed'
                """
                cursor.execute(query)
                result = cursor.fetchone()
                
                total_pnl = float(result['total_realized_pnl']) if result['total_realized_pnl'] else 0
                today_pnl = float(result['today_pnl']) if result['today_pnl'] else 0
                current_balance = starting_capital + total_pnl
                
                return {
                    'starting_capital': starting_capital,
                    'current_balance': current_balance,
                    'total_pnl': total_pnl,
                    'today_pnl': today_pnl,
                    'total_closed_trades': result['total_closed_trades']
                }
                
        except Exception as e:
            self.logger.error(f"Error getting account balance: {e}")
            return {'balance': starting_capital, 'total_pnl': 0}
    
    def get_recent_exercises(self, days: int = 7) -> List[Dict]:
        """Get recent option exercises from backend.data.database
        
        Returns all pending exercises regardless of date, plus completed
        exercises from the last N days.
        
        Args:
            days: Number of days to look back for completed exercises
            
        Returns:
            List of exercise records with details
        """
        if not self.conn:
            return []
            
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Query for pending exercises and recent completed ones
                cursor.execute("""
                    SELECT 
                        exercise_id,
                        exercise_date,
                        option_symbol,
                        strike_price,
                        option_type,
                        contracts,
                        shares_received,
                        disposal_status,
                        disposal_order_id,
                        disposal_price,
                        disposal_time,
                        detection_time,
                        notes
                    FROM portfolio.option_exercises
                    WHERE 
                        disposal_status IN ('PENDING', 'ORDER_PLACED')
                        OR (disposal_status = 'FILLED' 
                            AND exercise_date >= CURRENT_DATE - INTERVAL '%s days')
                    ORDER BY 
                        CASE 
                            WHEN disposal_status = 'PENDING' THEN 0
                            WHEN disposal_status = 'ORDER_PLACED' THEN 1
                            ELSE 2
                        END,
                        exercise_date DESC
                """, (days,))
                
                exercises = cursor.fetchall()
                
                # Convert to regular dicts and add calculated fields
                result = []
                for ex in exercises:
                    exercise = dict(ex)
                    
                    # Calculate balance impact (negative for cash outflow)
                    exercise['balance_impact'] = -(exercise['shares_received'] * float(exercise['strike_price']))
                    
                    # Calculate time since detection
                    if exercise['detection_time']:
                        time_since = datetime.now(pytz.UTC) - exercise['detection_time'].replace(tzinfo=pytz.UTC)
                        hours_since = time_since.total_seconds() / 3600
                        exercise['hours_since_detection'] = round(hours_since, 1)
                    else:
                        exercise['hours_since_detection'] = None
                        
                    # Add display-friendly fields
                    exercise['display_symbol'] = f"{exercise['strike_price']} {exercise['option_type']}"
                    
                    result.append(exercise)
                    
                return result
                
        except Exception as e:
            self.logger.error(f"Error fetching exercises: {e}")
            return []


# Async wrapper for integration with terminal UI
class AsyncDatabasePositionTracker:
    """Async wrapper for database position tracker"""
    
    def __init__(self):
        self.sync_tracker = DatabasePositionTracker()
        self.update_interval = 5  # seconds
        self._update_task = None
        
    async def start(self) -> bool:
        """Start position tracking"""
        connected = await asyncio.get_event_loop().run_in_executor(
            None, self.sync_tracker.connect
        )
        
        if connected:
            self._update_task = asyncio.create_task(self._update_loop())
            
        return connected
        
    async def stop(self):
        """Stop position tracking"""
        if self._update_task:
            self._update_task.cancel()
            
        await asyncio.get_event_loop().run_in_executor(
            None, self.sync_tracker.disconnect
        )
        
    async def _update_loop(self):
        """Periodic position update loop"""
        while True:
            try:
                await asyncio.sleep(self.update_interval)
                # Positions will be fetched on-demand
            except asyncio.CancelledError:
                break
                
    async def get_position_summary(self, options_chain: List[Dict]) -> Dict:
        """Get position summary asynchronously"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.sync_tracker.get_position_summary, options_chain
        )
        
    async def record_trade(self, trade_details: Dict) -> bool:
        """Record new trade asynchronously"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.sync_tracker.record_new_trade, trade_details
        )
        
    async def close_position(self, trade_id: str, exit_price: float, exit_reason: str = 'manual') -> bool:
        """Close position asynchronously"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.sync_tracker.close_position, trade_id, exit_price, exit_reason
        )
        
    async def get_daily_stats(self) -> Dict:
        """Get daily stats asynchronously"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.sync_tracker.get_daily_stats
        )