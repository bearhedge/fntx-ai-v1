#!/usr/bin/env python3
"""
Real-time ALM Data Service
Extends existing ALM track record with current day real-time data from IB Gateway
"""
import sys
import logging
from datetime import datetime, date
from typing import Dict, Optional, List
from decimal import Decimal

sys.path.append('/home/info/fntx-ai-v1/backend')
from trading.options_trader import OptionsTrader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealTimeALMService:
    """Service to get real-time ALM data from IB Gateway"""
    
    def __init__(self):
        self.trader = OptionsTrader(host='127.0.0.1', port=4002)
        
    def get_current_nav(self) -> Optional[Dict]:
        """Get current NAV and account values from IB Gateway"""
        try:
            # Connect to IB Gateway
            if not self.trader.connect():
                logger.error("Failed to connect to IB Gateway")
                return None
                
            logger.info("Connected to IB Gateway for real-time data")
            
            # Get account values
            account_values = self.trader.ib.accountValues()
            
            # Extract key values
            nav_data = {}
            for av in account_values:
                if av.tag == 'NetLiquidation':
                    nav_data['current_nav_usd'] = float(av.value)
                elif av.tag == 'TotalCashValue':
                    nav_data['cash_balance_usd'] = float(av.value)
                elif av.tag == 'BuyingPower':
                    nav_data['buying_power_usd'] = float(av.value)
                    
            # Get current positions
            positions = self.trader.get_positions()
            nav_data['positions'] = positions
            nav_data['position_count'] = len(positions)
            
            # Convert USD to HKD (approximate rate 7.8)
            usd_to_hkd = 7.8
            nav_data['current_nav_hkd'] = nav_data.get('current_nav_usd', 0) * usd_to_hkd
            nav_data['cash_balance_hkd'] = nav_data.get('cash_balance_usd', 0) * usd_to_hkd
            
            logger.info(f"Current NAV: ${nav_data.get('current_nav_usd', 0):,.2f} USD / {nav_data.get('current_nav_hkd', 0):,.2f} HKD")
            
            return nav_data
            
        except Exception as e:
            logger.error(f"Error getting current NAV: {e}")
            return None
        finally:
            if self.trader.ib and self.trader.ib.isConnected():
                self.trader.disconnect()
                
    def get_todays_trades(self) -> List[Dict]:
        """Get today's trades from IB Gateway"""
        try:
            if not self.trader.connect():
                return []
                
            # Get today's fills/executions
            today = datetime.now().strftime('%Y%m%d')
            
            # Get filled trades (which include contract details)
            filled_trades = self.trader.ib.fills()
            
            todays_trades = []
            for fill in filled_trades:
                if fill.execution.time:
                    exec_date = fill.execution.time.strftime('%Y%m%d')
                    if exec_date == today:
                        contract = fill.contract
                        execution = fill.execution
                        commission_report = fill.commissionReport
                        
                        trade_data = {
                            'symbol': contract.symbol,
                            'strike': getattr(contract, 'strike', None),
                            'right': getattr(contract, 'right', None),
                            'expiry': getattr(contract, 'lastTradeDateOrContractMonth', None),
                            'quantity': execution.shares,
                            'price': execution.price,
                            'time': execution.time,
                            'side': execution.side,
                            'commission': commission_report.commission if commission_report else 0,
                            'exec_id': execution.execId,
                            'exchange': execution.exchange
                        }
                        todays_trades.append(trade_data)
                        
            return todays_trades
            
        except Exception as e:
            logger.error(f"Error getting today's trades: {e}")
            return []
        finally:
            if self.trader.ib and self.trader.ib.isConnected():
                self.trader.disconnect()
                
    def generate_current_day_alm_entry(self, last_closing_nav: float) -> Dict:
        """Generate current day ALM entry in same format as historical data"""
        try:
            # Get real-time data
            nav_data = self.get_current_nav()
            if not nav_data:
                logger.error("Could not get current NAV data")
                return {}
                
            todays_trades = self.get_todays_trades()
            
            # Calculate P&L (simplified - would need more complex logic for actual P&L)
            current_nav_hkd = nav_data.get('current_nav_hkd', 0)
            gross_pnl = current_nav_hkd - last_closing_nav
            
            # Estimate commissions from trades (roughly)
            total_commissions = sum(trade.get('commission', 0) for trade in todays_trades) * 7.8  # Convert to HKD
            
            net_pnl = gross_pnl - total_commissions
            net_pnl_percent = (net_pnl / last_closing_nav * 100) if last_closing_nav > 0 else 0
            
            # Format current day entry
            current_day_entry = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'opening_nav': last_closing_nav,
                'net_cashflow': 0.0,  # Would need to detect deposits/withdrawals
                'gross_pnl': gross_pnl,
                'commissions': total_commissions,
                'net_pnl_percent': net_pnl_percent,
                'closing_nav': current_nav_hkd,
                'plug': 0.0,
                'assignment': False,  # Would need to detect assignments
                'trades': todays_trades,
                'is_realtime': True  # Flag to indicate this is real-time data
            }
            
            logger.info(f"Generated current day ALM entry: NAV {current_nav_hkd:,.2f} HKD, P&L: {gross_pnl:+.2f} HKD")
            
            return current_day_entry
            
        except Exception as e:
            logger.error(f"Error generating current day ALM entry: {e}")
            return {}

def test_realtime_alm():
    """Test the real-time ALM service"""
    service = RealTimeALMService()
    
    # Test getting current NAV
    print("Testing current NAV fetch...")
    nav_data = service.get_current_nav()
    if nav_data:
        print(f"✅ Current NAV: {nav_data.get('current_nav_hkd', 0):,.2f} HKD")
        print(f"✅ Positions: {nav_data.get('position_count', 0)}")
    else:
        print("❌ Failed to get current NAV")
        
    # Test getting today's trades
    print("\nTesting today's trades...")
    trades = service.get_todays_trades()
    print(f"✅ Found {len(trades)} trades today")
    for trade in trades:
        print(f"  - {trade['side']} {trade['quantity']} {trade['symbol']} @ ${trade['price']}")
        
    # Test generating current day entry
    print("\nTesting current day ALM entry generation...")
    last_closing_nav = 79299.20  # From July 25th
    current_entry = service.generate_current_day_alm_entry(last_closing_nav)
    if current_entry:
        print(f"✅ Current day entry generated:")
        print(f"  Date: {current_entry['date']}")
        print(f"  Opening NAV: {current_entry['opening_nav']:,.2f} HKD")
        print(f"  Current NAV: {current_entry['closing_nav']:,.2f} HKD")
        print(f"  P&L: {current_entry['gross_pnl']:+.2f} HKD ({current_entry['net_pnl_percent']:+.2f}%)")
    else:
        print("❌ Failed to generate current day entry")

if __name__ == "__main__":
    test_realtime_alm()