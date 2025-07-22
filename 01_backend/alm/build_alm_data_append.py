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
            connection.execute(insert_sql, events_to_insert)
            logging.info(f"Attempted to insert {len(events_to_insert)} events.")

    # --- Update Daily Summaries ---
    # This part is complex and would require re-calculating NAV from the start.
    # For an append-only script, a full recalculation is safer.
    # A true incremental update is beyond the scope of this quick fix.
    logging.warning("Daily summaries are not incrementally updated in this version. A full rebuild may be required for perfect accuracy.")
    logging.info("Append-mode data build process completed.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build ALM data, with an option for append-only.')
    parser.add_argument('--append', action='store_true', help='Run in append-only mode, ignoring duplicates.')
    args = parser.parse_args()
    
    parse_and_insert_data(DATABASE_URL, args.append)
