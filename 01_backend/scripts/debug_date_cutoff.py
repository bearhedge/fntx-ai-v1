#!/usr/bin/env python3
"""
Debug script to investigate why terminal UI only shows events up to July 14
when the XML data contains events through July 18
"""

import xml.etree.ElementTree as ET
from datetime import datetime

# Sample XML data from the user (containing events through July 18)
sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse>
<FlexStatements>
<FlexStatement accountId="U19860056" fromDate="20250701" toDate="20250717" whenGenerated="20250718;123456">
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250714P00616000" description="SPY 14JUL25 616 P" strike="616" expiry="20250714" putCall="P" date="20250714" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250714C00621000" description="SPY 14JUL25 621 C" strike="621" expiry="20250714" putCall="C" date="20250714" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250715P00622000" description="SPY 15JUL25 622 P" strike="622" expiry="20250715" putCall="P" date="20250715" transactionType="Assignment" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="STK" symbol="SPY" description="SPDR S&amp;P 500 ETF TRUST" date="20250715" transactionType="Buy" quantity="100" tradePrice="622" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250715C00624000" description="SPY 15JUL25 624 C" strike="624" expiry="20250715" putCall="C" date="20250715" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250716P00620000" description="SPY 16JUL25 620 P" strike="620" expiry="20250716" putCall="P" date="20250716" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250716C00626000" description="SPY 16JUL25 626 C" strike="626" expiry="20250716" putCall="C" date="20250716" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250717P00624000" description="SPY 17JUL25 624 P" strike="624" expiry="20250717" putCall="P" date="20250717" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250717C00628000" description="SPY 17JUL25 628 C" strike="628" expiry="20250717" putCall="C" date="20250717" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250718P00626000" description="SPY 18JUL25 626 P" strike="626" expiry="20250718" putCall="P" date="20250718" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250718C00628000" description="SPY 18JUL25 628 C" strike="628" expiry="20250718" putCall="C" date="20250718" transactionType="Expiration" quantity="1" tradePrice="0" />
</FlexStatement>
</FlexStatements>
</FlexQueryResponse>"""

def simulate_terminal_ui_parsing():
    """Simulate the exact parsing logic from run_terminal_ui.py"""
    print("DEBUG: Simulating terminal UI parsing logic")
    print("=" * 80)
    
    try:
        root = ET.fromstring(sample_xml)
        
        # Check report date range
        print("\nChecking FlexQuery date range:")
        for elem in root.iter():
            if elem.tag == 'FlexStatement':
                from_date = elem.get('fromDate', 'N/A')
                to_date = elem.get('toDate', 'N/A')
                account_id = elem.get('accountId', 'N/A')
                when_generated = elem.get('whenGenerated', 'N/A')
                print(f"  Report covers: {from_date} to {to_date}")
                print(f"  Account ID: {account_id}")
                print(f"  Generated at: {when_generated}")
                break
        
        # Parse exercises exactly like terminal UI
        exercises_found = []
        
        print("\n  Processing SPY Options:")
        for exercise in root.findall(".//OptionEAE"):
            asset_cat = exercise.get('assetCategory', '')
            symbol = exercise.get('symbol', '')
            
            # Skip non-SPY options
            if not (asset_cat == 'OPT' and 'SPY' in symbol.upper()):
                continue
            
            strike = exercise.get('strike')
            put_call = exercise.get('putCall', '')
            date = exercise.get('date')
            trans_type = exercise.get('transactionType')
            quantity = exercise.get('quantity', '0')
            
            # Include exercises, assignments AND expirations
            if trans_type in ['Exercise', 'Assignment', 'Expiration']:
                symbol_short = f"{strike}{put_call[0] if put_call else ''}"
                exercises_found.append({
                    'symbol': symbol_short,
                    'date': date,
                    'type': trans_type,
                    'quantity': int(quantity)
                })
        
        print(f"\nFound {len(exercises_found)} events")
        
        # Group by date for display
        by_date = {}
        for ex in exercises_found:
            date = ex['date']
            if date not in by_date:
                by_date[date] = {'assignments': [], 'expirations': [], 'exercises': [], 'pending': []}
            
            if ex['type'] == 'Assignment':
                by_date[date]['assignments'].append(ex['symbol'])
            elif ex['type'] == 'Expiration':
                by_date[date]['expirations'].append(ex['symbol'])
            elif ex['type'] == 'Exercise':
                by_date[date]['exercises'].append(ex['symbol'])
            else:
                by_date[date]['pending'].append(ex['symbol'])
        
        # Display summary table
        print("\n  ┌────────────┬───────────────────────────────────┐")
        print("  │    Date    │         Option Events             │")
        print("  ├────────────┼───────────────────────────────────┤")
        
        # Debug: show all dates before sorting
        print(f"\nDEBUG: All dates found: {list(by_date.keys())}")
        print(f"DEBUG: Sorted dates: {sorted(by_date.keys())}")
        
        for date in sorted(by_date.keys()):
            events = by_date[date]
            event_strs = []
            
            if events['assignments']:
                event_strs.append(f"✅ ASSIGN: {', '.join(events['assignments'])}")
            
            if events['expirations']:
                event_strs.append(f"⏰ EXPIRE: {', '.join(events['expirations'])}")
            
            if events['exercises']:
                event_strs.append(f"🏃 EXERCISE: {', '.join(events['exercises'])}")
            
            if events['pending']:
                event_strs.append(f"⚠️  PENDING: {', '.join(events['pending'])}")
            
            # Format date as MM/DD
            date_formatted = f"{date[4:6]}/{date[6:8]}"
            event_str = ', '.join(event_strs) if event_strs else "No events"
            
            # Truncate if too long
            if len(event_str) > 33:
                event_str = event_str[:30] + "..."
            
            print(f"  │ {date_formatted:^10} │ {event_str:<33} │")
        
        print("  └────────────┴───────────────────────────────────┘")
        
        # Summary counts
        total_assignments = sum(len(ex['assignments']) for ex in by_date.values())
        total_expirations = sum(len(ex['expirations']) for ex in by_date.values())
        total_exercises = sum(len(ex['exercises']) for ex in by_date.values())
        total_pending = sum(len(ex['pending']) for ex in by_date.values())
        
        print(f"\n  Summary: {total_assignments} assignments, {total_expirations} expirations, "
              f"{total_exercises} exercises, {total_pending} pending")
        
        # Additional debug: check if any dates are being filtered
        print("\n" + "=" * 80)
        print("DEBUG ANALYSIS:")
        print(f"1. Total events parsed: {len(exercises_found)}")
        print(f"2. Unique dates: {len(by_date)}")
        print(f"3. Date range in data: {min(by_date.keys())} to {max(by_date.keys())}")
        
        # Check for potential date parsing issues
        for ex in exercises_found:
            date_str = ex['date']
            try:
                # Try to parse as YYYYMMDD
                parsed_date = datetime.strptime(date_str, '%Y%m%d')
                if parsed_date.year != 2025 or parsed_date.month != 7:
                    print(f"WARNING: Unexpected date found: {date_str} -> {parsed_date}")
            except ValueError:
                print(f"ERROR: Could not parse date: {date_str}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simulate_terminal_ui_parsing()