#!/usr/bin/env python3
"""
Monthly parallel manager for 0DTE SPY options download
Manages concurrent downloads of multiple days within a month
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

class MonthlyParallelManager:
    def __init__(self, year: int, month: int, checkpoint_dir: str = "checkpoints"):
        self.year = year
        self.month = month
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_file = f"{checkpoint_dir}/monthly_{year}_{month:02d}.json"
        
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
                    "core_complete": 0,
                    "extended_complete": 0
                },
                "last_update": None
            }
    
    def save_checkpoint(self):
        """Save checkpoint to file"""
        self.checkpoint['last_update'] = datetime.now().isoformat()
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2, default=str)
    
    def get_trading_days(self) -> List[datetime]:
        """Get all trading days in the month"""
        # Get market calendar using pandas
        try:
            import pandas_market_calendars as mcal
            nyse = mcal.get_calendar('NYSE')
            
            start_date = datetime(self.year, self.month, 1)
            if self.month == 12:
                end_date = datetime(self.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(self.year, self.month + 1, 1) - timedelta(days=1)
            
            schedule = nyse.schedule(start_date=start_date, end_date=end_date)
            trading_days = [pd.Timestamp(date).to_pydatetime().date() 
                           for date in schedule.index]
            
            return [datetime.combine(date, datetime.min.time()) for date in trading_days]
            
        except ImportError:
            # Fallback to simple weekday logic
            print("Warning: pandas_market_calendars not installed, using simple weekday logic")
            
            holidays_2023_2025 = {
                # 2023
                datetime(2023, 1, 2),   # New Year's Day observed
                datetime(2023, 1, 16),  # MLK Day
                datetime(2023, 2, 20),  # Presidents Day
                datetime(2023, 4, 7),   # Good Friday
                datetime(2023, 5, 29),  # Memorial Day
                datetime(2023, 6, 19),  # Juneteenth
                datetime(2023, 7, 4),   # Independence Day
                datetime(2023, 9, 4),   # Labor Day
                datetime(2023, 11, 23), # Thanksgiving
                datetime(2023, 12, 25), # Christmas
                # 2024
                datetime(2024, 1, 1),   # New Year's Day
                datetime(2024, 1, 15),  # MLK Day
                datetime(2024, 2, 19),  # Presidents Day
                datetime(2024, 3, 29),  # Good Friday
                datetime(2024, 5, 27),  # Memorial Day
                datetime(2024, 6, 19),  # Juneteenth
                datetime(2024, 7, 4),   # Independence Day
                datetime(2024, 9, 2),   # Labor Day
                datetime(2024, 11, 28), # Thanksgiving
                datetime(2024, 12, 25), # Christmas
                # 2025
                datetime(2025, 1, 1),   # New Year's Day
                datetime(2025, 1, 20),  # MLK Day
                datetime(2025, 2, 17),  # Presidents Day
                datetime(2025, 4, 18),  # Good Friday
                datetime(2025, 5, 26),  # Memorial Day
                datetime(2025, 6, 19),  # Juneteenth
                datetime(2025, 7, 4),   # Independence Day
                datetime(2025, 9, 1),   # Labor Day
                datetime(2025, 11, 27), # Thanksgiving
                datetime(2025, 12, 25), # Christmas
            }
            
            trading_days = []
            current = datetime(self.year, self.month, 1)
            
            if self.month == 12:
                end = datetime(self.year + 1, 1, 1)
            else:
                end = datetime(self.year, self.month + 1, 1)
            
            while current < end:
                # Weekday and not holiday
                if current.weekday() < 5 and current not in holidays_2023_2025:
                    trading_days.append(current)
                current += timedelta(days=1)
            
            return trading_days
    
    def download_day(self, date: datetime, core_only: bool = False) -> Dict:
        """Download a single day using the strike-aware downloader"""
        date_str = date.strftime('%Y-%m-%d')
        
        # Check if already in progress or complete
        if date_str in self.checkpoint['days']:
            day_status = self.checkpoint['days'][date_str]
            if day_status['status'] in ['complete', 'in_progress']:
                return day_status
        
        # Mark as in progress
        self.checkpoint['days'][date_str] = {
            'status': 'in_progress',
            'start_time': datetime.now().isoformat(),
            'attempts': 1
        }
        self.save_checkpoint()
        
        # Build command
        cmd = [
            'python3', 'download_day_strikes.py',
            '--date', date_str
        ]
        
        if core_only:
            cmd.append('--core-only')
        
        try:
            # Run the download
            print(f"\n🚀 Starting download for {date_str}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Load the day's checkpoint to get results
            day_checkpoint_file = f"checkpoint_{date.strftime('%Y%m%d')}.json"
            if os.path.exists(day_checkpoint_file):
                with open(day_checkpoint_file, 'r') as f:
                    day_data = json.load(f)
                
                if day_data.get('status') == 'complete':
                    # Update our checkpoint with success
                    self.checkpoint['days'][date_str] = {
                        'status': 'complete',
                        'end_time': datetime.now().isoformat(),
                        'contracts': day_data['stats']['total_contracts'],
                        'ohlc_bars': day_data['stats']['total_ohlc_bars'],
                        'coverage': day_data['stats'].get('coverage', 0),
                        'core_complete': day_data['core_strikes']['status'] == 'complete',
                        'extended_complete': day_data['extended_strikes']['status'] == 'complete'
                    }
                    
                    # Update totals
                    self.checkpoint['stats']['completed_days'] += 1
                    self.checkpoint['stats']['total_contracts'] += day_data['stats']['total_contracts']
                    self.checkpoint['stats']['total_ohlc_bars'] += day_data['stats']['total_ohlc_bars']
                    
                    if day_data['core_strikes']['status'] == 'complete':
                        self.checkpoint['stats']['core_complete'] += 1
                    if day_data['extended_strikes']['status'] == 'complete':
                        self.checkpoint['stats']['extended_complete'] += 1
                    
                    print(f"✓ {date_str}: {day_data['stats']['total_contracts']} contracts")
                else:
                    # Partial completion
                    self.checkpoint['days'][date_str] = {
                        'status': 'partial',
                        'contracts': day_data['stats']['total_contracts'],
                        'core_complete': day_data['core_strikes']['status'] == 'complete',
                        'extended_complete': day_data['extended_strikes']['status'] == 'complete'
                    }
                    print(f"⚠️  {date_str}: Partial completion")
            else:
                # Failed
                self.checkpoint['days'][date_str] = {
                    'status': 'failed',
                    'error': result.stderr[:200] if result.stderr else 'Unknown error'
                }
                self.checkpoint['stats']['failed_days'] += 1
                print(f"✗ {date_str}: Failed")
            
        except Exception as e:
            self.checkpoint['days'][date_str] = {
                'status': 'failed',
                'error': str(e)[:200]
            }
            self.checkpoint['stats']['failed_days'] += 1
            print(f"✗ {date_str}: Exception - {str(e)[:50]}")
        
        self.save_checkpoint()
        return self.checkpoint['days'][date_str]
    
    def download_month_parallel(self, core_only: bool = False, 
                               max_days: Optional[int] = None) -> Dict:
        """Download entire month with parallel processing"""
        trading_days = self.get_trading_days()
        self.checkpoint['stats']['total_days'] = len(trading_days)
        
        print(f"\n{'='*80}")
        print(f"DOWNLOADING {self.year}-{self.month:02d} (0DTE SPY OPTIONS)")
        print(f"{'='*80}")
        print(f"Trading days: {len(trading_days)}")
        print(f"Max parallel: {self.max_workers}")
        print(f"Strategy: {'Core only (±10)' if core_only else 'Full (±20)'}")
        
        # Filter days that need downloading
        pending_days = []
        for day in trading_days:
            date_str = day.strftime('%Y-%m-%d')
            if date_str not in self.checkpoint['days'] or \
               self.checkpoint['days'][date_str]['status'] != 'complete':
                pending_days.append(day)
        
        if not pending_days:
            print("\n✓ All days already complete!")
            return self.get_summary()
        
        print(f"Pending days: {len(pending_days)}")
        
        # Limit days if requested
        if max_days:
            pending_days = pending_days[:max_days]
            print(f"Limited to: {max_days} days")
        
        # Download with thread pool
        completed = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks with rate limiting
            futures = {}
            for i, day in enumerate(pending_days):
                if i > 0:
                    time.sleep(self.rate_limit_delay)
                
                future = executor.submit(self.download_day, day, core_only)
                futures[future] = day
            
            # Process results as they complete
            for future in as_completed(futures):
                day = futures[future]
                try:
                    result = future.result()
                    if result['status'] == 'complete':
                        completed += 1
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    print(f"✗ {day.strftime('%Y-%m-%d')}: Executor error - {str(e)[:50]}")
                
                # Progress update
                total_processed = completed + failed
                print(f"\nProgress: {total_processed}/{len(pending_days)} "
                      f"({completed} complete, {failed} failed)")
        
        print(f"\n{'='*80}")
        print(f"Monthly download complete!")
        print(f"Completed: {completed}")
        print(f"Failed: {failed}")
        
        return self.get_summary()
    
    def get_summary(self) -> Dict:
        """Get summary of monthly download status"""
        trading_days = self.get_trading_days()
        
        summary = {
            "month": f"{self.year}-{self.month:02d}",
            "total_days": len(trading_days),
            "status": self.checkpoint['status'],
            "completed": 0,
            "partial": 0,
            "failed": 0,
            "pending": 0,
            "contracts": 0,
            "ohlc_bars": 0,
            "avg_coverage": 0
        }
        
        total_coverage = 0
        coverage_count = 0
        
        for day in trading_days:
            date_str = day.strftime('%Y-%m-%d')
            if date_str in self.checkpoint['days']:
                day_info = self.checkpoint['days'][date_str]
                
                if day_info['status'] == 'complete':
                    summary['completed'] += 1
                    summary['contracts'] += day_info.get('contracts', 0)
                    summary['ohlc_bars'] += day_info.get('ohlc_bars', 0)
                    
                    if 'coverage' in day_info:
                        total_coverage += day_info['coverage']
                        coverage_count += 1
                        
                elif day_info['status'] == 'partial':
                    summary['partial'] += 1
                elif day_info['status'] == 'failed':
                    summary['failed'] += 1
                else:
                    summary['pending'] += 1
            else:
                summary['pending'] += 1
        
        if coverage_count > 0:
            summary['avg_coverage'] = total_coverage / coverage_count
        
        # Update status
        if summary['completed'] == summary['total_days']:
            self.checkpoint['status'] = 'complete'
        elif summary['completed'] + summary['partial'] > 0:
            self.checkpoint['status'] = 'partial'
        elif summary['failed'] > 0:
            self.checkpoint['status'] = 'failed'
        
        self.save_checkpoint()
        
        return summary
    
    def print_detailed_status(self):
        """Print detailed status of all days in the month"""
        trading_days = self.get_trading_days()
        summary = self.get_summary()
        
        print(f"\n{'='*100}")
        print(f"DETAILED STATUS: {self.year}-{self.month:02d}")
        print(f"{'='*100}")
        
        print(f"\nSUMMARY:")
        print(f"  Total trading days: {summary['total_days']}")
        print(f"  Completed: {summary['completed']} ({summary['completed']/summary['total_days']*100:.1f}%)")
        print(f"  Partial: {summary['partial']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Pending: {summary['pending']}")
        print(f"  Total contracts: {summary['contracts']:,}")
        print(f"  Total OHLC bars: {summary['ohlc_bars']:,}")
        print(f"  Average coverage: {summary['avg_coverage']:.1f}%")
        
        print(f"\nDAILY BREAKDOWN:")
        print(f"{'Date':<12} {'Status':<10} {'Contracts':<10} {'Coverage':<10} {'Core':<6} {'Ext':<6}")
        print("-" * 60)
        
        for day in trading_days:
            date_str = day.strftime('%Y-%m-%d')
            day_str = day.strftime('%a')
            
            if date_str in self.checkpoint['days']:
                info = self.checkpoint['days'][date_str]
                status = info['status']
                contracts = info.get('contracts', 0)
                coverage = f"{info.get('coverage', 0):.1f}%" if 'coverage' in info else "N/A"
                core = "✓" if info.get('core_complete') else "-"
                ext = "✓" if info.get('extended_complete') else "-"
            else:
                status = "pending"
                contracts = 0
                coverage = "N/A"
                core = "-"
                ext = "-"
            
            print(f"{date_str:<12} {status:<10} {contracts:<10} {coverage:<10} {core:<6} {ext:<6}")

def main():
    parser = argparse.ArgumentParser(description='Monthly parallel manager for 0DTE downloads')
    parser.add_argument('--year', type=int, required=True, help='Year (e.g., 2023)')
    parser.add_argument('--month', type=int, required=True, help='Month (1-12)')
    parser.add_argument('--core-only', action='store_true',
                       help='Download only core strikes (±10 from ATM)')
    parser.add_argument('--max-days', type=int,
                       help='Maximum days to download in this session')
    parser.add_argument('--status', action='store_true',
                       help='Show status only, no downloads')
    parser.add_argument('--checkpoint-dir', type=str, default='checkpoints',
                       help='Directory for checkpoint files')
    
    args = parser.parse_args()
    
    # Validate inputs
    if args.month < 1 or args.month > 12:
        print("Error: Month must be between 1 and 12")
        return 1
    
    # Create manager
    manager = MonthlyParallelManager(
        year=args.year,
        month=args.month,
        checkpoint_dir=args.checkpoint_dir
    )
    
    if args.status:
        # Just show status
        manager.print_detailed_status()
    else:
        # Run downloads
        summary = manager.download_month_parallel(
            core_only=args.core_only,
            max_days=args.max_days
        )
        
        # Show final status
        manager.print_detailed_status()
        
        if summary['completed'] == summary['total_days']:
            print(f"\n✓ Month complete!")
            return 0
        else:
            print(f"\n⚠️  Month incomplete")
            return 1

if __name__ == "__main__":
    sys.exit(main())