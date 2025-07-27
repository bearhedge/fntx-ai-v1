"""
Utility functions for FNTX blockchain integration
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any
from decimal import Decimal
import ipfshttpclient

def format_date(date: datetime) -> int:
    """
    Format datetime to YYYYMMDD integer for smart contract
    
    Args:
        date: Datetime object
        
    Returns:
        Integer in YYYYMMDD format
    """
    return int(date.strftime("%Y%m%d"))

def calculate_metrics(trades: list, deposits: Decimal, withdrawals: Decimal) -> Dict[str, Any]:
    """
    Calculate comprehensive trading metrics
    
    Args:
        trades: List of trade dictionaries
        deposits: Total deposits for the period
        withdrawals: Total withdrawals for the period
        
    Returns:
        Dictionary of calculated metrics
    """
    # Calculate P&L
    total_pnl = sum(Decimal(str(t.get('pnl', 0))) for t in trades)
    
    # Calculate win rate
    winning_trades = [t for t in trades if Decimal(str(t.get('pnl', 0))) > 0]
    win_rate = len(winning_trades) / len(trades) if trades else 0
    
    # Calculate other metrics
    metrics = {
        'date': datetime.now().isoformat(),
        'trades_count': len(trades),
        'total_pnl': float(total_pnl),
        'win_rate': win_rate,
        'deposits': float(deposits),
        'withdrawals': float(withdrawals),
        'net_cash_flow': float(deposits - withdrawals),
        'trades': trades
    }
    
    return metrics

def ipfs_upload(data: Dict[str, Any], ipfs_url: str = "/ip4/127.0.0.1/tcp/5001") -> str:
    """
    Upload trading data to IPFS
    
    Args:
        data: Trading data dictionary
        ipfs_url: IPFS API URL
        
    Returns:
        IPFS hash
    """
    try:
        # Connect to IPFS
        client = ipfshttpclient.connect(ipfs_url)
        
        # Convert to JSON
        json_data = json.dumps(data, indent=2, default=str)
        
        # Upload to IPFS
        result = client.add_json(data)
        
        return result
    except Exception as e:
        # If IPFS is not available, use a mock hash for development
        print(f"IPFS upload failed: {e}")
        print("Using mock hash for development")
        
        # Create deterministic hash from data
        data_str = json.dumps(data, sort_keys=True, default=str)
        mock_hash = hashlib.sha256(data_str.encode()).hexdigest()
        return f"Qm{mock_hash[:44]}"  # Mock IPFS hash format

def ipfs_retrieve(ipfs_hash: str, ipfs_url: str = "/ip4/127.0.0.1/tcp/5001") -> Dict[str, Any]:
    """
    Retrieve trading data from IPFS
    
    Args:
        ipfs_hash: IPFS hash of the data
        ipfs_url: IPFS API URL
        
    Returns:
        Trading data dictionary
    """
    try:
        # Connect to IPFS
        client = ipfshttpclient.connect(ipfs_url)
        
        # Retrieve data
        data = client.get_json(ipfs_hash)
        
        return data
    except Exception as e:
        print(f"IPFS retrieval failed: {e}")
        # Return mock data for development
        return {
            'error': 'IPFS not available',
            'hash': ipfs_hash,
            'mock_data': True
        }

def create_daily_record(
    trading_results: Dict[str, Any],
    account_snapshot: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a comprehensive daily record for blockchain storage
    
    Args:
        trading_results: Results from trading system
        account_snapshot: Account balance snapshot
        
    Returns:
        Formatted record ready for IPFS/blockchain
    """
    record = {
        'version': '1.0',
        'timestamp': datetime.now().isoformat(),
        'account': {
            'starting_balance': account_snapshot.get('starting_balance', 0),
            'ending_balance': account_snapshot.get('ending_balance', 0),
            'deposits': account_snapshot.get('deposits', 0),
            'withdrawals': account_snapshot.get('withdrawals', 0)
        },
        'trading': {
            'total_trades': len(trading_results.get('trades', [])),
            'realized_pnl': trading_results.get('total_pnl', 0),
            'fees': trading_results.get('fees', 0),
            'win_rate': trading_results.get('win_rate', 0)
        },
        'performance': {
            'daily_return': calculate_daily_return(
                account_snapshot.get('starting_balance', 0),
                trading_results.get('total_pnl', 0)
            ),
            'sharpe_ratio': trading_results.get('sharpe_ratio', 0),
            'max_drawdown': trading_results.get('max_drawdown', 0)
        },
        'positions': trading_results.get('open_positions', []),
        'trades': trading_results.get('trades', [])
    }
    
    return record

def calculate_daily_return(starting_balance: float, pnl: float) -> float:
    """Calculate daily return percentage"""
    if starting_balance <= 0:
        return 0
    return (pnl / starting_balance) * 100

def verify_record_integrity(record: Dict[str, Any]) -> bool:
    """
    Verify that a trading record has all required fields
    
    Args:
        record: Trading record dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        'version',
        'timestamp',
        'account',
        'trading',
        'performance'
    ]
    
    for field in required_fields:
        if field not in record:
            return False
    
    # Verify nested fields
    if 'starting_balance' not in record.get('account', {}):
        return False
    
    if 'total_trades' not in record.get('trading', {}):
        return False
    
    return True