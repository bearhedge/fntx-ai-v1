#!/usr/bin/env python3
"""
Test script to verify the strike-aware download system
Tests a single day download with the new two-tier strategy
"""
import subprocess
import sys
from datetime import datetime

def test_single_day():
    """Test downloading a single recent day"""
    # Use a recent trading day
    test_date = "2023-01-03"  # First trading day of January 2023
    
    print("="*80)
    print("TESTING STRIKE-AWARE DOWNLOAD SYSTEM")
    print("="*80)
    print(f"Test date: {test_date}")
    print("This will download both core (±10) and extended (±11-20) strikes")
    print()
    
    # Run the download
    cmd = [
        'python3', 'download_day_strikes.py',
        '--date', test_date
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n✓ Test successful!")
        print("\nYou can now:")
        print("1. Check the checkpoint file: checkpoint_20230103.json")
        print("2. Query the database to see the downloaded data")
        print("3. Run the monthly manager: python3 monthly_parallel_manager.py --year 2023 --month 1 --status")
        print("4. Start the full download: python3 master_0dte_orchestrator.py --run")
        return 0
    else:
        print("\n✗ Test failed!")
        print("Please check the error messages above")
        return 1

if __name__ == "__main__":
    sys.exit(test_single_day())