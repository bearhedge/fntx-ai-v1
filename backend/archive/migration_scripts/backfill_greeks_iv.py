#!/usr/bin/env python3
"""
Backfill Greeks and IV data for already downloaded contracts
"""
import sys
import os
import requests
import psycopg2
import time
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
import json

sys.path.append('/home/info/fntx-ai-v1')
from backend.config.theta_config import THETA_HTTP_API, DB_CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/info/fntx-ai-v1/logs/greeks_iv_backfill.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GreeksIVBackfiller:
    def __init__(self, max_workers: int = 5):
        self.session = requests.Session()
        self.max_workers = max_workers
        self.stats = {
            'contracts_processed': 0,
            'greeks_records': 0,
            'iv_records': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
    def get_contracts_missing_greeks(self) -> List[Tuple]:
        """Get all contracts that have OHLC but no Greeks/IV data"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT oc.contract_id, oc.symbol, oc.expiration, oc.strike, oc.option_type
            FROM theta.options_contracts oc
            INNER JOIN theta.options_ohlc ohlc ON oc.contract_id = ohlc.contract_id
            LEFT JOIN theta.options_greeks g ON oc.contract_id = g.contract_id
            WHERE g.contract_id IS NULL
            AND oc.symbol = 'SPY'
            ORDER BY oc.expiration DESC, oc.strike
        """)
        
        contracts = cursor.fetchall()
        cursor.close()
        conn.close()
        
        logger.info(f"Found {len(contracts)} contracts missing Greeks/IV data")
        return contracts
    
    def download_greeks_for_contract(self, contract_info: Tuple) -> Dict:
        """Download and store Greeks/IV for a single contract"""
        contract_id, symbol, expiration, strike, option_type = contract_info
        
        try:
            # Format parameters
            exp_str = expiration.strftime('%Y%m%d')
            params = {
                'root': symbol,
                'exp': exp_str,
                'strike': int(strike * 1000),  # Convert to ThetaData format
                'right': option_type,
                'start_date': '20170101',
                'end_date': datetime.now().strftime('%Y%m%d'),
                'ivl': 60000  # 1-minute intervals
            }
            
            # Download Greeks (includes IV)
            url = f"{THETA_HTTP_API}/v2/hist/option/greeks"
            response = self.session.get(url, params=params, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('response'):
                    greeks_count, iv_count = self.store_greeks_and_iv(contract_id, data['response'])
                    return {
                        'status': 'success',
                        'greeks': greeks_count,
                        'iv': iv_count
                    }
            
            return {'status': 'no_data', 'greeks': 0, 'iv': 0}
            
        except Exception as e:
            logger.error(f"Error processing {exp_str} {strike}{option_type}: {e}")
            return {'status': 'error', 'greeks': 0, 'iv': 0}
    
    def store_greeks_and_iv(self, contract_id: int, data: List) -> Tuple[int, int]:
        """Store Greeks and IV data from API response"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        greeks_records = []
        iv_records = []
        
        try:
            for row in data:
                try:
                    # Format: [ms_of_day, bid, ask, delta, theta, vega, rho, epsilon, lambda, implied_vol, iv_error, ms_of_day2, underlying_price, date]
                    if len(row) < 14:
                        continue
                    
                    date_str = str(row[13])
                    if '.' in date_str or len(date_str) != 8:
                        continue
                    
                    date_obj = datetime.strptime(date_str, "%Y%m%d")
                    ms_of_day = row[0]
                    timestamp = date_obj + timedelta(milliseconds=ms_of_day)
                    
                    # Extract Greeks - limit to 4 decimal places to avoid overflow
                    delta = round(float(row[3]), 4) if row[3] else 0.0
                    theta = round(float(row[4]), 4) if row[4] else 0.0
                    vega = round(float(row[5]), 4) if row[5] else 0.0
                    rho = round(float(row[6]), 4) if row[6] else 0.0
                    implied_vol = round(float(row[9]), 4) if row[9] else 0.0
                    
                    # Cap delta to prevent overflow (max 99.999999)
                    if abs(delta) > 99:
                        delta = 99.0 if delta > 0 else -99.0
                    
                    # Store Greeks (gamma is 0 as not provided)
                    greeks_records.append((
                        contract_id, timestamp, delta, 0.0, theta, vega, rho
                    ))
                    
                    # Store IV if valid
                    if implied_vol > 0:
                        iv_records.append((contract_id, timestamp, implied_vol))
                        
                except (ValueError, IndexError):
                    continue
            
            # Bulk insert Greeks
            if greeks_records:
                from psycopg2.extras import execute_batch
                execute_batch(cursor, """
                    INSERT INTO theta.options_greeks 
                    (contract_id, datetime, delta, gamma, theta, vega, rho)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (contract_id, datetime) DO NOTHING
                """, greeks_records, page_size=1000)
            
            # Bulk insert IV
            if iv_records:
                execute_batch(cursor, """
                    INSERT INTO theta.options_iv 
                    (contract_id, datetime, implied_volatility)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (contract_id, datetime) DO NOTHING
                """, iv_records, page_size=1000)
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Storage error: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
        
        return len(greeks_records), len(iv_records)
    
    def run_backfill(self):
        """Run the backfill process"""
        logger.info("Starting Greeks/IV backfill process...")
        
        # Get contracts needing backfill
        contracts = self.get_contracts_missing_greeks()
        total_contracts = len(contracts)
        
        if total_contracts == 0:
            logger.info("No contracts need Greeks/IV backfill")
            return
        
        # Estimate time
        time_per_contract = 0.2  # seconds (based on API latency)
        estimated_time = (total_contracts * time_per_contract) / self.max_workers / 60
        logger.info(f"Estimated time: {estimated_time:.1f} minutes for {total_contracts} contracts")
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            for contract in contracts:
                future = executor.submit(self.download_greeks_for_contract, contract)
                futures.append(future)
            
            # Process results
            completed = 0
            for future in as_completed(futures):
                result = future.result()
                
                if result['status'] == 'success':
                    self.stats['contracts_processed'] += 1
                    self.stats['greeks_records'] += result['greeks']
                    self.stats['iv_records'] += result['iv']
                elif result['status'] == 'error':
                    self.stats['errors'] += 1
                
                completed += 1
                
                # Progress update every 100 contracts
                if completed % 100 == 0:
                    progress_pct = (completed / total_contracts) * 100
                    elapsed = (datetime.now() - self.stats['start_time']).total_seconds() / 60
                    rate = completed / elapsed if elapsed > 0 else 0
                    eta = (total_contracts - completed) / rate if rate > 0 else 0
                    
                    logger.info(f"Progress: {completed}/{total_contracts} ({progress_pct:.1f}%) | "
                              f"Rate: {rate:.0f} contracts/min | ETA: {eta:.1f} min | "
                              f"Greeks: {self.stats['greeks_records']:,} | IV: {self.stats['iv_records']:,}")
        
        # Final summary
        runtime = datetime.now() - self.stats['start_time']
        logger.info(f"\nBackfill completed in {runtime}")
        logger.info(f"Contracts processed: {self.stats['contracts_processed']:,}")
        logger.info(f"Greeks records added: {self.stats['greeks_records']:,}")
        logger.info(f"IV records added: {self.stats['iv_records']:,}")
        logger.info(f"Errors: {self.stats['errors']}")

if __name__ == "__main__":
    # Check if main download is still running
    if os.system("pgrep -f enhanced_spy_downloader.py > /dev/null") == 0:
        logger.info("Main download still running. Starting Greeks/IV backfill in parallel...")
    
    backfiller = GreeksIVBackfiller(max_workers=5)
    backfiller.run_backfill()