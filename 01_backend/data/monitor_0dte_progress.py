#!/usr/bin/env python3
"""
Real-time monitoring dashboard for 0DTE download progress
Shows current status, speed, and estimates
"""
import sys
import os
import json
import time
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import argparse

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

class ProgressMonitor:
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        self.master_checkpoint_file = f"{checkpoint_dir}/master_progress.json"
        
    def load_master_checkpoint(self) -> Optional[Dict]:
        """Load master checkpoint"""
        if os.path.exists(self.master_checkpoint_file):
            with open(self.master_checkpoint_file, 'r') as f:
                return json.load(f)
        return None
    
    def get_current_month_status(self) -> Optional[Dict]:
        """Get status of currently downloading month"""
        # Find most recently modified monthly checkpoint
        monthly_files = [f for f in os.listdir(self.checkpoint_dir) 
                        if f.startswith('monthly_') and f.endswith('.json')]
        
        if not monthly_files:
            return None
        
        # Get most recent
        latest_file = max(monthly_files, 
                         key=lambda f: os.path.getmtime(os.path.join(self.checkpoint_dir, f)))
        
        with open(os.path.join(self.checkpoint_dir, latest_file), 'r') as f:
            month_data = json.load(f)
        
        # Extract month info from filename
        parts = latest_file.replace('monthly_', '').replace('.json', '').split('_')
        year = int(parts[0])
        month = int(parts[1])
        
        return {
            'year': year,
            'month': month,
            'data': month_data
        }
    
    def get_current_day_status(self) -> Optional[Dict]:
        """Get status of currently downloading day"""
        # Find most recently modified day checkpoint
        day_files = [f for f in os.listdir('.') 
                    if f.startswith('checkpoint_') and f.endswith('.json')]
        
        if not day_files:
            return None
        
        # Get most recent
        latest_file = max(day_files, 
                         key=lambda f: os.path.getmtime(f))
        
        # Skip if not modified recently (within 5 minutes)
        if time.time() - os.path.getmtime(latest_file) > 300:
            return None
        
        with open(latest_file, 'r') as f:
            day_data = json.load(f)
        
        return {
            'date': day_data.get('date'),
            'data': day_data
        }
    
    def get_database_stats(self) -> Dict:
        """Get current database statistics"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Total contracts
            cursor.execute("SELECT COUNT(*) FROM theta.options_contracts WHERE symbol='SPY'")
            total_contracts = cursor.fetchone()[0]
            
            # Total OHLC bars
            cursor.execute("SELECT COUNT(*) FROM theta.options_ohlc")
            total_ohlc = cursor.fetchone()[0]
            
            # Date range
            cursor.execute("""
                SELECT MIN(oc.expiration), MAX(oc.expiration)
                FROM theta.options_contracts oc
                WHERE symbol='SPY'
            """)
            date_range = cursor.fetchone()
            
            # Recent activity (last hour)
            cursor.execute("""
                SELECT COUNT(DISTINCT contract_id)
                FROM theta.options_ohlc
                WHERE datetime > NOW() - INTERVAL '1 hour'
            """)
            recent_contracts = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return {
                'total_contracts': total_contracts,
                'total_ohlc_bars': total_ohlc,
                'date_range': date_range,
                'recent_contracts': recent_contracts
            }
        except Exception as e:
            return {
                'error': str(e),
                'total_contracts': 0,
                'total_ohlc_bars': 0
            }
    
    def calculate_speed(self, master_data: Dict) -> Dict:
        """Calculate download speed and estimates"""
        if not master_data.get('start_time'):
            return {'error': 'No start time recorded'}
        
        start_time = datetime.fromisoformat(master_data['start_time'])
        elapsed = datetime.now() - start_time
        elapsed_hours = elapsed.total_seconds() / 3600
        
        stats = master_data['stats']
        completed_days = stats['completed_days']
        
        if elapsed_hours > 0 and completed_days > 0:
            days_per_hour = completed_days / elapsed_hours
            contracts_per_hour = stats['total_contracts'] / elapsed_hours
            
            remaining_days = stats['total_days'] - completed_days
            estimated_hours = remaining_days / days_per_hour if days_per_hour > 0 else 0
            
            return {
                'days_per_hour': days_per_hour,
                'contracts_per_hour': contracts_per_hour,
                'elapsed_hours': elapsed_hours,
                'estimated_hours_remaining': estimated_hours
            }
        
        return {
            'days_per_hour': 0,
            'contracts_per_hour': 0,
            'elapsed_hours': elapsed_hours
        }
    
    def display_dashboard(self, refresh_interval: int = 30):
        """Display live dashboard"""
        try:
            while True:
                # Clear screen
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # Load data
                master_data = self.load_master_checkpoint()
                current_month = self.get_current_month_status()
                current_day = self.get_current_day_status()
                db_stats = self.get_database_stats()
                
                # Header
                print("=" * 100)
                print("0DTE DOWNLOAD PROGRESS MONITOR".center(100))
                print(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(100))
                print("=" * 100)
                
                if master_data:
                    stats = master_data['stats']
                    speed = self.calculate_speed(master_data)
                    
                    # Overall Progress
                    print("\n📊 OVERALL PROGRESS")
                    print("-" * 50)
                    print(f"Phase: {master_data['current_phase'].upper()}")
                    print(f"Months: {stats['completed_months']}/{stats['total_months']} "
                          f"({stats['completed_months']/stats['total_months']*100:.1f}%)")
                    print(f"Days: {stats['completed_days']}/{stats['total_days']} "
                          f"({stats['completed_days']/stats['total_days']*100:.1f}%)")
                    
                    # Progress bar
                    progress = stats['completed_days'] / stats['total_days'] if stats['total_days'] > 0 else 0
                    bar_length = 40
                    filled = int(bar_length * progress)
                    bar = "█" * filled + "░" * (bar_length - filled)
                    print(f"Progress: [{bar}] {progress*100:.1f}%")
                    
                    # Speed metrics
                    print(f"\n⚡ SPEED METRICS")
                    print("-" * 50)
                    print(f"Days/hour: {speed.get('days_per_hour', 0):.2f}")
                    print(f"Contracts/hour: {speed.get('contracts_per_hour', 0):.0f}")
                    print(f"Elapsed: {speed.get('elapsed_hours', 0):.1f} hours")
                    print(f"ETA: {speed.get('estimated_hours_remaining', 0):.1f} hours")
                    
                    if speed.get('estimated_hours_remaining', 0) > 0:
                        eta_datetime = datetime.now() + timedelta(hours=speed['estimated_hours_remaining'])
                        print(f"Completion: {eta_datetime.strftime('%Y-%m-%d %H:%M')}")
                
                # Current Month
                if current_month:
                    month_data = current_month['data']
                    print(f"\n📅 CURRENT MONTH: {current_month['year']}-{current_month['month']:02d}")
                    print("-" * 50)
                    
                    month_days = len(month_data['days'])
                    completed_days = sum(1 for d in month_data['days'].values() 
                                       if d['status'] == 'complete')
                    print(f"Days: {completed_days}/{month_days}")
                    print(f"Contracts: {month_data['stats']['total_contracts']:,}")
                    
                    # Recent days
                    recent_days = sorted(month_data['days'].items(), 
                                       key=lambda x: x[0], reverse=True)[:5]
                    print("\nRecent days:")
                    for date, info in recent_days:
                        status_icon = "✓" if info['status'] == 'complete' else "⏳"
                        contracts = info.get('contracts', 0)
                        print(f"  {status_icon} {date}: {contracts} contracts")
                
                # Current Day
                if current_day:
                    day_data = current_day['data']
                    print(f"\n📍 CURRENT DAY: {current_day['date']}")
                    print("-" * 50)
                    
                    # Core vs Extended progress
                    core = day_data['core_strikes']
                    extended = day_data['extended_strikes']
                    
                    print(f"Core strikes: {core['status']} ({core['contracts']} contracts)")
                    print(f"Extended strikes: {extended['status']} ({extended['contracts']} contracts)")
                    
                    if day_data['stats']['atm_strike']:
                        print(f"ATM strike: ${day_data['stats']['atm_strike']}")
                        print(f"SPY open: ${day_data['stats']['spy_open']:.2f}")
                
                # Database Stats
                print(f"\n💾 DATABASE STATS")
                print("-" * 50)
                if 'error' not in db_stats:
                    print(f"Total contracts: {db_stats['total_contracts']:,}")
                    print(f"Total OHLC bars: {db_stats['total_ohlc_bars']:,}")
                    print(f"Recent activity: {db_stats['recent_contracts']} contracts (last hour)")
                    
                    if db_stats['date_range'][0]:
                        print(f"Date range: {db_stats['date_range'][0]} to {db_stats['date_range'][1]}")
                else:
                    print(f"Database error: {db_stats['error']}")
                
                # Footer
                print(f"\n{'='*100}")
                print(f"Refreshing every {refresh_interval} seconds... (Ctrl+C to exit)")
                
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")
    
    def generate_report(self, output_file: str = None):
        """Generate a comprehensive progress report"""
        master_data = self.load_master_checkpoint()
        
        if not master_data:
            print("No master checkpoint found!")
            return
        
        report = []
        report.append("=" * 80)
        report.append("0DTE DOWNLOAD PROGRESS REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        
        stats = master_data['stats']
        
        # Summary
        report.append("\nSUMMARY:")
        report.append(f"  Date range: {master_data['start_date']} to {master_data['end_date']}")
        report.append(f"  Current phase: {master_data['current_phase']}")
        report.append(f"  Months completed: {stats['completed_months']}/{stats['total_months']}")
        report.append(f"  Days completed: {stats['completed_days']}/{stats['total_days']}")
        report.append(f"  Total contracts: {stats['total_contracts']:,}")
        report.append(f"  Total OHLC bars: {stats['total_ohlc_bars']:,}")
        
        # Time analysis
        if master_data.get('start_time'):
            start_time = datetime.fromisoformat(master_data['start_time'])
            elapsed = datetime.now() - start_time
            report.append(f"\nTIME ANALYSIS:")
            report.append(f"  Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            report.append(f"  Elapsed: {elapsed.days} days, {elapsed.seconds//3600} hours")
            
            speed = self.calculate_speed(master_data)
            report.append(f"  Speed: {speed.get('days_per_hour', 0):.2f} days/hour")
            report.append(f"  ETA: {speed.get('estimated_hours_remaining', 0):.1f} hours")
        
        # Monthly breakdown
        report.append(f"\nMONTHLY BREAKDOWN:")
        report.append(f"{'Month':<10} {'Status':<12} {'Days':<15} {'Contracts':<12}")
        report.append("-" * 60)
        
        for month_key, month_info in sorted(master_data['months'].items()):
            status = "Complete" if month_info['completed_days'] == month_info['total_days'] else "Partial"
            days = f"{month_info['completed_days']}/{month_info['total_days']}"
            contracts = f"{month_info['contracts']:,}"
            report.append(f"{month_key:<10} {status:<12} {days:<15} {contracts:<12}")
        
        # Output
        report_text = "\n".join(report)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"Report saved to: {output_file}")
        else:
            print(report_text)

def main():
    parser = argparse.ArgumentParser(description='Monitor 0DTE download progress')
    parser.add_argument('--dashboard', action='store_true',
                       help='Show live dashboard')
    parser.add_argument('--report', action='store_true',
                       help='Generate progress report')
    parser.add_argument('--output', type=str,
                       help='Output file for report')
    parser.add_argument('--refresh', type=int, default=30,
                       help='Dashboard refresh interval in seconds')
    parser.add_argument('--checkpoint-dir', type=str, default='checkpoints',
                       help='Directory for checkpoint files')
    
    args = parser.parse_args()
    
    monitor = ProgressMonitor(checkpoint_dir=args.checkpoint_dir)
    
    if args.dashboard:
        monitor.display_dashboard(refresh_interval=args.refresh)
    elif args.report:
        monitor.generate_report(output_file=args.output)
    else:
        # Show quick status
        master_data = monitor.load_master_checkpoint()
        if master_data:
            stats = master_data['stats']
            print(f"Progress: {stats['completed_days']}/{stats['total_days']} days "
                  f"({stats['completed_days']/stats['total_days']*100:.1f}%)")
            print(f"Contracts: {stats['total_contracts']:,}")
            print(f"Phase: {master_data['current_phase']}")
        else:
            print("No download in progress")

if __name__ == "__main__":
    sys.exit(main())