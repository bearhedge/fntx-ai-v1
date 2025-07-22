#!/usr/bin/env python3
"""
Test OTM-only filtering in the smart strike selection
Verifies that ITM options are correctly excluded
"""
import sys
import psycopg2
from datetime import datetime
from download_day_strikes import StrikeAwareDailyDownloader
import os

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def verify_otm_filtering(date: str = "2023-01-03"):
    """Verify that only OTM options were downloaded"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Get ATM strike from checkpoint
        checkpoint_file = f"checkpoint_{date.replace('-', '')}.json"
        if os.path.exists(checkpoint_file):
            import json
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                atm_strike = checkpoint['stats']['atm_strike']
                print(f"ATM Strike: ${atm_strike}")
        else:
            print("No checkpoint file found")
            return
        
        # Check for ITM calls (strikes <= ATM)
        cursor.execute("""
            SELECT strike, option_type, COUNT(*) as count
            FROM theta.options_contracts
            WHERE symbol = 'SPY' 
            AND expiration = %s
            AND option_type = 'C'
            AND strike <= %s
            GROUP BY strike, option_type
            ORDER BY strike
        """, (date, atm_strike))
        
        itm_calls = cursor.fetchall()
        if itm_calls:
            print(f"\n❌ Found {len(itm_calls)} ITM call strikes (should be 0):")
            for strike, opt_type, count in itm_calls:
                print(f"   ${strike} {opt_type}")
        else:
            print("\n✅ No ITM calls found (correct)")
        
        # Check for ITM puts (strikes >= ATM)
        cursor.execute("""
            SELECT strike, option_type, COUNT(*) as count
            FROM theta.options_contracts
            WHERE symbol = 'SPY' 
            AND expiration = %s
            AND option_type = 'P'
            AND strike >= %s
            GROUP BY strike, option_type
            ORDER BY strike
        """, (date, atm_strike))
        
        itm_puts = cursor.fetchall()
        if itm_puts:
            print(f"\n❌ Found {len(itm_puts)} ITM put strikes (should be 0):")
            for strike, opt_type, count in itm_puts:
                print(f"   ${strike} {opt_type}")
        else:
            print("\n✅ No ITM puts found (correct)")
        
        # Show OTM distribution
        cursor.execute("""
            SELECT 
                option_type,
                COUNT(DISTINCT strike) as unique_strikes,
                MIN(strike) as min_strike,
                MAX(strike) as max_strike,
                COUNT(*) as total_contracts
            FROM theta.options_contracts
            WHERE symbol = 'SPY' 
            AND expiration = %s
            GROUP BY option_type
            ORDER BY option_type
        """, (date,))
        
        print("\n📊 OTM Options Distribution:")
        for opt_type, unique_strikes, min_strike, max_strike, total in cursor.fetchall():
            if opt_type == 'C':
                print(f"   Calls: {unique_strikes} strikes (${min_strike}-${max_strike})")
                print(f"          All should be > ${atm_strike} ✓" if min_strike > atm_strike else f"          ERROR: Found strikes <= ${atm_strike}")
            else:
                print(f"   Puts:  {unique_strikes} strikes (${min_strike}-${max_strike})")
                print(f"          All should be < ${atm_strike} ✓" if max_strike < atm_strike else f"          ERROR: Found strikes >= ${atm_strike}")
        
        # Show strike distribution around ATM
        cursor.execute("""
            SELECT strike, option_type, COUNT(DISTINCT contract_id) as contracts
            FROM theta.options_contracts
            WHERE symbol = 'SPY' 
            AND expiration = %s
            AND strike BETWEEN %s AND %s
            GROUP BY strike, option_type
            ORDER BY strike, option_type
        """, (date, atm_strike - 5, atm_strike + 5))
        
        print(f"\n📍 Strikes around ATM (${atm_strike}):")
        current_strike = None
        for strike, opt_type, contracts in cursor.fetchall():
            if strike != current_strike:
                current_strike = strike
                distance = strike - atm_strike
                print(f"\n   ${strike} ({'+' if distance >= 0 else ''}{distance} from ATM):")
            
            # Check if correctly filtered
            if opt_type == 'C' and strike <= atm_strike:
                status = "❌ ITM call (should be filtered)"
            elif opt_type == 'P' and strike >= atm_strike:
                status = "❌ ITM put (should be filtered)"
            elif opt_type == 'C' and strike > atm_strike:
                status = "✅ OTM call"
            elif opt_type == 'P' and strike < atm_strike:
                status = "✅ OTM put"
            else:
                status = "?"
            
            print(f"      {opt_type}: {contracts} contracts - {status}")
        
    except Exception as e:
        print(f"Error verifying OTM filtering: {e}")
        return 1
    finally:
        cursor.close()
        conn.close()
    
    return 0

def test_otm_download():
    """Test downloading with OTM filtering enabled"""
    print("🧪 Testing OTM-only download for Jan 3, 2023\n")
    
    # First, clean existing data
    print("1️⃣ Cleaning existing data...")
    os.system("python3 clean_jan3_data.py")
    
    # Remove checkpoint to start fresh
    checkpoint_file = "checkpoint_20230103.json"
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
        print("   Removed old checkpoint file")
    
    print("\n2️⃣ Running download with OTM filtering...")
    
    # Create downloader with smart selection (includes OTM filtering)
    downloader = StrikeAwareDailyDownloader(use_smart_selection=True)
    
    # Test date
    test_date = datetime(2023, 1, 3)
    
    # Run download
    result = downloader.download_day(test_date)
    
    if result['status'] == 'complete':
        print("\n3️⃣ Download complete! Verifying OTM filtering...")
        verify_otm_filtering("2023-01-03")
        
        # Show statistics
        print(f"\n📈 Download Statistics:")
        print(f"   Total contracts: {result['stats']['total_contracts']}")
        print(f"   Strike selection: {result['stats']['strike_selection_method']}")
        print(f"   ATM strike: ${result['stats']['atm_strike']}")
        print(f"   ATM IV: {result['stats'].get('atm_iv', 0):.1%}")
    else:
        print(f"\n❌ Download failed: {result.get('errors', ['Unknown error'])}")

if __name__ == "__main__":
    test_otm_download()