"""
FNTX Status Command - Display account status and positions
"""
import click
import os
import sys
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from typing import Dict, List

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

console = Console()

@click.command()
@click.option('--detailed', is_flag=True, help='Show detailed account information')
def status(detailed: bool):
    """Display account status and current positions"""
    
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
        
        # Get account summary
        account_values = ib.accountSummary()
        account_info = {item.tag: item.value for item in account_values}
        
        # Create layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        # Header
        layout["header"].update(
            Panel(f"[bold cyan]FNTX Account Status[/bold cyan] - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        )
        
        # Main content split
        layout["main"].split_row(
            Layout(name="account"),
            Layout(name="positions")
        )
        
        # Account summary
        account_table = Table(title="Account Summary", show_header=False)
        account_table.add_column("Metric", style="cyan")
        account_table.add_column("Value", style="white", justify="right")
        
        # Key metrics
        metrics = {
            "Net Liquidation": f"${float(account_info.get('NetLiquidation', 0)):,.2f}",
            "Available Funds": f"${float(account_info.get('AvailableFunds', 0)):,.2f}",
            "Buying Power": f"${float(account_info.get('BuyingPower', 0)):,.2f}",
            "Daily P&L": f"${float(account_info.get('DailyPnL', 0)):,.2f}",
            "Unrealized P&L": f"${float(account_info.get('UnrealizedPnL', 0)):,.2f}",
            "Realized P&L": f"${float(account_info.get('RealizedPnL', 0)):,.2f}",
        }
        
        for metric, value in metrics.items():
            account_table.add_row(metric, value)
        
        if detailed:
            account_table.add_row("", "")  # Spacer
            account_table.add_row("Maintenance Margin", f"${float(account_info.get('MaintMarginReq', 0)):,.2f}")
            account_table.add_row("Initial Margin", f"${float(account_info.get('InitMarginReq', 0)):,.2f}")
            account_table.add_row("Excess Liquidity", f"${float(account_info.get('ExcessLiquidity', 0)):,.2f}")
        
        layout["account"].update(Panel(account_table))
        
        # Positions
        positions = ib.positions()
        positions_table = Table(title="Open Positions")
        positions_table.add_column("Symbol", style="cyan")
        positions_table.add_column("Type", style="white")
        positions_table.add_column("Qty", style="white", justify="right")
        positions_table.add_column("Avg Cost", style="white", justify="right")
        positions_table.add_column("Mkt Value", style="white", justify="right")
        positions_table.add_column("P&L", justify="right")
        
        total_pnl = 0
        for pos in positions:
            pnl = pos.unrealizedPNL if pos.unrealizedPNL else 0
            total_pnl += pnl
            
            pnl_color = "green" if pnl >= 0 else "red"
            
            if pos.contract.secType == 'OPT':
                positions_table.add_row(
                    f"{pos.contract.symbol} {pos.contract.strike}{pos.contract.right}",
                    pos.contract.lastTradeDateOrContractMonth,
                    str(pos.position),
                    f"${pos.avgCost:.2f}",
                    f"${pos.marketValue:.2f}" if pos.marketValue else "N/A",
                    f"[{pnl_color}]${pnl:.2f}[/{pnl_color}]"
                )
            else:
                positions_table.add_row(
                    pos.contract.symbol,
                    pos.contract.secType,
                    str(pos.position),
                    f"${pos.avgCost:.2f}",
                    f"${pos.marketValue:.2f}" if pos.marketValue else "N/A",
                    f"[{pnl_color}]${pnl:.2f}[/{pnl_color}]"
                )
        
        if not positions:
            positions_table.add_row("[dim]No open positions[/dim]", "", "", "", "", "")
        else:
            positions_table.add_row("", "", "", "", "[bold]Total:[/bold]", 
                                   f"[{'green' if total_pnl >= 0 else 'red'}]${total_pnl:.2f}")
        
        layout["positions"].update(Panel(positions_table))
        
        # Footer - Trading rules reminder
        rules_text = (
            "[dim]Trading Rules: Max 5 contracts/day | Delta < 0.15 | Exit by 3:45 PM[/dim]"
        )
        layout["footer"].update(Panel(rules_text, style="dim"))
        
        console.print(layout)
        
        # Check daily limits
        check_daily_limits()
        
        ib.disconnect()
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if 'ib' in locals():
            ib.disconnect()

def check_daily_limits():
    """Check if daily trading limits have been reached"""
    log_dir = os.path.expanduser("~/.fntx/trades")
    log_file = os.path.join(log_dir, f"trades_{datetime.now().strftime('%Y%m%d')}.json")
    
    if os.path.exists(log_file):
        with open(log_file) as f:
            trades = json.load(f)
            
        total_contracts = sum(t.get('contracts', 0) for t in trades)
        
        if total_contracts >= 5:
            console.print(f"\n[yellow]⚠ Daily limit reached:[/yellow] {total_contracts}/5 contracts traded today")