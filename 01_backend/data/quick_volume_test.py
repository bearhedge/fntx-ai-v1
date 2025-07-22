#!/usr/bin/env python3
"""
Quick test of volume-based filtering logic
"""
import sys
import psycopg2

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def test_current_data_volume():
    """Test volume filtering on existing data"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Check if we have any data
        cursor.execute("""
            SELECT COUNT(*) FROM theta.options_contracts 
            WHERE symbol = 'SPY' AND expiration = '2023-01-03'
        """)
        
        contract_count = cursor.fetchone()[0]
        print(f"Found {contract_count} contracts for Jan 3, 2023")
        
        if contract_count == 0:
            print("No data to test. Run the download first.")
            return
        
        # Get bar counts per contract
        cursor.execute("""
            SELECT 
                c.strike,
                c.option_type,
                COUNT(o.datetime) as bar_count
            FROM theta.options_contracts c
            JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            WHERE c.symbol = 'SPY' 
            AND c.expiration = '2023-01-03'
            GROUP BY c.contract_id, c.strike, c.option_type
            ORDER BY c.strike, c.option_type
        """)
        
        results = cursor.fetchall()
        
        min_bars = 20  # Updated threshold
        print(f"\n📊 Volume Analysis ({min_bars}+ bar threshold):")
        print(f"{'Strike':<8} {'Type':<4} {'Bars':<5} {'Status'}")
        print("-" * 30)
        
        above_threshold = 0
        below_threshold = 0
        
        for strike, opt_type, bar_count in results:
            if bar_count >= min_bars:
                status = "✅ KEEP"
                above_threshold += 1
            else:
                status = "❌ FILTER"
                below_threshold += 1
            
            print(f"${strike:<7} {opt_type:<4} {bar_count:<5} {status}")
        
        total = len(results)
        print(f"\nSummary:")
        print(f"  Total: {total} contracts")
        print(f"  Keep (≥{min_bars} bars): {above_threshold} ({above_threshold/total*100:.1f}%)")
        print(f"  Filter (<{min_bars} bars): {below_threshold} ({below_threshold/total*100:.1f}%)")
        
        # Show the filtering would work
        if below_threshold > 0:
            print(f"\n💡 Volume filtering would reduce contracts by {below_threshold/total*100:.1f}%")
            print("   Only keeping contracts with substantial trading activity")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        cursor.close()
        conn.close()
    
    return 0

if __name__ == "__main__":
    test_current_data_volume()