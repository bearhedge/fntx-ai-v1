"""
FNTX PnL Command - Display profit and loss summaries
"""
import click
import os
import sys
import json
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from typing import Dict, List

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

console = Console()

@click.command()
@click.option('--days', default=7, help='Number of days to show (default: 7)')
@click.option('--detailed', is_flag=True, help='Show detailed trade breakdown')
def pnl(days: int, detailed: bool):
    """Display P&L summaries for recent trading activity"""
    
    config_dir = os.path.expanduser("~/.fntx")
    
    if not os.path.exists(os.path.join(config_dir, "ib_config.json")):
        console.print("[red]Error:[/red] Not connected to IB Gateway. Run: fntx connect ibkr")
        return
    
    try:
        from ib_insync import IB
        
        ib = IB()
        with open(os.path.join(config_dir, "ib_config.json")) as f:
            ib_config = json.load(f)
        
        ib.connect('127.0.0.1', ib_config['port'], clientId=ib_config['client_id'])
        
        # Get account P&L
        account_values = ib.accountSummary()
        account_info = {item.tag: item.value for item in account_values}
        
        # Today's P&L
        daily_pnl = float(account_info.get('DailyPnL', 0))
        unrealized_pnl = float(account_info.get('UnrealizedPnL', 0))
        realized_pnl = float(account_info.get('RealizedPnL', 0))
        
        # Display summary
        console.print(Panel(
            f"[bold]P&L Summary[/bold]\n\n"
            f"[cyan]Today's P&L:[/cyan] [{'green' if daily_pnl >= 0 else 'red'}]${daily_pnl:,.2f}[/{'green' if daily_pnl >= 0 else 'red'}]\n"
            f"[cyan]Unrealized P&L:[/cyan] [{'green' if unrealized_pnl >= 0 else 'red'}]${unrealized_pnl:,.2f}[/{'green' if unrealized_pnl >= 0 else 'red'}]\n"
            f"[cyan]Realized P&L:[/cyan] [{'green' if realized_pnl >= 0 else 'red'}]${realized_pnl:,.2f}[/{'green' if realized_pnl >= 0 else 'red'}]",
            title=f"Account P&L - {datetime.now().strftime('%Y-%m-%d')}"
        ))
        
        # Historical P&L from trades
        if days > 1:
            console.print("\n[bold]Historical P&L[/bold]")
            display_historical_pnl(days, detailed)
        
        # Trade statistics
        if detailed:
            console.print("\n[bold]Trade Statistics[/bold]")
            display_trade_statistics()
        
        ib.disconnect()
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if 'ib' in locals():
            ib.disconnect()

def display_historical_pnl(days: int, detailed: bool):
    """Display historical P&L from trade logs"""
    log_dir = os.path.expanduser("~/.fntx/trades")
    
    if not os.path.exists(log_dir):
        console.print("[yellow]No historical trade data found[/yellow]")
        return
    
    # Create table
    table = Table(box=box.SIMPLE)
    table.add_column("Date", style="cyan")
    table.add_column("Trades", justify="center")
    table.add_column("Contracts", justify="center")
    table.add_column("P&L", justify="right")
    
    total_pnl = 0
    total_trades = 0
    total_contracts = 0
    
    # Get trade files for last N days
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime('%Y%m%d')
        log_file = os.path.join(log_dir, f"trades_{date_str}.json")
        
        if os.path.exists(log_file):
            with open(log_file) as f:
                trades = json.load(f)
            
            daily_trades = len(trades)
            daily_contracts = sum(t.get('contracts', 0) for t in trades)
            daily_pnl = sum(t.get('pnl', 0) for t in trades)  # Assuming PnL is tracked
            
            total_trades += daily_trades
            total_contracts += daily_contracts
            total_pnl += daily_pnl
            
            pnl_color = "green" if daily_pnl >= 0 else "red"
            
            table.add_row(
                date.strftime('%Y-%m-%d'),
                str(daily_trades),
                str(daily_contracts),
                f"[{pnl_color}]${daily_pnl:,.2f}[/{pnl_color}]"
            )
    
    if total_trades > 0:
        table.add_row("", "", "", "")  # Separator
        table.add_row(
            "[bold]Total[/bold]",
            f"[bold]{total_trades}[/bold]",
            f"[bold]{total_contracts}[/bold]",
            f"[bold][{'green' if total_pnl >= 0 else 'red'}]${total_pnl:,.2f}[/{'green' if total_pnl >= 0 else 'red'}][/bold]"
        )
    
    console.print(table)

def display_trade_statistics():
    """Display detailed trade statistics"""
    log_dir = os.path.expanduser("~/.fntx/trades")
    
    if not os.path.exists(log_dir):
        return
    
    all_trades = []
    
    # Collect all trades from last 30 days
    for i in range(30):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime('%Y%m%d')
        log_file = os.path.join(log_dir, f"trades_{date_str}.json")
        
        if os.path.exists(log_file):
            with open(log_file) as f:
                trades = json.load(f)
                all_trades.extend(trades)
    
    if not all_trades:
        console.print("[yellow]No trade statistics available[/yellow]")
        return
    
    # Calculate statistics
    total_trades = len(all_trades)
    avg_contracts = sum(t.get('contracts', 0) for t in all_trades) / total_trades if total_trades > 0 else 0
    
    # Delta distribution
    deltas = [t.get('delta', 0) for t in all_trades if 'delta' in t]
    avg_delta = sum(deltas) / len(deltas) if deltas else 0
    
    stats_table = Table(show_header=False, box=box.SIMPLE)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", justify="right")
    
    stats_table.add_row("Total Trades (30d)", str(total_trades))
    stats_table.add_row("Avg Contracts/Trade", f"{avg_contracts:.1f}")
    stats_table.add_row("Avg Delta", f"{avg_delta:.3f}")
    stats_table.add_row("Win Rate", "[dim]Requires execution data[/dim]")
    stats_table.add_row("Avg Win", "[dim]Requires execution data[/dim]")
    stats_table.add_row("Avg Loss", "[dim]Requires execution data[/dim]")
    
    console.print(stats_table)