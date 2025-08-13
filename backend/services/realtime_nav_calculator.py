#!/usr/bin/env python3
"""
Real-time NAV Calculator Service
Calculates current day NAV from real-time positions and market data
"""

import logging
import psycopg2
from datetime import datetime, date, timezone, time as dt_time
from decimal import Decimal, getcontext
from typing import Dict, List, Optional, Tuple
import asyncio
import json
from dataclasses import dataclass

from ib_insync import IB, Stock, Option, util as ib_util

# Set precision for calculations
getcontext().prec = 18

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NAVComponents:
    """NAV calculation components"""
    cash_balance: Decimal = Decimal('0')
    position_value: Decimal = Decimal('0')
    unrealized_pnl: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')
    commissions: Decimal = Decimal('0')
    total_nav: Decimal = Decimal('0')
    opening_nav: Decimal = Decimal('0')
    net_pnl: Decimal = Decimal('0')
    calculation_timestamp: datetime = None

class RealtimeNAVCalculator:
    """
    Service for calculating real-time NAV from IB Gateway data
    """
    
    def __init__(self, config=None):
        self.config = config or {
            'ib_host': '127.0.0.1',
            'ib_port': 4002,
            'client_id': 101,
            'db_host': 'localhost',
            'db_name': 'options_data',
            'db_user': 'postgres',
            'db_password': 'theta_data_2024',
            'calculation_interval': 60,  # seconds
            'hkd_usd_rate': Decimal('7.8')
        }
        self.ib = None
        self.db_conn = None
        self.is_running = False
        self.last_nav_components = None
        
    def connect_services(self) -> bool:
        """Connect to IB Gateway and database"""
        try:
            # Connect to database
            self.db_conn = psycopg2.connect(
                host=self.config['db_host'],
                database=self.config['db_name'],
                user=self.config['db_user'],
                password=self.config['db_password']
            )
            self.db_conn.autocommit = True
            logger.info("Connected to database")
            
            # Connect to IB Gateway
            self.ib = IB()
            self.ib.connect(
                host=self.config['ib_host'],
                port=self.config['ib_port'],
                clientId=self.config['client_id'],
                timeout=20
            )
            
            if self.ib.isConnected():
                logger.info("Connected to IB Gateway")
                return True
            else:
                logger.error("Failed to connect to IB Gateway")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to services: {e}")
            return False
    
    def get_opening_nav(self, target_date: date) -> Decimal:
        """Get opening NAV for the specified date"""
        try:
            with self.db_conn.cursor() as cursor:
                # First try to get from historical data (previous day's closing NAV)
                cursor.execute("""
                    SELECT closing_nav_hkd 
                    FROM alm_reporting.daily_summary 
                    WHERE summary_date < %s 
                    ORDER BY summary_date DESC 
                    LIMIT 1
                """, (target_date,))
                
                result = cursor.fetchone()
                if result:
                    return Decimal(str(result[0]))
                
                # Fallback: get from real-time data if available
                cursor.execute("""
                    SELECT opening_nav_hkd 
                    FROM alm_realtime.daily_summary 
                    WHERE summary_date = %s
                """, (target_date,))
                
                result = cursor.fetchone()
                if result:
                    return Decimal(str(result[0]))
                
                logger.warning(f"No opening NAV found for {target_date}")
                return Decimal('0')
                
        except Exception as e:
            logger.error(f"Error getting opening NAV: {e}")
            return Decimal('0')
    
    def get_current_positions(self) -> List[Dict]:
        """Get current positions from IB Gateway"""
        try:
            positions = []
            ib_positions = self.ib.positions()
            
            for position in ib_positions:
                if position.position == 0:
                    continue
                
                contract = position.contract
                
                # Determine instrument type
                instrument_type = 'STOCK'
                strike_price = None
                option_type = None
                expiry_date = None
                
                if hasattr(contract, 'strike') and contract.strike:
                    instrument_type = 'OPTION'
                    strike_price = Decimal(str(contract.strike))
                    option_type = contract.right
                    expiry_date = datetime.strptime(contract.lastTradeDateOrContractMonth, '%Y%m%d').date()
                
                # Get market price
                market_price = Decimal('0')
                if position.marketPrice:
                    market_price = Decimal(str(position.marketPrice))
                    if contract.currency == 'USD':
                        market_price *= self.config['hkd_usd_rate']
                
                # Calculate market value
                market_value = market_price * Decimal(str(abs(position.position)))
                if position.position < 0:  # Short position
                    market_value = -market_value
                
                # Calculate unrealized P&L
                unrealized_pnl = Decimal('0')
                if position.unrealizedPNL:
                    unrealized_pnl = Decimal(str(position.unrealizedPNL))
                    if contract.currency == 'USD':
                        unrealized_pnl *= self.config['hkd_usd_rate']
                
                positions.append({
                    'symbol': contract.symbol,
                    'instrument_type': instrument_type,
                    'strike_price': strike_price,
                    'option_type': option_type,
                    'expiry_date': expiry_date,
                    'quantity': position.position,
                    'market_price': market_price,
                    'market_value': market_value,
                    'avg_cost': Decimal(str(position.avgCost)) if position.avgCost else Decimal('0'),
                    'unrealized_pnl': unrealized_pnl
                })
            
            logger.info(f"Retrieved {len(positions)} positions from IB Gateway")
            return positions
            
        except Exception as e:
            logger.error(f"Error getting current positions: {e}")
            return []
    
    def get_account_values(self) -> Dict[str, Decimal]:
        """Get current account values from IB Gateway"""
        try:
            account_values = {}
            
            # Request account summary
            summary_tags = [
                'NetLiquidation', 'TotalCashValue', 'AccruedCash',
                'BuyingPower', 'GrossPositionValue', 'DayTradesRemaining'
            ]
            
            account_data = self.ib.accountSummary('All', summary_tags)
            
            for item in account_data:
                if item.currency in ['USD', 'BASE']:
                    value = Decimal(str(item.value))
                    if item.currency == 'USD':
                        value *= self.config['hkd_usd_rate']
                    account_values[item.tag] = value
            
            logger.debug(f"Retrieved account values: {list(account_values.keys())}")
            return account_values
            
        except Exception as e:
            logger.error(f"Error getting account values: {e}")
            return {}
    
    def get_todays_realized_pnl(self) -> Decimal:
        """Get today's realized P&L from trade executions"""
        try:
            today = date.today()
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COALESCE(SUM(realized_pnl_hkd), 0) as total_realized_pnl
                    FROM alm_realtime.trade_executions 
                    WHERE DATE(execution_timestamp) = %s
                """, (today,))
                
                result = cursor.fetchone()
                return Decimal(str(result[0])) if result else Decimal('0')
                
        except Exception as e:
            logger.error(f"Error getting today's realized P&L: {e}")
            return Decimal('0')
    
    def get_todays_commissions(self) -> Decimal:
        """Get today's commission costs"""
        try:
            today = date.today()
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COALESCE(SUM(commission_hkd), 0) as total_commissions
                    FROM alm_realtime.trade_executions 
                    WHERE DATE(execution_timestamp) = %s
                """, (today,))
                
                result = cursor.fetchone()
                return Decimal(str(result[0])) if result else Decimal('0')
                
        except Exception as e:
            logger.error(f"Error getting today's commissions: {e}")
            return Decimal('0')
    
    def calculate_nav_components(self) -> NAVComponents:
        """Calculate all NAV components"""
        try:
            nav_components = NAVComponents()
            nav_components.calculation_timestamp = datetime.now(timezone.utc)
            
            # Get opening NAV
            today = date.today()
            nav_components.opening_nav = self.get_opening_nav(today)
            
            # Get account values
            account_values = self.get_account_values()
            nav_components.cash_balance = account_values.get('TotalCashValue', Decimal('0'))
            
            # Get current positions and calculate position value
            positions = self.get_current_positions()
            nav_components.position_value = sum(pos['market_value'] for pos in positions)
            nav_components.unrealized_pnl = sum(pos['unrealized_pnl'] for pos in positions)
            
            # Get today's trading activity
            nav_components.realized_pnl = self.get_todays_realized_pnl()
            nav_components.commissions = self.get_todays_commissions()
            
            # Calculate total NAV
            nav_components.total_nav = (
                nav_components.cash_balance + 
                nav_components.position_value
            )
            
            # Calculate net P&L
            nav_components.net_pnl = (
                nav_components.realized_pnl + 
                nav_components.unrealized_pnl - 
                nav_components.commissions
            )
            
            logger.info(f"NAV calculated: Total={nav_components.total_nav}, "
                       f"Cash={nav_components.cash_balance}, "
                       f"Positions={nav_components.position_value}, "
                       f"Net P&L={nav_components.net_pnl}")
            
            return nav_components
            
        except Exception as e:
            logger.error(f"Error calculating NAV components: {e}")
            return NAVComponents()
    
    def store_nav_calculation(self, nav_components: NAVComponents):
        """Store NAV calculation in database"""
        try:
            today = date.today()
            
            with self.db_conn.cursor() as cursor:
                # Update or insert daily summary
                cursor.execute("""
                    INSERT INTO alm_realtime.daily_summary (
                        summary_date, current_nav_hkd, opening_nav_hkd,
                        total_pnl_hkd, realized_pnl_hkd, unrealized_pnl_hkd,
                        position_value_hkd, cash_balance_hkd, broker_fees_hkd,
                        data_source, calculation_version
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (summary_date) DO UPDATE SET
                        current_nav_hkd = EXCLUDED.current_nav_hkd,
                        total_pnl_hkd = EXCLUDED.total_pnl_hkd,
                        realized_pnl_hkd = EXCLUDED.realized_pnl_hkd,
                        unrealized_pnl_hkd = EXCLUDED.unrealized_pnl_hkd,
                        position_value_hkd = EXCLUDED.position_value_hkd,
                        cash_balance_hkd = EXCLUDED.cash_balance_hkd,
                        broker_fees_hkd = EXCLUDED.broker_fees_hkd,
                        calculation_version = EXCLUDED.calculation_version + 1,
                        last_updated = CURRENT_TIMESTAMP
                """, (
                    today,
                    nav_components.total_nav,
                    nav_components.opening_nav,
                    nav_components.net_pnl,
                    nav_components.realized_pnl,
                    nav_components.unrealized_pnl,
                    nav_components.position_value,
                    nav_components.cash_balance,
                    nav_components.commissions,
                    'IB_REALTIME',
                    1
                ))
                
                # Store portfolio metrics
                cursor.execute("""
                    INSERT INTO alm_realtime.portfolio_metrics (
                        as_of_timestamp, total_nav_hkd, cash_balance_hkd,
                        position_value_hkd, day_pnl_hkd, total_pnl_hkd,
                        calculation_version, data_source
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    nav_components.calculation_timestamp,
                    nav_components.total_nav,
                    nav_components.cash_balance,
                    nav_components.position_value,
                    nav_components.net_pnl,
                    nav_components.net_pnl,
                    1,
                    'IB_REALTIME'
                ))
            
            logger.info("NAV calculation stored successfully")
            
        except Exception as e:
            logger.error(f"Error storing NAV calculation: {e}")
    
    def validate_nav_calculation(self, nav_components: NAVComponents) -> bool:
        """Validate NAV calculation for reasonableness"""
        try:
            # Check for negative NAV (usually indicates error)
            if nav_components.total_nav < 0:
                logger.warning(f"Negative NAV detected: {nav_components.total_nav}")
                return False
            
            # Check for large changes from previous calculation
            if self.last_nav_components:
                nav_change = abs(nav_components.total_nav - self.last_nav_components.total_nav)
                nav_change_pct = nav_change / self.last_nav_components.total_nav if self.last_nav_components.total_nav > 0 else 0
                
                # Alert on large changes (>5%)
                if nav_change_pct > Decimal('0.05'):
                    logger.warning(f"Large NAV change detected: {nav_change_pct:.2%}")
                    # Still return True but log for investigation
            
            # Check for reasonable values
            if nav_components.total_nav > Decimal('10000000'):  # 10M HKD
                logger.warning(f"Unusually high NAV: {nav_components.total_nav}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating NAV calculation: {e}")
            return False
    
    def update_system_status(self, status: str, error_message: str = None):
        """Update system status"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO alm_realtime.system_status (
                        service_name, status, last_heartbeat, error_message,
                        connection_status
                    ) VALUES (
                        %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (service_name) DO UPDATE SET
                        status = EXCLUDED.status,
                        last_heartbeat = EXCLUDED.last_heartbeat,
                        error_message = EXCLUDED.error_message,
                        connection_status = EXCLUDED.connection_status,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    'realtime_nav_calculator',
                    status,
                    datetime.now(timezone.utc),
                    error_message,
                    'CONNECTED' if self.ib and self.ib.isConnected() else 'DISCONNECTED'
                ))
                
        except Exception as e:
            logger.error(f"Error updating system status: {e}")
    
    async def run_calculation_loop(self):
        """Main calculation loop"""
        while self.is_running:
            try:
                # Skip calculations outside trading hours if needed
                current_time = datetime.now().time()
                if current_time < dt_time(9, 30) or current_time > dt_time(16, 0):
                    # Still run but less frequently outside trading hours
                    await asyncio.sleep(self.config['calculation_interval'] * 2)
                    continue
                
                # Calculate NAV
                nav_components = self.calculate_nav_components()
                
                # Validate calculation
                if self.validate_nav_calculation(nav_components):
                    # Store calculation
                    self.store_nav_calculation(nav_components)
                    self.last_nav_components = nav_components
                    self.update_system_status('RUNNING')
                else:
                    logger.error("NAV calculation validation failed")
                    self.update_system_status('ERROR', 'NAV validation failed')
                
                # Wait for next calculation
                await asyncio.sleep(self.config['calculation_interval'])
                
            except Exception as e:
                logger.error(f"Error in calculation loop: {e}")
                self.update_system_status('ERROR', str(e))
                await asyncio.sleep(self.config['calculation_interval'])
    
    async def start(self):
        """Start the NAV calculation service"""
        logger.info("Starting Real-time NAV Calculator")
        
        if not self.connect_services():
            logger.error("Failed to connect to required services")
            return False
        
        self.is_running = True
        self.update_system_status('STARTING')
        
        # Run calculation loop
        await self.run_calculation_loop()
        
        return True
    
    def stop(self):
        """Stop the NAV calculation service"""
        logger.info("Stopping Real-time NAV Calculator")
        self.is_running = False
        
        if self.ib:
            self.ib.disconnect()
        
        if self.db_conn:
            self.db_conn.close()
        
        self.update_system_status('STOPPED')

def main():
    """Main entry point"""
    calculator = RealtimeNAVCalculator()
    
    try:
        asyncio.run(calculator.start())
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        calculator.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        calculator.stop()

if __name__ == "__main__":
    main()