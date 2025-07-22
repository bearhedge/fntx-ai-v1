#!/usr/bin/env python3
"""
Test the smart strike selection with download_day_strikes.py
"""
import subprocess
import sys
import json
import os

def test_smart_download():
    """Test downloading with smart strike selection"""
    test_date = "2023-01-03"
    
    print("="*80)
    print("TESTING SMART STRIKE SELECTION DOWNLOAD")
    print("="*80)
    print(f"Test date: {test_date}")
    print("This will use IV-based dynamic strike selection")
    print()
    
    # Run the download with smart selection
    cmd = [
        'python3', 'download_day_strikes.py',
        '--date', test_date
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n✓ Download successful!")
        
        # Load and display checkpoint stats
        checkpoint_file = f"checkpoint_{test_date.replace('-', '')}.json"
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
            
            print("\n📊 Download Statistics:")
            print(f"  Selection method: {checkpoint['stats'].get('strike_selection_method', 'unknown')}")
            print(f"  Total contracts: {checkpoint['stats']['total_contracts']}")
            print(f"  Total OHLC bars: {checkpoint['stats']['total_ohlc_bars']}")
            print(f"  Coverage: {checkpoint['stats'].get('coverage', 0):.1f}%")
            
            if 'smart_strikes' in checkpoint and checkpoint['smart_strikes']['strikes']:
                strikes = checkpoint['smart_strikes']['strikes']
                print(f"  Smart strikes: {len(strikes)} (${min(strikes)}-${max(strikes)})")
            
            if checkpoint['stats'].get('atm_iv'):
                print(f"  ATM IV: {checkpoint['stats']['atm_iv']:.1%}")
        
        print("\n✓ Smart selection test complete!")
        print("\nComparison:")
        print("  Old system: 80 contracts across $352-$392")
        print(f"  Smart system: {checkpoint['stats']['total_contracts']} contracts")
        
        return 0
    else:
        print("\n✗ Test failed!")
        return 1

if __name__ == "__main__":
    sys.exit(test_smart_download())