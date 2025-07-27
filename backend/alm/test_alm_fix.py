#!/usr/bin/env python3
"""
Test script to verify ALM currency conversion fix
"""
import sys
import os
import logging
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alm.build_alm_data import build_alm_data, get_starting_nav, parse_all_events, HKD_USD_RATE

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_alm_fix():
    """Test the ALM data build with currency conversion fix"""
    
    # First, let's check what the starting NAV is
    try:
        starting_nav = get_starting_nav()
        print(f"\nStarting NAV: {starting_nav:.2f} HKD")
        print(f"Exchange rate: 1 USD = {HKD_USD_RATE} HKD")
        
        # Parse events to see the conversions
        events = parse_all_events()
        print(f"\nTotal events parsed: {len(events)}")
        
        # Show first few events with significant cash impact
        print("\nFirst few events with cash impact:")
        count = 0
        for event in events:
            if abs(event['cash_impact']) > 100:  # Show significant transactions
                print(f"\n{event['timestamp']} - {event['type']}")
                print(f"  Description: {event['description']}")
                print(f"  Cash impact: {event['cash_impact']:.2f} HKD")
                print(f"  PnL impact: {event['pnl_impact']:.2f} HKD")
                count += 1
                if count >= 5:
                    break
        
        # Calculate expected NAV after all events
        nav = starting_nav
        for event in events:
            nav = nav + event['cash_impact'] + event['pnl_impact']
        
        print(f"\nExpected final NAV after all events: {nav:.2f} HKD")
        
        # Now let's check the database results
        DATABASE_URL = "postgresql://postgres:theta_data_2024@localhost:5432/options_data"
        engine = create_engine(DATABASE_URL)
        
        print("\n" + "="*50)
        print("Running full ALM data build...")
        print("="*50)
        
        # Run the build
        build_alm_data(DATABASE_URL)
        
        # Query the results
        with engine.connect() as conn:
            # Check chronological events
            result = conn.execute(text("""
                SELECT 
                    event_timestamp,
                    event_type,
                    description,
                    cash_impact_hkd,
                    realized_pnl_hkd,
                    nav_after_event_hkd
                FROM alm_reporting.chronological_events
                ORDER BY event_timestamp
                LIMIT 10
            """))
            
            print("\nFirst 10 events in database:")
            for row in result:
                print(f"\n{row[0]} - {row[1]}")
                print(f"  {row[2]}")
                print(f"  Cash: {row[3]:.2f} HKD, PnL: {row[4]:.2f} HKD")
                print(f"  NAV after: {row[5]:.2f} HKD")
            
            # Check daily summary
            result = conn.execute(text("""
                SELECT 
                    summary_date,
                    opening_nav_hkd,
                    closing_nav_hkd,
                    total_pnl_hkd,
                    net_cash_flow_hkd
                FROM alm_reporting.daily_summary
                ORDER BY summary_date
            """))
            
            print("\n" + "="*50)
            print("Daily Summary:")
            print("="*50)
            for row in result:
                print(f"\nDate: {row[0]}")
                print(f"  Opening NAV: {row[1]:,.2f} HKD")
                print(f"  Closing NAV: {row[2]:,.2f} HKD")
                print(f"  Total PnL: {row[3]:,.2f} HKD")
                print(f"  Net Cash Flow: {row[4]:,.2f} HKD")
                print(f"  Change: {row[2] - row[1]:,.2f} HKD")
        
    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_alm_fix()