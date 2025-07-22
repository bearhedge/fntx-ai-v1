#!/usr/bin/env python3
"""
Monthly parallel manager for 0DTE SPY options download - V2
Uses the dynamic strike downloader with IV NULL preservation
"""
import sys
import os
import json
import subprocess
import threading
import queue
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import pandas as pd

sys.path.append('/home/info/fntx-ai-v1/01_backend')

class MonthlyParallelManagerV2:
    def __init__(self, year: int, month: int, checkpoint_dir: str = "checkpoints_v2"):
        self.year = year
        self.month = month
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_file = f"{checkpoint_dir}/monthly_{year}_{month:02d}_v2.json"
        
        # Create checkpoint directory if it doesn't exist
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        # Parallel configuration
        self.max_workers = 3  # Max concurrent downloads
        self.rate_limit_delay = 1  # Seconds between starting new downloads
        
        # Load or create checkpoint
        self.checkpoint = self.load_checkpoint()
        
    def load_checkpoint(self) -> Dict:
        """Load monthly checkpoint file or create new one"""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        else:
            return {
                "year": self.year,
                "month": self.month,
                "status": "initialized",
                "days": {},
                "stats": {
                    "total_days": 0,
                    "completed_days": 0,
                    "failed_days": 0,
                    "total_contracts": 0,
                    "total_ohlc_bars": 0,
                    "total_greeks_bars": 0,
                    "total_iv_bars": 0,
                    "total_iv_nulls": 0,
                    "average_coverage": 0.0,
                    "average_iv_coverage": 0.0
                },
                "start_time": None,
                "end_time": None
            }
    
    def save_checkpoint(self):
        """Save checkpoint to file"""
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2, default=str)
    
    def get_trading_days(self) -> List[datetime]:
        """Get all trading days for the month"""
        # Get US market calendar
        start_date = datetime(self.year, self.month, 1)
        if self.month == 12:
            end_date = datetime(self.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(self.year, self.month + 1, 1) - timedelta(days=1)
        
        # For now, use weekdays as approximation (you could use pandas_market_calendars for accuracy)
        trading_days = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Monday-Friday
                trading_days.append(current)
            current += timedelta(days=1)
        
        # Remove known holidays for January 2023
        holidays = [
            datetime(2023, 1, 2),  # New Year's Day (observed)
            datetime(2023, 1, 16), # Martin Luther King Jr. Day
        ]
        
        trading_days = [d for d in trading_days if d not in holidays]
        
        return trading_days
    
    def download_day(self, date: datetime) -> Dict:
        """Download data for a single day"""
        date_str = date.strftime('%Y-%m-%d')
        
        # Check if already complete
        if date_str in self.checkpoint['days']:
            day_status = self.checkpoint['days'][date_str]
            if day_status['status'] == 'complete':
                return day_status
        
        # Mark as in progress
        self.checkpoint['days'][date_str] = {
            'status': 'in_progress',
            'start_time': datetime.now().isoformat(),
            'attempts': 1
        }
        self.save_checkpoint()
        
        # Build command for V2 downloader
        cmd = [
            'python3', 'download_day_strikes_dynamic_v2.py',
            '--date', date_str
        ]
        
        try:
            # Run the download
            print(f"\n🚀 Starting download for {date_str}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Load the day's checkpoint to get results
            day_checkpoint_file = f"checkpoint_{date.strftime('%Y%m%d')}_dynamic_v2.json"
            if os.path.exists(day_checkpoint_file):
                with open(day_checkpoint_file, 'r') as f:
                    day_data = json.load(f)
                
                if day_data.get('status') == 'complete':
                    # Calculate IV coverage
                    total_iv_points = day_data['stats'].get('total_iv_bars', 0)
                    iv_nulls = day_data['stats'].get('total_iv_nulls', 0)
                    iv_coverage = ((total_iv_points - iv_nulls) / total_iv_points * 100) if total_iv_points > 0 else 0
                    
                    # Update our checkpoint with success
                    self.checkpoint['days'][date_str] = {
                        'status': 'complete',
                        'end_time': datetime.now().isoformat(),
                        'contracts': day_data['stats']['total_contracts'],
                        'ohlc_bars': day_data['stats']['total_ohlc_bars'],
                        'greeks_bars': day_data['stats']['total_greeks_bars'],
                        'iv_bars': day_data['stats']['total_iv_bars'],
                        'iv_nulls': day_data['stats']['total_iv_nulls'],
                        'coverage': day_data['stats'].get('coverage', 0),
                        'iv_coverage': iv_coverage,
                        'atm_strike': day_data['stats'].get('atm_strike'),
                        'atm_iv': day_data['stats'].get('atm_iv')
                    }
                    
                    # Update totals
                    self.checkpoint['stats']['completed_days'] += 1
                    self.checkpoint['stats']['total_contracts'] += day_data['stats']['total_contracts']
                    self.checkpoint['stats']['total_ohlc_bars'] += day_data['stats']['total_ohlc_bars']
                    self.checkpoint['stats']['total_greeks_bars'] += day_data['stats']['total_greeks_bars']
                    self.checkpoint['stats']['total_iv_bars'] += day_data['stats']['total_iv_bars']
                    self.checkpoint['stats']['total_iv_nulls'] += day_data['stats']['total_iv_nulls']
                    
                    print(f"✓ {date_str}: {day_data['stats']['total_contracts']} contracts, "
                          f"{day_data['stats']['coverage']:.1f}% OHLC coverage, "
                          f"{iv_coverage:.1f}% IV coverage")
                    
                    return self.checkpoint['days'][date_str]
                else:
                    # Mark as failed
                    self.checkpoint['days'][date_str] = {
                        'status': 'failed',
                        'error': day_data.get('errors', ['Unknown error'])
                    }
                    self.checkpoint['stats']['failed_days'] += 1
                    print(f"✗ {date_str}: Failed - {day_data.get('errors')}")
            else:
                # No checkpoint file found
                self.checkpoint['days'][date_str] = {
                    'status': 'failed',
                    'error': 'No checkpoint file found'
                }
                self.checkpoint['stats']['failed_days'] += 1
                print(f"✗ {date_str}: No checkpoint file found")
                
        except Exception as e:
            self.checkpoint['days'][date_str] = {
                'status': 'failed',
                'error': str(e)
            }
            self.checkpoint['stats']['failed_days'] += 1
            print(f"✗ {date_str}: Exception - {str(e)}")
        
        self.save_checkpoint()
        return self.checkpoint['days'][date_str]
    
    def run_parallel(self):
        """Run downloads in parallel"""
        trading_days = self.get_trading_days()
        self.checkpoint['stats']['total_days'] = len(trading_days)
        
        # Filter out already completed days
        days_to_download = []
        for day in trading_days:
            date_str = day.strftime('%Y-%m-%d')
            if date_str not in self.checkpoint['days'] or \
               self.checkpoint['days'][date_str]['status'] != 'complete':
                days_to_download.append(day)
        
        if not days_to_download:
            print("✓ All days already downloaded!")
            return
        
        print(f"\n📅 Downloading {len(days_to_download)} days for {self.year}-{self.month:02d}")
        print(f"   Using {self.max_workers} parallel workers")
        print(f"   Days to download: {len(days_to_download)}")
        print(f"   Already complete: {len(trading_days) - len(days_to_download)}")
        
        # Set start time
        if not self.checkpoint['start_time']:
            self.checkpoint['start_time'] = datetime.now().isoformat()
        
        # Run downloads in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all downloads with rate limiting
            futures = {}
            for i, day in enumerate(days_to_download):
                if i > 0:
                    time.sleep(self.rate_limit_delay)
                
                future = executor.submit(self.download_day, day)
                futures[future] = day
            
            # Process completions
            for future in as_completed(futures):
                day = futures[future]
                try:
                    result = future.result()
                    self.save_checkpoint()
                except Exception as e:
                    print(f"✗ Error processing {day}: {e}")
        
        # Set end time
        self.checkpoint['end_time'] = datetime.now().isoformat()
        
        # Calculate averages
        completed = self.checkpoint['stats']['completed_days']
        if completed > 0:
            total_coverage = sum(
                day['coverage'] for day in self.checkpoint['days'].values() 
                if day['status'] == 'complete'
            )
            total_iv_coverage = sum(
                day.get('iv_coverage', 0) for day in self.checkpoint['days'].values() 
                if day['status'] == 'complete'
            )
            self.checkpoint['stats']['average_coverage'] = total_coverage / completed
            self.checkpoint['stats']['average_iv_coverage'] = total_iv_coverage / completed
        
        self.checkpoint['status'] = 'complete'
        self.save_checkpoint()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print download summary"""
        print(f"\n{'='*80}")
        print(f"Monthly Download Summary for {self.year}-{self.month:02d}")
        print(f"{'='*80}")
        
        stats = self.checkpoint['stats']
        print(f"Total trading days: {stats['total_days']}")
        print(f"Completed days: {stats['completed_days']}")
        print(f"Failed days: {stats['failed_days']}")
        print(f"Total contracts: {stats['total_contracts']:,}")
        print(f"Total OHLC bars: {stats['total_ohlc_bars']:,}")
        print(f"Total Greeks bars: {stats['total_greeks_bars']:,}")
        print(f"Total IV bars: {stats['total_iv_bars']:,}")
        print(f"Total IV NULLs: {stats['total_iv_nulls']:,}")
        print(f"Average OHLC coverage: {stats['average_coverage']:.1f}%")
        print(f"Average IV coverage: {stats['average_iv_coverage']:.1f}%")
        
        if self.checkpoint['start_time'] and self.checkpoint['end_time']:
            start = datetime.fromisoformat(self.checkpoint['start_time'])
            end = datetime.fromisoformat(self.checkpoint['end_time'])
            duration = end - start
            print(f"Total time: {duration}")
        
        print(f"{'='*80}")

def main():
    parser = argparse.ArgumentParser(description='Download monthly 0DTE data in parallel - V2')
    parser.add_argument('--year', type=int, required=True, help='Year (e.g., 2023)')
    parser.add_argument('--month', type=int, required=True, help='Month (1-12)')
    parser.add_argument('--workers', type=int, default=3, help='Max parallel workers')
    
    args = parser.parse_args()
    
    # Create manager
    manager = MonthlyParallelManagerV2(args.year, args.month)
    manager.max_workers = args.workers
    
    # Run downloads
    manager.run_parallel()

if __name__ == "__main__":
    main()