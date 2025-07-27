"""
FNTX Connect Command - Establish connections to IB Gateway and Theta Terminal
"""
import click
import os
import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Optional

# Add parent directories to path to import from rl_trading
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../rl-trading/spy_options'))

console = Console()

@click.group()
def connect():
    """Manage connections to trading infrastructure"""
    pass

@connect.command()
@click.option('--port', default=7497, help='IB Gateway port (7497 for paper, 7496 for live)')
@click.option('--client-id', default=1, help='Client ID for IB connection')
def ibkr(port: int, client_id: int):
    """Connect to Interactive Brokers Gateway"""
    try:
        from ib_insync import IB, util
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Connecting to IB Gateway...", total=None)
            
            ib = IB()
            try:
                ib.connect('127.0.0.1', port, clientId=client_id)
                progress.update(task, description="[green]Connected to IB Gateway!")
                
                # Get account info
                account = ib.managedAccounts()[0] if ib.managedAccounts() else "N/A"
                
                console.print(Panel(
                    f"[bold green]✓ IB Gateway Connected[/bold green]\n\n"
                    f"[cyan]Account:[/cyan] {account}\n"
                    f"[cyan]Port:[/cyan] {port}\n"
                    f"[cyan]Client ID:[/cyan] {client_id}\n"
                    f"[cyan]Mode:[/cyan] {'Paper Trading' if port == 7497 else 'Live Trading'}",
                    title="IB Connection Status"
                ))
                
                # Save connection config
                config_dir = os.path.expanduser("~/.fntx")
                os.makedirs(config_dir, exist_ok=True)
                
                with open(os.path.join(config_dir, "ib_config.json"), "w") as f:
                    import json
                    json.dump({
                        "port": port,
                        "client_id": client_id,
                        "account": account,
                        "connected": True,
                        "timestamp": time.time()
                    }, f)
                
                ib.disconnect()
                
            except Exception as e:
                progress.update(task, description=f"[red]Failed to connect: {str(e)}")
                console.print(f"\n[red]Error:[/red] {str(e)}")
                console.print("\n[yellow]Troubleshooting:[/yellow]")
                console.print("1. Ensure IB Gateway is running")
                console.print("2. Check API settings are enabled")
                console.print("3. Verify port number (7497 for paper, 7496 for live)")
                return
                
    except ImportError:
        console.print("[red]Error:[/red] ib_insync not installed")
        console.print("Run: pip install ib_insync")

@connect.command()
@click.option('--host', default='127.0.0.1', help='Theta Terminal host')
@click.option('--port', default=25510, help='Theta Terminal port')
def theta(host: str, port: int):
    """Connect to Theta Terminal"""
    import requests
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Connecting to Theta Terminal...", total=None)
        
        try:
            # Test connection to Theta Terminal
            response = requests.get(f"http://{host}:{port}/v2/system/status", timeout=5)
            
            if response.status_code == 200:
                progress.update(task, description="[green]Connected to Theta Terminal!")
                
                console.print(Panel(
                    f"[bold green]✓ Theta Terminal Connected[/bold green]\n\n"
                    f"[cyan]Host:[/cyan] {host}\n"
                    f"[cyan]Port:[/cyan] {port}\n"
                    f"[cyan]Status:[/cyan] Online",
                    title="Theta Connection Status"
                ))
                
                # Save connection config
                config_dir = os.path.expanduser("~/.fntx")
                os.makedirs(config_dir, exist_ok=True)
                
                with open(os.path.join(config_dir, "theta_config.json"), "w") as f:
                    import json
                    json.dump({
                        "host": host,
                        "port": port,
                        "connected": True,
                        "timestamp": time.time()
                    }, f)
            else:
                raise Exception(f"HTTP {response.status_code}")
                
        except Exception as e:
            progress.update(task, description=f"[red]Failed to connect: {str(e)}")
            console.print(f"\n[red]Error:[/red] {str(e)}")
            console.print("\n[yellow]Troubleshooting:[/yellow]")
            console.print("1. Ensure Theta Terminal is running")
            console.print(f"2. Check if Theta Terminal is listening on {host}:{port}")
            console.print("3. Run: java -jar ThetaTerminal.jar")

@connect.command()
def status():
    """Check connection status for all services"""
    config_dir = os.path.expanduser("~/.fntx")
    
    # Check IB connection
    ib_status = "[red]Disconnected[/red]"
    ib_details = "Not configured"
    
    ib_config_path = os.path.join(config_dir, "ib_config.json")
    if os.path.exists(ib_config_path):
        import json
        with open(ib_config_path) as f:
            config = json.load(f)
            if time.time() - config.get("timestamp", 0) < 3600:  # 1 hour timeout
                ib_status = "[green]Connected[/green]"
                ib_details = f"Account: {config.get('account', 'N/A')}"
    
    # Check Theta connection
    theta_status = "[red]Disconnected[/red]"
    theta_details = "Not configured"
    
    theta_config_path = os.path.join(config_dir, "theta_config.json")
    if os.path.exists(theta_config_path):
        import json
        with open(theta_config_path) as f:
            config = json.load(f)
            if time.time() - config.get("timestamp", 0) < 3600:  # 1 hour timeout
                theta_status = "[green]Connected[/green]"
                theta_details = f"Host: {config.get('host', 'N/A')}:{config.get('port', 'N/A')}"
    
    console.print(Panel(
        f"[bold]Connection Status[/bold]\n\n"
        f"[cyan]IB Gateway:[/cyan] {ib_status}\n"
        f"  {ib_details}\n\n"
        f"[cyan]Theta Terminal:[/cyan] {theta_status}\n"
        f"  {theta_details}",
        title="FNTX Trading Infrastructure"
    ))

@connect.command()
def all():
    """Connect to all services (IB Gateway and Theta Terminal)"""
    console.print("[bold]Connecting to all services...[/bold]\n")
    
    # Connect to IB Gateway
    ctx = click.Context(ibkr)
    ctx.invoke(ibkr)
    
    console.print()  # Add spacing
    
    # Connect to Theta Terminal
    ctx = click.Context(theta)
    ctx.invoke(theta)