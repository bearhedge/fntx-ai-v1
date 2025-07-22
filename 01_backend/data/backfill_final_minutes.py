#!/usr/bin/env python3
"""
Backfill 3:59 PM 1-minute data for existing SPY options contracts
Adds a single 1-minute bar at 3:59 PM to better approximate closing prices
"""
import os
import sys
import time
import logging
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import requests
import json
from typing import List, Dict, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/info/fntx-ai-v1/08_logs/backfill_final_minutes.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ThetaTerminal API configuration
THETA_API_URL = "http://localhost:25510"
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'options_data',
    'user': 'info'
}

class FinalMinutesBackfiller:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.conn.autocommit = False
        self.stats = {
            'total_contracts': 0,
            'processed_contracts': 0,
            'ohlc_records': 0,
            'greeks_records': 0,
            'iv_records': 0,
            'iv_interpolated': 0,
            'errors': 0
        }
        
    def get_existing_contracts(self) -> List[Dict]:
        """Get all contracts that need backfilling"""
        query = """
        SELECT DISTINCT 
            c.contract_id, c.symbol, c.expiration, c.strike, c.option_type
        FROM theta.options_contracts c
        WHERE c.contract_id IN (
            SELECT DISTINCT contract_id FROM theta.options_ohlc
        )
        ORDER BY c.expiration, c.strike, c.option_type
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query)
            contracts = []
            for row in cur.fetchall():
                contracts.append({
                    'contract_id': row[0],
                    'symbol': row[1],
                    'expiration': row[2],
                    'strike': float(row[3]),
                    'option_type': row[4]
                })
        
        logger.info(f"Found {len(contracts)} contracts to backfill")
        self.stats['total_contracts'] = len(contracts)
        return contracts
    
    def get_trading_days(self) -> List[datetime.date]:
        """Get all trading days that need backfilling"""
        query = """
        SELECT DISTINCT DATE(datetime) as trading_date
        FROM theta.options_ohlc
        ORDER BY trading_date
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query)
            days = [row[0] for row in cur.fetchall()]
        
        logger.info(f"Found {len(days)} trading days to process")
        return days
    
    def check_existing_data(self, contract_id: int, date: datetime.date) -> bool:
        """Check if we already have 3:59 PM data"""
        query = """
        SELECT 1 FROM theta.options_ohlc 
        WHERE contract_id = %s 
        AND datetime = %s::timestamp
        LIMIT 1
        """
        
        datetime_str = f"{date} 15:59:00"
        with self.conn.cursor() as cur:
            cur.execute(query, (contract_id, datetime_str))
            return cur.fetchone() is not None
    
    def download_minute_data(self, date: datetime.date, contracts: List[Dict]) -> Dict:
        """Download 3:59 PM 1-minute data for all contracts on a date"""
        # Filter contracts expiring on this date
        days_contracts = [c for c in contracts if c['expiration'] == date]
        
        if not days_contracts:
            return {}
        
        logger.info(f"Downloading 3:59 PM data for {len(days_contracts)} contracts on {date}")
        
        results = {}
        
        # Download data for each contract
        for contract in days_contracts:
            try:
                # Skip if we already have 3:59 PM data
                if self.check_existing_data(contract['contract_id'], date):
                    logger.debug(f"Skipping {contract['strike']}{contract['option_type']} - already has 3:59 PM data")
                    continue
                
                # Construct ThetaTerminal request
                endpoint = f"{THETA_API_URL}/v2/hist/option/ohlc"
                params = {
                    'root': contract['symbol'],
                    'exp': date.strftime('%Y%m%d'),
                    'strike': int(contract['strike'] * 1000),  # ThetaTerminal uses strike*1000
                    'right': contract['option_type'],
                    'start_date': date.strftime('%Y%m%d'),
                    'end_date': date.strftime('%Y%m%d'),
                    'ivl': 60000  # 1 minute intervals
                }
                
                response = requests.get(endpoint, params=params, timeout=30)
                
                if response.status_code == 200:
                    try:
                        json_data = response.json()
                        if not isinstance(json_data, dict) or 'response' not in json_data:
                            logger.warning(f"Unexpected response format for {contract['strike']}{contract['option_type']}: {type(json_data)} - {str(json_data)[:200]}")
                            continue
                            
                        data = json_data['response']
                        if not data:
                            continue
                            
                        # Parse and store data
                        for record in data:
                            # Format: [ms_of_day, open, high, low, close, volume, count, date]
                            date_str = str(record[7])
                            date_obj = datetime.strptime(date_str, "%Y%m%d")
                            
                            # Convert ms_of_day to full timestamp
                            ms_of_day = record[0]
                            timestamp = date_obj + timedelta(milliseconds=ms_of_day)
                            
                            # Only keep 3:59 PM data
                            if timestamp.time() == pd.Timestamp('15:59:00').time():
                                if contract['contract_id'] not in results:
                                    results[contract['contract_id']] = []
                                
                                results[contract['contract_id']].append({
                                    'datetime': timestamp,
                                    'open': record[1] if record[1] > 0 else None,  # open
                                    'high': record[2] if record[2] > 0 else None,  # high
                                    'low': record[3] if record[3] > 0 else None,   # low
                                    'close': record[4] if record[4] > 0 else None, # close
                                    'volume': record[5] if len(record) > 5 else 0,  # volume
                                    'trade_count': record[6] if len(record) > 6 else 0  # count
                                })
                    except Exception as e:
                        logger.error(f"Error parsing response for {contract['strike']}{contract['option_type']}: {type(e).__name__}: {str(e)}")
                        continue
                else:
                    if response.status_code == 404 or "No data" in response.text:
                        # No data available for this contract at 3:59 PM - this is normal
                        logger.debug(f"No data for {contract['strike']}{contract['option_type']} at 3:59 PM")
                    else:
                        logger.warning(f"Failed to get 3:59 PM data for {contract['strike']}{contract['option_type']}: {response.status_code} - {response.text[:100]}")
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error downloading {contract['strike']}{contract['option_type']} on {date}: {e}")
                self.stats['errors'] += 1
                
        # Now get Greeks and IV data
        self.download_greeks_iv(date, days_contracts, results)
        
        return results
    
    def download_greeks_iv(self, date: datetime.date, contracts: List[Dict], results: Dict):
        """Download Greeks and IV data for 3:59 PM"""
        for contract in contracts:
            if contract['contract_id'] not in results:
                continue
                
            try:
                # Greeks endpoint
                endpoint = f"{THETA_API_URL}/v2/hist/option/greeks"
                params = {
                    'root': contract['symbol'],
                    'exp': date.strftime('%Y%m%d'),
                    'strike': int(contract['strike'] * 1000),
                    'right': contract['option_type'],
                    'start_date': date.strftime('%Y%m%d'),
                    'end_date': date.strftime('%Y%m%d'),
                    'ivl': 60000
                }
                
                response = requests.get(endpoint, params=params, timeout=30)
                
                if response.status_code == 200:
                    try:
                        json_data = response.json()
                        if not isinstance(json_data, dict) or 'response' not in json_data:
                            logger.warning(f"Unexpected Greeks response format for {contract['strike']}{contract['option_type']}")
                            continue
                            
                        data = json_data['response']
                        if not data:
                            continue
                            
                        # Match Greeks to OHLC data
                        for i, record in enumerate(data):
                            # Format: [ms_of_day, bid, ask, delta, theta, vega, rho, epsilon, lambda, implied_vol, iv_error, ms_of_day2, underlying_price, date]
                            if len(record) < 14:
                                logger.warning(f"Incomplete Greeks record for {contract['strike']}{contract['option_type']}")
                                continue
                                
                            date_str = str(int(record[13]))  # date is at index 13
                            date_obj = datetime.strptime(date_str, "%Y%m%d")
                            
                            # Convert ms_of_day to full timestamp
                            ms_of_day = record[0]
                            timestamp = date_obj + timedelta(milliseconds=ms_of_day)
                            
                            if timestamp.time() == pd.Timestamp('15:59:00').time() and contract['contract_id'] in results and len(results[contract['contract_id']]) > 0:
                                results[contract['contract_id']][i].update({
                                    'delta': record[3],   # delta at index 3
                                    'gamma': None,        # gamma not provided in this API
                                    'theta': record[4],   # theta at index 4
                                    'vega': record[5],    # vega at index 5
                                    'rho': record[6],     # rho at index 6
                                    'implied_volatility': record[9] if record[9] != 0 else None,  # IV at index 9
                                    'iv_interpolated': False
                                })
                    except Exception as e:
                        logger.error(f"Error parsing Greeks response for {contract['strike']}{contract['option_type']}: {e}")
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error downloading Greeks for {contract['strike']}{contract['option_type']}: {e}")
                
    def insert_data(self, contract_id: int, records: List[Dict]):
        """Insert the 3:59 PM data maintaining consistency"""
        try:
            with self.conn.cursor() as cur:
                # Insert OHLC data
                for record in records:
                    # OHLC
                    cur.execute("""
                        INSERT INTO theta.options_ohlc 
                        (contract_id, datetime, open, high, low, close, volume, trade_count)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (contract_id, datetime) DO NOTHING
                    """, (
                        contract_id,
                        record['datetime'],
                        record.get('open'),
                        record.get('high'),
                        record.get('low'),
                        record.get('close'),
                        record.get('volume', 0),
                        record.get('trade_count', 0)
                    ))
                    self.stats['ohlc_records'] += 1
                    
                    # Greeks (if available)
                    if record.get('delta') is not None:
                        cur.execute("""
                            INSERT INTO theta.options_greeks
                            (contract_id, datetime, delta, gamma, theta, vega, rho)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (contract_id, datetime) DO NOTHING
                        """, (
                            contract_id,
                            record['datetime'],
                            record.get('delta'),
                            record.get('gamma'),
                            record.get('theta'),
                            record.get('vega'),
                            record.get('rho')
                        ))
                        self.stats['greeks_records'] += 1
                    
                    # IV (if available or interpolate)
                    iv_value = record.get('implied_volatility')
                    is_interpolated = False
                    
                    if iv_value is None and record.get('delta') is not None:
                        # Could interpolate here if needed
                        # For now, we'll skip missing IV
                        pass
                    
                    if iv_value is not None:
                        cur.execute("""
                            INSERT INTO theta.options_iv
                            (contract_id, datetime, implied_volatility, is_interpolated)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (contract_id, datetime) DO NOTHING
                        """, (
                            contract_id,
                            record['datetime'],
                            iv_value,
                            is_interpolated
                        ))
                        self.stats['iv_records'] += 1
                        if is_interpolated:
                            self.stats['iv_interpolated'] += 1
                
                self.conn.commit()
                self.stats['processed_contracts'] += 1
                
        except Exception as e:
            logger.error(f"Error inserting data for contract {contract_id}: {e}")
            self.conn.rollback()
            raise
    
    def run_backfill(self):
        """Main backfill process"""
        logger.info("Starting 3:59 PM backfill process")
        
        try:
            # Get contracts and days
            contracts = self.get_existing_contracts()
            trading_days = self.get_trading_days()
            
            # Process each day
            for i, date in enumerate(trading_days):
                logger.info(f"Processing day {i+1}/{len(trading_days)}: {date}")
                
                # Download data for all contracts on this date
                day_data = self.download_minute_data(date, contracts)
                
                # Insert data for each contract
                for contract_id, records in day_data.items():
                    if records:
                        self.insert_data(contract_id, records)
                
                # Progress update
                if (i + 1) % 10 == 0:
                    logger.info(f"Progress: {i+1}/{len(trading_days)} days completed")
                    logger.info(f"Stats: {self.stats}")
            
            logger.info("3:59 PM backfill completed successfully!")
            logger.info(f"Final stats: {self.stats}")
            
        except Exception as e:
            logger.error(f"3:59 PM backfill failed: {e}")
            raise
        finally:
            self.conn.close()

if __name__ == "__main__":
    backfiller = FinalMinutesBackfiller()
    backfiller.run_backfill()