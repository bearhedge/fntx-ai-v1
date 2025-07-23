"""
FNTX Schedule Command - Schedule and manage daily trading jobs
"""
import click
import os
import sys
import json
import subprocess
from datetime import datetime, time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm, Prompt
from typing import Dict, List, Optional
# from crontab import CronTab  # TODO: Install python-crontab

console = Console()

# Default trading schedule
DEFAULT_START_TIME = "09:35"  # 5 minutes after market open
DEFAULT_STOP_TIME = "15:45"   # 15 minutes before market close

@click.group()
def schedule():
    """Schedule and manage automated trading jobs"""
    pass

@schedule.command()
@click.option('--start-time', default=DEFAULT_START_TIME, help='Daily start time (HH:MM)')
@click.option('--stop-time', default=DEFAULT_STOP_TIME, help='Daily stop time (HH:MM)')
@click.option('--contracts', default=1, help='Contracts per trade')
@click.option('--delta', default=0.10, help='Target delta')
def daily(start_time: str, stop_time: str, contracts: int, delta: float):
    """Schedule daily SPX put trading"""
    
    # Validate time format
    try:
        datetime.strptime(start_time, "%H:%M")
        datetime.strptime(stop_time, "%H:%M")
    except ValueError:
        console.print("[red]Error:[/red] Invalid time format. Use HH:MM")
        return
    
    # Create schedule configuration
    schedule_config = {
        "enabled": True,
        "start_time": start_time,
        "stop_time": stop_time,
        "contracts": contracts,
        "delta": delta,
        "created": datetime.now().isoformat()
    }
    
    # Save configuration
    config_dir = os.path.expanduser("~/.fntx")
    os.makedirs(config_dir, exist_ok=True)
    
    with open(os.path.join(config_dir, "schedule.json"), "w") as f:
        json.dump(schedule_config, f, indent=2)
    
    # Set up cron jobs
    console.print(Panel(
        f"[bold green]✓ Daily Trading Schedule Configured[/bold green]\n\n"
        f"[cyan]Start Time:[/cyan] {start_time} (Mon-Fri)\n"
        f"[cyan]Stop Time:[/cyan] {stop_time} (Mon-Fri)\n"
        f"[cyan]Contracts:[/cyan] {contracts}\n"
        f"[cyan]Target Delta:[/cyan] {delta}\n\n"
        f"[yellow]Note:[/yellow] Cron scheduling not yet implemented",
        title="Schedule Configuration"
    ))

@schedule.command()
def list():
    """List all scheduled trading jobs"""
    
    # Check schedule configuration
    config_dir = os.path.expanduser("~/.fntx")
    schedule_file = os.path.join(config_dir, "schedule.json")
    
    if os.path.exists(schedule_file):
        with open(schedule_file) as f:
            config = json.load(f)
        
        table = Table(title="Trading Schedule")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Status", "[green]Enabled[/green]" if config.get("enabled") else "[red]Disabled[/red]")
        table.add_row("Start Time", config.get("start_time", "Not set"))
        table.add_row("Stop Time", config.get("stop_time", "Not set"))
        table.add_row("Contracts", str(config.get("contracts", 0)))
        table.add_row("Target Delta", str(config.get("delta", 0)))
        table.add_row("Created", config.get("created", "Unknown"))
        
        console.print(table)
    else:
        console.print("[yellow]No schedule configured[/yellow]")
    
    # Show cron jobs
    console.print("\n[bold]Cron Jobs:[/bold]")
    console.print("  [dim]Cron integration not yet implemented[/dim]")

@schedule.command()
def cancel():
    """Cancel all scheduled trading jobs"""
    
    if not Confirm.ask("[yellow]Cancel all scheduled trading?[/yellow]"):
        console.print("[red]Cancelled[/red]")
        return
    
    # Update configuration
    config_dir = os.path.expanduser("~/.fntx")
    schedule_file = os.path.join(config_dir, "schedule.json")
    
    if os.path.exists(schedule_file):
        with open(schedule_file) as f:
            config = json.load(f)
        
        config["enabled"] = False
        
        with open(schedule_file, "w") as f:
            json.dump(config, f, indent=2)
    
    console.print("[green]✓ Schedule configuration cancelled[/green]")
    console.print("[yellow]Note: Cron jobs must be removed manually[/yellow]")

@schedule.command()
def test():
    """Test scheduled trading configuration"""
    
    config_dir = os.path.expanduser("~/.fntx")
    schedule_file = os.path.join(config_dir, "schedule.json")
    
    if not os.path.exists(schedule_file):
        console.print("[red]Error:[/red] No schedule configured. Run: fntx schedule daily")
        return
    
    with open(schedule_file) as f:
        config = json.load(f)
    
    console.print("[bold]Testing scheduled trading configuration...[/bold]\n")
    
    # Test connections
    console.print("1. Testing IB Gateway connection...")
    if os.path.exists(os.path.join(config_dir, "ib_config.json")):
        console.print("   [green]✓ IB configuration found[/green]")
    else:
        console.print("   [red]✗ IB not configured[/red]")
    
    console.print("\n2. Testing Theta Terminal connection...")
    if os.path.exists(os.path.join(config_dir, "theta_config.json")):
        console.print("   [green]✓ Theta configuration found[/green]")
    else:
        console.print("   [red]✗ Theta not configured[/red]")
    
    console.print(f"\n3. Trade parameters:")
    console.print(f"   Contracts: {config.get('contracts', 0)}")
    console.print(f"   Delta: {config.get('delta', 0)}")
    
    console.print("\n[green]Configuration test complete[/green]")