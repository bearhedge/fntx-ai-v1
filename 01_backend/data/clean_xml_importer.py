
import xml.etree.ElementTree as ET
import pandas as pd
from sqlalchemy import create_engine, text
import logging
import os
from typing import List, Dict, Any

# --- Configuration ---
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# --- Database Connection ---
# Replace with your actual database connection string
# For example: 'postgresql://user:password@host:port/database'
DATABASE_URL = "postgresql://info:your_password@localhost:5432/options_data"

class CleanXMLImporter:
    """
    A clean, efficient XML importer for FlexQuery data.
    - Parses XML files directly.
    - Uses pandas for data transformation.
    - Uses SQLAlchemy for efficient database insertion.
    - Processes data in chunks to avoid timeouts.
    """
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        logging.info("Database engine created.")

    def _parse_xml_to_dataframe(self, file_path: str, record_tag: str) -> pd.DataFrame:
        """Parses a FlexQuery XML file into a pandas DataFrame."""
        if not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return pd.DataFrame()

        logging.info(f"Parsing XML file: {file_path}")
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            records = []
            for record in root.iter(record_tag):
                records.append(record.attrib)
                
            df = pd.DataFrame(records)
            logging.info(f"Successfully parsed {len(df)} records from {os.path.basename(file_path)}")
            return df
        except ET.ParseError as e:
            logging.error(f"XML Parse Error in {file_path}: {e}")
            return pd.DataFrame()
        except Exception as e:
            logging.error(f"An unexpected error occurred during XML parsing: {e}")
            return pd.DataFrame()

    def import_trades(self, file_path: str):
        """Imports trades data from a FlexQuery XML file."""
        trades_df = self._parse_xml_to_dataframe(file_path, 'Trade')
        
        if trades_df.empty:
            logging.warning("No trades data to import.")
            return

        # --- Data Transformation ---
        # Rename columns to match the database schema
        # This is the comprehensive mapping from the FlexQuery XML attributes to the database columns.
        column_mapping = {
            # Identifiers
            'clientAccountID': 'client_account_id',
            'accountAlias': 'account_alias',
            'tradeID': 'ibkr_trade_id',
            'ibOrderID': 'ibkr_order_id',
            'ibExecID': 'ibkr_exec_id',
            'transactionID': 'transaction_id',
            'conid': 'con_id',
            'securityID': 'security_id',
            'underlyingConid': 'underlying_con_id',
            'underlyingSymbol': 'underlying_symbol',
            'underlyingSecurityID': 'underlying_security_id',
            'serialNumber': 'serial_number',

            # Descriptions
            'symbol': 'symbol',
            'description': 'description',
            'assetClass': 'asset_class',

            # Contract Details
            'strike': 'strike_price',
            'putCall': 'option_type',
            'expiry': 'expiration_date',
            'multiplier': 'multiplier',
            'listingExchange': 'listing_exchange',
            'underlyingListingExchange': 'underlying_listing_exchange',

            # Trade Execution
            'tradeDate': 'trade_date',
            'tradeTime': 'trade_time',
            'dateTime': 'trade_datetime',
            'quantity': 'quantity',
            'tradePrice': 'trade_price',
            'tradeMoney': 'trade_money',
            'buySell': 'buy_sell',
            'exchange': 'exchange',
            'orderType': 'order_type',
            
            # Financials
            'proceeds': 'proceeds',
            'ibCommission': 'commission',
            'ibFee': 'fee',
            'netCash': 'net_cash',
            'costBasis': 'cost_basis',
            'realizedPnl': 'realized_pnl',
            'fifoPnlRealized': 'fifo_pnl_realized',
            'mtmPnl': 'mtm_pnl',
            'closePrice': 'close_price',

            # Related/Original Trade Info
            'origTradePrice': 'orig_trade_price',
            'origTradeDate': 'orig_trade_date',
            'origTradeID': 'orig_trade_id',
            'origOrderID': 'orig_order_id',
            'origTransactionID': 'orig_transaction_id',

            # Reporting
            'reportDate': 'report_date',
            'levelOfDetail': 'level_of_detail',
            'currencyPrimary': 'currency_primary',
            'transactionType': 'transaction_type',
            'code': 'code',
            'changeInPrice': 'change_in_price',
            'changeInQuantity': 'change_in_quantity',
            'deliveryType': 'delivery_type'
        }
        trades_df.rename(columns=column_mapping, inplace=True)

        # --- Data Type Conversion and Cleaning ---
        numeric_columns = [
            'strike_price', 'quantity', 'trade_price', 'proceeds', 'commission',
            'fee', 'cost_basis', 'realized_pnl', 'mtm_pnl', 'trade_money',
            'net_cash', 'close_price', 'fifo_pnl_realized', 'orig_trade_price',
            'change_in_price', 'change_in_quantity', 'multiplier'
        ]
        
        for col in numeric_columns:
            if col in trades_df.columns:
                # Replace empty strings with None (which becomes NULL in DB)
                trades_df[col] = trades_df[col].replace('', None)
                # Convert column to numeric, coercing errors to None
                trades_df[col] = pd.to_numeric(trades_df[col], errors='coerce')

        date_columns = ['expiration_date', 'trade_date', 'report_date', 'orig_trade_date']
        for col in date_columns:
            if col in trades_df.columns:
                trades_df[col] = pd.to_datetime(trades_df[col], errors='coerce').dt.date

        # Handle datetime specifically
        if 'trade_datetime' in trades_df.columns:
            trades_df['trade_datetime'] = pd.to_datetime(
                trades_df['trade_datetime'].str.replace(';', ' '), 
                errors='coerce'
            )

        # Select only the columns that exist in our table
        # This prevents errors if the XML has extra fields
        final_columns = [col for col in column_mapping.values() if col in trades_df.columns]
        trades_df = trades_df[final_columns]

        # --- Data Loading ---
        self._load_dataframe_to_db(trades_df, 'trades', 'portfolio')

    def _load_dataframe_to_db(self, df: pd.DataFrame, table_name: str, schema: str, chunk_size: int = 100):
        """Loads a DataFrame into a database table in chunks."""
        full_table_name = f"{schema}.{table_name}"
        logging.info(f"Loading {len(df)} records into {full_table_name}...")

        try:
            with self.engine.connect() as connection:
                df.to_sql(
                    name=table_name,
                    con=connection,
                    schema=schema,
                    if_exists='append',
                    index=False,
                    chunksize=chunk_size,
                    method='multi'
                )
            logging.info(f"Successfully loaded data into {full_table_name}.")
        except Exception as e:
            logging.error(f"Database load failed for {full_table_name}: {e}")


if __name__ == '__main__':
    # --- Main Execution ---
    importer = CleanXMLImporter(DATABASE_URL)
    
    # Define the path to your data files
    data_path = '/home/info/fntx-ai-v1/04_data/'
    
    # --- Import Trades ---
    trades_file_mtd = os.path.join(data_path, 'Trades_(1257686)_MTD.xml')
    trades_file_lbd = os.path.join(data_path, 'Trades_(1257690)_LBD.xml')
    
    importer.import_trades(trades_file_mtd)
    importer.import_trades(trades_file_lbd)

    logging.info("--- Import process finished ---")
