#!/usr/bin/env python3
"""
Test volume-based filtering (70+ rows) vs old ITM/OTM logic
Validates that we capture liquid contracts regardless of position
"""
import sys
import psycopg2
from datetime import datetime
from download_day_strikes import StrikeAwareDailyDownloader
import os

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

def analyze_volume_distribution(date: str = "2023-01-03"):
    """Analyze volume distribution to validate 70-bar threshold"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Get OHLC bar counts per contract
        cursor.execute("""
            SELECT 
                c.strike,
                c.option_type,
                COUNT(o.datetime) as bar_count,
                MIN(o.datetime) as first_bar,
                MAX(o.datetime) as last_bar,
                AVG(o.volume) as avg_volume
            FROM theta.options_contracts c
            JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            WHERE c.symbol = 'SPY' 
            AND c.expiration = %s
            GROUP BY c.contract_id, c.strike, c.option_type
            ORDER BY c.strike, c.option_type
        """, (date,))
        
        results = cursor.fetchall()
        
        if not results:
            print(f"No data found for {date}")
            return
        
        # Analyze volume distribution
        above_70 = []
        below_70 = []
        
        print(f"\n📊 Volume Distribution Analysis for {date}")
        print(f"{'Strike':<8} {'Type':<4} {'Bars':<5} {'Duration':<20} {'Avg Vol':<8} {'Status'}")
        print("-" * 65)
        
        for strike, opt_type, bar_count, first_bar, last_bar, avg_volume in results:
            duration = f"{first_bar.strftime('%H:%M')}-{last_bar.strftime('%H:%M')}"
            avg_vol = int(avg_volume) if avg_volume else 0
            
            if bar_count >= 70:
                status = "✅ KEEP"
                above_70.append((strike, opt_type, bar_count))
            else:
                status = "❌ FILTER"
                below_70.append((strike, opt_type, bar_count))
            
            print(f"${strike:<7} {opt_type:<4} {bar_count:<5} {duration:<20} {avg_vol:<8} {status}")
        
        # Summary statistics
        total_contracts = len(results)
        kept_contracts = len(above_70)
        filtered_contracts = len(below_70)
        
        print(f"\n📈 Volume Filtering Summary:")
        print(f"   Total contracts: {total_contracts}")
        print(f"   Kept (≥70 bars): {kept_contracts} ({kept_contracts/total_contracts*100:.1f}%)")
        print(f"   Filtered (<70 bars): {filtered_contracts} ({filtered_contracts/total_contracts*100:.1f}%)")
        
        # Show distribution by bar count ranges
        bar_ranges = {
            "0-20": 0, "21-40": 0, "41-60": 0, "61-70": 0, "71-80": 0, "81+": 0
        }
        
        for _, _, bar_count in results:
            if bar_count <= 20:
                bar_ranges["0-20"] += 1
            elif bar_count <= 40:
                bar_ranges["21-40"] += 1
            elif bar_count <= 60:
                bar_ranges["41-60"] += 1
            elif bar_count <= 70:
                bar_ranges["61-70"] += 1
            elif bar_count <= 80:
                bar_ranges["71-80"] += 1
            else:
                bar_ranges["81+"] += 1
        
        print(f"\n📊 Bar Count Distribution:")
        for range_name, count in bar_ranges.items():
            percentage = (count / total_contracts) * 100
            print(f"   {range_name:<8} bars: {count} contracts ({percentage:.1f}%)")
        
    except Exception as e:
        print(f"Error analyzing volume distribution: {e}")
        return 1
    finally:
        cursor.close()
        conn.close()
    
    return 0

def compare_old_vs_new_filtering(date: str = "2023-01-03"):
    """Compare old ITM/OTM filtering vs new volume filtering"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Get current data with bar counts
        cursor.execute("""
            SELECT 
                c.strike,
                c.option_type,
                COUNT(o.datetime) as bar_count,
                c.contract_id
            FROM theta.options_contracts c
            JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
            WHERE c.symbol = 'SPY' 
            AND c.expiration = %s
            GROUP BY c.contract_id, c.strike, c.option_type
            ORDER BY c.strike, c.option_type
        """, (date,))
        
        results = cursor.fetchall()
        
        if not results:
            print("No data to compare")
            return
        
        # Get ATM from checkpoint (if available)
        checkpoint_file = f"checkpoint_{date.replace('-', '')}.json"
        atm_strike = 372  # Default from our previous data
        
        if os.path.exists(checkpoint_file):
            import json
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                atm_strike = checkpoint['stats']['atm_strike']
        
        print(f"\n🔄 Comparing Filtering Methods (ATM: ${atm_strike})")
        print(f"{'Strike':<8} {'Type':<4} {'Bars':<5} {'Old Logic':<12} {'New Logic':<12} {'Match'}")
        print("-" * 70)
        
        old_kept = 0
        new_kept = 0
        both_kept = 0
        
        for strike, opt_type, bar_count, contract_id in results:
            # Old ITM/OTM logic
            if opt_type == 'C' and strike <= atm_strike:
                old_filter = "❌ ITM"
            elif opt_type == 'P' and strike >= atm_strike:
                old_filter = "❌ ITM"
            else:
                old_filter = "✅ OTM"
                old_kept += 1
            
            # New volume logic
            if bar_count >= 70:
                new_filter = "✅ VOLUME"
                new_kept += 1
            else:
                new_filter = "❌ LOW VOL"
            
            # Check if both methods agree
            old_keep = old_filter.startswith("✅")
            new_keep = new_filter.startswith("✅")
            
            if old_keep and new_keep:
                match = "✅ BOTH"
                both_kept += 1
            elif old_keep != new_keep:
                match = "⚠️  DIFF"
            else:
                match = "❌ NEITHER"
            
            print(f"${strike:<7} {opt_type:<4} {bar_count:<5} {old_filter:<12} {new_filter:<12} {match}")
        
        total = len(results)
        print(f"\n📊 Filtering Comparison:")
        print(f"   Total contracts: {total}")
        print(f"   Old method kept: {old_kept} ({old_kept/total*100:.1f}%)")
        print(f"   New method kept: {new_kept} ({new_kept/total*100:.1f}%)")
        print(f"   Both methods kept: {both_kept} ({both_kept/total*100:.1f}%)")
        
        # Show contracts where methods disagree
        disagreements = total - both_kept - (total - old_kept - new_kept + both_kept)
        if disagreements > 0:
            print(f"\n⚠️  Methods disagree on {disagreements} contracts")
            print("   This shows volume filtering captures different liquid contracts")
        
    except Exception as e:
        print(f"Error comparing filtering methods: {e}")
        return 1
    finally:
        cursor.close()
        conn.close()
    
    return 0

def test_new_volume_system():
    """Test the new volume-based filtering system"""
    print("🧪 Testing Volume-Based Filtering System\n")
    
    # First, analyze existing data
    print("1️⃣ Analyzing current data volume distribution...")
    analyze_volume_distribution("2023-01-03")
    
    print("\n" + "="*70)
    print("2️⃣ Comparing old vs new filtering methods...")
    compare_old_vs_new_filtering("2023-01-03")
    
    print("\n" + "="*70)
    print("3️⃣ Testing fresh download with volume filtering...")
    
    # Clean and re-download with new system
    print("   Cleaning existing data...")
    os.system("python3 clean_jan3_data.py")
    
    # Remove checkpoint
    checkpoint_file = "checkpoint_20230103.json"
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
        print("   Removed old checkpoint")
    
    # Download with new volume filtering
    downloader = StrikeAwareDailyDownloader(use_smart_selection=True)
    test_date = datetime(2023, 1, 3)
    
    print("   Running download with volume-based filtering...")
    result = downloader.download_day(test_date)
    
    if result['status'] == 'complete':
        print("\n✅ New system test complete!")
        print(f"   Contracts downloaded: {result['stats']['total_contracts']}")
        print(f"   Coverage: {result['stats'].get('coverage', 0):.1f}%")
        
        # Analyze the new results
        print("\n4️⃣ Final volume distribution with new system:")
        analyze_volume_distribution("2023-01-03")
    else:
        print(f"\n❌ Test failed: {result.get('errors', ['Unknown error'])}")

if __name__ == "__main__":
    test_new_volume_system()