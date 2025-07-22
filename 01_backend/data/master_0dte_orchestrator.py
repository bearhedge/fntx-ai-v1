#!/usr/bin/env python3
"""
Master orchestrator for downloading 2.5 years of 0DTE SPY options data
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

class Master0DTEOrchestrator:
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        self.master_checkpoint_file = f"{checkpoint_dir}/master_progress.json"
        
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
                    "estimated_remaining_hours": 0
                },
                "current_phase": "core",  # 'core' or 'extended'
                "last_update": None,
                "start_time": None,
                "tmux_session": None
            }
    
    def save_checkpoint(self):
        """Save checkpoint to file"""
        self.checkpoint['last_update'] = datetime.now().isoformat()
        with open(self.master_checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2, default=str)
    
    def get_all_months(self) -> List[Tuple[int, int]]:
        """Get all months in the date range"""
        months = []
        current = datetime(self.start_year, self.start_month, 1)
        end = datetime(self.end_year, self.end_month + 1, 1)
        
        while current < end:
            months.append((current.year, current.month))
            # Move to next month
            if current.month == 12:
                current = datetime(current.year + 1, 1, 1)
            else:
                current = datetime(current.year, current.month + 1, 1)
        
        return months
    
    def update_month_status(self, year: int, month: int):
        """Update status for a specific month from its checkpoint"""
        month_key = f"{year}-{month:02d}"
        month_checkpoint_file = f"{self.checkpoint_dir}/monthly_{year}_{month:02d}.json"
        
        if os.path.exists(month_checkpoint_file):
            with open(month_checkpoint_file, 'r') as f:
                month_data = json.load(f)
            
            # Count completed days
            completed_days = sum(1 for day_info in month_data['days'].values() 
                               if day_info['status'] == 'complete')
            
            total_days = month_data['stats']['total_days']
            
            self.checkpoint['months'][month_key] = {
                'status': month_data['status'],
                'total_days': total_days,
                'completed_days': completed_days,
                'contracts': month_data['stats']['total_contracts'],
                'ohlc_bars': month_data['stats']['total_ohlc_bars']
            }
            
            return completed_days == total_days
        
        return False
    
    def estimate_remaining_time(self) -> float:
        """Estimate remaining download time in hours"""
        all_months = self.get_all_months()
        
        # Count remaining days
        remaining_days = 0
        for year, month in all_months:
            month_key = f"{year}-{month:02d}"
            if month_key in self.checkpoint['months']:
                month_info = self.checkpoint['months'][month_key]
                remaining_days += (month_info['total_days'] - month_info['completed_days'])
            else:
                # Estimate 21 trading days per month
                remaining_days += 21
        
        # Estimate based on phase
        if self.checkpoint['current_phase'] == 'core':
            # Core downloads: ~5 minutes per day
            minutes_per_day = 5
        else:
            # Extended downloads: ~3 minutes per day (fewer strikes)
            minutes_per_day = 3
        
        return (remaining_days * minutes_per_day) / 60
    
    def download_month(self, year: int, month: int, core_only: bool = False) -> bool:
        """Download a single month"""
        month_key = f"{year}-{month:02d}"
        
        print(f"\n{'='*80}")
        print(f"DOWNLOADING {month_key}")
        print(f"{'='*80}")
        
        cmd = [
            'python3', 'monthly_parallel_manager.py',
            '--year', str(year),
            '--month', str(month),
            '--checkpoint-dir', self.checkpoint_dir
        ]
        
        if core_only:
            cmd.append('--core-only')
        
        try:
            # Run the monthly download
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Update our status from the month's checkpoint
            month_complete = self.update_month_status(year, month)
            
            # Update global stats
            self.update_global_stats()
            
            if month_complete:
                print(f"✓ {month_key} complete!")
                return True
            else:
                print(f"⚠️  {month_key} incomplete")
                return False
                
        except Exception as e:
            print(f"✗ {month_key} failed: {str(e)[:100]}")
            return False
    
    def update_global_stats(self):
        """Update global statistics from all months"""
        all_months = self.get_all_months()
        
        total_months = len(all_months)
        completed_months = 0
        total_days = 0
        completed_days = 0
        total_contracts = 0
        total_ohlc_bars = 0
        
        for year, month in all_months:
            month_key = f"{year}-{month:02d}"
            if month_key in self.checkpoint['months']:
                month_info = self.checkpoint['months'][month_key]
                
                total_days += month_info['total_days']
                completed_days += month_info['completed_days']
                total_contracts += month_info['contracts']
                total_ohlc_bars += month_info['ohlc_bars']
                
                if month_info['completed_days'] == month_info['total_days']:
                    completed_months += 1
        
        self.checkpoint['stats'] = {
            'total_months': total_months,
            'completed_months': completed_months,
            'total_days': total_days,
            'completed_days': completed_days,
            'total_contracts': total_contracts,
            'total_ohlc_bars': total_ohlc_bars,
            'estimated_remaining_hours': self.estimate_remaining_time()
        }
        
        self.save_checkpoint()
    
    def run_two_phase_download(self, start_from: Optional[str] = None,
                              months_per_session: Optional[int] = None):
        """Run the two-phase download strategy"""
        all_months = self.get_all_months()
        
        if not self.checkpoint.get('start_time'):
            self.checkpoint['start_time'] = datetime.now().isoformat()
        
        # Phase 1: Download core strikes for all months
        if self.checkpoint['current_phase'] == 'core':
            print("\n" + "="*80)
            print("PHASE 1: DOWNLOADING CORE STRIKES (±10 from ATM)")
            print("="*80)
            
            # Find starting point
            start_idx = 0
            if start_from:
                for i, (year, month) in enumerate(all_months):
                    if f"{year}-{month:02d}" == start_from:
                        start_idx = i
                        break
            
            # Download core strikes
            downloaded = 0
            for year, month in all_months[start_idx:]:
                month_key = f"{year}-{month:02d}"
                
                # Skip if already complete
                if month_key in self.checkpoint['months'] and \
                   self.checkpoint['months'][month_key]['completed_days'] > 0:
                    print(f"\n⏭️  Skipping {month_key} (already has data)")
                    continue
                
                # Download month
                self.download_month(year, month, core_only=True)
                downloaded += 1
                
                # Check session limit
                if months_per_session and downloaded >= months_per_session:
                    print(f"\n📍 Session limit reached ({months_per_session} months)")
                    break
                
                # Show progress
                self.print_progress()
            
            # Check if phase 1 is complete
            all_core_complete = True
            for year, month in all_months:
                month_key = f"{year}-{month:02d}"
                if month_key not in self.checkpoint['months'] or \
                   self.checkpoint['months'][month_key]['completed_days'] == 0:
                    all_core_complete = False
                    break
            
            if all_core_complete:
                self.checkpoint['current_phase'] = 'extended'
                self.save_checkpoint()
                print("\n✓ PHASE 1 COMPLETE! Moving to extended strikes...")
        
        # Phase 2: Download extended strikes
        if self.checkpoint['current_phase'] == 'extended':
            print("\n" + "="*80)
            print("PHASE 2: DOWNLOADING EXTENDED STRIKES (±11-20 from ATM)")
            print("="*80)
            
            # Find starting point
            start_idx = 0
            if start_from:
                for i, (year, month) in enumerate(all_months):
                    if f"{year}-{month:02d}" == start_from:
                        start_idx = i
                        break
            
            # Download extended strikes
            downloaded = 0
            for year, month in all_months[start_idx:]:
                month_key = f"{year}-{month:02d}"
                
                # Download month (full, which includes extended)
                self.download_month(year, month, core_only=False)
                downloaded += 1
                
                # Check session limit
                if months_per_session and downloaded >= months_per_session:
                    print(f"\n📍 Session limit reached ({months_per_session} months)")
                    break
                
                # Show progress
                self.print_progress()
    
    def print_progress(self):
        """Print current progress"""
        stats = self.checkpoint['stats']
        
        print(f"\n{'='*80}")
        print("OVERALL PROGRESS")
        print(f"{'='*80}")
        print(f"Months: {stats['completed_months']}/{stats['total_months']} "
              f"({stats['completed_months']/stats['total_months']*100:.1f}%)")
        print(f"Days: {stats['completed_days']}/{stats['total_days']} "
              f"({stats['completed_days']/stats['total_days']*100:.1f}%)")
        print(f"Contracts: {stats['total_contracts']:,}")
        print(f"OHLC bars: {stats['total_ohlc_bars']:,}")
        print(f"Phase: {self.checkpoint['current_phase'].upper()}")
        print(f"Est. time remaining: {stats['estimated_remaining_hours']:.1f} hours")
        
        if self.checkpoint.get('start_time'):
            elapsed = datetime.now() - datetime.fromisoformat(self.checkpoint['start_time'])
            print(f"Elapsed time: {elapsed.days}d {elapsed.seconds//3600}h {(elapsed.seconds%3600)//60}m")
    
    def print_detailed_status(self):
        """Print detailed status by month"""
        all_months = self.get_all_months()
        
        print(f"\n{'='*100}")
        print("DETAILED STATUS BY MONTH")
        print(f"{'='*100}")
        print(f"{'Month':<8} {'Status':<12} {'Days':<15} {'Contracts':<12} {'OHLC Bars':<12}")
        print("-" * 80)
        
        for year, month in all_months:
            month_key = f"{year}-{month:02d}"
            
            if month_key in self.checkpoint['months']:
                info = self.checkpoint['months'][month_key]
                status = info['status']
                days = f"{info['completed_days']}/{info['total_days']}"
                contracts = f"{info['contracts']:,}"
                ohlc = f"{info['ohlc_bars']:,}"
            else:
                status = "pending"
                days = "0/??"
                contracts = "0"
                ohlc = "0"
            
            print(f"{month_key:<8} {status:<12} {days:<15} {contracts:<12} {ohlc:<12}")
        
        # Summary by year
        print(f"\n{'='*100}")
        print("SUMMARY BY YEAR")
        print(f"{'='*100}")
        
        for year in range(self.start_year, self.end_year + 1):
            year_contracts = 0
            year_days = 0
            year_complete_days = 0
            
            for month in range(1, 13):
                if year == self.end_year and month > self.end_month:
                    break
                if year == self.start_year and month < self.start_month:
                    continue
                    
                month_key = f"{year}-{month:02d}"
                if month_key in self.checkpoint['months']:
                    info = self.checkpoint['months'][month_key]
                    year_contracts += info['contracts']
                    year_days += info['total_days']
                    year_complete_days += info['completed_days']
            
            completion = (year_complete_days / year_days * 100) if year_days > 0 else 0
            print(f"{year}: {year_complete_days}/{year_days} days ({completion:.1f}%), "
                  f"{year_contracts:,} contracts")
    
    def create_tmux_script(self):
        """Create a tmux script for background execution"""
        script_content = f"""#!/bin/bash
# Tmux script for 0DTE download
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Create new tmux session
tmux new-session -d -s odte_download

# Send commands to the session
tmux send-keys -t odte_download "cd {os.getcwd()}" C-m
tmux send-keys -t odte_download "python3 master_0dte_orchestrator.py --run" C-m

echo "Download started in tmux session 'odte_download'"
echo "To view: tmux attach -t odte_download"
echo "To detach: Ctrl+B then D"
echo "To kill: tmux kill-session -t odte_download"
"""
        
        script_file = "start_odte_download.sh"
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_file, 0o755)
        print(f"\n✓ Created tmux script: {script_file}")
        print("Run with: ./start_odte_download.sh")

def main():
    parser = argparse.ArgumentParser(description='Master orchestrator for 0DTE downloads')
    parser.add_argument('--run', action='store_true',
                       help='Start the download process')
    parser.add_argument('--status', action='store_true',
                       help='Show current status')
    parser.add_argument('--start-from', type=str,
                       help='Start from specific month (YYYY-MM)')
    parser.add_argument('--months-per-session', type=int,
                       help='Limit months per session')
    parser.add_argument('--create-tmux', action='store_true',
                       help='Create tmux script for background execution')
    parser.add_argument('--checkpoint-dir', type=str, default='checkpoints',
                       help='Directory for checkpoint files')
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = Master0DTEOrchestrator(checkpoint_dir=args.checkpoint_dir)
    
    if args.create_tmux:
        orchestrator.create_tmux_script()
    elif args.status:
        orchestrator.print_progress()
        orchestrator.print_detailed_status()
    elif args.run:
        print("="*80)
        print("0DTE SPY OPTIONS DOWNLOAD - MASTER ORCHESTRATOR")
        print("="*80)
        print(f"Date range: Jan 2023 - June 2025")
        print(f"Strategy: Two-phase (Core ±10, then Extended ±20)")
        print(f"Checkpoint dir: {args.checkpoint_dir}")
        
        # Start download
        orchestrator.run_two_phase_download(
            start_from=args.start_from,
            months_per_session=args.months_per_session
        )
        
        # Final status
        orchestrator.print_progress()
        
        if orchestrator.checkpoint['stats']['completed_days'] == \
           orchestrator.checkpoint['stats']['total_days']:
            print("\n✓ ALL DOWNLOADS COMPLETE!")
            return 0
        else:
            print("\n⏸️  Download paused. Run again to continue.")
            return 1
    else:
        parser.print_help()

if __name__ == "__main__":
    sys.exit(main())