import pandas as pd
from sqlalchemy import create_engine, text
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from collections import defaultdict

# --- Configuration ---
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
DATABASE_URL = "postgresql://postgres:theta_data_2024@localhost:5432/options_data"
DATA_DIR = "/home/info/fntx-ai-v1/04_data"
HKD_USD_RATE = 7.8472

def get_xml_files(file_type):
    """Finds all MTD and LBD XML files for a given file type."""
    files = [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if file_type in f and (f.endswith("_LBD.xml") or f.endswith("_MTD.xml"))]
    if not files:
        logging.warning(f"No MTD or LBD files found for type: {file_type}")
    return files

def get_period_summary_data():
    """Gets starting NAV and total withdrawals from the MTD NAV file."""
    nav_files = get_xml_files("NAV")
    mtd_file = next((f for f in nav_files if "MTD" in f), None)
    if not mtd_file:
        raise FileNotFoundError("No NAV MTD file found.")
    
    tree = ET.parse(mtd_file)
    nav_summary = tree.find(".//ChangeInNAV")
    if nav_summary is None:
        raise ValueError("Could not find ChangeInNAV element in NAV file.")
        
    start_nav = float(nav_summary.get('startingValue'))
    withdrawals = float(nav_summary.get('depositsWithdrawals'))
    
    return start_nav, withdrawals

def get_event_timestamp(event_attribs):
    """Extracts a datetime object from a raw event's attributes."""
    if 'tradeDate' in event_attribs:
        trade_time = event_attribs.get('tradeTime', '16:00:00').replace(':', '')
        return datetime.strptime(f"{event_attribs.get('tradeDate')} {trade_time}", "%Y%m%d %H%M%S")
    return None

def build_alm_data(db_url: str):
    """Parses financial data, correctly calculates NAV, and populates the database."""
    engine = create_engine(db_url)
    with engine.connect() as connection:
        with connection.begin():
            logging.info("Clearing existing ALM data.")
            connection.execute(text("TRUNCATE TABLE alm_reporting.chronological_events, alm_reporting.daily_summary, alm_reporting.stock_positions RESTART IDENTITY;"))

            start_nav, total_withdrawals = get_period_summary_data()

            # 1. Parse and de-duplicate all trades
            raw_trades = {}
            for file_path in get_xml_files("Trades"):
                for trade in ET.parse(file_path).findall(".//Trade"):
                    trans_id = trade.get('transactionID')
                    if trans_id: raw_trades[trans_id] = trade.attrib
            
            all_raw_events = sorted(raw_trades.values(), key=get_event_timestamp)
            logging.info(f"Processing {len(all_raw_events)} unique trade events.")

            # 2. Create a single aggregate withdrawal event
            if total_withdrawals != 0:
                first_day = get_event_timestamp(all_raw_events[0]).date() if all_raw_events else datetime.now().date()
                withdrawal_event = {
                    'timestamp': datetime.combine(first_day, datetime.min.time()),
                    'id': 'AGGREGATE_WITHDRAWAL',
                    'type': 'Withdrawal',
                    'description': f'Aggregate monthly withdrawal',
                    'cash_impact_hkd': total_withdrawals,
                    'realized_pnl_hkd': 0
                }
            
            # 3. Identify assignment pairs
            book_trades_by_time = defaultdict(list)
            for event in all_raw_events:
                if event.get('transactionType') == 'BookTrade':
                    ts = get_event_timestamp(event)
                    if ts: book_trades_by_time[ts].append(event)
            
            assignment_pairs = {}
            for trades in book_trades_by_time.values():
                if len(trades) >= 2 and {'STK', 'OPT'}.issubset({t.get('assetCategory') for t in trades}):
                    stock_trade = next((t for t in trades if t.get('assetCategory') == 'STK'), None)
                    if stock_trade:
                        for trade in trades:
                            assignment_pairs[trade.get('transactionID')] = stock_trade.get('transactionID')

            # 4. Process events chronologically
            current_cash = start_nav
            open_positions = {}
            processed_events = [withdrawal_event] if total_withdrawals != 0 else []
            current_cash += total_withdrawals # Apply withdrawal at the start

            for event_attribs in all_raw_events:
                event_ts = get_event_timestamp(event_attribs)
                if not event_ts: continue
                
                trans_id = event_attribs.get('transactionID')
                event_data = {'timestamp': event_ts, 'id': trans_id, 'cash_impact_hkd': 0, 'realized_pnl_hkd': 0}

                qty, price, proceeds, commission, pnl, symbol, currency = (event_attribs.get(k, 0) for k in ['quantity', 'tradePrice', 'proceeds', 'ibCommission', 'fifoPnlRealized', 'symbol', 'currency'])
                qty, price, proceeds, commission, pnl = map(float, [qty, price, proceeds, commission, pnl])
                
                rate = HKD_USD_RATE if currency == 'USD' else 1.0

                if event_attribs.get('transactionType') == 'BookTrade':
                    if trans_id in assignment_pairs:
                        if event_attribs.get('assetCategory') == 'STK':
                            cash_impact = (proceeds + commission) * rate
                            event_data.update({'type': 'Assignment', 'description': f"Assigned: {'Sold' if qty < 0 else 'Bought'} {abs(qty)} {symbol} @ {price}", 'cash_impact_hkd': cash_impact})
                            current_cash += cash_impact
                            open_positions[symbol] = {'qty': qty, 'entry_price': price, 'id': trans_id, 'rate': rate}
                            connection.execute(text("INSERT INTO alm_reporting.stock_positions (symbol, quantity, entry_price, entry_date, entry_transaction_id, status) VALUES (:symbol, :qty, :price, :date, :id, 'OPEN')"), {'symbol': symbol, 'qty': qty, 'price': price, 'date': event_ts, 'id': trans_id})
                        else: continue
                    else:
                        pnl_hkd = pnl * rate
                        event_data.update({'type': 'Expiration', 'description': f"Expired: {symbol}", 'realized_pnl_hkd': pnl_hkd})
                        current_cash += pnl_hkd
                else:
                    cash_impact = (proceeds + commission) * rate
                    event_data.update({'type': 'Trade', 'description': f"{'Bought' if qty > 0 else 'Sold'} {abs(qty)} {symbol} @ {price}", 'cash_impact_hkd': cash_impact})
                    current_cash += cash_impact
                    
                    if symbol in open_positions and open_positions[symbol]['qty'] * qty < 0:
                        pos = open_positions.pop(symbol)
                        realized_pnl = (price - pos['entry_price']) * pos['qty'] * -1 * pos['rate']
                        event_data['realized_pnl_hkd'] = realized_pnl
                        current_cash += realized_pnl
                        connection.execute(text("UPDATE alm_reporting.stock_positions SET status='CLOSED', exit_price=:p, exit_date=:d, exit_transaction_id=:id, realized_pnl_hkd=:pnl WHERE entry_transaction_id=:eid"), {'p': price, 'd': event_ts, 'id': trans_id, 'pnl': realized_pnl, 'eid': pos['id']})
                    else:
                        pnl_hkd = pnl * rate
                        event_data['realized_pnl_hkd'] = pnl_hkd
                        current_cash += pnl_hkd
                
                positions_value = sum(pos['qty'] * pos['entry_price'] * pos['rate'] for pos in open_positions.values())
                event_data['nav_after_event_hkd'] = current_cash + positions_value
                processed_events.append(event_data)

            # 5. Insert processed data
            processed_events.sort(key=lambda x: x['timestamp'])
            for event in processed_events:
                connection.execute(text("INSERT INTO alm_reporting.chronological_events (event_timestamp, event_type, description, cash_impact_hkd, realized_pnl_hkd, nav_after_event_hkd, source_transaction_id) VALUES (:timestamp, :type, :description, :cash_impact_hkd, :realized_pnl_hkd, :nav_after_event_hkd, :id)"), event)
            
            if processed_events:
                df = pd.DataFrame(processed_events)
                df['date'] = df['timestamp'].dt.date
                summary = df.groupby('date').agg(total_pnl_hkd=('realized_pnl_hkd', 'sum'), net_cash_flow_hkd=('cash_impact_hkd', 'sum')).reset_index()
                navs_df = df.groupby('date')['nav_after_event_hkd'].last().reset_index().rename(columns={'nav_after_event_hkd': 'closing_nav_hkd'})
                navs_df['opening_nav_hkd'] = navs_df['closing_nav_hkd'].shift(1)
                navs_df.loc[0, 'opening_nav_hkd'] = start_nav
                summary = pd.merge(summary, navs_df, on='date')
                for _, row in summary.iterrows():
                    connection.execute(text("INSERT INTO alm_reporting.daily_summary (summary_date, opening_nav_hkd, closing_nav_hkd, total_pnl_hkd, net_cash_flow_hkd) VALUES (:date, :opening_nav_hkd, :closing_nav_hkd, :total_pnl_hkd, :net_cash_flow_hkd)"), row.to_dict())
            
            logging.info("ALM reporting data build process completed successfully.")

if __name__ == '__main__':
    build_alm_data(DATABASE_URL)
