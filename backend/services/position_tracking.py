#!/usr/bin/env python3
"""
Position Tracking Service
Provides current position information for the Risk Manager
"""

from typing import List, Dict, Any
import psycopg2
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    "dbname": "options_data",
    "user": "postgres", 
    "password": "theta_data_2024",
    "host": "localhost"
}


def get_current_positions() -> List[Dict[str, Any]]:
    """
    Get current open positions from the database
    
    Returns:
        List of position dictionaries with symbol, quantity, etc.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Query for current positions
        # This is a simplified version - actual implementation would join with trades table
        query = """
            SELECT 
                symbol,
                SUM(quantity) as quantity,
                AVG(entry_price) as avg_price
            FROM trading.positions
            WHERE closed_at IS NULL
            AND symbol LIKE 'SPY%'
            GROUP BY symbol
            HAVING SUM(quantity) != 0
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        positions = []
        for row in results:
            positions.append({
                'symbol': row[0],
                'quantity': int(row[1]),
                'avg_price': float(row[2]) if row[2] else 0.0
            })
            
        cursor.close()
        conn.close()
        
        return positions
        
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        # Return empty list on error
        return []


def get_position_summary() -> Dict[str, Any]:
    """
    Get a summary of current positions
    
    Returns:
        Dictionary with position counts and totals
    """
    positions = get_current_positions()
    
    call_count = 0
    put_count = 0
    total_value = 0.0
    
    for pos in positions:
        if pos['quantity'] != 0:
            if 'C' in pos['symbol']:
                call_count += abs(pos['quantity'])
            elif 'P' in pos['symbol']:
                put_count += abs(pos['quantity'])
            total_value += abs(pos['quantity'] * pos['avg_price'] * 100)
    
    return {
        'call_contracts': call_count,
        'put_contracts': put_count,
        'total_contracts': call_count + put_count,
        'total_value': total_value
    }


if __name__ == "__main__":
    # Test the service
    print("Testing Position Tracking Service...")
    
    positions = get_current_positions()
    print(f"\nCurrent Positions: {len(positions)}")
    
    for pos in positions:
        print(f"  {pos['symbol']}: {pos['quantity']} @ ${pos['avg_price']:.2f}")
    
    summary = get_position_summary()
    print(f"\nPosition Summary:")
    print(f"  Calls: {summary['call_contracts']}")
    print(f"  Puts: {summary['put_contracts']}")
    print(f"  Total Value: ${summary['total_value']:,.2f}")