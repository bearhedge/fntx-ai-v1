#!/usr/bin/env python3
"""
Show All NFT Views - Non-interactive demo of all visualization modes
"""

import sys
sys.path.append('..')
from defi.cli.nft_terminal_viewer import TerminalNFTViewer
from datetime import datetime
from rich.console import Console

def main():
    """Show all NFT visualization modes"""
    
    console = Console()
    viewer = TerminalNFTViewer()
    
    # Sample trading data
    sample_metrics = {
        'date': '2025-01-26',
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
        'max_drawdown_30d': -5.2,
        'dpi': 0.075,
        'tvpi': 1.087,
        'rvpi': 1.087,
    }
    
    console.print("\n[bold cyan]🚀 FNTX Trading NFT Terminal Viewer - All Views Demo[/bold cyan]\n")
    
    # 1. Trading Card View
    console.print("\n[bold yellow]1. Trading Card View[/bold yellow]")
    console.print("[dim]This is how your daily trading performance looks as an NFT card:[/dim]\n")
    viewer.display_trading_nft(sample_metrics, mode='card')
    
    console.print("\n" + "="*80 + "\n")
    
    # 2. ASCII Art View  
    console.print("[bold yellow]2. ASCII Art View[/bold yellow]")
    console.print("[dim]Pure ASCII representation for maximum compatibility:[/dim]\n")
    viewer.display_trading_nft(sample_metrics, mode='ascii')
    
    console.print("\n" + "="*80 + "\n")
    
    # 3. Chart View
    console.print("[bold yellow]3. Chart View[/bold yellow]")
    console.print("[dim]Performance visualization with charts and graphs:[/dim]\n")
    viewer.display_trading_nft(sample_metrics, mode='chart')
    
    console.print("\n" + "="*80 + "\n")
    
    # 4. Detailed View
    console.print("[bold yellow]4. Detailed Metrics View[/bold yellow]")
    console.print("[dim]All metrics in organized tables:[/dim]\n")
    viewer.display_trading_nft(sample_metrics, mode='detailed')
    
    console.print("\n" + "="*80 + "\n")
    
    # 5. Gallery View
    console.print("[bold yellow]5. Gallery View (Multiple Days)[/bold yellow]")
    console.print("[dim]Browse multiple trading days at once:[/dim]\n")
    
    # Generate multiple days
    records = []
    for i in range(7):
        record = sample_metrics.copy()
        record['date'] = f"2025-01-{20+i}"
        record['net_pnl'] = sample_metrics['net_pnl'] + (i - 3) * 500
        record['win_rate'] = 65 + i * 3
        record['sharpe_30d'] = 1.5 + i * 0.2
        records.append(record)
    
    viewer._display_gallery_view(records)
    
    console.print("\n" + "="*80 + "\n")
    
    console.print("[bold green]✅ Demo Complete![/bold green]")
    console.print("\n[dim]This is how your trading performance will be displayed in the terminal.")
    console.print("Each day creates a unique NFT stored on the blockchain.")
    console.print("You have 24 hours to correct any mistakes before it becomes permanent.[/dim]\n")
    
    console.print("[bold]Key Features:[/bold]")
    console.print("• Multiple visualization modes for different preferences")
    console.print("• Rich terminal graphics without needing a web browser")
    console.print("• All data stored immutably on blockchain")
    console.print("• 24-hour grace period for corrections")
    console.print("• Visual representation of P&L, Greeks, and performance metrics\n")


if __name__ == "__main__":
    main()