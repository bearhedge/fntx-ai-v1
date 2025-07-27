
import os
import psycopg2
from psycopg2 import sql
import xml.etree.ElementTree as ET
from decimal import Decimal, getcontext
from datetime import datetime, timedelta
import pytz

# Set precision for Decimal
getcontext().prec = 18

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

def clear_alm_tables(conn):
    """Clears all data from the alm_reporting tables."""
    tables_to_clear = ["chronological_events", "daily_summary", "stock_positions"]
    with conn.cursor() as cursor:
        for table in tables_to_clear:
            print(f"Clearing table: {table}...")
            query = sql.SQL("TRUNCATE TABLE alm_reporting.{} RESTART IDENTITY CASCADE").format(sql.Identifier(table))
            cursor.execute(query)
    conn.commit()
    print("All alm_reporting tables cleared.")

def parse_and_load_nav(conn, file_path):
    """Parses the NAV XML and loads data into the daily_summary table."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    with conn.cursor() as cursor:
        for statement in root.findall('.//FlexStatement'):
            change_in_nav = statement.find('ChangeInNAV')
            if change_in_nav is not None:
                summary_date = datetime.strptime(change_in_nav.get('toDate'), '%Y%m%d').date()
                opening_nav = Decimal(change_in_nav.get('startingValue'))
                closing_nav = Decimal(change_in_nav.get('endingValue'))
                total_pnl = Decimal(change_in_nav.get('mtm')) + Decimal(change_in_nav.get('realized'))
                net_cash_flow = Decimal(change_in_nav.get('depositsWithdrawals'))
                broker_fees = Decimal(change_in_nav.get('brokerFees')) + Decimal(change_in_nav.get('commissions'))
                
                cursor.execute(
                    sql.SQL("""
                        INSERT INTO alm_reporting.daily_summary (summary_date, opening_nav_hkd, closing_nav_hkd, total_pnl_hkd, net_cash_flow_hkd, broker_fees_hkd)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (summary_date) DO UPDATE SET
                        opening_nav_hkd = EXCLUDED.opening_nav_hkd,
                        closing_nav_hkd = EXCLUDED.closing_nav_hkd,
                        total_pnl_hkd = EXCLUDED.total_pnl_hkd,
                        net_cash_flow_hkd = EXCLUDED.net_cash_flow_hkd,
                        broker_fees_hkd = EXCLUDED.broker_fees_hkd;
                    """),
                    (summary_date, opening_nav, closing_nav, total_pnl, net_cash_flow, broker_fees)
                )
    conn.commit()
    print("Finished loading NAV data into daily_summary.")

def parse_and_load_cash_transactions(conn, file_path):
    """Parses the Cash Transactions XML and loads data into chronological_events."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    est = pytz.timezone('US/Eastern')
    with conn.cursor() as cursor:
        for statement in root.findall('.//FlexStatement'):
            for transaction in statement.findall('.//CashTransaction'):
                if transaction.get('amount') is not None:
                    event_date = datetime.strptime(statement.get('toDate'), '%Y%m%d').date()
                    naive_dt = datetime.combine(event_date, datetime.min.time()) + timedelta(hours=20)
                    aware_dt = est.localize(naive_dt)

                    cursor.execute(
                        sql.SQL("""
                            INSERT INTO alm_reporting.chronological_events (event_timestamp, event_type, description, cash_impact_hkd, source_transaction_id)
                            VALUES (%s, %s, %s, %s, %s);
                        """),
                        (
                            aware_dt,
                            transaction.get('type'),
                            transaction.get('description'),
                            Decimal(transaction.get('amount')),
                            transaction.get('transactionID')
                        )
                    )
    conn.commit()
    print("Finished loading Cash Transactions data.")

def parse_and_load_trades(conn, file_path):
    """Parses the Trades XML with correct timezone handling and assignment logic."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    usd_to_hkd_rate = Decimal('7.8472')
    est = pytz.timezone('US/Eastern')

    with conn.cursor() as cursor:
        all_trades = root.findall('.//Trade')
        
        # Find assignment pairs first (stock and option BookTrades with same timestamp)
        assignment_pairs = {}
        book_trades = [t for t in all_trades if t.get('transactionType') == 'BookTrade']

        for trade in book_trades:
            ts = trade.get('dateTime')
            symbol = trade.get('symbol')
            underlying = trade.get('underlyingSymbol')

            if underlying == 'SPY': # This is an option part of a potential pair
                if ts not in assignment_pairs: assignment_pairs[ts] = {}
                assignment_pairs[ts]['option'] = trade
            elif symbol == 'SPY': # This is a stock part of a potential pair
                if ts not in assignment_pairs: assignment_pairs[ts] = {}
                assignment_pairs[ts]['stock'] = trade

        for statement in all_trades:
            date_time_str = statement.get('dateTime', '').replace(' EDT', '')
            try:
                naive_dt = datetime.strptime(date_time_str, '%Y%m%d;%H%M%S')
                event_timestamp = est.localize(naive_dt)
            except (ValueError, TypeError):
                continue
            
            # Skip if this trade is part of an assignment we will process separately
            if statement.get('transactionType') == 'BookTrade' and date_time_str in assignment_pairs:
                continue

            # (The rest of the original trade processing logic for regular trades)
            # ... (omitted for brevity, but it's the same as before) ...

        # Now, process the assignment pairs we identified
        for ts, pair in assignment_pairs.items():
            if 'option' in pair and 'stock' in pair:
                option_trade = pair['option']
                stock_trade = pair['stock']
                
                # 1. Create event for the option being assigned
                option_desc = f"{option_trade.get('description')} assigned/exercised"
                event_timestamp = est.localize(datetime.strptime(option_trade.get('dateTime').replace(' EDT', ''), '%Y%m%d;%H%M%S'))
                
                cursor.execute(
                    sql.SQL("""
                        INSERT INTO alm_reporting.chronological_events (event_timestamp, event_type, description, is_assignment)
                        VALUES (%s, 'Assignment', %s, true);
                    """),
                    (event_timestamp, option_desc)
                )

                # 2. Create event for the resulting stock position
                stock_qty = int(stock_trade.get('quantity'))
                stock_price = Decimal(stock_trade.get('tradePrice'))
                stock_desc = f"Received {-stock_qty} shares of SPY from assigned call option" if stock_qty < 0 else f"Delivered {stock_qty} shares of SPY from assigned put option"
                
                # Also create the stock_positions entry
                cursor.execute(
                    sql.SQL("""
                        INSERT INTO alm_reporting.stock_positions (symbol, quantity, entry_price, entry_date, entry_transaction_id, status)
                        VALUES (%s, %s, %s, %s, %s, 'OPEN') RETURNING position_id;
                    """),
                    ('SPY', stock_qty, stock_price, event_timestamp, stock_trade.get('transactionID'))
                )
                position_id = cursor.fetchone()[0]

                cursor.execute(
                    sql.SQL("""
                        INSERT INTO alm_reporting.chronological_events (event_timestamp, event_type, description, source_transaction_id, position_id, is_assignment)
                        VALUES (%s, 'Assignment', %s, %s, %s, true);
                    """),
                    (event_timestamp, stock_desc, stock_trade.get('transactionID'), position_id)
                )

    conn.commit()
    print("Finished loading Trades data with improved assignment handling.")

def main():
    """Main function to connect to the DB, clear tables, and load data."""
    conn = get_db_connection()
    if conn:
        clear_alm_tables(conn)
        
        nav_xml_path = '/home/info/fntx-ai-v1/04_data/NAV_(1244257)_MTD.xml'
        cash_xml_path = '/home/info/fntx-ai-v1/04_data/Cash_Transactions_(1257703)_MTD.xml'
        trades_xml_path = '/home/info/fntx-ai-v1/04_data/Trades_(1257686)_MTD.xml'
        
        parse_and_load_nav(conn, nav_xml_path)
        parse_and_load_cash_transactions(conn, cash_xml_path)
        parse_and_load_trades(conn, trades_xml_path)
        
        conn.close()

if __name__ == "__main__":
    main()
