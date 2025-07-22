
import pandas as pd
from sqlalchemy import create_engine, text
import logging
import argparse
from datetime import datetime, time, timedelta
import pytz

# --- Configuration ---
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

DATABASE_URL = "postgresql://postgres:theta_data_2024@localhost:5432/options_data"
US_EASTERN = pytz.timezone('US/Eastern')
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)

def get_trading_phase(timestamp_utc):
    ts_eastern = timestamp_utc.astimezone(US_EASTERN)
    ts_time = ts_eastern.time()
    if ts_time < MARKET_OPEN: return "Pre-Market"
    if MARKET_OPEN <= ts_time <= MARKET_CLOSE: return "Market Hours"
    return "After-Hours"

def generate_narrative(db_url: str, period: str):
    engine = create_engine(db_url)
    with engine.connect() as connection:
        today = datetime.now().date()
        if period == 'MTD': start_date = today.replace(day=1)
        else: start_date = today - timedelta(days=10)
        end_date = today + timedelta(days=1)

        events_df = pd.read_sql(text("""
            SELECT * FROM alm_reporting.chronological_events
            WHERE event_timestamp >= :start AND event_timestamp < :end
            ORDER BY event_timestamp ASC;
        """), connection, params={'start': start_date, 'end': end_date})
        
        summary_df = pd.read_sql(text("""
            SELECT * FROM alm_reporting.daily_summary
            WHERE summary_date >= :start AND summary_date < :end
            ORDER BY summary_date ASC;
        """), connection, params={'start': start_date, 'end': end_date})

    print("\n" + "="*80 + "\nDETAILED TRADING NARRATIVE\n" + "="*80)
    if events_df.empty:
        print("\nNo detailed events found for the period.")
        return

    events_df['event_timestamp'] = pd.to_datetime(events_df['event_timestamp'])
    if events_df['event_timestamp'].dt.tz is None:
        events_df['event_timestamp'] = events_df['event_timestamp'].dt.tz_localize('UTC')
    
    for date, day_events in events_df.groupby(events_df['event_timestamp'].dt.date):
        day_summary = summary_df[summary_df['summary_date'] == date]
        opening_nav = day_summary['opening_nav_hkd'].iloc[0] if not day_summary.empty else 0
        
        print(f"\n** TRADING DAY: {date.strftime('%A, %B %d, %Y').upper()} **")
        print(f"Opening NAV: {opening_nav:,.2f} HKD")

        day_events['phase'] = day_events['event_timestamp'].apply(get_trading_phase)
        for phase, phase_events in day_events.groupby('phase'):
            print(f"\n--- {phase} ---")
            for _, event in phase_events.iterrows():
                ts_eastern = event['event_timestamp'].astimezone(US_EASTERN)
                print(f"\n  {ts_eastern.strftime('%I:%M:%S %p EDT')}: {event['description']}")
                if event['cash_impact_hkd'] != 0:
                    print(f"    Cash Impact: {event['cash_impact_hkd']:+,.2f} HKD")
                if event['realized_pnl_hkd'] != 0:
                    print(f"    Realized P&L: {event['realized_pnl_hkd']:+,.2f} HKD")
                print(f"    NAV After: {event['nav_after_event_hkd']:,.2f} HKD")

        if not day_summary.empty:
            print(f"\n--- End of Day Summary ---")
            print(f"Closing NAV: {day_summary.iloc[0]['closing_nav_hkd']:,.2f} HKD")
            print(f"Daily P&L: {day_summary.iloc[0]['total_pnl_hkd']:+,.2f} HKD")
            print(f"Net Cash Flow: {day_summary.iloc[0]['net_cash_flow_hkd']:+,.2f} HKD")
        print("\n" + "-"*60)

    print("\n" + "="*80 + f"\nPERIOD SUMMARY ({period})\n" + "="*80)
    if not summary_df.empty:
        summary_df.rename(columns={'summary_date': 'Date', 'opening_nav_hkd': 'Opening NAV', 'closing_nav_hkd': 'Closing NAV', 'total_pnl_hkd': 'Daily P&L', 'net_cash_flow_hkd': 'Cash Flow'}, inplace=True)
        summary_df['Date'] = pd.to_datetime(summary_df['Date']).dt.strftime('%Y-%m-%d')
        for col in ['Opening NAV', 'Closing NAV', 'Daily P&L', 'Cash Flow']:
            summary_df[col] = summary_df[col].map(lambda x: f"{x:,.2f}")
        print(summary_df.to_string(index=False))

        total_pnl = pd.to_numeric(summary_df['Daily P&L'].str.replace(',', '')).sum()
        first_nav = pd.to_numeric(summary_df['Opening NAV'].iloc[0].replace(',', ''))
        last_nav = pd.to_numeric(summary_df['Closing NAV'].iloc[-1].replace(',', ''))
        print(f"\nPeriod Total P&L: {total_pnl:+,.2f} HKD")
        print(f"Period NAV Change: {last_nav - first_nav:+,.2f} HKD ({first_nav:,.2f} -> {last_nav:,.2f})")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate ALM Narrative Report.')
    parser.add_argument('--period', type=str, default='MTD', help='Reporting period (e.g., MTD, Last 10 Days)')
    generate_narrative(DATABASE_URL, parser.parse_args().period)
