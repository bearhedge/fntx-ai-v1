"""
Data Adapter for FNTX Track Record

Bridges between calculation engine output and blockchain 36-field format.
No modifications to calculation engine required.
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional
import numpy as np

class TrackRecordDataAdapter:
    """Adapts calculation engine output to blockchain format"""
    
    def __init__(self):
        self.trading_day_counter = self._load_day_counter()
        self.historical_data = []  # For 30-day calculations
        
    def _load_day_counter(self) -> int:
        """Load the current trading day number from file"""
        try:
            with open('.fntx/trading_day_counter.json', 'r') as f:
                data = json.load(f)
                return data.get('day_number', 0)
        except:
            return 0
    
    def _save_day_counter(self):
        """Save the updated trading day counter"""
        import os
        os.makedirs('.fntx', exist_ok=True)
        with open('.fntx/trading_day_counter.json', 'w') as f:
            json.dump({'day_number': self.trading_day_counter}, f)
    
    def adapt_calculation_engine_output(self, 
                                      calc_engine_data: Dict,
                                      market_data: Dict,
                                      account_data: Dict) -> Dict:
        """
        Transform calculation engine output to 36-field blockchain format
        
        Args:
            calc_engine_data: Output from calculation engine
            market_data: Current market data (SPY price, etc.)
            account_data: Account balance information
            
        Returns:
            Dictionary with all 36 fields ready for blockchain
        """
        
        # Increment trading day counter
        self.trading_day_counter += 1
        self._save_day_counter()
        
        # Get current timestamp
        now = datetime.now()
        
        # Calculate implied turnover
        contracts = calc_engine_data.get('total_contracts', 0)
        spy_price = market_data.get('spy_price', 450)  # Default to 450 if not provided
        implied_turnover = contracts * 100 * spy_price
        
        # Extract P&L components
        gross_pnl = calc_engine_data.get('gross_pnl', 0)
        commissions = calc_engine_data.get('commissions', 0)
        interest = calc_engine_data.get('interest_expense', 0)
        other_fees = calc_engine_data.get('other_fees', 0)
        net_pnl = gross_pnl + commissions + interest + other_fees
        
        # Calculate return percentage
        balance_start = account_data.get('balance_start', 200000)
        net_return_pct = (net_pnl / balance_start) * 100 if balance_start > 0 else 0
        
        # Annualized return (simple approximation)
        return_annualized = net_return_pct * 252  # Trading days per year
        
        # Win/Loss tracking
        expired = calc_engine_data.get('positions_expired', 0)
        assigned = calc_engine_data.get('positions_assigned', 0)
        stopped = calc_engine_data.get('positions_stopped', 0)
        total_positions = expired + assigned + stopped
        win_rate = (expired / total_positions * 100) if total_positions > 0 else 0
        
        # Fund metrics calculation
        initial_capital = account_data.get('initial_capital', 200000)
        current_value = account_data.get('balance_end', balance_start + net_pnl)
        distributions = account_data.get('total_distributions', 0)
        
        dpi = (distributions / initial_capital) if initial_capital > 0 else 0
        tvpi = (current_value / initial_capital) if initial_capital > 0 else 1
        rvpi = tvpi  # For individual trader, RVPI = TVPI
        
        # Build the record
        record = {
            # Box 1: Identity & Time
            'date': now.strftime('%Y%m%d'),
            'trading_day_num': self.trading_day_counter,
            'timestamp': now.strftime('%H:%M:%S'),
            
            # Box 2: Account State
            'balance_start': balance_start,
            'balance_end': account_data.get('balance_end', balance_start + net_pnl),
            'deposits': account_data.get('deposits', 0),
            'withdrawals': account_data.get('withdrawals', 0),
            
            # Box 3: P&L Breakdown
            'gross_pnl': gross_pnl,
            'commissions': commissions,
            'interest_expense': interest,
            'other_fees': other_fees,
            'net_pnl': net_pnl,
            
            # Box 4: Performance Metrics
            'net_return_pct': net_return_pct,
            'return_annualized': return_annualized,
            'sharpe_30d': self._calculate_sharpe_30d(),
            'sortino_30d': self._calculate_sortino_30d(),
            'volatility_30d': self._calculate_volatility_30d(),
            'max_drawdown_30d': self._calculate_max_drawdown_30d(),
            
            # Box 5: Trading Activity
            'contracts_total': contracts,
            'put_contracts': calc_engine_data.get('put_contracts', contracts),
            'call_contracts': calc_engine_data.get('call_contracts', 0),
            'premium_collected': calc_engine_data.get('premium_collected', 0),
            'margin_used': calc_engine_data.get('margin_used', 0),
            'position_size_pct': (contracts * 100 * spy_price / balance_start) if balance_start > 0 else 0,
            'implied_turnover': implied_turnover,
            
            # Box 6: Greeks
            'delta_exposure': calc_engine_data.get('portfolio_delta', 0),
            'gamma_exposure': calc_engine_data.get('portfolio_gamma', 0),
            'theta_income': calc_engine_data.get('theta_income', 0),
            'vega_exposure': calc_engine_data.get('portfolio_vega', 0),
            
            # Box 7: Win/Loss Tracking
            'positions_expired': expired,
            'positions_assigned': assigned,
            'positions_stopped': stopped,
            'win_rate': win_rate,
            
            # Box 8: Fund Metrics
            'dpi': dpi,
            'tvpi': tvpi,
            'rvpi': rvpi
        }
        
        # Store for 30-day calculations
        self._update_historical_data(record)
        
        return record
    
    def _update_historical_data(self, record: Dict):
        """Store record for rolling calculations"""
        self.historical_data.append({
            'date': record['date'],
            'net_return_pct': record['net_return_pct'],
            'balance_end': record['balance_end']
        })
        
        # Keep only last 30 records
        if len(self.historical_data) > 30:
            self.historical_data.pop(0)
    
    def _calculate_sharpe_30d(self) -> float:
        """Calculate 30-day rolling Sharpe ratio"""
        if len(self.historical_data) < 2:
            return 0.0
        
        returns = [d['net_return_pct'] for d in self.historical_data]
        if len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualized Sharpe
        sharpe = (mean_return / std_return) * np.sqrt(252)
        return round(sharpe, 2)
    
    def _calculate_sortino_30d(self) -> float:
        """Calculate 30-day rolling Sortino ratio"""
        if len(self.historical_data) < 2:
            return 0.0
        
        returns = [d['net_return_pct'] for d in self.historical_data]
        negative_returns = [r for r in returns if r < 0]
        
        if not negative_returns:
            return 3.0  # Max if no negative returns
        
        mean_return = np.mean(returns)
        downside_std = np.std(negative_returns)
        
        if downside_std == 0:
            return 3.0
        
        # Annualized Sortino
        sortino = (mean_return / downside_std) * np.sqrt(252)
        return round(sortino, 2)
    
    def _calculate_volatility_30d(self) -> float:
        """Calculate 30-day rolling volatility"""
        if len(self.historical_data) < 2:
            return 0.0
        
        returns = [d['net_return_pct'] for d in self.historical_data]
        
        # Annualized volatility
        daily_vol = np.std(returns)
        annual_vol = daily_vol * np.sqrt(252)
        
        return round(annual_vol, 2)
    
    def _calculate_max_drawdown_30d(self) -> float:
        """Calculate 30-day maximum drawdown"""
        if len(self.historical_data) < 2:
            return 0.0
        
        balances = [d['balance_end'] for d in self.historical_data]
        
        # Calculate running maximum
        running_max = balances[0]
        max_drawdown = 0
        
        for balance in balances[1:]:
            running_max = max(running_max, balance)
            drawdown = (balance - running_max) / running_max * 100
            max_drawdown = min(max_drawdown, drawdown)
        
        return round(max_drawdown, 2)


# Example usage
if __name__ == "__main__":
    adapter = TrackRecordDataAdapter()
    
    # Mock data from calculation engine
    calc_engine_output = {
        'total_contracts': 5,
        'gross_pnl': 1250,
        'commissions': -65,
        'interest_expense': -12,
        'other_fees': -125,
        'premium_collected': 5250,
        'margin_used': 45000,
        'portfolio_delta': -0.12,
        'portfolio_gamma': -0.008,
        'theta_income': 850,
        'portfolio_vega': -120,
        'positions_expired': 5,
        'positions_assigned': 0,
        'positions_stopped': 0
    }
    
    market_data = {
        'spy_price': 450
    }
    
    account_data = {
        'balance_start': 200000,
        'balance_end': 201048,
        'deposits': 0,
        'withdrawals': 0,
        'initial_capital': 200000,
        'total_distributions': 0
    }
    
    # Convert to blockchain format
    blockchain_record = adapter.adapt_calculation_engine_output(
        calc_engine_output,
        market_data,
        account_data
    )
    
    print(json.dumps(blockchain_record, indent=2))