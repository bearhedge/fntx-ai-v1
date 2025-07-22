#!/usr/bin/env python3
"""
Test script to verify exercise parsing from FlexQuery XML
"""
import os
import sys
import xml.etree.ElementTree as ET

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '01_backend'))

from services.ibkr_flex_query_enhanced import flex_query_enhanced


def test_exercise_parsing():
    """Test parsing of OptionEAE section"""
    print("Fetching IBKR FlexQuery report...")
    
    # Request report
    reference_code = flex_query_enhanced.request_flex_report()
    if not reference_code:
        print("Failed to request report")
        return
        
    # Wait and get XML
    import time
    time.sleep(5)
    
    xml_data = flex_query_enhanced.get_flex_report(reference_code)
    if not xml_data:
        print("Failed to get report")
        return
        
    # Parse XML
    root = ET.fromstring(xml_data)
    
    print("\n" + "="*60)
    print("OPTION EXERCISE/ASSIGNMENT ANALYSIS")
    print("="*60)
    
    # Get report date range
    stmt = root.find(".//FlexStatement")
    if stmt:
        print(f"\nReport Period: {stmt.get('fromDate')} to {stmt.get('toDate')}")
    
    # Parse OptionEAE section
    print("\nAnalyzing OptionEAE entries...")
    
    assignments = []
    expirations = []
    
    for exercise in root.findall(".//OptionEAE"):
        asset_cat = exercise.get('assetCategory', '')
        symbol = exercise.get('symbol', '')
        trans_type = exercise.get('transactionType', '')
        
        # Only process SPY options
        if asset_cat == 'OPT' and 'SPY' in symbol.upper():
            strike = exercise.get('strike')
            put_call = exercise.get('putCall')
            date = exercise.get('date')
            quantity = exercise.get('quantity')
            
            entry = {
                'symbol': symbol,
                'strike': strike,
                'type': 'PUT' if put_call == 'P' else 'CALL',
                'date': date,
                'quantity': quantity,
                'trans_type': trans_type
            }
            
            if trans_type in ['Exercise', 'Assignment']:
                assignments.append(entry)
            elif trans_type == 'Expiration':
                expirations.append(entry)
    
    # Display results
    print(f"\nFound {len(assignments)} Assignment(s):")
    for a in assignments:
        print(f"  ✅ {a['date']}: SPY {a['strike']} {a['type']} - "
              f"{a['quantity']} contract(s) {a['trans_type']}")
    
    print(f"\nFound {len(expirations)} Expiration(s) (not exercises):")
    for e in expirations:
        print(f"  ⏰ {e['date']}: SPY {e['strike']} {e['type']} - Expired worthless")
    
    # Check for stock positions from assignments
    print("\nStock positions from assignments:")
    for exercise in root.findall(".//OptionEAE"):
        if (exercise.get('assetCategory') == 'STK' and 
            exercise.get('symbol') == 'SPY' and
            exercise.get('transactionType') == 'Buy'):
            
            quantity = exercise.get('quantity')
            price = exercise.get('tradePrice')
            date = exercise.get('date')
            print(f"  📈 {date}: Received {quantity} SPY @ ${price} from assignment")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total Assignments: {len(assignments)}")
    print(f"Total Expirations: {len(expirations)}")
    
    if assignments:
        print("\n⚠️  ACTION REQUIRED: Assignments detected!")
        print("These options were exercised and you received/delivered shares.")
    else:
        print("\n✅ No assignments detected - only expirations.")


if __name__ == "__main__":
    test_exercise_parsing()