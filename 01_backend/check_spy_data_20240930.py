#!/usr/bin/env python3
"""
Script to check if SPY options data exists for September 30, 2024
"""
import sys
import os
import psycopg2
from datetime import datetime
# from tabulate import tabulate  # Optional, will use simple formatting if not available
try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.theta_config import DB_CONFIG

def check_spy_data_for_date(target_date='2024-09-30'):
    """Check if SPY options data exists for a specific date"""
    
    print(f"🔍 Checking SPY options data for {target_date}")
    print("=" * 80)
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 1. Check if contracts exist for this expiration
        print("\n📋 Checking contracts expiring on", target_date)
        cursor.execute("""
            SELECT 
                contract_id,
                symbol,
                expiration,
                strike,
                option_type
            FROM theta.options_contracts
            WHERE symbol = 'SPY' 
            AND expiration = %s
            ORDER BY strike, option_type
        """, (target_date,))
        
        contracts = cursor.fetchall()
        
        if not contracts:
            print(f"❌ No SPY contracts found expiring on {target_date}")
            return
        
        print(f"✅ Found {len(contracts)} SPY contracts expiring on {target_date}")
        
        # Show strike range
        strikes = sorted(set(row[3] for row in contracts))
        print(f"📊 Strike range: ${min(strikes)} - ${max(strikes)}")
        print(f"📊 Number of unique strikes: {len(strikes)}")
        
        # 2. Check data availability for these contracts
        contract_ids = [row[0] for row in contracts]
        
        # Check OHLC data
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT contract_id) as contracts_with_data,
                COUNT(*) as total_records,
                MIN(datetime) as earliest_data,
                MAX(datetime) as latest_data
            FROM theta.options_ohlc
            WHERE contract_id = ANY(%s)
        """, (contract_ids,))
        
        ohlc_stats = cursor.fetchone()
        
        # Check Greeks data
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT contract_id) as contracts_with_data,
                COUNT(*) as total_records,
                MIN(datetime) as earliest_data,
                MAX(datetime) as latest_data
            FROM theta.options_greeks
            WHERE contract_id = ANY(%s)
        """, (contract_ids,))
        
        greeks_stats = cursor.fetchone()
        
        # Check IV data
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT contract_id) as contracts_with_data,
                COUNT(*) as total_records,
                MIN(datetime) as earliest_data,
                MAX(datetime) as latest_data
            FROM theta.options_iv
            WHERE contract_id = ANY(%s)
        """, (contract_ids,))
        
        iv_stats = cursor.fetchone()
        
        # Display results
        print("\n📊 Data Availability Summary:")
        print("-" * 80)
        
        data_summary = [
            ["Data Type", "Contracts with Data", "Total Records", "Date Range"],
            ["OHLC", 
             f"{ohlc_stats[0]}/{len(contracts)} ({ohlc_stats[0]/len(contracts)*100:.1f}%)" if ohlc_stats[0] else "0/0",
             f"{ohlc_stats[1]:,}" if ohlc_stats[1] else "0",
             f"{ohlc_stats[2]} to {ohlc_stats[3]}" if ohlc_stats[2] else "No data"],
            ["Greeks", 
             f"{greeks_stats[0]}/{len(contracts)} ({greeks_stats[0]/len(contracts)*100:.1f}%)" if greeks_stats[0] else "0/0",
             f"{greeks_stats[1]:,}" if greeks_stats[1] else "0",
             f"{greeks_stats[2]} to {greeks_stats[3]}" if greeks_stats[2] else "No data"],
            ["IV", 
             f"{iv_stats[0]}/{len(contracts)} ({iv_stats[0]/len(contracts)*100:.1f}%)" if iv_stats[0] else "0/0",
             f"{iv_stats[1]:,}" if iv_stats[1] else "0",
             f"{iv_stats[2]} to {iv_stats[3]}" if iv_stats[2] else "No data"]
        ]
        
        if HAS_TABULATE:
            print(tabulate(data_summary, headers="firstrow", tablefmt="grid"))
        else:
            # Simple formatting without tabulate
            for row in data_summary:
                print(f"{row[0]:<15} {row[1]:<25} {row[2]:<15} {row[3]}")
        
        # 3. Sample some specific contracts to show detail
        print("\n📋 Sample Contracts (first 10):")
        print("-" * 80)
        
        sample_data = []
        for i, (contract_id, symbol, exp, strike, opt_type) in enumerate(contracts[:10]):
            # Get data counts for this specific contract
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM theta.options_ohlc WHERE contract_id = %s) as ohlc_count,
                    (SELECT COUNT(*) FROM theta.options_greeks WHERE contract_id = %s) as greeks_count,
                    (SELECT COUNT(*) FROM theta.options_iv WHERE contract_id = %s) as iv_count
            """, (contract_id, contract_id, contract_id))
            
            counts = cursor.fetchone()
            sample_data.append([
                f"{symbol} {strike}{opt_type}",
                exp.strftime("%Y-%m-%d"),
                counts[0],
                counts[1], 
                counts[2]
            ])
        
        if HAS_TABULATE:
            print(tabulate(sample_data, 
                          headers=["Contract", "Expiration", "OHLC Records", "Greeks Records", "IV Records"],
                          tablefmt="grid"))
        else:
            # Simple formatting without tabulate
            print(f"{'Contract':<15} {'Expiration':<12} {'OHLC Records':<12} {'Greeks Records':<14} {'IV Records'}")
            print("-" * 70)
            for row in sample_data:
                print(f"{row[0]:<15} {row[1]:<12} {row[2]:<12} {row[3]:<14} {row[4]}")
        
        # 4. Check for data on the specific date
        print(f"\n📅 Checking for data ON {target_date}:")
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT o.contract_id) as contracts_with_data,
                COUNT(*) as total_records
            FROM theta.options_ohlc o
            JOIN theta.options_contracts c ON o.contract_id = c.contract_id
            WHERE c.symbol = 'SPY' 
            AND c.expiration = %s
            AND DATE(o.datetime) = %s
        """, (target_date, target_date))
        
        same_day_stats = cursor.fetchone()
        
        if same_day_stats[1] > 0:
            print(f"✅ Found {same_day_stats[1]:,} OHLC records for {same_day_stats[0]} contracts on {target_date}")
        else:
            print(f"❌ No OHLC data found specifically on {target_date}")
            
        # Close connection
        cursor.close()
        conn.close()
        
        print("\n✅ Data check complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check SPY options data for a specific date')
    parser.add_argument('--date', type=str, default='2024-09-30',
                       help='Date to check (YYYY-MM-DD format)')
    
    args = parser.parse_args()
    
    # Validate date format
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("❌ Invalid date format. Please use YYYY-MM-DD")
        sys.exit(1)
    
    check_spy_data_for_date(args.date)


if __name__ == "__main__":
    main()