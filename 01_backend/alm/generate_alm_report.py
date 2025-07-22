
import psycopg2
from psycopg2 import sql
from decimal import Decimal
from datetime import datetime, timedelta
import pytz

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname="options_data",
            user="postgres",
            password="theta_data_2024",
            host="localhost"
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to the database: {e}")
        return None

def get_daily_summary(cursor, summary_date):
    """Fetches the daily summary for a given date."""
    cursor.execute(
        "SELECT opening_nav_hkd, closing_nav_hkd, total_pnl_hkd, net_cash_flow_hkd FROM alm_reporting.daily_summary WHERE summary_date = %s",
        (summary_date,)
    )
    return cursor.fetchone()

def get_events_for_period(cursor, start_time, end_time):
    """Fetches all chronological events within a given time window."""
    cursor.execute(
        """
        SELECT event_timestamp, event_type, description, cash_impact_hkd, realized_pnl_hkd, ib_commission_hkd, is_assignment
        FROM alm_reporting.chronological_events 
        WHERE event_timestamp >= %s AND event_timestamp < %s
        ORDER BY event_timestamp
        """,
        (start_time, end_time)
    )
    return cursor.fetchall()

def format_hdk(amount):
    """Formats a decimal amount as HKD currency."""
    if amount is None: amount = Decimal(0)
    return f"{amount:,.2f} HKD"

def group_events(events, time_window_minutes=15):
    """Groups consecutive trading events."""
    if not events: return []
    grouped, current_group = [], [events[0]]
    for i in range(1, len(events)):
        is_trade = events[i][1] == 'Trade' and events[i-1][1] == 'Trade'
        time_diff = (events[i][0] - events[i-1][0]).total_seconds() / 60
        if is_trade and time_diff < time_window_minutes:
            current_group.append(events[i])
        else:
            grouped.append(current_group)
            current_group = [events[i]]
    grouped.append(current_group)
    return grouped

def generate_report_for_date(cursor, summary_date, previous_closing_nav):
    """Generates the final, correct report based on the manually verified logic."""
    daily_summary = get_daily_summary(cursor, summary_date)
    if not daily_summary: return previous_closing_nav

    opening_nav, closing_nav, total_pnl, net_cash_flow = daily_summary
    
    hkt = pytz.timezone('Asia/Hong_Kong')
    est = pytz.timezone('US/Eastern')

    period_start = est.localize(datetime.combine(summary_date - timedelta(days=1), datetime.min.time()) + timedelta(hours=16))
    period_end = est.localize(datetime.combine(summary_date, datetime.min.time()) + timedelta(hours=16))
    market_open_time = est.localize(datetime.combine(summary_date, datetime.min.time()) + timedelta(hours=9, minutes=30))

    print(f"--- US Trading Day: {summary_date.strftime('%A, %B %d, %Y')} (All times in HKT) ---\n")
    
    all_events = get_events_for_period(cursor, period_start, period_end)
    
    pre_market_events = [e for e in all_events if e[0] < market_open_time]
    intraday_events = [e for e in all_events if e[0] >= market_open_time]

    # 1. Start with previous day's official close
    running_nav = previous_closing_nav
    print(f"* Previous Close ({period_start.astimezone(hkt).strftime('%Y-%m-%d %H:%M:%S HKT')}):")
    print(f"    * Starting NAV: {format_hdk(running_nav)}\n")

    # 2. Process Overnight / Pre-Market Events
    if pre_market_events:
        print("  Overnight / Pre-Market Period:\n")
        for event in pre_market_events:
            ts, etype, desc, cash, pnl, comm, is_assign = event
            nav_impact = (pnl or 0) + (comm or 0)
            if etype != 'Trade': nav_impact += (cash or 0)
            running_nav += nav_impact
            print(f"* {ts.astimezone(hkt).strftime('%Y-%m-%d %H:%M:%S HKT')}: {desc}")
            if pnl is not None and pnl != 0: print(f"    * P&L Impact: {format_hdk(pnl)}")
            if comm is not None and comm != 0: print(f"    * Commissions: {format_hdk(comm)}")
            if is_assign: print(f"    * Note: Assignment has no immediate P&L impact.")
            print(f"    * NAV becomes: {format_hdk(running_nav)}\n")

    # 3. Market Open
    print(f"* Market Open ({market_open_time.astimezone(hkt).strftime('%Y-%m-%d %H:%M:%S HKT')}):")
    print(f"    * Official Opening NAV: {format_hdk(opening_nav)}")
    print(f"    * Calculated Opening NAV (after overnight events): {format_hdk(running_nav)}\n")

    # 4. Process Intraday Events
    if intraday_events:
        print("  Intraday Trading Period:\n")
        for group in group_events(intraday_events):
            if len(group) > 1:
                net_pnl = sum((e[4] or 0) + (e[5] or 0) for e in group)
                running_nav += net_pnl
                print(f"* {group[0][0].astimezone(hkt).strftime('%H:%M')} - {group[-1][0].astimezone(hkt).strftime('%H:%M HKT')}: You execute several day trades.")
                print(f"    * Net Realized P&L Impact: {format_hdk(net_pnl)}")
                print(f"    * NAV becomes: {format_hdk(running_nav)}\n")
            else:
                ts, etype, desc, cash, pnl, comm, is_assign = group[0]
                nav_impact = (pnl or 0) + (comm or 0)
                if etype != 'Trade': nav_impact += (cash or 0)
                running_nav += nav_impact
                print(f"* {ts.astimezone(hkt).strftime('%Y-%m-%d %H:%M:%S HKT')}: {desc}")
                if pnl is not None and pnl != 0: print(f"    * P&L Impact: {format_hdk(pnl)}")
                if comm is not None and comm != 0: print(f"    * Commissions: {format_hdk(comm)}")
                print(f"    * NAV becomes: {format_hdk(running_nav)}\n")

    # 5. Market Close
    print(f"* Market Close ({period_end.astimezone(hkt).strftime('%Y-%m-%d %H:%M:%S HKT')}):")
    final_calculated_nav = opening_nav + (total_pnl or 0) + (net_cash_flow or 0)
    print(f"    * Official Closing NAV: {format_hdk(closing_nav)}")
    print(f"    * Calculated Closing NAV (from daily components): {format_hdk(final_calculated_nav)}")
    discrepancy = final_calculated_nav - closing_nav
    if abs(discrepancy) > 1:
        print(f"    * Discrepancy: {format_hdk(discrepancy)}")
    print("\n" + "="*50 + "\n")
    
    return closing_nav

def main():
    """Main function to generate the ALM report."""
    conn = get_db_connection()
    if conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT summary_date FROM alm_reporting.daily_summary ORDER BY summary_date;")
            dates = [row[0] for row in cursor.fetchall()]
            
            previous_closing_nav = Decimal(0)
            if dates:
                first_day = dates[0]
                cursor.execute("SELECT closing_nav_hkd FROM alm_reporting.daily_summary WHERE summary_date = %s", (first_day - timedelta(days=1),))
                result = cursor.fetchone()
                if result:
                    previous_closing_nav = result[0]
                else: 
                    cursor.execute("SELECT opening_nav_hkd FROM alm_reporting.daily_summary WHERE summary_date = %s", (first_day,))
                    result = cursor.fetchone()
                    if result:
                        previous_closing_nav = result[0]

            for summary_date in dates:
                previous_closing_nav = generate_report_for_date(cursor, summary_date, previous_closing_nav)
        conn.close()

if __name__ == "__main__":
    main()
