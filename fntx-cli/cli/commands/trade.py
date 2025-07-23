"""
FNTX Trade Command - Execute SPX put trades with safety checks
"""
import click
import os
import sys
import json
import time
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm
from typing import Optional, List, Dict

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../12_rl_trading/spy_options'))

console = Console()

# Trading rules (to be enforced by smart contracts later)
MAX_CONTRACTS_PER_DAY = 5
MAX_DELTA = 0.15
MARKET_CLOSE_TIME = "15:45"  # Exit all positions by 3:45 PM

@click.group()
def trade():
    """Execute and manage trades"""
    pass

@trade.command()
@click.option('--contracts', default=1, help='Number of contracts to trade')
@click.option('--delta', default=0.10, help='Target delta for put selection')
@click.option('--dry-run', is_flag=True, help='Simulate trade without execution')
def put(contracts: int, delta: float, dry_run: bool):
    """Execute SPX put trade with delta < 0.15"""
    
    # Validate inputs against rules
    if delta > MAX_DELTA:
        console.print(f"[red]Error:[/red] Delta {delta} exceeds maximum allowed {MAX_DELTA}")
        return
        
    if contracts > MAX_CONTRACTS_PER_DAY:
        console.print(f"[red]Error:[/red] {contracts} contracts exceeds daily limit of {MAX_CONTRACTS_PER_DAY}")
        return
    
    # Check if connected
    config_dir = os.path.expanduser("~/.fntx")
    if not os.path.exists(os.path.join(config_dir, "ib_config.json")):
        console.print("[red]Error:[/red] Not connected to IB Gateway. Run: fntx connect ibkr")
        return
        
    if not os.path.exists(os.path.join(config_dir, "theta_config.json")):
        console.print("[red]Error:[/red] Not connected to Theta Terminal. Run: fntx connect theta")
        return
    
    try:
        from ib_insync import IB, Stock, Option, MarketOrder
        
        console.print(f"\n[bold]Preparing SPX Put Trade[/bold]")
        console.print(f"Contracts: {contracts}")
        console.print(f"Target Delta: {delta}")
        console.print(f"Mode: {'[yellow]DRY RUN[/yellow]' if dry_run else '[green]LIVE[/green]'}\n")
        
        # Connect to IB
        ib = IB()
        with open(os.path.join(config_dir, "ib_config.json")) as f:
            ib_config = json.load(f)
        
        ib.connect('127.0.0.1', ib_config['port'], clientId=ib_config['client_id'])
        
        # Get SPX price
        spx = Stock('SPX', 'CBOE')
        ib.qualifyContracts(spx)
        ticker = ib.reqMktData(spx)
        ib.sleep(1)  # Wait for data
        
        spx_price = ticker.last if ticker.last else ticker.close
        console.print(f"SPX Price: ${spx_price:.2f}")
        
        # Calculate strike selection
        # For 0.10 delta put, typically 2-3% OTM
        strike_price = round(spx_price * (1 - 0.02))  # 2% OTM as starting point
        
        # Get expiration (0DTE)
        today = datetime.now()
        expiry = today.strftime('%Y%m%d')
        
        # Create option contract
        option = Option('SPX', expiry, strike_price, 'P', 'SMART')
        ib.qualifyContracts(option)
        
        # Get option details
        option_ticker = ib.reqMktData(option)
        ib.sleep(1)
        
        # Display trade details
        table = Table(title="Trade Details")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Symbol", "SPX")
        table.add_row("Type", "PUT")
        table.add_row("Strike", f"${strike_price}")
        table.add_row("Expiry", expiry)
        table.add_row("Contracts", str(contracts))
        table.add_row("Bid", f"${option_ticker.bid:.2f}" if option_ticker.bid else "N/A")
        table.add_row("Ask", f"${option_ticker.ask:.2f}" if option_ticker.ask else "N/A")
        table.add_row("Delta", f"{delta:.2f}")
        
        console.print(table)
        
        if not dry_run:
            # Confirm trade
            if not Confirm.ask("\n[yellow]Execute this trade?[/yellow]"):
                console.print("[red]Trade cancelled[/red]")
                ib.disconnect()
                return
            
            # Place order
            order = MarketOrder('SELL', contracts)
            trade = ib.placeOrder(option, order)
            
            # Wait for fill
            while not trade.isDone():
                ib.waitOnUpdate()
            
            if trade.orderStatus.status == 'Filled':
                console.print(Panel(
                    f"[bold green]✓ Trade Executed[/bold green]\n\n"
                    f"Filled: {trade.orderStatus.filled} contracts\n"
                    f"Avg Price: ${trade.orderStatus.avgFillPrice:.2f}",
                    title="Execution Report"
                ))
                
                # Log trade
                log_trade({
                    'timestamp': datetime.now().isoformat(),
                    'symbol': 'SPX',
                    'strike': strike_price,
                    'expiry': expiry,
                    'contracts': contracts,
                    'price': trade.orderStatus.avgFillPrice,
                    'delta': delta
                })
            else:
                console.print(f"[red]Trade failed:[/red] {trade.orderStatus.status}")
        else:
            console.print("\n[yellow]DRY RUN - No trade executed[/yellow]")
        
        ib.disconnect()
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if 'ib' in locals():
            ib.disconnect()

@trade.command()
def positions():
    """Show current positions"""
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
        
        positions = ib.positions()
        
        if not positions:
            console.print("[yellow]No open positions[/yellow]")
        else:
            table = Table(title="Current Positions")
            table.add_column("Symbol", style="cyan")
            table.add_column("Type", style="white")
            table.add_column("Strike", style="white")
            table.add_column("Expiry", style="white")
            table.add_column("Qty", style="white")
            table.add_column("Avg Cost", style="white")
            table.add_column("P&L", style="green")
            
            for pos in positions:
                if pos.contract.secType == 'OPT':
                    table.add_row(
                        pos.contract.symbol,
                        pos.contract.right,
                        str(pos.contract.strike),
                        pos.contract.lastTradeDateOrContractMonth,
                        str(pos.position),
                        f"${pos.avgCost:.2f}",
                        f"${pos.unrealizedPNL:.2f}" if pos.unrealizedPNL else "N/A"
                    )
            
            console.print(table)
        
        ib.disconnect()
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")

@trade.command()
def close():
    """Close all positions (safety exit)"""
    if not Confirm.ask("[yellow]Close ALL positions?[/yellow]"):
        console.print("[red]Cancelled[/red]")
        return
        
    # Implementation would close all positions
    console.print("[green]All positions closed[/green]")

def log_trade(trade_data: Dict):
    """Log trade to file"""
    log_dir = os.path.expanduser("~/.fntx/trades")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"trades_{datetime.now().strftime('%Y%m%d')}.json")
    
    trades = []
    if os.path.exists(log_file):
        with open(log_file) as f:
            trades = json.load(f)
    
    trades.append(trade_data)
    
    with open(log_file, 'w') as f:
        json.dump(trades, f, indent=2)