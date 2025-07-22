"""
Wallet management commands for FNTX tokens
"""
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Optional
import asyncio

console = Console()


@click.group()
def wallet():
    """Manage your FNTX tokens and wallet"""
    pass


@wallet.command()
@click.option('--address', help='Wallet address to check')
async def balance(address: Optional[str]):
    """Check your FNTX token balance"""
    if not address:
        address = "0x1234...5678"  # Default/stored address
    
    console.print(Panel(
        f"[bold]Wallet Balance[/bold]\n\n"
        f"Address: [cyan]{address}[/cyan]\n\n"
        f"FNTX Tokens: [green]10,000.00[/green]\n"
        f"SOUL Tokens: [yellow]5,250.00[/yellow]\n"
        f"Staked FNTX: [blue]8,000.00[/blue]\n\n"
        f"USD Value: [bold green]$10,000.00[/bold green]",
        title="FNTX Wallet",
        border_style="cyan"
    ))


@wallet.command()
@click.argument('amount', type=float)
@click.option('--duration', type=click.Choice(['30', '90', '180', '365']), 
              default='90', help='Staking duration in days')
async def stake(amount: float, duration: str):
    """Stake FNTX tokens for rewards and governance"""
    apr = {'30': 8, '90': 12, '180': 15, '365': 20}[duration]
    
    console.print(f"\n[bold]Staking Details:[/bold]")
    console.print(f"Amount: [cyan]{amount:,.2f} FNTX[/cyan]")
    console.print(f"Duration: [yellow]{duration} days[/yellow]")
    console.print(f"APR: [green]{apr}%[/green]")
    console.print(f"Est. Rewards: [green]{amount * apr / 100 * int(duration) / 365:,.2f} FNTX[/green]")
    
    if click.confirm("\nProceed with staking?"):
        with console.status("[bold green]Staking tokens...") as status:
            await asyncio.sleep(2)  # Simulate blockchain transaction
            console.print("[bold green]✓ Tokens staked successfully![/bold green]")
            console.print(f"Transaction ID: [dim]0xabcd...ef01[/dim]")
    else:
        console.print("[yellow]Staking cancelled[/yellow]")


@wallet.command()
@click.argument('amount', type=float)
@click.argument('recipient')
async def send(amount: float, recipient: str):
    """Send FNTX tokens to another address"""
    console.print(f"\n[bold]Transfer Details:[/bold]")
    console.print(f"Amount: [cyan]{amount:,.2f} FNTX[/cyan]")
    console.print(f"To: [yellow]{recipient}[/yellow]")
    console.print(f"Network Fee: [dim]0.1 FNTX[/dim]")
    
    if click.confirm("\nConfirm transfer?"):
        with console.status("[bold green]Sending tokens...") as status:
            await asyncio.sleep(2)  # Simulate blockchain transaction
            console.print("[bold green]✓ Transfer completed![/bold green]")
            console.print(f"Transaction ID: [dim]0x9876...5432[/dim]")
    else:
        console.print("[yellow]Transfer cancelled[/yellow]")


@wallet.command()
async def rewards():
    """View your staking rewards and claim them"""
    console.print("\n[bold]Staking Rewards[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Stake ID", style="cyan")
    table.add_column("Amount", style="yellow")
    table.add_column("Duration", style="green")
    table.add_column("Rewards", style="green")
    table.add_column("Status", style="blue")
    
    table.add_row("STK-001", "5,000 FNTX", "90 days", "150 FNTX", "Active")
    table.add_row("STK-002", "3,000 FNTX", "180 days", "225 FNTX", "Active")
    table.add_row("STK-003", "2,000 FNTX", "30 days", "13 FNTX", "Claimable")
    
    console.print(table)
    
    console.print(f"\n[bold green]Total Claimable: 13 FNTX[/bold green]")
    
    if click.confirm("\nClaim available rewards?"):
        with console.status("[bold green]Claiming rewards...") as status:
            await asyncio.sleep(1.5)
            console.print("[bold green]✓ Rewards claimed successfully![/bold green]")


@wallet.command()
async def history():
    """View transaction history"""
    console.print("\n[bold]Transaction History[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Date", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Amount", style="green")
    table.add_column("Status", style="blue")
    table.add_column("TX ID", style="dim")
    
    table.add_row("2025-01-18", "Stake", "5,000 FNTX", "Confirmed", "0xabc...123")
    table.add_row("2025-01-17", "Receive", "+100 FNTX", "Confirmed", "0xdef...456")
    table.add_row("2025-01-16", "Send", "-50 FNTX", "Confirmed", "0xghi...789")
    table.add_row("2025-01-15", "Rewards", "+25 FNTX", "Confirmed", "0xjkl...012")
    
    console.print(table)


# Apply async wrapper to commands
def async_command(f):
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

balance = async_command(balance)
stake = async_command(stake)
send = async_command(send)
rewards = async_command(rewards)
history = async_command(history)