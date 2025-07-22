#!/usr/bin/env python3
"""
Progress manager for December 2022 0DTE download
Coordinates daily downloads and tracks overall progress
"""
import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List
import argparse

class December2022ProgressManager:
    def __init__(self, checkpoint_file: str = "december_2022_progress.json"):
        self.checkpoint_file = checkpoint_file
        self.checkpoint = self.load_checkpoint()
        
        # All trading days in December 2022
        self.trading_days = self.get_trading_days()
        
    def load_checkpoint(self) -> Dict:
        """Load checkpoint file or create new one"""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        else:
            return {
                "status": "initialized",
                "trading_days": {},
                "last_successful": None,
                "total_contracts": 0,
                "total_ohlc_bars": 0,
                "total_greeks_bars": 0,
                "total_iv_bars": 0
            }
    
    def save_checkpoint(self):
        """Save checkpoint to file"""
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2, default=str)
    
    def get_trading_days(self) -> List[datetime]:
        """Get all trading days in December 2022"""
        holidays = [
            datetime(2022, 12, 26)  # Christmas observed
        ]
        
        trading_days = []
        current = datetime(2022, 12, 1)
        end = datetime(2022, 12, 31)
        
        while current <= end:
            # Weekday and not holiday
            if current.weekday() < 5 and current not in holidays:
                trading_days.append(current)
            current += timedelta(days=1)
        
        return trading_days
    
    def get_status_summary(self) -> Dict:
        """Get summary of download status"""
        completed = []
        pending = []
        failed = []
        
        for day in self.trading_days:
            date_str = day.strftime('%Y-%m-%d')
            
            if date_str in self.checkpoint['trading_days']:
                day_info = self.checkpoint['trading_days'][date_str]
                if day_info.get('status') == 'complete':
                    completed.append((day, day_info))
                elif day_info.get('status') == 'failed':
                    failed.append((day, day_info))
                else:
                    pending.append(day)
            else:
                pending.append(day)
        
        return {
            'total': len(self.trading_days),
            'completed': completed,
            'pending': pending,
            'failed': failed
        }
    
    def print_status(self):
        """Print current download status"""
        status = self.get_status_summary()
        
        print("\nDECEMBER 2022 0DTE DOWNLOAD STATUS")
        print("="*80)
        print(f"Total trading days: {status['total']}")
        print(f"Completed: {len(status['completed'])}")
        print(f"Pending: {len(status['pending'])}")
        print(f"Failed: {len(status['failed'])}")
        
        if status['completed']:
            print(f"\n✓ COMPLETED DAYS ({len(status['completed'])}):")
            print("-"*80)
            
            total_coverage = 0
            for day, info in status['completed']:
                coverage = info.get('coverage', 0)
                total_coverage += coverage
                print(f"  {day.strftime('%Y-%m-%d')} ({day.strftime('%a')}): "
                      f"{info['contracts']} contracts, {coverage:.1f}% coverage")
            
            avg_coverage = total_coverage / len(status['completed'])
            print(f"\nAverage coverage: {avg_coverage:.1f}%")
        
        if status['pending']:
            print(f"\n⏳ PENDING DAYS ({len(status['pending'])}):")
            print("-"*80)
            for day in status['pending'][:5]:  # Show first 5
                print(f"  {day.strftime('%Y-%m-%d')} ({day.strftime('%a')})")
            if len(status['pending']) > 5:
                print(f"  ... and {len(status['pending']) - 5} more")
        
        if status['failed']:
            print(f"\n✗ FAILED DAYS ({len(status['failed'])}):")
            print("-"*80)
            for day, info in status['failed']:
                print(f"  {day.strftime('%Y-%m-%d')}: {info.get('reason', 'Unknown error')}")
        
        # Overall stats
        print(f"\nOVERALL STATISTICS:")
        print("-"*80)
        print(f"Total contracts: {self.checkpoint['total_contracts']:,}")
        print(f"Total OHLC bars: {self.checkpoint['total_ohlc_bars']:,}")
        print(f"Total Greeks bars: {self.checkpoint['total_greeks_bars']:,}")
        print(f"Total IV bars: {self.checkpoint['total_iv_bars']:,}")
    
    def download_next_day(self, strikes: int = 40) -> bool:
        """Download the next pending day"""
        status = self.get_status_summary()
        
        if not status['pending']:
            print("No pending days to download")
            return False
        
        next_day = status['pending'][0]
        date_str = next_day.strftime('%Y-%m-%d')
        
        print(f"\nDownloading {date_str}...")
        
        # Run the daily downloader
        cmd = [
            'python3', 'download_december_day.py',
            '--date', date_str,
            '--strikes', str(strikes),
            '--checkpoint', self.checkpoint_file
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ Successfully downloaded {date_str}")
                
                # Reload checkpoint to get updated stats
                self.checkpoint = self.load_checkpoint()
                return True
            else:
                print(f"✗ Failed to download {date_str}")
                print(f"Error: {result.stderr}")
                
                # Mark as failed
                if date_str not in self.checkpoint['trading_days']:
                    self.checkpoint['trading_days'][date_str] = {}
                
                self.checkpoint['trading_days'][date_str]['status'] = 'failed'
                self.checkpoint['trading_days'][date_str]['reason'] = result.stderr[:100]
                self.save_checkpoint()
                
                return False
                
        except Exception as e:
            print(f"✗ Exception downloading {date_str}: {e}")
            return False
    
    def download_all_remaining(self, strikes: int = 40, max_days: int = None):
        """Download all remaining days"""
        status = self.get_status_summary()
        remaining = len(status['pending'])
        
        if not remaining:
            print("All days already downloaded!")
            return
        
        print(f"\nStarting download of {remaining} remaining days...")
        
        downloaded = 0
        failed = 0
        
        while True:
            if max_days and downloaded >= max_days:
                print(f"\nReached maximum days limit ({max_days})")
                break
            
            if not self.download_next_day(strikes):
                failed += 1
                # Continue with next day even if one fails
            else:
                downloaded += 1
            
            # Check if we're done
            status = self.get_status_summary()
            if not status['pending']:
                break
            
            print(f"\nProgress: {downloaded} downloaded, {failed} failed, "
                  f"{len(status['pending'])} remaining")
        
        print(f"\n{'='*80}")
        print(f"Download session complete!")
        print(f"Downloaded: {downloaded} days")
        print(f"Failed: {failed} days")
        
        # Final status
        self.print_status()
    
    def retry_failed_days(self, strikes: int = 40):
        """Retry all failed days"""
        status = self.get_status_summary()
        
        if not status['failed']:
            print("No failed days to retry")
            return
        
        print(f"\nRetrying {len(status['failed'])} failed days...")
        
        for day, info in status['failed']:
            date_str = day.strftime('%Y-%m-%d')
            
            # Reset status to allow retry
            self.checkpoint['trading_days'][date_str]['status'] = 'pending'
            self.save_checkpoint()
            
            # Try download
            if self.download_next_day(strikes):
                print(f"✓ Successfully retried {date_str}")
            else:
                print(f"✗ Failed again: {date_str}")
    
    def generate_report(self):
        """Generate comprehensive download report"""
        report_file = f"december_2022_final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        status = self.get_status_summary()
        
        report = {
            "summary": {
                "total_trading_days": status['total'],
                "completed_days": len(status['completed']),
                "failed_days": len(status['failed']),
                "pending_days": len(status['pending']),
                "total_contracts": self.checkpoint['total_contracts'],
                "total_ohlc_bars": self.checkpoint['total_ohlc_bars'],
                "total_greeks_bars": self.checkpoint['total_greeks_bars'],
                "total_iv_bars": self.checkpoint['total_iv_bars']
            },
            "daily_details": {},
            "failed_days": []
        }
        
        # Add daily details
        for day, info in status['completed']:
            date_str = day.strftime('%Y-%m-%d')
            report['daily_details'][date_str] = info
        
        # Add failed days
        for day, info in status['failed']:
            report['failed_days'].append({
                'date': day.strftime('%Y-%m-%d'),
                'reason': info.get('reason', 'Unknown')
            })
        
        # Calculate overall coverage
        if status['completed']:
            total_coverage = sum(info.get('coverage', 0) for _, info in status['completed'])
            report['summary']['average_coverage'] = total_coverage / len(status['completed'])
        
        # Save report
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Report saved to: {report_file}")
        
        return report

def main():
    parser = argparse.ArgumentParser(description='Manage December 2022 0DTE download progress')
    parser.add_argument('--status', action='store_true',
                       help='Show current download status')
    parser.add_argument('--start', action='store_true',
                       help='Start downloading remaining days')
    parser.add_argument('--next', action='store_true',
                       help='Download next pending day')
    parser.add_argument('--retry', action='store_true',
                       help='Retry failed days')
    parser.add_argument('--report', action='store_true',
                       help='Generate final report')
    parser.add_argument('--strikes', type=int, default=40,
                       help='Number of strikes above/below ATM (default: 40)')
    parser.add_argument('--max-days', type=int,
                       help='Maximum days to download in one session')
    parser.add_argument('--checkpoint', type=str, default='december_2022_progress.json',
                       help='Checkpoint file path')
    
    args = parser.parse_args()
    
    # Create manager
    manager = December2022ProgressManager(checkpoint_file=args.checkpoint)
    
    # Execute requested action
    if args.status:
        manager.print_status()
    elif args.next:
        manager.download_next_day(strikes=args.strikes)
    elif args.start:
        manager.download_all_remaining(strikes=args.strikes, max_days=args.max_days)
    elif args.retry:
        manager.retry_failed_days(strikes=args.strikes)
    elif args.report:
        manager.generate_report()
    else:
        # Default: show status
        manager.print_status()
        print("\nUse --help to see available commands")

if __name__ == "__main__":
    main()