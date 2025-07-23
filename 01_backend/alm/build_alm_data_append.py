import pandas as pd
from sqlalchemy import create_engine, text
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime
import argparse

# --- Configuration ---
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
DATABASE_URL = "postgresql://postgres:theta_data_2024@localhost:5432/options_data"
DATA_DIR = "/home/info/fntx-ai-v1/04_data"
HKD_USD_RATE = 7.8472

def get_newest_xml_files(directory, file_type_prefix):
    """Finds the most recent XML file for a given type."""
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.startswith(file_type_prefix) and f.endswith(".xml")]
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def parse_and_insert_data(db_url: str, append: bool):
    """Parses financial data from the latest XML files and inserts into the database."""
    engine = create_engine(db_url)
    
    if not append:
        logging.warning("Running in non-append mode. This will clear existing data.")
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("TRUNCATE TABLE alm_reporting.chronological_events, alm_reporting.daily_summary RESTART IDENTITY;"))

    # Define file prefixes
    file_prefixes = {
        "Trades": "Trades_",
        "Cash_Transactions": "Cash_Transactions_",
        "NAV": "NAV_"
    }

    # Get latest files
    trade_file = get_newest_xml_files(DATA_DIR, file_prefixes["Trades"])
    cash_file = get_newest_xml_files(DATA_DIR, file_prefixes["Cash_Transactions"])
    nav_file = get_newest_xml_files(DATA_DIR, file_prefixes["NAV"])

    if not all([trade_file, cash_file, nav_file]):
        logging.error("One or more required XML files are missing. Aborting.")
        return

    logging.info(f"Processing trade file: {trade_file}")
    logging.info(f"Processing cash transaction file: {cash_file}")
    logging.info(f"Processing NAV file: {nav_file}")

    # --- Process Trades ---
    trades_tree = ET.parse(trade_file)
    all_trades = trades_tree.findall(".//Trade")
    
    events_to_insert = []
    for trade in all_trades:
        attribs = trade.attrib
        event_ts = datetime.strptime(f"{attribs.get('tradeDate')} {attribs.get('tradeTime', '16:00:00')}", "%Y%m%d %H%M%S")
        
        pnl = float(attribs.get('fifoPnlRealized', 0))
        commission = float(attribs.get('ibCommission', 0))
        
        event = {
            'event_timestamp': event_ts,
            'event_type': 'Trade',
            'description': attribs.get('description'),
            'cash_impact_hkd': (float(attribs.get('proceeds', 0)) + commission) * HKD_USD_RATE,
            'realized_pnl_hkd': pnl * HKD_USD_RATE,
            'ib_commission_hkd': commission * HKD_USD_RATE,
            'source_transaction_id': attribs.get('transactionID')
        }
        events_to_insert.append(event)

    # --- Process Cash Transactions ---
    cash_tree = ET.parse(cash_file)
    all_cash_trans = cash_tree.findall(".//CashTransaction")

    for trans in all_cash_trans:
        attribs = trans.attrib
        # Skip trades, as they are handled separately
        if attribs.get('type') == 'Trade':
            continue

        event_ts = datetime.strptime(attribs.get('dateTime'), "%Y%m%d;%H%M%S")
        
        event = {
            'event_timestamp': event_ts,
            'event_type': attribs.get('type'),
            'description': attribs.get('description'),
            'cash_impact_hkd': float(attribs.get('amount', 0)) * HKD_USD_RATE,
            'realized_pnl_hkd': 0,
            'ib_commission_hkd': 0,
            'source_transaction_id': attribs.get('transactionID')
        }
        events_to_insert.append(event)
    
    logging.info(f"Found a total of {len(events_to_insert)} events in the XML files.")

    # --- Insert Events into Database ---
    if not events_to_insert:
        logging.info("No new events to insert.")
        return

    with engine.connect() as connection:
        with connection.begin():
            insert_sql = text("""
                INSERT INTO alm_reporting.chronological_events (
                    event_timestamp, event_type, description, cash_impact_hkd, 
                    realized_pnl_hkd, ib_commission_hkd, source_transaction_id
                ) VALUES (
                    :event_timestamp, :event_type, :description, :cash_impact_hkd, 
                    :realized_pnl_hkd, :ib_commission_hkd, :source_transaction_id
                )
                ON CONFLICT (source_transaction_id) DO NOTHING;
            """)
            result = connection.execute(insert_sql, events_to_insert)
            logging.info(f"Successfully inserted {result.rowcount} new events into the database.")

    # --- Update Daily Summaries ---
    logging.info("Calculating and updating daily summaries.")
    df = pd.DataFrame(events_to_insert)
    if not df.empty:
        df['date'] = pd.to_datetime(df['event_timestamp']).dt.date
        
        # Log the date range of events found
        min_date = df['date'].min()
        max_date = df['date'].max()
        logging.info(f"Date range of events found in XML: {min_date} to {max_date}")

        # Aggregate financial data from events
        summary_agg = df.groupby('date').agg(
            total_pnl_hkd=('realized_pnl_hkd', 'sum'),
            net_cash_flow_hkd=('cash_impact_hkd', 'sum')
        ).reset_index()

        # Get NAV data
        nav_tree = ET.parse(nav_file)
        nav_summary_node = nav_tree.find(".//ChangeInNAV")
        start_nav = float(nav_summary_node.get('startingValue', 0))
        end_nav = float(nav_summary_node.get('endingValue', 0))
        
        # For a single day's import, we can approximate
        if len(summary_agg['date'].unique()) == 1:
            summary_date = summary_agg['date'].iloc[0]
            summary_agg['opening_nav_hkd'] = start_nav
            summary_agg['closing_nav_hkd'] = end_nav
            summary_agg = summary_agg.rename(columns={'date': 'summary_date'})
            
            logging.info(f"Calculated summary data for {summary_date}: {summary_agg.to_dict('records')}")

            # Insert or update the summary table
            with engine.connect() as connection:
                with connection.begin():
                    for _, row in summary_agg.iterrows():
                        upsert_sql = text("""
                            INSERT INTO alm_reporting.daily_summary (
                                summary_date, opening_nav_hkd, closing_nav_hkd, 
                                total_pnl_hkd, net_cash_flow_hkd
                            ) VALUES (
                                :summary_date, :opening_nav_hkd, :closing_nav_hkd, 
                                :total_pnl_hkd, :net_cash_flow_hkd
                            )
                            ON CONFLICT (summary_date) DO UPDATE SET
                                opening_nav_hkd = EXCLUDED.opening_nav_hkd,
                                closing_nav_hkd = EXCLUDED.closing_nav_hkd,
                                total_pnl_hkd = EXCLUDED.total_pnl_hkd,
                                net_cash_flow_hkd = EXCLUDED.net_cash_flow_hkd,
                                last_updated = CURRENT_TIMESTAMP;
                        """)
                        connection.execute(upsert_sql, row.to_dict())
                    logging.info(f"Upserted daily summary for: {summary_date}")
        else:
            logging.warning(f"Multi-day summary update from a single file is not yet implemented. Found {len(summary_agg['date'].unique())} unique dates.")

    logging.info("Append-mode data build process completed.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build ALM data, with an option for append-only.')
    parser.add_argument('--append', action='store_true', help='Run in append-only mode, ignoring duplicates.')
    args = parser.parse_args()
    
    parse_and_insert_data(DATABASE_URL, args.append)
