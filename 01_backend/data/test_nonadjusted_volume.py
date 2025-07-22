#!/usr/bin/env python3
"""
Test non-adjusted prices with 60-bar volume filtering
"""
import sys
import psycopg2

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def analyze_with_correct_atm(date: str = "2023-01-03"):
    """Analyze data with correct ATM based on non-adjusted prices"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Correct ATM based on non-adjusted price
        nonadj_open = 384.37
        correct_atm = 384
        
        print(f"📊 Analysis with Correct ATM (Non-Adjusted Prices)")
        print(f"   Non-adjusted SPY open: ${nonadj_open:.2f}")
        print(f"   Correct ATM strike: ${correct_atm}")
        print(f"   (Previously using: $372 based on adjusted price)")
        
        # Get all contracts with bar counts
        cursor.execute("""
            SELECT 
                c.strike,
                c.option_type,
                COUNT(o.datetime) as bar_count,
                ABS(c.strike - %s) as distance_from_atm
            FROM theta.options_contracts c
            JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            WHERE c.symbol = 'SPY' 
            AND c.expiration = %s
            GROUP BY c.contract_id, c.strike, c.option_type
            ORDER BY distance_from_atm, c.option_type
        """, (correct_atm, date))
        
        results = cursor.fetchall()
        
        # Analyze with 60-bar threshold
        min_bars = 60
        calls_kept = []
        puts_kept = []
        
        print(f"\n📈 Volume Analysis (60-bar threshold, 5 hours):")
        print(f"{'Strike':<8} {'Type':<4} {'Bars':<5} {'Dist':<5} {'Status'}")
        print("-" * 40)
        
        for strike, opt_type, bar_count, distance in results[:20]:  # Show closest 20
            if bar_count >= min_bars:
                status = "✅ KEEP"
                if opt_type == 'C':
                    calls_kept.append((strike, bar_count))
                else:
                    puts_kept.append((strike, bar_count))
            else:
                status = "❌ FILTER"
            
            print(f"${strike:<7} {opt_type:<4} {bar_count:<5} ±{distance:<4} {status}")
        
        print(f"\n📊 Summary with 60-bar filter:")
        print(f"   Calls kept: {len(calls_kept)}")
        print(f"   Puts kept: {len(puts_kept)}")
        print(f"   Total kept: {len(calls_kept) + len(puts_kept)}")
        
        # Show the actual strikes that would be kept
        if calls_kept:
            print(f"\n📈 Call strikes kept: {[s for s, _ in sorted(calls_kept)]}")
        if puts_kept:
            print(f"📉 Put strikes kept: {[s for s, _ in sorted(puts_kept)]}")
        
        # Check if we meet the 5-10 per side target
        if len(calls_kept) >= 5 and len(puts_kept) >= 5:
            print(f"\n✅ Target met: {len(calls_kept)} calls and {len(puts_kept)} puts")
        else:
            print(f"\n⚠️  Below target: Need 5-10 per side")
            
            # Show what we'd get with 50-bar threshold
            calls_50 = sum(1 for _, _, bars, _ in results if _ == 'C' and bars >= 50)
            puts_50 = sum(1 for _, _, bars, _ in results if _ == 'P' and bars >= 50)
            print(f"   With 50-bar threshold: {calls_50} calls, {puts_50} puts")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        cursor.close()
        conn.close()
    
    return 0

if __name__ == "__main__":
    analyze_with_correct_atm()