#!/usr/bin/env python3
"""
Monthly ALM Report Archiver
Runs at end of each month to save the full month's performance report
"""

import os
import sys
import subprocess
from datetime import datetime, date
from pathlib import Path
import shutil

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
DATA_BASE_DIR = "/home/info/fntx-ai-v1/database/ibkr/data"
ALM_SCRIPT = "/home/info/fntx-ai-v1/backend/alm/calculation_engine_v1.py"

def ensure_month_directory(year, month):
    """Create month directory if it doesn't exist"""
    month_name = datetime(year, month, 1).strftime("%B")
    # Use the same format as IBKR data directories: "MonthYear"
    month_dir = os.path.join(DATA_BASE_DIR, f"{month_name}{year}")
    Path(month_dir).mkdir(parents=True, exist_ok=True)
    return month_dir

def run_calculation_engine():
    """Run the calculation engine and capture output"""
    try:
        result = subprocess.run(
            ["python3", ALM_SCRIPT],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(ALM_SCRIPT)
        )
        
        if result.returncode != 0:
            print(f"Error running calculation engine: {result.stderr}")
            return None
            
        return result.stdout
    except Exception as e:
        print(f"Failed to run calculation engine: {e}")
        return None

def save_monthly_report(year, month, report_content):
    """Save the report to the appropriate month directory"""
    month_dir = ensure_month_directory(year, month)
    month_name = datetime(year, month, 1).strftime("%B")
    
    # Create filename like "July_2025_Track_Record.txt"
    filename = f"{month_name}_{year}_Track_Record.txt"
    filepath = os.path.join(month_dir, filename)
    
    # Save the report
    with open(filepath, 'w') as f:
        f.write(f"# {month_name} {year} ALM Trading Track Record\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        f.write(report_content)
    
    print(f"Monthly report saved to: {filepath}")
    return filepath

def main():
    """Main function - runs at end of month"""
    # Get current date
    today = date.today()
    
    # If running on last day of month or first day of next month
    # (in case cron runs slightly after midnight)
    if today.day == 1:
        # Use previous month
        if today.month == 1:
            year = today.year - 1
            month = 12
        else:
            year = today.year
            month = today.month - 1
    else:
        year = today.year
        month = today.month
    
    print(f"Generating ALM report for {datetime(year, month, 1).strftime('%B %Y')}...")
    
    # Run calculation engine
    report_content = run_calculation_engine()
    
    if report_content:
        # Save the report
        filepath = save_monthly_report(year, month, report_content)
        
        # Also create a symlink to latest report
        latest_link = os.path.join(DATA_BASE_DIR, "latest_monthly_report.txt")
        if os.path.exists(latest_link):
            os.remove(latest_link)
        os.symlink(filepath, latest_link)
        
        print("Monthly ALM report archived successfully!")
    else:
        print("Failed to generate monthly report")
        sys.exit(1)

if __name__ == "__main__":
    main()