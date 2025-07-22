#!/usr/bin/env python3
"""Parse ALL OptionEAE entries from the user-provided XML"""
import xml.etree.ElementTree as ET

# The full XML provided by the user (from their correction message)
user_xml = """<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250714P00616000" description="SPY 14JUL25 616 P" strike="616" expiry="20250714" putCall="P" date="20250714" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250714C00621000" description="SPY 14JUL25 621 C" strike="621" expiry="20250714" putCall="C" date="20250714" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250715P00622000" description="SPY 15JUL25 622 P" strike="622" expiry="20250715" putCall="P" date="20250715" transactionType="Assignment" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="STK" symbol="SPY" description="SPDR S&amp;P 500 ETF TRUST" date="20250715" transactionType="Buy" quantity="100" tradePrice="622" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250715C00624000" description="SPY 15JUL25 624 C" strike="624" expiry="20250715" putCall="C" date="20250715" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250716P00620000" description="SPY 16JUL25 620 P" strike="620" expiry="20250716" putCall="P" date="20250716" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250716C00626000" description="SPY 16JUL25 626 C" strike="626" expiry="20250716" putCall="C" date="20250716" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250717P00624000" description="SPY 17JUL25 624 P" strike="624" expiry="20250717" putCall="P" date="20250717" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250717C00628000" description="SPY 17JUL25 628 C" strike="628" expiry="20250717" putCall="C" date="20250717" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250718P00626000" description="SPY 18JUL25 626 P" strike="626" expiry="20250718" putCall="P" date="20250718" transactionType="Expiration" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250718C00628000" description="SPY 18JUL25 628 C" strike="628" expiry="20250718" putCall="C" date="20250718" transactionType="Expiration" quantity="1" tradePrice="0" />"""

# Wrap in proper XML structure
full_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse>
<FlexStatements>
<FlexStatement>
<OptionEAE>
{user_xml}
</OptionEAE>
</FlexStatement>
</FlexStatements>
</FlexQueryResponse>"""

def analyze_all_entries():
    """Analyze all OptionEAE entries"""
    root = ET.fromstring(full_xml)
    
    print("FULL ANALYSIS OF OPTIONAE ENTRIES")
    print("="*60)
    
    assignments = []
    expirations = []
    stock_buys = []
    
    # Group by date
    by_date = {}
    
    for i, exercise in enumerate(root.findall(".//OptionEAE"), 1):
        asset_cat = exercise.get('assetCategory', '')
        symbol = exercise.get('symbol', '')
        trans_type = exercise.get('transactionType', '')
        date = exercise.get('date', '')
        
        if date not in by_date:
            by_date[date] = []
        
        if asset_cat == 'OPT' and 'SPY' in symbol.upper():
            strike = exercise.get('strike')
            put_call = exercise.get('putCall')
            
            entry = {
                'strike': strike,
                'type': 'PUT' if put_call == 'P' else 'CALL',
                'trans_type': trans_type,
                'symbol': f"{strike}{put_call}"
            }
            
            by_date[date].append(entry)
            
            if trans_type == 'Assignment':
                assignments.append((date, entry))
            elif trans_type == 'Expiration':
                expirations.append((date, entry))
                
        elif asset_cat == 'STK' and symbol == 'SPY':
            quantity = exercise.get('quantity')
            price = exercise.get('tradePrice')
            stock_buys.append((date, f"{quantity} SPY @ ${price}"))
            by_date[date].append({'type': 'STOCK', 'details': f"Buy {quantity} @ ${price}"})
    
    # Display by date
    for date in sorted(by_date.keys()):
        print(f"\n{date}:")
        for entry in by_date[date]:
            if entry.get('trans_type') == 'Assignment':
                print(f"  ✅ ASSIGNMENT: SPY {entry['strike']} {entry['type']}")
            elif entry.get('trans_type') == 'Expiration':
                print(f"  ⏰ EXPIRATION: SPY {entry['strike']} {entry['type']}")
            elif entry.get('type') == 'STOCK':
                print(f"  📈 STOCK BUY: {entry['details']}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total Assignments: {len(assignments)}")
    print(f"Total Expirations: {len(expirations)}")
    print(f"Total Entries: {len(assignments) + len(expirations) + len(stock_buys)}")
    
    # Assignments detail
    if assignments:
        print(f"\n✅ ASSIGNMENTS ({len(assignments)}):")
        for date, a in assignments:
            print(f"  - {date}: SPY {a['strike']} {a['type']}")
    
    # Expirations detail  
    print(f"\n⏰ EXPIRATIONS ({len(expirations)}):")
    for date, e in expirations:
        print(f"  - {date}: SPY {e['strike']} {e['type']}")

if __name__ == "__main__":
    analyze_all_entries()