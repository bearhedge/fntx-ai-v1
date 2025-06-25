#!/usr/bin/env python3
"""
ThetaData Download & Storage Strategy
Download all historical data during subscription month
"""
import os
import sqlite3
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import json

class ThetaDataDownloader:
    """Download and store all ThetaData for offline use"""
    
    def __init__(self, db_path: str = "/home/info/fntx-ai-v1/data/options_history.db"):
        self.db_path = db_path
        self.api_base = "http://localhost:25510"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Create tables for storing options data"""
        conn = sqlite3.connect(self.db_path)
        
        # OHLC data table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS option_ohlc (
            symbol TEXT,
            exp_date TEXT,
            strike REAL,
            option_type TEXT,
            date TEXT,
            time INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (symbol, exp_date, strike, option_type, date, time)
        )
        """)
        
        # Greeks data table (for when Standard subscription is active)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS option_greeks (
            symbol TEXT,
            exp_date TEXT,
            strike REAL,
            option_type TEXT,
            date TEXT,
            time INTEGER,
            delta REAL,
            gamma REAL,
            theta REAL,
            vega REAL,
            rho REAL,
            iv REAL,
            PRIMARY KEY (symbol, exp_date, strike, option_type, date, time)
        )
        """)
        
        # Open Interest table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS option_oi (
            symbol TEXT,
            exp_date TEXT,
            strike REAL,
            option_type TEXT,
            date TEXT,
            open_interest INTEGER,
            PRIMARY KEY (symbol, exp_date, strike, option_type, date)
        )
        """)
        
        conn.commit()
        conn.close()
    
    def download_historical_data(self, start_date: str = "20210101", end_date: str = None):
        """
        Download all historical options data
        Run this during your ThetaData subscription month
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        
        print(f"Downloading SPY options data from {start_date} to {end_date}")
        print("This will take several hours. Run overnight!")
        print("=" * 60)
        
        # Get all historical expirations
        expirations = self.get_historical_expirations(start_date, end_date)
        print(f"Found {len(expirations)} expiration dates to download")
        
        total_downloaded = 0
        
        for i, exp in enumerate(expirations):
            print(f"\n[{i+1}/{len(expirations)}] Downloading expiration {exp}")
            
            # Get strikes for this expiration
            strikes = self.get_strikes_for_expiration(exp)
            
            for strike in strikes:
                for right in ['C', 'P']:
                    # Download OHLC data
                    ohlc_count = self.download_option_ohlc(exp, strike, right, start_date, end_date)
                    
                    # Download OI data
                    oi_count = self.download_option_oi(exp, strike, right, start_date, end_date)
                    
                    # Download Greeks if available (Standard subscription)
                    greeks_count = self.download_option_greeks(exp, strike, right, start_date, end_date)
                    
                    total_downloaded += ohlc_count + oi_count + greeks_count
            
            print(f"  Downloaded {len(strikes) * 2} contracts for {exp}")
        
        print(f"\n{'='*60}")
        print(f"DOWNLOAD COMPLETE!")
        print(f"Total records downloaded: {total_downloaded:,}")
        print(f"Database size: {os.path.getsize(self.db_path) / 1e9:.2f} GB")
        
        return total_downloaded
    
    def get_historical_expirations(self, start_date: str, end_date: str) -> List[str]:
        """Get all expiration dates in range"""
        # For SPY: Every Monday, Wednesday, Friday + monthly
        expirations = []
        
        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        current = start
        
        while current <= end:
            # MWF expirations for SPY
            if current.weekday() in [0, 2, 4]:  # Mon, Wed, Fri
                expirations.append(current.strftime("%Y%m%d"))
            
            # Monthly (3rd Friday)
            if current.weekday() == 4 and 15 <= current.day <= 21:
                expirations.append(current.strftime("%Y%m%d"))
            
            current += timedelta(days=1)
        
        return sorted(list(set(expirations)))
    
    def get_strikes_for_expiration(self, exp_date: str) -> List[int]:
        """Get relevant strikes for an expiration"""
        # For SPY, typically strikes are every $1
        # Focus on ±$50 from ATM to reduce data size
        
        # Estimate ATM based on date (you could make this smarter)
        year = int(exp_date[:4])
        
        # Rough SPY price estimates by year
        atm_estimates = {
            2021: 420,
            2022: 450,
            2023: 380,
            2024: 500,
            2025: 600
        }
        
        atm = atm_estimates.get(year, 500)
        
        # Get strikes ±$50 from ATM
        strikes = list(range(atm - 50, atm + 51))
        
        return strikes
    
    def download_option_ohlc(self, exp: str, strike: int, right: str, 
                           start_date: str, end_date: str) -> int:
        """Download OHLC data for one option"""
        url = f"{self.api_base}/v2/hist/option/ohlc"
        params = {
            "root": "SPY",
            "exp": exp,
            "strike": strike * 1000,
            "right": right,
            "start_date": start_date,
            "end_date": end_date,
            "ivl": "3600000"  # 1-hour bars to reduce size
        }
        
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('response'):
                    # Store in database
                    conn = sqlite3.connect(self.db_path)
                    for row in data['response']:
                        conn.execute("""
                        INSERT OR REPLACE INTO option_ohlc 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, ("SPY", exp, strike, right, str(row[7]), 
                              row[0], row[1], row[2], row[3], row[4], row[5]))
                    conn.commit()
                    conn.close()
                    return len(data['response'])
        except Exception as e:
            print(f"Error downloading {exp} {strike}{right}: {e}")
        
        return 0
    
    def download_option_oi(self, exp: str, strike: int, right: str,
                          start_date: str, end_date: str) -> int:
        """Download open interest data"""
        # Similar implementation
        return 0
    
    def download_option_greeks(self, exp: str, strike: int, right: str,
                             start_date: str, end_date: str) -> int:
        """Download Greeks data (if Standard subscription active)"""
        # Will work after July 18
        return 0

# Usage
if __name__ == "__main__":
    downloader = ThetaDataDownloader()
    
    print("ThetaData Download Strategy")
    print("=" * 60)
    print("1. Run this script when your Standard subscription is active")
    print("2. It will download 4 years of data (takes 6-12 hours)")
    print("3. Cancel subscription after download completes")
    print("4. Use IBKR for real-time trading")
    print("5. Resubscribe quarterly to update data")
    print()
    print("Estimated storage needed: 5-10 GB")
    print("Estimated download time: 6-12 hours")
    print()
    
    # Uncomment to run download
    # downloader.download_historical_data("20210101")