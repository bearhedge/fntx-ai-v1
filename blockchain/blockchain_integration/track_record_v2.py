"""
TrackRecord V2 Integration - Full 36-field on-chain storage

Handles posting and retrieving comprehensive daily trading records.
"""

import os
import json
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from web3 import Web3

class TrackRecordV2:
    """Interface for TrackRecordV2 smart contract with 36-field structure"""
    
    def __init__(self, web3: Web3, contract_address: str, abi_path: str = None):
        self.w3 = web3
        self.contract_address = contract_address
        
        # Load ABI
        if abi_path:
            with open(abi_path, 'r') as f:
                abi = json.load(f)
        else:
            # Default ABI location
            abi_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "artifacts",
                "contracts",
                "TrackRecordV2.sol",
                "TrackRecordV2.json"
            )
            with open(abi_path, 'r') as f:
                artifact = json.load(f)
                abi = artifact['abi']
        
        self.contract = self.w3.eth.contract(
            address=self.contract_address,
            abi=abi
        )
    
    def prepare_daily_record(self, raw_data: Dict) -> Dict:
        """
        Convert raw trading data to blockchain format (36 fields)
        
        All monetary values converted to cents (x100)
        All percentages scaled appropriately
        """
        
        # Helper function to convert dollars to cents
        def to_cents(value):
            return int(Decimal(str(value)) * 100)
        
        # Helper function to scale percentages
        def scale_pct(value, scale):
            return int(Decimal(str(value)) * scale)
        
        record = {
            # Box 1: Identity & Time
            "date": int(raw_data['date']),  # YYYYMMDD
            "tradingDayNum": int(raw_data['trading_day_num']),
            "timestamp": int(raw_data['timestamp'].replace(':', '')),  # HHMMSS
            
            # Box 2: Account State
            "balanceStart": to_cents(raw_data['balance_start']),
            "balanceEnd": to_cents(raw_data['balance_end']),
            "deposits": to_cents(raw_data.get('deposits', 0)),
            "withdrawals": to_cents(raw_data.get('withdrawals', 0)),
            
            # Box 3: P&L Breakdown
            "grossPnl": to_cents(raw_data['gross_pnl']),
            "commissions": to_cents(raw_data['commissions']),  # Negative
            "interestExpense": to_cents(raw_data['interest_expense']),  # Negative
            "otherFees": to_cents(raw_data['other_fees']),  # Negative
            "netPnl": to_cents(raw_data['net_pnl']),
            
            # Box 4: Performance Metrics
            "netReturnPct": scale_pct(raw_data['net_return_pct'], 1000),  # 0.524% = 524
            "returnAnnualized": scale_pct(raw_data['return_annualized'], 10),  # 191.2% = 1912
            "sharpe30d": scale_pct(raw_data['sharpe_30d'], 100),  # 2.1 = 210
            "sortino30d": scale_pct(raw_data['sortino_30d'], 100),  # 2.8 = 280
            "volatility30d": scale_pct(raw_data['volatility_30d'], 100),  # 11.2% = 1120
            "maxDrawdown30d": scale_pct(raw_data['max_drawdown_30d'], 100),  # -2.1% = -210
            
            # Box 5: Trading Activity
            "contractsTotal": int(raw_data['contracts_total']),
            "putContracts": int(raw_data['put_contracts']),
            "callContracts": int(raw_data['call_contracts']),
            "premiumCollected": to_cents(raw_data['premium_collected']),
            "marginUsed": to_cents(raw_data['margin_used']),
            "positionSizePct": scale_pct(raw_data['position_size_pct'], 100),  # 1.0% = 100
            "impliedTurnover": to_cents(raw_data['implied_turnover']),
            
            # Box 6: Greeks
            "deltaExposure": scale_pct(raw_data['delta_exposure'], 100),  # -0.12 = -12
            "gammaExposure": scale_pct(raw_data['gamma_exposure'], 1000),  # -0.008 = -8
            "thetaIncome": to_cents(raw_data['theta_income']),
            "vegaExposure": int(raw_data['vega_exposure']),  # Already scaled
            
            # Box 7: Win/Loss Tracking
            "positionsExpired": int(raw_data['positions_expired']),
            "positionsAssigned": int(raw_data['positions_assigned']),
            "positionsStopped": int(raw_data['positions_stopped']),
            "winRate": scale_pct(raw_data['win_rate'], 10),  # 82.5% = 825
            
            # Box 8: Fund Metrics
            "dpi": scale_pct(raw_data['dpi'], 10000),  # 0.15 = 1500
            "tvpi": scale_pct(raw_data['tvpi'], 10000),  # 10.25 = 102500
            "rvpi": scale_pct(raw_data['rvpi'], 10000)   # 10.10 = 101000
        }
        
        return record
    
    async def post_daily_record(self, record_data: Dict, private_key: str) -> str:
        """
        Post a daily record to the blockchain
        
        Args:
            record_data: Dictionary with all 36 fields
            private_key: Private key for signing transaction
            
        Returns:
            Transaction hash
        """
        account = self.w3.eth.account.from_key(private_key)
        
        # Prepare the record
        record = self.prepare_daily_record(record_data)
        
        # Build transaction
        tx = self.contract.functions.postDailyRecord(record).build_transaction({
            'from': account.address,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'gasPrice': self.w3.eth.gas_price,
        })
        
        # Sign and send
        signed_tx = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        return tx_hash.hex()
    
    def get_record(self, trader: str, date: int) -> Optional[Dict]:
        """
        Retrieve a daily record from the blockchain
        
        Args:
            trader: Trader's address
            date: Date in YYYYMMDD format
            
        Returns:
            Dictionary with all 36 fields (descaled to normal values)
        """
        try:
            record = self.contract.functions.getRecord(trader, date).call()
            return self._decode_record(record)
        except Exception as e:
            if "Record does not exist" in str(e):
                return None
            raise
    
    def get_record_range(self, trader: str, start_date: int, end_date: int) -> List[Dict]:
        """
        Get multiple records for a date range
        """
        records = self.contract.functions.getRecordRange(
            trader,
            start_date,
            end_date
        ).call()
        
        return [self._decode_record(r) for r in records]
    
    def get_trader_stats(self, trader: str) -> Dict:
        """
        Get overall statistics for a trader
        """
        stats = self.contract.functions.getTraderStats(trader).call()
        
        return {
            'first_date': stats[0],
            'last_date': stats[1],
            'total_days': stats[2],
            'total_net_pnl': Decimal(stats[3]) / 100,  # Convert from cents
            'current_balance': Decimal(stats[4]) / 100  # Convert from cents
        }
    
    def _decode_record(self, record: tuple) -> Dict:
        """
        Convert blockchain record back to human-readable format
        """
        # The record is returned as a tuple, need to map back to dict
        # Order must match the struct in the smart contract
        
        return {
            # Box 1: Identity & Time
            'date': record[0],
            'trading_day_num': record[1],
            'timestamp': f"{str(record[2]).zfill(6)[:2]}:{str(record[2]).zfill(6)[2:4]}:{str(record[2]).zfill(6)[4:]}",
            
            # Box 2: Account State
            'balance_start': Decimal(record[3]) / 100,
            'balance_end': Decimal(record[4]) / 100,
            'deposits': Decimal(record[5]) / 100,
            'withdrawals': Decimal(record[6]) / 100,
            
            # Box 3: P&L Breakdown
            'gross_pnl': Decimal(record[7]) / 100,
            'commissions': Decimal(record[8]) / 100,
            'interest_expense': Decimal(record[9]) / 100,
            'other_fees': Decimal(record[10]) / 100,
            'net_pnl': Decimal(record[11]) / 100,
            
            # Box 4: Performance Metrics
            'net_return_pct': Decimal(record[12]) / 1000,
            'return_annualized': Decimal(record[13]) / 10,
            'sharpe_30d': Decimal(record[14]) / 100,
            'sortino_30d': Decimal(record[15]) / 100,
            'volatility_30d': Decimal(record[16]) / 100,
            'max_drawdown_30d': Decimal(record[17]) / 100,
            
            # Box 5: Trading Activity
            'contracts_total': record[18],
            'put_contracts': record[19],
            'call_contracts': record[20],
            'premium_collected': Decimal(record[21]) / 100,
            'margin_used': Decimal(record[22]) / 100,
            'position_size_pct': Decimal(record[23]) / 100,
            'implied_turnover': Decimal(record[24]) / 100,
            
            # Box 6: Greeks
            'delta_exposure': Decimal(record[25]) / 100,
            'gamma_exposure': Decimal(record[26]) / 1000,
            'theta_income': Decimal(record[27]) / 100,
            'vega_exposure': record[28],
            
            # Box 7: Win/Loss Tracking
            'positions_expired': record[29],
            'positions_assigned': record[30],
            'positions_stopped': record[31],
            'win_rate': Decimal(record[32]) / 10,
            
            # Box 8: Fund Metrics
            'dpi': Decimal(record[33]) / 10000,
            'tvpi': Decimal(record[34]) / 10000,
            'rvpi': Decimal(record[35]) / 10000
        }


# Example usage
if __name__ == "__main__":
    # Example of how to use this
    from web3 import Web3
    
    # Connect to Polygon
    w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
    
    # Initialize track record interface
    track_record = TrackRecordV2(
        w3,
        contract_address="0x...",  # Deploy address
    )
    
    # Example daily data
    daily_data = {
        'date': '20240115',
        'trading_day_num': 1,
        'timestamp': '09:35:22',
        'balance_start': 200000,
        'balance_end': 201048,
        'deposits': 0,
        'withdrawals': 0,
        'gross_pnl': 1250,
        'commissions': -65,
        'interest_expense': -12,
        'other_fees': -125,
        'net_pnl': 1048,
        'net_return_pct': 0.524,
        'return_annualized': 191.2,
        'sharpe_30d': 2.1,
        'sortino_30d': 2.8,
        'volatility_30d': 11.2,
        'max_drawdown_30d': -2.1,
        'contracts_total': 5,
        'put_contracts': 3,
        'call_contracts': 2,
        'premium_collected': 5250,
        'margin_used': 45000,
        'position_size_pct': 1.0,
        'implied_turnover': 2250000,
        'delta_exposure': -0.12,
        'gamma_exposure': -0.008,
        'theta_income': 850,
        'vega_exposure': -120,
        'positions_expired': 5,
        'positions_assigned': 0,
        'positions_stopped': 0,
        'win_rate': 100.0,
        'dpi': 0.00,
        'tvpi': 1.005,
        'rvpi': 1.005
    }
    
    # Post to blockchain
    # tx_hash = await track_record.post_daily_record(daily_data, private_key)