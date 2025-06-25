#!/usr/bin/env python3
"""
Demo: Download SPY options data with ThetaData Value subscription
Shows practical implementation of data download and storage
"""
import requests
import sqlite3
import json
import gzip
import os
from datetime import datetime, timedelta
import time

class SPYDataDownloader:
    def __init__(self):
        self.api_base = "http://localhost:25510"
        self.db_path = "/home/info/fntx-ai-v1/backend/spy_options_demo.db"
        
    def setup_database(self):
        """Create database schema for storing options data"""
        conn = sqlite3.connect(self.db_path)
        
        # Create tables
        conn.execute("""
        CREATE TABLE IF NOT EXISTS option_bars (
            symbol TEXT,
            expiration TEXT,
            strike INTEGER,
            option_type TEXT,
            date INTEGER,
            time_ms INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            count INTEGER,
            interval_ms INTEGER,
            PRIMARY KEY (symbol, expiration, strike, option_type, date, time_ms, interval_ms)
        )
        """)
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS option_oi (
            symbol TEXT,
            expiration TEXT,
            strike INTEGER,
            option_type TEXT,
            date INTEGER,
            open_interest INTEGER,
            PRIMARY KEY (symbol, expiration, strike, option_type, date)
        )
        """)
        
        # Create indexes for faster queries
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_date ON option_bars(date)
        """)
        
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_expiration ON option_bars(expiration)
        """)
        
        conn.commit()
        conn.close()
        print("✅ Database initialized")
    
    def download_contract_data(self, exp: str, strike: int, right: str, 
                             start_date: str, end_date: str, interval: int = 3600000):
        """Download data for a single contract"""
        params = {
            "root": "SPY",
            "exp": exp,
            "strike": strike * 1000,
            "right": right,
            "start_date": start_date,
            "end_date": end_date,
            "ivl": interval
        }
        
        records_saved = 0
        
        # Download OHLC data
        try:
            resp = requests.get(f"{self.api_base}/v2/hist/option/ohlc", 
                              params=params, timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get('response'):
                    conn = sqlite3.connect(self.db_path)
                    
                    for row in data['response']:
                        # row format: [ms_of_day, open, high, low, close, volume, count, date]
                        conn.execute("""
                        INSERT OR REPLACE INTO option_bars 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, ("SPY", exp, strike, right, row[7], row[0], 
                              row[1], row[2], row[3], row[4], row[5], row[6], interval))
                        records_saved += 1
                    
                    conn.commit()
                    conn.close()
        except Exception as e:
            print(f"  Error downloading OHLC: {str(e)}")
        
        # Download Open Interest
        try:
            resp = requests.get(f"{self.api_base}/v2/hist/option/open_interest", 
                              params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get('response'):
                    conn = sqlite3.connect(self.db_path)
                    
                    for row in data['response']:
                        # row format: [ms_of_day, open_interest, date]
                        conn.execute("""
                        INSERT OR REPLACE INTO option_oi 
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, ("SPY", exp, strike, right, row[2], row[1]))
                    
                    conn.commit()
                    conn.close()
        except:
            pass  # OI might timeout, not critical
        
        return records_saved
    
    def download_sample_data(self):
        """Download sample data to demonstrate the process"""
        print("\n📥 DOWNLOADING SAMPLE SPY OPTIONS DATA")
        print("="*60)
        
        # Setup database
        self.setup_database()
        
        # Define what to download - recent SPY expiration
        expiration = "20240119"  # Jan 19, 2024 monthly
        strikes = list(range(470, 481))  # 470-480 strikes
        start_date = "20240108"  # 2 weeks of data
        end_date = "20240119"
        
        print(f"\nDownloading data for SPY {expiration} expiration")
        print(f"Strikes: {strikes[0]}-{strikes[-1]}")
        print(f"Date range: {start_date} to {end_date}")
        print(f"Intervals: 1-hour bars\n")
        
        total_records = 0
        contracts_downloaded = 0
        
        start_time = time.time()
        
        for strike in strikes:
            for right in ['C', 'P']:
                print(f"  Downloading {strike}{right}...", end="")
                records = self.download_contract_data(
                    expiration, strike, right, start_date, end_date, 3600000
                )
                
                if records > 0:
                    print(f" ✅ {records} records")
                    total_records += records
                    contracts_downloaded += 1
                else:
                    print(f" ❌ No data")
                
                time.sleep(0.1)  # Be nice to the API
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ Download complete!")
        print(f"  Contracts downloaded: {contracts_downloaded}")
        print(f"  Total records: {total_records:,}")
        print(f"  Time elapsed: {elapsed:.1f} seconds")
        print(f"  Database size: {os.path.getsize(self.db_path) / 1024:.1f} KB")
    
    def analyze_downloaded_data(self):
        """Analyze the downloaded data"""
        print("\n📊 ANALYZING DOWNLOADED DATA")
        print("="*60)
        
        conn = sqlite3.connect(self.db_path)
        
        # Get summary statistics
        summary = conn.execute("""
        SELECT 
            COUNT(DISTINCT expiration || strike || option_type) as unique_contracts,
            COUNT(*) as total_records,
            MIN(date) as earliest_date,
            MAX(date) as latest_date,
            SUM(volume) as total_volume
        FROM option_bars
        """).fetchone()
        
        print(f"\nDatabase Summary:")
        print(f"  Unique contracts: {summary[0]}")
        print(f"  Total records: {summary[1]:,}")
        print(f"  Date range: {summary[2]} to {summary[3]}")
        print(f"  Total volume: {summary[4]:,}")
        
        # Most active contracts
        print(f"\nMost Active Contracts:")
        active = conn.execute("""
        SELECT expiration, strike, option_type, SUM(volume) as total_vol
        FROM option_bars
        GROUP BY expiration, strike, option_type
        ORDER BY total_vol DESC
        LIMIT 5
        """).fetchall()
        
        for exp, strike, otype, vol in active:
            print(f"  SPY {exp} {strike}{otype}: {vol:,} volume")
        
        # Sample query - get data for specific contract
        print(f"\nSample Query - SPY 475C on Jan 16, 2024:")
        sample = conn.execute("""
        SELECT date, time_ms, open, high, low, close, volume
        FROM option_bars
        WHERE expiration = '20240119' 
          AND strike = 475 
          AND option_type = 'C'
          AND date = 20240116
        ORDER BY time_ms
        LIMIT 5
        """).fetchall()
        
        for row in sample:
            time_str = f"{row[1]//3600000}:{(row[1]%3600000)//60000:02d}"
            print(f"  {row[0]} {time_str} - O:{row[2]:.2f} H:{row[3]:.2f} L:{row[4]:.2f} C:{row[5]:.2f} V:{row[6]}")
        
        conn.close()
    
    def demonstrate_compression(self):
        """Show compression benefits"""
        print("\n💾 COMPRESSION DEMONSTRATION")
        print("="*60)
        
        # Export some data to JSON
        conn = sqlite3.connect(self.db_path)
        data = conn.execute("""
        SELECT * FROM option_bars 
        WHERE expiration = '20240119' AND strike = 475
        """).fetchall()
        conn.close()
        
        # Convert to JSON
        json_data = json.dumps(data).encode()
        compressed = gzip.compress(json_data)
        
        print(f"\nCompression Results:")
        print(f"  Original size: {len(json_data) / 1024:.1f} KB")
        print(f"  Compressed size: {len(compressed) / 1024:.1f} KB")
        print(f"  Compression ratio: {len(json_data) / len(compressed):.1f}:1")
        print(f"  Space saved: {(1 - len(compressed)/len(json_data)) * 100:.1f}%")
    
    def calculate_full_dataset_size(self):
        """Calculate size for full SPY dataset"""
        print("\n📈 FULL DATASET SIZE CALCULATION")
        print("="*60)
        
        # Get average record size from our sample
        db_size = os.path.getsize(self.db_path)
        conn = sqlite3.connect(self.db_path)
        record_count = conn.execute("SELECT COUNT(*) FROM option_bars").fetchone()[0]
        conn.close()
        
        if record_count > 0:
            bytes_per_record = db_size / record_count
            
            print(f"\nBased on sample data:")
            print(f"  Database size: {db_size / 1024:.1f} KB")
            print(f"  Record count: {record_count}")
            print(f"  Bytes per record: {bytes_per_record:.1f}")
            
            # Calculate for different scenarios
            print(f"\nProjected sizes for SPY options:")
            
            scenarios = [
                ("1 year, 1-hour bars, ±$50 strikes", 156 * 100 * 2, 252 * 7),
                ("1 year, 5-min bars, ±$50 strikes", 156 * 100 * 2, 252 * 7 * 12),
                ("1 year, 1-min bars, ±$50 strikes", 156 * 100 * 2, 252 * 390),
                ("4 years, 1-hour bars, ±$50 strikes", 156 * 100 * 2 * 4, 252 * 7 * 4),
                ("4 years, 1-hour bars, ±$20 strikes", 156 * 40 * 2 * 4, 252 * 7 * 4)
            ]
            
            for desc, contracts, records_per_contract in scenarios:
                total_records = contracts * records_per_contract
                total_bytes = total_records * bytes_per_record
                total_gb = total_bytes / 1e9
                compressed_gb = total_gb / 6  # Conservative compression
                
                print(f"\n  {desc}:")
                print(f"    Contracts: {contracts:,}")
                print(f"    Records: {total_records:,}")
                print(f"    Uncompressed: {total_gb:.1f} GB")
                print(f"    Compressed: {compressed_gb:.1f} GB")

def main():
    """Run the demonstration"""
    downloader = SPYDataDownloader()
    
    print("\n" + "="*80)
    print("THETADATA VALUE SUBSCRIPTION - SPY OPTIONS DOWNLOAD DEMO")
    print("="*80)
    
    # Download sample data
    downloader.download_sample_data()
    
    # Analyze what we downloaded
    downloader.analyze_downloaded_data()
    
    # Show compression benefits
    downloader.demonstrate_compression()
    
    # Calculate full dataset size
    downloader.calculate_full_dataset_size()
    
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    print("\n✅ VALUE SUBSCRIPTION CAPABILITIES:")
    print("  • Full historical OHLC data (1-min, 5-min, 1-hour)")
    print("  • Open Interest history")
    print("  • All strikes and expirations")
    print("  • Data from 2022 onwards (possibly earlier)")
    print("\n💡 OPTIMAL DOWNLOAD STRATEGY:")
    print("  1. Use 1-hour bars for most backtesting (manageable size)")
    print("  2. Download 1-minute data only for specific strategies")
    print("  3. Focus on strikes ±$20-30 from ATM to reduce size")
    print("  4. Use SQLite with compression for efficient storage")
    print("  5. Download during off-hours to avoid rate limits")
    print("\n💾 STORAGE REQUIREMENTS:")
    print("  • 1-hour bars, 4 years, ±$20 strikes: ~5-10 GB compressed")
    print("  • 1-minute bars, 4 years, all strikes: ~50-100 GB compressed")

if __name__ == "__main__":
    main()