#!/usr/bin/env python3
"""
Master orchestrator for downloading 2.5 years of 0DTE SPY options data - V2
Uses the dynamic strike downloader with IV NULL preservation
Manages the entire download process from Jan 2023 to June 2025
"""
import sys
import os
import json
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import argparse

sys.path.append('/home/info/fntx-ai-v1/01_backend')

class Master0DTEOrchestratorV2:
    def __init__(self, checkpoint_dir: str = "checkpoints_v2"):
        self.checkpoint_dir = checkpoint_dir
        self.master_checkpoint_file = f"{checkpoint_dir}/master_progress_v2.json"
        
        # Create checkpoint directory
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        # Date range: Jan 2023 to June 2025
        self.start_year = 2023
        self.start_month = 1
        self.end_year = 2025
        self.end_month = 6
        
        # Load or create master checkpoint
        self.checkpoint = self.load_checkpoint()
    
    def load_checkpoint(self) -> Dict:
        """Load master checkpoint file or create new one"""
        if os.path.exists(self.master_checkpoint_file):
            with open(self.master_checkpoint_file, 'r') as f:
                return json.load(f)
        else:
            return {
                "status": "initialized",
                "start_date": f"{self.start_year}-{self.start_month:02d}",
                "end_date": f"{self.end_year}-{self.end_month:02d}",
                "months": {},
                "stats": {
                    "total_months": 0,
                    "completed_months": 0,
                    "total_days": 0,
                    "completed_days": 0,
                    "total_contracts": 0,
                    "total_ohlc_bars": 0,
                    "total_greeks_bars": 0,
                    "total_iv_bars": 0,
                    "total_iv_nulls": 0,
                    "average_ohlc_coverage": 0.0,
                    "average_iv_coverage": 0.0
                },
                "start_time": None,
                "end_time": None
            }
    
    def save_checkpoint(self):
        """Save checkpoint to file"""
        with open(self.master_checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2, default=str)
    
    def get_months_to_download(self) -> List[Tuple[int, int]]:
        """Get list of (year, month) tuples to download"""
        months = []
        
        current_year = self.start_year
        current_month = self.start_month
        
        while (current_year < self.end_year) or (current_year == self.end_year and current_month <= self.end_month):
            months.append((current_year, current_month))
            
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
        
        return months
    
    def download_month(self, year: int, month: int, workers: int = 2) -> Dict:
        """Download a single month using monthly_parallel_manager_v2"""
        month_key = f"{year}-{month:02d}"
        
        # Check if already complete
        if month_key in self.checkpoint['months'] and self.checkpoint['months'][month_key]['status'] == 'complete':
            print(f"✓ {month_key} already complete")
            return self.checkpoint['months'][month_key]
        
        print(f"\n{'='*60}")
        print(f"Downloading {month_key}")
        print(f"{'='*60}")
        
        # Mark as in progress
        self.checkpoint['months'][month_key] = {
            'status': 'in_progress',
            'start_time': datetime.now().isoformat()
        }
        self.save_checkpoint()
        
        # Run monthly parallel manager
        cmd = [
            'python3', 'monthly_parallel_manager_v2.py',
            '--year', str(year),
            '--month', str(month),
            '--workers', str(workers)
        ]
        
        try:
            # Run the monthly download
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Load the monthly checkpoint to get results
            monthly_checkpoint_file = f"{self.checkpoint_dir}/monthly_{year}_{month:02d}_v2.json"
            if os.path.exists(monthly_checkpoint_file):
                with open(monthly_checkpoint_file, 'r') as f:
                    monthly_data = json.load(f)
                
                if monthly_data.get('status') == 'complete':
                    # Update our checkpoint with success
                    self.checkpoint['months'][month_key] = {
                        'status': 'complete',
                        'end_time': datetime.now().isoformat(),
                        'completed_days': monthly_data['stats']['completed_days'],
                        'total_days': monthly_data['stats']['total_days'],
                        'contracts': monthly_data['stats']['total_contracts'],
                        'ohlc_bars': monthly_data['stats']['total_ohlc_bars'],
                        'greeks_bars': monthly_data['stats']['total_greeks_bars'],
                        'iv_bars': monthly_data['stats']['total_iv_bars'],
                        'iv_nulls': monthly_data['stats']['total_iv_nulls'],
                        'avg_ohlc_coverage': monthly_data['stats']['average_coverage'],
                        'avg_iv_coverage': monthly_data['stats']['average_iv_coverage']
                    }
                    
                    # Update totals
                    self.checkpoint['stats']['completed_months'] += 1
                    self.checkpoint['stats']['completed_days'] += monthly_data['stats']['completed_days']
                    self.checkpoint['stats']['total_contracts'] += monthly_data['stats']['total_contracts']
                    self.checkpoint['stats']['total_ohlc_bars'] += monthly_data['stats']['total_ohlc_bars']
                    self.checkpoint['stats']['total_greeks_bars'] += monthly_data['stats']['total_greeks_bars']
                    self.checkpoint['stats']['total_iv_bars'] += monthly_data['stats']['total_iv_bars']
                    self.checkpoint['stats']['total_iv_nulls'] += monthly_data['stats']['total_iv_nulls']
                    
                    print(f"✓ {month_key} complete: {monthly_data['stats']['completed_days']} days, "
                          f"{monthly_data['stats']['total_contracts']} contracts")
                    
                    return self.checkpoint['months'][month_key]
                else:
                    # Partial completion
                    self.checkpoint['months'][month_key] = {
                        'status': 'partial',
                        'completed_days': monthly_data['stats']['completed_days'],
                        'total_days': monthly_data['stats']['total_days']
                    }
            else:
                # No checkpoint file found
                self.checkpoint['months'][month_key] = {
                    'status': 'failed',
                    'error': 'No monthly checkpoint file found'
                }
                
        except Exception as e:
            self.checkpoint['months'][month_key] = {
                'status': 'failed',
                'error': str(e)
            }
            print(f"✗ {month_key}: Exception - {str(e)}")
        
        self.save_checkpoint()
        return self.checkpoint['months'][month_key]
    
    def run(self, workers: int = 2, delay_between_months: int = 30):
        """Run the complete download process"""
        months_to_download = self.get_months_to_download()
        self.checkpoint['stats']['total_months'] = len(months_to_download)
        
        # Count total estimated days (approx 20 trading days per month)
        self.checkpoint['stats']['total_days'] = len(months_to_download) * 20
        
        # Set start time
        if not self.checkpoint['start_time']:
            self.checkpoint['start_time'] = datetime.now().isoformat()
        
        print(f"\n🚀 Master 0DTE Orchestrator V2")
        print(f"   Period: {self.start_year}-{self.start_month:02d} to {self.end_year}-{self.end_month:02d}")
        print(f"   Total months: {len(months_to_download)}")
        print(f"   Estimated days: ~{len(months_to_download) * 20}")
        print(f"   Workers per month: {workers}")
        
        # Process each month
        for year, month in months_to_download:
            month_key = f"{year}-{month:02d}"
            
            # Skip if already complete
            if month_key in self.checkpoint['months'] and \
               self.checkpoint['months'][month_key]['status'] == 'complete':
                print(f"\n✓ Skipping {month_key} (already complete)")
                continue
            
            # Download the month
            result = self.download_month(year, month, workers)
            
            # Save checkpoint after each month
            self.save_checkpoint()
            
            # Delay between months (except for the last one)
            if (year, month) != months_to_download[-1] and result['status'] == 'complete':
                print(f"\n⏳ Waiting {delay_between_months} seconds before next month...")
                time.sleep(delay_between_months)
        
        # Set end time
        self.checkpoint['end_time'] = datetime.now().isoformat()
        self.checkpoint['status'] = 'complete'
        
        # Calculate final statistics
        if self.checkpoint['stats']['completed_months'] > 0:
            total_ohlc_coverage = 0
            total_iv_coverage = 0
            for month_data in self.checkpoint['months'].values():
                if month_data['status'] == 'complete':
                    total_ohlc_coverage += month_data.get('avg_ohlc_coverage', 0)
                    total_iv_coverage += month_data.get('avg_iv_coverage', 0)
            
            self.checkpoint['stats']['average_ohlc_coverage'] = total_ohlc_coverage / self.checkpoint['stats']['completed_months']
            self.checkpoint['stats']['average_iv_coverage'] = total_iv_coverage / self.checkpoint['stats']['completed_months']
        
        self.save_checkpoint()
        
        # Print final summary
        self.print_summary()
    
    def print_summary(self):
        """Print download summary"""
        print(f"\n{'='*80}")
        print(f"Master Download Summary")
        print(f"{'='*80}")
        
        stats = self.checkpoint['stats']
        print(f"Period: {self.checkpoint['start_date']} to {self.checkpoint['end_date']}")
        print(f"Total months: {stats['total_months']}")
        print(f"Completed months: {stats['completed_months']}")
        print(f"Total days: {stats['total_days']}")
        print(f"Completed days: {stats['completed_days']}")
        print(f"Total contracts: {stats['total_contracts']:,}")
        print(f"Total OHLC bars: {stats['total_ohlc_bars']:,}")
        print(f"Total Greeks bars: {stats['total_greeks_bars']:,}")
        print(f"Total IV bars: {stats['total_iv_bars']:,}")
        print(f"Total IV NULLs: {stats['total_iv_nulls']:,}")
        print(f"Average OHLC coverage: {stats['average_ohlc_coverage']:.1f}%")
        print(f"Average IV coverage: {stats['average_iv_coverage']:.1f}%")
        
        if self.checkpoint['start_time'] and self.checkpoint['end_time']:
            start = datetime.fromisoformat(self.checkpoint['start_time'])
            end = datetime.fromisoformat(self.checkpoint['end_time'])
            duration = end - start
            print(f"Total time: {duration}")
        
        # Show failed months
        failed_months = [month for month, data in self.checkpoint['months'].items() 
                        if data['status'] == 'failed']
        if failed_months:
            print(f"\n⚠️  Failed months: {', '.join(failed_months)}")
        
        print(f"{'='*80}")

def main():
    parser = argparse.ArgumentParser(description='Master orchestrator for 2.5 years of 0DTE downloads - V2')
    parser.add_argument('--workers', type=int, default=2, 
                       help='Number of parallel workers per month (default: 2)')
    parser.add_argument('--delay', type=int, default=30,
                       help='Seconds to wait between months (default: 30)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from last checkpoint')
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = Master0DTEOrchestratorV2()
    
    # Run the complete download
    orchestrator.run(workers=args.workers, delay_between_months=args.delay)

if __name__ == "__main__":
    main()