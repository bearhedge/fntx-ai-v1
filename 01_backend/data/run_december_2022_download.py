#!/usr/bin/env python3
"""
Master script to execute December 2022 0DTE SPY options download
Coordinates cleanup, setup, download, and validation
"""
import subprocess
import sys
import os
from datetime import datetime

def run_command(cmd, description):
    """Run a command and handle output"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd='/home/info/fntx-ai-v1/01_backend/data'
        )
        
        if result.stdout:
            print(result.stdout)
        
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    """Execute complete December 2022 download workflow"""
    print("DECEMBER 2022 SPY 0DTE OPTIONS DOWNLOAD WORKFLOW")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description='December 2022 0DTE Download Workflow')
    parser.add_argument('--skip-cleanup', action='store_true', 
                       help='Skip database cleanup step')
    parser.add_argument('--skip-timescale', action='store_true',
                       help='Skip TimescaleDB setup')
    parser.add_argument('--skip-validation', action='store_true',
                       help='Skip post-download validation')
    parser.add_argument('--strikes', type=int, default=40,
                       help='Number of strikes above/below ATM (default: 40)')
    
    args = parser.parse_args()
    
    # Step 1: Database cleanup
    if not args.skip_cleanup:
        print("\n📌 Step 1: Database Cleanup")
        if not run_command(
            "python3 clean_december_2022_data.py",
            "Cleaning existing December 2022 data"
        ):
            print("❌ Cleanup failed. Use --skip-cleanup to bypass.")
            return 1
    else:
        print("\n⏭️  Skipping database cleanup")
    
    # Step 2: TimescaleDB setup
    if not args.skip_timescale:
        print("\n📌 Step 2: TimescaleDB Setup")
        if not run_command(
            "python3 setup_timescaledb.py",
            "Setting up TimescaleDB optimizations"
        ):
            print("⚠️  TimescaleDB setup failed. Continuing with standard PostgreSQL.")
    else:
        print("\n⏭️  Skipping TimescaleDB setup")
    
    # Step 3: Download data
    print("\n📌 Step 3: Download December 2022 Data")
    download_cmd = f"python3 december_2022_0dte_enhanced.py --strikes {args.strikes}"
    
    if not run_command(
        download_cmd,
        f"Downloading with ±{args.strikes} strikes from ATM"
    ):
        print("❌ Download failed!")
        return 1
    
    # Step 4: Validate data
    if not args.skip_validation:
        print("\n📌 Step 4: Validate Downloaded Data")
        if not run_command(
            "python3 validate_december_2022_data.py",
            "Running comprehensive validation"
        ):
            print("⚠️  Validation found issues. Check the report for details.")
    else:
        print("\n⏭️  Skipping validation")
    
    # Summary
    print("\n" + "="*80)
    print("WORKFLOW COMPLETE")
    print("="*80)
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check logs
    log_dir = "/home/info/fntx-ai-v1/08_logs"
    print(f"\n📄 Check these files for detailed reports:")
    
    # Find most recent report files
    import glob
    reports = sorted(glob.glob(f"{log_dir}/december_2022_*.json"), reverse=True)
    for report in reports[:2]:  # Show last 2 reports
        print(f"   - {report}")
    
    print("\n✅ December 2022 0DTE download workflow completed successfully!")
    
    # Quick stats
    print("\n📊 Quick Database Check:")
    run_command(
        """psql -d options_data -c "SELECT COUNT(*) as contracts, 
        MIN(expiration) as first_date, MAX(expiration) as last_date 
        FROM theta.options_contracts 
        WHERE symbol='SPY' AND expiration >= '2022-12-01' AND expiration <= '2022-12-31'" """,
        "Checking downloaded contracts"
    )
    
    return 0

if __name__ == "__main__":
    sys.exit(main())