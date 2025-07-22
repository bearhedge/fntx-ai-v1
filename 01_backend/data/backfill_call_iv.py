#!/usr/bin/env python3
"""
Backfill missing IV data for call options
IV is in field [4] for calls, field [2] for puts
"""
import sys
import requests
import psycopg2
import time
from datetime import datetime
from typing import List, Dict
from psycopg2.extras import execute_batch

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

class CallIVBackfiller:
    def __init__(self):
        self.api_url = "http://127.0.0.1:25510/v2/hist/option/implied_volatility"
        self.delay = 0.2  # 200ms between requests
        self.stats = {
            'contracts_processed': 0,
            'iv_records_added': 0,
            'contracts_skipped': 0,
            'errors': 0
        }
        
    def get_contracts_missing_iv(self) -> List[Dict]:
        """Get all call contracts that have OHLC but no IV data"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        query = """
        SELECT DISTINCT 
            oc.contract_id,
            oc.symbol,
            oc.expiration,
            oc.strike,
            oc.option_type,
            COUNT(DISTINCT ohlc.datetime) as ohlc_count,
            COUNT(DISTINCT iv.datetime) as iv_count
        FROM theta.options_contracts oc
        JOIN theta.options_ohlc ohlc ON oc.contract_id = ohlc.contract_id
        LEFT JOIN theta.options_iv iv ON oc.contract_id = iv.contract_id
        WHERE oc.symbol = 'SPY'
          AND oc.expiration >= '2022-12-01'
          AND oc.expiration <= '2022-12-31'
          AND oc.option_type = 'C'  -- Calls only
          AND oc.expiration = ohlc.datetime::date  -- 0DTE only
        GROUP BY oc.contract_id, oc.symbol, oc.expiration, oc.strike, oc.option_type
        HAVING COUNT(DISTINCT iv.datetime) = 0  -- No IV data
        ORDER BY oc.expiration, oc.strike
        """
        
        cursor.execute(query)
        contracts = []
        for row in cursor.fetchall():
            contracts.append({
                'contract_id': row[0],
                'symbol': row[1],
                'expiration': row[2],
                'strike': row[3],
                'option_type': row[4],
                'ohlc_count': row[5],
                'iv_count': row[6]
            })
        
        cursor.close()
        conn.close()
        
        return contracts
    
    def parse_timestamp(self, ms_of_day: int, date_int: int) -> datetime:
        """Parse timestamp from ms_of_day and date integer"""
        hours = ms_of_day // (1000 * 60 * 60)
        minutes = (ms_of_day % (1000 * 60 * 60)) // (1000 * 60)
        seconds = (ms_of_day % (1000 * 60)) // 1000
        
        year = date_int // 10000
        month = (date_int % 10000) // 100
        day = date_int % 100
        
        return datetime(year, month, day, hours, minutes, seconds)
    
    def download_and_save_iv(self, contract: Dict) -> int:
        """Download and save IV data for a single contract"""
        exp_str = contract['expiration'].strftime('%Y%m%d')
        
        params = {
            'root': 'SPY',
            'exp': exp_str,
            'strike': int(contract['strike']) * 1000,
            'right': 'C',
            'start_date': exp_str,
            'end_date': exp_str,
            'ivl': 300000  # 5 minutes
        }
        
        try:
            r = requests.get(self.api_url, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                records = data.get('response', [])
                
                if records:
                    conn = psycopg2.connect(**DB_CONFIG)
                    cursor = conn.cursor()
                    
                    iv_count = 0
                    for record in records:
                        # Parse timestamp
                        ts = self.parse_timestamp(record[0], int(exp_str))
                        
                        # For calls, IV is in field [4]
                        implied_vol = float(record[4]) if record[4] is not None and record[4] > 0 else None
                        
                        if implied_vol:
                            cursor.execute("""
                                INSERT INTO theta.options_iv
                                (contract_id, datetime, implied_volatility)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (contract_id, datetime) DO NOTHING
                            """, (contract['contract_id'], ts, implied_vol))
                            
                            if cursor.rowcount > 0:
                                iv_count += 1
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    return iv_count
                    
        except Exception as e:
            print(f"Error processing ${contract['strike']}C {contract['expiration']}: {str(e)[:50]}")
            self.stats['errors'] += 1
            
        return 0
    
    def backfill_all(self):
        """Backfill IV data for all missing call contracts"""
        print("BACKFILLING CALL OPTION IV DATA")
        print("="*80)
        
        # Get contracts missing IV
        contracts = self.get_contracts_missing_iv()
        print(f"Found {len(contracts)} call contracts missing IV data")
        
        if not contracts:
            print("No contracts to backfill!")
            return
        
        # Process each contract
        for i, contract in enumerate(contracts):
            print(f"\rProcessing {i+1}/{len(contracts)}: "
                  f"${contract['strike']}C {contract['expiration'].strftime('%Y-%m-%d')}...", 
                  end='', flush=True)
            
            iv_added = self.download_and_save_iv(contract)
            
            if iv_added > 0:
                self.stats['contracts_processed'] += 1
                self.stats['iv_records_added'] += iv_added
            else:
                self.stats['contracts_skipped'] += 1
            
            # Progress update every 20 contracts
            if (i + 1) % 20 == 0:
                print(f"\n  Progress: {self.stats['contracts_processed']} processed, "
                      f"{self.stats['iv_records_added']} IV records added")
            
            time.sleep(self.delay)
        
        # Print final report
        self.print_report()
    
    def print_report(self):
        """Print backfill report"""
        print("\n\n" + "="*80)
        print("BACKFILL COMPLETE")
        print("="*80)
        print(f"Contracts processed: {self.stats['contracts_processed']}")
        print(f"IV records added: {self.stats['iv_records_added']:,}")
        print(f"Contracts skipped: {self.stats['contracts_skipped']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['contracts_processed'] > 0:
            avg_iv_per_contract = self.stats['iv_records_added'] / self.stats['contracts_processed']
            print(f"Average IV records per contract: {avg_iv_per_contract:.1f}")

def main():
    backfiller = CallIVBackfiller()
    backfiller.backfill_all()

if __name__ == "__main__":
    main()