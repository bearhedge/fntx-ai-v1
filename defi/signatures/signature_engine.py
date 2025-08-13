"""
Signature Engine - Core component for generating daily trading signatures

Handles the complete process of collecting data, verification, and blockchain submission.
"""

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import asyncio

from ..core import FNTXBlockchain
from .merkle_tree import MerkleTree
from .data_verifier import DataVerifier


@dataclass
class DailyTradingSignature:
    """Complete daily trading signature with all fields"""
    
    # Core Metrics
    date: str  # YYYYMMDD
    timestamp: int  # Unix timestamp
    trading_day_num: int
    
    # Account State
    opening_balance: Decimal
    closing_balance: Decimal
    deposits: Decimal
    withdrawals: Decimal
    
    # P&L Metrics
    gross_pnl: Decimal
    commissions: Decimal
    interest_expense: Decimal
    interest_accruals: Decimal  # Earning on cash
    net_pnl: Decimal
    net_pnl_percentage: float
    annualized_pnl_percentage: float
    
    # Trading Activity
    position_size_percentage: float
    contracts_traded: int
    notional_volume: Decimal
    implied_turnover: Decimal
    
    # Greeks & Risk
    delta_exposure: Decimal
    gamma_exposure: Decimal
    theta_decay: Decimal
    vega_exposure: Decimal
    implied_volatility_avg: float
    
    # Performance Metrics (Multiple timeframes)
    win_rate_30d: float
    win_rate_mtd: float
    win_rate_ytd: float
    win_rate_all_time: float
    
    volatility_30d: float
    volatility_mtd: float
    volatility_ytd: float
    volatility_all_time: float
    
    sharpe_ratio_30d: float
    sharpe_ratio_mtd: float
    sharpe_ratio_ytd: float
    sharpe_ratio_all_time: float
    
    max_drawdown_30d: float
    max_drawdown_mtd: float
    max_drawdown_ytd: float
    max_drawdown_all_time: float
    
    # Fund Metrics
    dpi: float  # Distributions to Paid-In
    tvpi: float  # Total Value to Paid-In
    rvpi: float  # Residual Value to Paid-In
    
    # Verification
    merkle_root: str
    calculation_hash: str
    data_source_hash: str  # Hash of raw input data


class SignatureEngine:
    """Main engine for generating and managing trading signatures"""
    
    def __init__(self, blockchain: FNTXBlockchain, verifier: DataVerifier):
        self.blockchain = blockchain
        self.verifier = verifier
        self.signatures: Dict[str, DailyTradingSignature] = {}
        
    async def generate_daily_signature(self, 
                                     date: datetime,
                                     trading_data: Dict,
                                     market_data: Dict,
                                     account_data: Dict) -> Tuple[DailyTradingSignature, str]:
        """
        Generate a complete daily trading signature
        
        Returns:
            Tuple of (signature, transaction_hash)
        """
        
        # Step 1: Verify input data integrity
        verification_result = await self.verifier.verify_data_integrity(
            trading_data, market_data, account_data
        )
        if not verification_result.is_valid:
            raise ValueError(f"Data verification failed: {verification_result.errors}")
        
        # Step 2: Calculate all metrics
        metrics = await self._calculate_all_metrics(
            date, trading_data, market_data, account_data
        )
        
        # Step 3: Build Merkle tree
        merkle_tree = self._build_merkle_tree(metrics)
        
        # Step 4: Generate hashes
        calculation_hash = self._hash_calculations(metrics)
        data_source_hash = self._hash_input_data(trading_data, market_data, account_data)
        
        # Step 5: Create signature
        signature = DailyTradingSignature(
            date=date.strftime('%Y%m%d'),
            timestamp=int(date.timestamp()),
            merkle_root=merkle_tree.root,
            calculation_hash=calculation_hash,
            data_source_hash=data_source_hash,
            **metrics
        )
        
        # Step 6: Submit to blockchain
        tx_hash = await self._submit_to_blockchain(signature)
        
        # Step 7: Store locally
        self.signatures[signature.date] = signature
        
        return signature, tx_hash
    
    async def _calculate_all_metrics(self, 
                                   date: datetime,
                                   trading_data: Dict,
                                   market_data: Dict,
                                   account_data: Dict) -> Dict:
        """Calculate all required metrics for the signature"""
        
        # Extract basic data
        metrics = {
            'trading_day_num': trading_data.get('trading_day_num', 1),
            
            # Account state
            'opening_balance': Decimal(str(account_data['opening_balance'])),
            'closing_balance': Decimal(str(account_data['closing_balance'])),
            'deposits': Decimal(str(account_data.get('deposits', 0))),
            'withdrawals': Decimal(str(account_data.get('withdrawals', 0))),
            
            # P&L breakdown
            'gross_pnl': Decimal(str(trading_data['gross_pnl'])),
            'commissions': Decimal(str(trading_data['commissions'])),
            'interest_expense': Decimal(str(trading_data.get('interest_expense', 0))),
            'interest_accruals': Decimal(str(trading_data.get('interest_accruals', 0))),
        }
        
        # Calculate net P&L
        metrics['net_pnl'] = (
            metrics['gross_pnl'] + 
            metrics['commissions'] + 
            metrics['interest_expense'] + 
            metrics['interest_accruals']
        )
        
        # Calculate percentages
        if metrics['opening_balance'] > 0:
            metrics['net_pnl_percentage'] = float(
                (metrics['net_pnl'] / metrics['opening_balance']) * 100
            )
            metrics['annualized_pnl_percentage'] = metrics['net_pnl_percentage'] * 252
        else:
            metrics['net_pnl_percentage'] = 0.0
            metrics['annualized_pnl_percentage'] = 0.0
        
        # Trading activity
        contracts = trading_data.get('contracts_traded', 0)
        spy_price = Decimal(str(market_data.get('spy_price', 450)))
        
        metrics['contracts_traded'] = contracts
        metrics['notional_volume'] = Decimal(str(trading_data.get('notional_volume', 0)))
        metrics['implied_turnover'] = contracts * 100 * spy_price
        
        if metrics['opening_balance'] > 0:
            metrics['position_size_percentage'] = float(
                (metrics['implied_turnover'] / metrics['opening_balance']) * 100
            )
        else:
            metrics['position_size_percentage'] = 0.0
        
        # Greeks
        metrics['delta_exposure'] = Decimal(str(trading_data.get('delta_exposure', 0)))
        metrics['gamma_exposure'] = Decimal(str(trading_data.get('gamma_exposure', 0)))
        metrics['theta_decay'] = Decimal(str(trading_data.get('theta_decay', 0)))
        metrics['vega_exposure'] = Decimal(str(trading_data.get('vega_exposure', 0)))
        metrics['implied_volatility_avg'] = float(trading_data.get('implied_volatility_avg', 0))
        
        # Performance metrics for all timeframes
        for timeframe in ['30d', 'mtd', 'ytd', 'all_time']:
            metrics[f'win_rate_{timeframe}'] = float(
                trading_data.get(f'win_rate_{timeframe}', 0)
            )
            metrics[f'volatility_{timeframe}'] = float(
                trading_data.get(f'volatility_{timeframe}', 0)
            )
            metrics[f'sharpe_ratio_{timeframe}'] = float(
                trading_data.get(f'sharpe_ratio_{timeframe}', 0)
            )
            metrics[f'max_drawdown_{timeframe}'] = float(
                trading_data.get(f'max_drawdown_{timeframe}', 0)
            )
        
        # Fund metrics
        initial_capital = Decimal(str(account_data.get('initial_capital', 200000)))
        total_distributions = Decimal(str(account_data.get('total_distributions', 0)))
        
        if initial_capital > 0:
            metrics['dpi'] = float(total_distributions / initial_capital)
            metrics['tvpi'] = float(metrics['closing_balance'] / initial_capital)
            metrics['rvpi'] = float(metrics['closing_balance'] / initial_capital)
        else:
            metrics['dpi'] = 0.0
            metrics['tvpi'] = 1.0
            metrics['rvpi'] = 1.0
        
        return metrics
    
    def _build_merkle_tree(self, metrics: Dict) -> MerkleTree:
        """Build Merkle tree from metrics"""
        
        # Convert all metrics to strings for hashing
        leaves = []
        for key, value in sorted(metrics.items()):
            if isinstance(value, Decimal):
                value = str(value)
            leaf = f"{key}:{value}"
            leaves.append(leaf)
        
        merkle_tree = MerkleTree(leaves)
        return merkle_tree
    
    def _hash_calculations(self, metrics: Dict) -> str:
        """Generate hash of all calculations"""
        
        # Sort metrics for consistent hashing
        sorted_metrics = json.dumps(metrics, sort_keys=True, default=str)
        return hashlib.sha256(sorted_metrics.encode()).hexdigest()
    
    def _hash_input_data(self, trading_data: Dict, market_data: Dict, account_data: Dict) -> str:
        """Generate hash of input data"""
        
        combined_data = {
            'trading': trading_data,
            'market': market_data,
            'account': account_data
        }
        
        sorted_data = json.dumps(combined_data, sort_keys=True, default=str)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    async def _submit_to_blockchain(self, signature: DailyTradingSignature) -> str:
        """Submit signature to blockchain"""
        
        # Convert signature to blockchain format
        blockchain_data = self._convert_to_blockchain_format(signature)
        
        # Submit transaction
        tx_hash = await self.blockchain.post_daily_record(
            blockchain_data,
            private_key=self.blockchain.account.key
        )
        
        return tx_hash
    
    def _convert_to_blockchain_format(self, signature: DailyTradingSignature) -> Dict:
        """Convert signature to format expected by smart contract"""
        
        # This matches the 36-field structure we defined
        return {
            'date': signature.date,
            'trading_day_num': signature.trading_day_num,
            'timestamp': str(signature.timestamp),
            
            # Account state
            'balance_start': float(signature.opening_balance),
            'balance_end': float(signature.closing_balance),
            'deposits': float(signature.deposits),
            'withdrawals': float(signature.withdrawals),
            
            # P&L
            'gross_pnl': float(signature.gross_pnl),
            'commissions': float(signature.commissions),
            'interest_expense': float(signature.interest_expense),
            'other_fees': float(signature.interest_accruals),  # Using for other fees
            'net_pnl': float(signature.net_pnl),
            
            # Performance (using 30d for smart contract)
            'net_return_pct': signature.net_pnl_percentage,
            'return_annualized': signature.annualized_pnl_percentage,
            'sharpe_30d': signature.sharpe_ratio_30d,
            'sortino_30d': signature.sharpe_ratio_30d * 1.2,  # Approximation
            'volatility_30d': signature.volatility_30d,
            'max_drawdown_30d': signature.max_drawdown_30d,
            
            # Trading
            'contracts_total': signature.contracts_traded,
            'put_contracts': signature.contracts_traded,  # Assuming all puts for now
            'call_contracts': 0,
            'premium_collected': float(signature.gross_pnl),  # Approximation
            'margin_used': float(signature.implied_turnover * Decimal('0.02')),  # 2% margin
            'position_size_pct': signature.position_size_percentage,
            'implied_turnover': float(signature.implied_turnover),
            
            # Greeks
            'delta_exposure': float(signature.delta_exposure),
            'gamma_exposure': float(signature.gamma_exposure),
            'theta_income': float(signature.theta_decay),
            'vega_exposure': float(signature.vega_exposure),
            
            # Win/Loss
            'positions_expired': 0,  # Need to track this
            'positions_assigned': 0,
            'positions_stopped': 0,
            'win_rate': signature.win_rate_30d,
            
            # Fund metrics
            'dpi': signature.dpi,
            'tvpi': signature.tvpi,
            'rvpi': signature.rvpi
        }
    
    async def get_signature(self, date: str) -> Optional[DailyTradingSignature]:
        """Retrieve a signature by date"""
        return self.signatures.get(date)
    
    async def get_signature_range(self, start_date: str, end_date: str) -> List[DailyTradingSignature]:
        """Get signatures for a date range"""
        
        signatures = []
        for date_str, signature in self.signatures.items():
            if start_date <= date_str <= end_date:
                signatures.append(signature)
        
        return sorted(signatures, key=lambda s: s.date)