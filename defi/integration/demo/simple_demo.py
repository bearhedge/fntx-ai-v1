#!/usr/bin/env python3
"""
Simple CLI Demo - Shows NFT visualization in terminal without dependencies
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append('..')
from defi.cli.nft_terminal_viewer import TerminalNFTViewer


def main():
    """Run simple NFT visualization demo"""
    
    viewer = TerminalNFTViewer()
    
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("\n🚀 FNTX Trading NFT Terminal Viewer Demo\n")
    print("This demo shows how your trading performance looks as NFTs in the terminal.\n")
    
    # Sample trading data
    sample_metrics = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'net_pnl': 2450.50,
        'opening_balance': 215000,
        'closing_balance': 217450.50,
        'gross_pnl': 2650,
        'commissions': -150,
        'interest_expense': -50,
        'win_rate': 82.5,
        'win_rate_30d': 82.5,
        'win_rate_mtd': 79.2,
        'win_rate_ytd': 77.8,
        'win_rate_all_time': 75.5,
        'sharpe_30d': 2.3,
        'sharpe_mtd': 2.1,
        'sharpe_ytd': 1.9,
        'sharpe_all_time': 1.8,
        'volatility_30d': 12.5,
        'volatility_mtd': 11.8,
        'volatility_ytd': 10.9,
        'volatility_all_time': 10.2,
        'contracts_traded': 67,
        'implied_turnover': 3015000,
        'delta_exposure': -0.15,
        'gamma_exposure': 0.023,
        'theta_decay': 125,
        'vega_exposure': -50,
        'token_id': 1,
        'version': 1,
        'deposits': 0,
        'withdrawals': 0,
        'other_fees': 0,
    }
    
    while True:
        print("Choose a view mode:")
        print("1. Trading Card View")
        print("2. Chart View")
        print("3. Detailed Metrics")
        print("4. ASCII Art View")
        print("5. Gallery View (Multiple Days)")
        print("6. Exit")
        
        choice = input("\nSelect (1-6): ")
        
        if choice == '1':
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n📊 Trading Card View\n")
            viewer.display_trading_nft(sample_metrics, mode='card')
        
        elif choice == '2':
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n📈 Chart View\n")
            viewer.display_trading_nft(sample_metrics, mode='chart')
        
        elif choice == '3':
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n📋 Detailed Metrics View\n")
            viewer.display_trading_nft(sample_metrics, mode='detailed')
        
        elif choice == '4':
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n🎨 ASCII Art View\n")
            viewer.display_trading_nft(sample_metrics, mode='ascii')
        
        elif choice == '5':
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n🖼️  Gallery View\n")
            
            # Generate multiple days
            records = []
            for i in range(7):
                record = sample_metrics.copy()
                record['date'] = f"2025-01-{20+i}"
                record['net_pnl'] = sample_metrics['net_pnl'] + (i - 3) * 500
                record['win_rate'] = 65 + i * 3
                records.append(record)
            
            viewer._display_gallery_view(records)
        
        elif choice == '6':
            print("\nThanks for trying the FNTX NFT viewer! 👋")
            break
        
        else:
            print("Invalid choice, please try again.")
            continue
        
        input("\nPress Enter to continue...")
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n🚀 FNTX Trading NFT Terminal Viewer Demo\n")


if __name__ == "__main__":
    main()