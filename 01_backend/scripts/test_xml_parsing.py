#!/usr/bin/env python3
"""Test XML parsing with sample data"""
import xml.etree.ElementTree as ET

# Sample XML data (just the OptionEAE section)
sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse>
<FlexStatements>
<FlexStatement>
<OptionEAE>
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250715P00622000" description="SPY 15JUL25 622 P" strike="622" expiry="20250715" putCall="P" date="20250715" transactionType="Assignment" quantity="1" tradePrice="0" />
<OptionEAE accountId="U19860056" assetCategory="STK" symbol="SPY" description="SPDR S&amp;P 500 ETF TRUST" date="20250715" transactionType="Buy" quantity="100" tradePrice="622" />
<OptionEAE accountId="U19860056" assetCategory="OPT" symbol="SPY   250716P00620000" description="SPY 16JUL25 620 P" strike="620" expiry="20250716" putCall="P" date="20250716" transactionType="Expiration" quantity="1" tradePrice="0" />
</OptionEAE>
</FlexStatement>
</FlexStatements>
</FlexQueryResponse>"""

def test_parsing():
    """Test parsing logic"""
    root = ET.fromstring(sample_xml)
    
    print("Testing OptionEAE parsing...")
    print("="*60)
    
    assignments = []
    expirations = []
    stock_buys = []
    
    for exercise in root.findall(".//OptionEAE"):
        asset_cat = exercise.get('assetCategory', '')
        symbol = exercise.get('symbol', '')
        trans_type = exercise.get('transactionType', '')
        
        print(f"\nProcessing: {asset_cat} - {symbol[:20]}... - {trans_type}")
        
        if asset_cat == 'OPT' and 'SPY' in symbol.upper():
            if trans_type in ['Exercise', 'Assignment']:
                strike = exercise.get('strike')
                put_call = exercise.get('putCall')
                date = exercise.get('date')
                print(f"  ✅ ASSIGNMENT: SPY {strike}{put_call} on {date}")
                assignments.append(exercise)
            elif trans_type == 'Expiration':
                strike = exercise.get('strike')
                put_call = exercise.get('putCall')
                date = exercise.get('date')
                print(f"  ⏰ EXPIRATION: SPY {strike}{put_call} on {date}")
                expirations.append(exercise)
                
        elif asset_cat == 'STK' and symbol == 'SPY' and trans_type == 'Buy':
            quantity = exercise.get('quantity')
            price = exercise.get('tradePrice')
            date = exercise.get('date')
            print(f"  📈 STOCK BUY: {quantity} SPY @ ${price} on {date}")
            stock_buys.append(exercise)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Assignments found: {len(assignments)}")
    print(f"Expirations found: {len(expirations)}")
    print(f"Stock buys from assignment: {len(stock_buys)}")
    
    if assignments:
        print("\n✅ Correct! Found the 622P assignment on 2025-07-15")
    else:
        print("\n❌ Error: Did not find the assignment")

if __name__ == "__main__":
    test_parsing()