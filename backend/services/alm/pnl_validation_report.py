#!/usr/bin/env python3
"""
Comprehensive P&L validation report comparing table vs narrative calculations
"""

import psycopg2
from decimal import Decimal
from datetime import datetime

HKD_USD_RATE = Decimal('7.8472')

def format_hkd(amount):
    """Format amount as HKD"""
    return f"{amount:,.2f}"

def get_comprehensive_daily_data(cursor, date):
    """Get all data needed for both table and narrative calculations"""
    
    # Get summary data
    cursor.execute("""
        SELECT 
            opening_nav_hkd,
            closing_nav_hkd,
            total_pnl_hkd,
            net_cash_flow_hkd
        FROM alm_reporting.daily_summary
        WHERE summary_date = %s
    """, (date,))
    
    summary = cursor.fetchone()
    if not summary:
        return None
    
    data = {
        'date': date,
        'opening_nav': Decimal(str(summary[0])),
        'closing_nav': Decimal(str(summary[1])),
        'gross_pnl_from_nav': Decimal(str(summary[2])),  # This is from NAV file
        'net_cash_flow': Decimal(str(summary[3]))
    }
    
    # Get deposits before market open
    cursor.execute("""
        SELECT COALESCE(SUM(cash_impact_hkd), 0) as deposits_before_open
        FROM alm_reporting.chronological_events
        WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = %s
        AND event_type = 'Deposits/Withdrawals'
        AND cash_impact_hkd > 0
        AND EXTRACT(HOUR FROM event_timestamp AT TIME ZONE 'US/Eastern') < 9.5
    """, (date,))
    
    data['deposits_before_open'] = Decimal(str(cursor.fetchone()[0]))
    
    # Get commissions
    cursor.execute("""
        SELECT COALESCE(SUM(ib_commission_hkd), 0) as commission_total
        FROM alm_reporting.chronological_events
        WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = %s
    """, (date,))
    
    data['commission_total'] = Decimal(str(cursor.fetchone()[0]))
    
    # Get realized P&L from trades
    cursor.execute("""
        SELECT COALESCE(SUM(realized_pnl_hkd), 0) as realized_pnl
        FROM alm_reporting.chronological_events
        WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = %s
        AND event_type = 'Trade'
    """, (date,))
    
    data['realized_pnl_trades'] = Decimal(str(cursor.fetchone()[0]))
    
    # Calculate values
    data['adjusted_opening_nav'] = data['opening_nav'] + data['deposits_before_open']
    data['net_pnl'] = data['gross_pnl_from_nav'] - data['commission_total']
    
    # Table calculation (what's shown in summary table)
    # The table appears to show: gross P&L / opening NAV
    data['table_return_pct'] = (data['gross_pnl_from_nav'] / data['opening_nav'] * 100) if data['opening_nav'] != 0 else 0
    
    # Narrative calculation (what should be shown in daily narratives)
    # Should be: net P&L / adjusted NAV (if deposits before open) or opening NAV
    if data['deposits_before_open'] > 0:
        data['narrative_return_pct'] = (data['net_pnl'] / data['adjusted_opening_nav'] * 100) if data['adjusted_opening_nav'] != 0 else 0
        data['nav_base_used'] = 'Adjusted NAV'
    else:
        data['narrative_return_pct'] = (data['net_pnl'] / data['opening_nav'] * 100) if data['opening_nav'] != 0 else 0
        data['nav_base_used'] = 'Opening NAV'
    
    # What the corrected table should show
    data['correct_return_pct'] = data['narrative_return_pct']
    
    return data

def main():
    """Generate comprehensive validation report"""
    
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="options_data",
        user="postgres",
        password="theta_data_2024"
    )
    
    try:
        with conn.cursor() as cursor:
            # Get all dates
            cursor.execute("""
                SELECT DISTINCT summary_date 
                FROM alm_reporting.daily_summary 
                ORDER BY summary_date
            """)
            
            dates = [row[0] for row in cursor.fetchall()]
            
            print("=== P&L VALIDATION REPORT ===\n")
            print("This report validates that daily returns are calculated correctly.")
            print("Correct formula: Net P&L / (Adjusted NAV if deposits before market open, else Opening NAV)\n")
            
            print("Date       | Opening NAV | Deposits | Adj NAV    | Gross P&L | Commission | Net P&L   | Table % | Correct % | Diff")
            print("-" * 110)
            
            discrepancies = []
            
            for date in dates:
                data = get_comprehensive_daily_data(cursor, date)
                if not data:
                    continue
                
                diff = data['table_return_pct'] - data['correct_return_pct']
                
                # Format the row
                print(f"{date} | {format_hkd(data['opening_nav']):>11} | {format_hkd(data['deposits_before_open']):>8} | "
                      f"{format_hkd(data['adjusted_opening_nav']):>10} | {format_hkd(data['gross_pnl_from_nav']):>9} | "
                      f"{format_hkd(data['commission_total']):>10} | {format_hkd(data['net_pnl']):>9} | "
                      f"{data['table_return_pct']:>6.2f}% | {data['correct_return_pct']:>8.2f}% | "
                      f"{diff:>5.2f}%")
                
                if abs(diff) > 0.01:
                    discrepancies.append(data)
            
            # Detailed analysis of discrepancies
            if discrepancies:
                print(f"\n\n=== DISCREPANCIES FOUND: {len(discrepancies)} days ===\n")
                
                for data in discrepancies:
                    print(f"\n{data['date']}:")
                    print(f"  Opening NAV: {format_hkd(data['opening_nav'])} HKD")
                    if data['deposits_before_open'] > 0:
                        print(f"  Deposits before market open: {format_hkd(data['deposits_before_open'])} HKD")
                        print(f"  Adjusted Opening NAV: {format_hkd(data['adjusted_opening_nav'])} HKD")
                    print(f"  Gross P&L (from NAV): {format_hkd(data['gross_pnl_from_nav'])} HKD")
                    print(f"  Commissions: {format_hkd(data['commission_total'])} HKD")
                    print(f"  Net P&L: {format_hkd(data['net_pnl'])} HKD")
                    print(f"\n  Table shows: {data['gross_pnl_from_nav']:,.2f} / {data['opening_nav']:,.2f} = {data['table_return_pct']:.2f}%")
                    print(f"  Should show: {data['net_pnl']:,.2f} / {data['adjusted_opening_nav'] if data['deposits_before_open'] > 0 else data['opening_nav']:,.2f} = {data['correct_return_pct']:.2f}%")
                    print(f"  Difference: {data['table_return_pct'] - data['correct_return_pct']:.2f}%")
            else:
                print("\n\nNo discrepancies found! All calculations are consistent.")
            
            # Special focus on July 28th
            print("\n\n=== JULY 28TH DETAILED ANALYSIS ===")
            july_28_data = get_comprehensive_daily_data(cursor, datetime(2025, 7, 28).date())
            
            if july_28_data:
                print(f"\nValues from backend.data.database:")
                print(f"  Opening NAV: {format_hkd(july_28_data['opening_nav'])} HKD")
                print(f"  Deposit before market open: {format_hkd(july_28_data['deposits_before_open'])} HKD")
                print(f"  Adjusted Opening NAV: {format_hkd(july_28_data['adjusted_opening_nav'])} HKD")
                print(f"  Gross P&L: {format_hkd(july_28_data['gross_pnl_from_nav'])} HKD")
                print(f"  Commissions: {format_hkd(july_28_data['commission_total'])} HKD")
                print(f"  Net P&L: {format_hkd(july_28_data['net_pnl'])} HKD")
                
                print(f"\nCalculations:")
                print(f"  Table currently shows: {july_28_data['table_return_pct']:.2f}%")
                print(f"    = Gross P&L / Opening NAV")
                print(f"    = {july_28_data['gross_pnl_from_nav']:,.2f} / {july_28_data['opening_nav']:,.2f}")
                print(f"    = {july_28_data['table_return_pct']:.4f}%")
                
                print(f"\n  Should show: {july_28_data['correct_return_pct']:.2f}%")
                print(f"    = Net P&L / Adjusted NAV (because of deposit before open)")
                print(f"    = {july_28_data['net_pnl']:,.2f} / {july_28_data['adjusted_opening_nav']:,.2f}")
                print(f"    = {july_28_data['correct_return_pct']:.4f}%")
                
                # Using exact values from the verify script
                print(f"\n  Verification using exact values:")
                gross_pnl = Decimal('463.29')
                commissions = Decimal('31.22')
                net_pnl = gross_pnl - commissions
                original_nav = Decimal('79299.20')
                deposit = Decimal('119945.00')
                adjusted_nav = original_nav + deposit
                
                print(f"    Net P&L = {gross_pnl} - {commissions} = {net_pnl}")
                print(f"    Adjusted NAV = {original_nav} + {deposit} = {adjusted_nav}")
                print(f"    Return = {net_pnl} / {adjusted_nav} = {(net_pnl/adjusted_nav*100):.4f}%")
                print(f"    Rounded to 2 decimals = {(net_pnl/adjusted_nav*100):.2f}%")
                
    finally:
        conn.close()

if __name__ == "__main__":
    main()