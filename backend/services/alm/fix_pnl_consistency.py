#!/usr/bin/env python3
"""
Fix to ensure P&L calculations are consistent between table and narrative
The key issue is that we should always use the NAV file's P&L as the source of truth
"""

import psycopg2
from decimal import Decimal

def analyze_pnl_sources():
    """Analyze different P&L sources to understand discrepancies"""
    
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="options_data",
        user="postgres",
        password="theta_data_2024"
    )
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    s.summary_date,
                    s.opening_nav_hkd,
                    s.total_pnl_hkd as nav_file_pnl,
                    COALESCE(t.trades_realized_pnl, 0) as trades_realized_pnl,
                    COALESCE(c.total_commissions, 0) as total_commissions,
                    s.total_pnl_hkd - COALESCE(c.total_commissions, 0) as net_pnl,
                    COALESCE(d.deposits_before_open, 0) as deposits_before_open
                FROM alm_reporting.daily_summary s
                LEFT JOIN (
                    SELECT 
                        DATE(event_timestamp AT TIME ZONE 'US/Eastern') as date,
                        SUM(realized_pnl_hkd) as trades_realized_pnl
                    FROM alm_reporting.chronological_events
                    WHERE event_type = 'Trade'
                    GROUP BY DATE(event_timestamp AT TIME ZONE 'US/Eastern')
                ) t ON s.summary_date = t.date
                LEFT JOIN (
                    SELECT 
                        DATE(event_timestamp AT TIME ZONE 'US/Eastern') as date,
                        SUM(ib_commission_hkd) as total_commissions
                    FROM alm_reporting.chronological_events
                    GROUP BY DATE(event_timestamp AT TIME ZONE 'US/Eastern')
                ) c ON s.summary_date = c.date
                LEFT JOIN (
                    SELECT 
                        DATE(event_timestamp AT TIME ZONE 'US/Eastern') as date,
                        SUM(cash_impact_hkd) as deposits_before_open
                    FROM alm_reporting.chronological_events
                    WHERE event_type = 'Deposits/Withdrawals'
                    AND cash_impact_hkd > 0
                    AND EXTRACT(HOUR FROM event_timestamp AT TIME ZONE 'US/Eastern') < 9.5
                    GROUP BY DATE(event_timestamp AT TIME ZONE 'US/Eastern')
                ) d ON s.summary_date = d.date
                ORDER BY s.summary_date
            """)
            
            results = cursor.fetchall()
            
            print("=== P&L SOURCE ANALYSIS ===\n")
            print("Date       | NAV File P&L | Trades P&L | Commissions | Difference | Deposits | Return Formula")
            print("-" * 100)
            
            for row in results:
                date = row[0]
                opening_nav = Decimal(str(row[1]))
                nav_pnl = Decimal(str(row[2]))
                trades_pnl = Decimal(str(row[3]))
                commissions = Decimal(str(row[4]))
                net_pnl = Decimal(str(row[5]))
                deposits = Decimal(str(row[6]))
                
                diff = trades_pnl - nav_pnl
                
                # Calculate return
                if deposits > 0:
                    adjusted_nav = opening_nav + deposits
                    return_pct = (net_pnl / adjusted_nav * 100) if adjusted_nav != 0 else 0
                    formula = f"{net_pnl:.2f}/{adjusted_nav:.2f}"
                else:
                    return_pct = (net_pnl / opening_nav * 100) if opening_nav != 0 else 0
                    formula = f"{net_pnl:.2f}/{opening_nav:.2f}"
                
                print(f"{date} | {nav_pnl:>12,.2f} | {trades_pnl:>10,.2f} | {commissions:>11,.2f} | "
                      f"{diff:>10,.2f} | {deposits:>8,.0f} | {formula} = {return_pct:.2f}%")
                
                if date.strftime('%Y-%m-%d') == '2025-07-28':
                    print("\n  July 28th Analysis:")
                    print(f"    NAV file reports P&L: {nav_pnl:.2f}")
                    print(f"    Trades show P&L: {trades_pnl:.2f}")
                    print(f"    Difference: {diff:.2f}")
                    print(f"    Commissions: {commissions:.2f}")
                    print(f"    The NAV file P&L should be used as the authoritative source")
                    print(f"    Net P&L = {nav_pnl:.2f} - {abs(commissions):.2f} = {net_pnl:.2f}")
                    print(f"    Return = {net_pnl:.2f} / {adjusted_nav:.2f} = {return_pct:.2f}%")
            
    finally:
        conn.close()

def fix_narrative_calculation():
    """
    The fix is to ensure the narrative uses the same calculation as the table:
    - Use NAV file P&L (not sum of trades)
    - Subtract commissions to get net P&L
    - Divide by adjusted NAV if deposits before market open
    """
    
    print("\n\n=== FIX RECOMMENDATION ===")
    print("\nThe issue is that the narrative might be using realized P&L from trades")
    print("instead of the NAV file's P&L value.")
    print("\nTo fix:")
    print("1. Always use daily_summary.total_pnl_hkd as the gross P&L")
    print("2. Subtract commissions to get net P&L")
    print("3. Use adjusted NAV when deposits occur before market open")
    print("\nThis ensures both table and narrative use the same values and formula.")

if __name__ == "__main__":
    analyze_pnl_sources()
    fix_narrative_calculation()