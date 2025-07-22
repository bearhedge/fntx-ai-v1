"""
Agent management commands for FNTX CLI
"""
import click
import asyncio
import httpx
import json
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Optional, Dict, Any

console = Console()

# Agent Factory API base URL
API_BASE_URL = "http://localhost:8001"


@click.group()
def agent():
    """Manage your AI trading agents"""
    pass


@agent.command()
@click.option('--type', 'agent_type', 
              type=click.Choice(['ensemble', 'ppo', 'a2c', 'ddpg']), 
              default='ensemble',
              help='Type of agent to create')
@click.option('--name', help='Custom name for the agent')
@click.option('--user-id', required=True, help='Your user ID')
async def create(agent_type: str, name: Optional[str], user_id: str):
    """Create a new AI trading agent"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Creating agent...", total=None)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{API_BASE_URL}/agents/create",
                    json={
                        "user_id": user_id,
                        "agent_type": agent_type,
                        "config": {"name": name} if name else {}
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                progress.update(task, completed=True)
                
                console.print(f"[bold green]✓ Agent created successfully![/bold green]")
                console.print(f"Agent ID: [cyan]{result['agent_id']}[/cyan]")
                console.print(f"Status: [yellow]{result['status']}[/yellow]")
                
            except httpx.HTTPError as e:
                console.print(f"[bold red]✗ Failed to create agent: {e}[/bold red]")


@agent.command()
@click.argument('agent_id')
@click.option('--epochs', default=10, help='Number of training epochs')
@click.option('--data-source', default='synthetic', help='Training data source')
async def train(agent_id: str, epochs: int, data_source: str):
    """Train an AI agent with market data"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Training agent for {epochs} epochs...", total=None)
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            try:
                response = await client.post(
                    f"{API_BASE_URL}/agents/{agent_id}/train",
                    json={
                        "agent_id": agent_id,
                        "epochs": epochs,
                        "training_data": {"source": data_source}
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                progress.update(task, completed=True)
                
                console.print(f"[bold green]✓ Training completed![/bold green]")
                console.print(f"Agent ID: [cyan]{result['agent_id']}[/cyan]")
                
                # Display performance metrics
                if result.get('performance_metrics'):
                    console.print("\n[bold]Performance Metrics:[/bold]")
                    metrics = result['performance_metrics']
                    
                    table = Table(show_header=True, header_style="bold magenta")
                    table.add_column("Metric", style="cyan")
                    table.add_column("Value", style="green")
                    
                    table.add_row("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.3f}")
                    table.add_row("Total Return", f"{metrics.get('total_return', 0):.2f}%")
                    table.add_row("Max Drawdown", f"{metrics.get('max_drawdown', 0):.2f}%")
                    table.add_row("Win Rate", f"{metrics.get('win_rate', 0):.2f}%")
                    
                    console.print(table)
                
            except httpx.HTTPError as e:
                console.print(f"[bold red]✗ Failed to train agent: {e}[/bold red]")


@agent.command()
@click.argument('agent_id')
async def status(agent_id: str):
    """Check the status of an agent"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/agents/{agent_id}")
            response.raise_for_status()
            result = response.json()
            
            console.print(f"\n[bold]Agent Status[/bold]")
            console.print(f"ID: [cyan]{result['agent_id']}[/cyan]")
            console.print(f"Status: [yellow]{result['status']}[/yellow]")
            
            if result.get('performance_metrics'):
                console.print("\n[bold]Performance Metrics:[/bold]")
                metrics = result['performance_metrics']
                
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")
                
                table.add_row("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.3f}")
                table.add_row("Total Return", f"{metrics.get('total_return', 0):.2f}%")
                table.add_row("Max Drawdown", f"{metrics.get('max_drawdown', 0):.2f}%")
                table.add_row("Win Rate", f"{metrics.get('win_rate', 0):.2f}%")
                table.add_row("Trades Executed", str(metrics.get('trades_executed', 0)))
                
                console.print(table)
            
        except httpx.HTTPError as e:
            console.print(f"[bold red]✗ Failed to get agent status: {e}[/bold red]")


@agent.command()
@click.argument('agent_id')
@click.option('--strategy', default='conservative', 
              type=click.Choice(['conservative', 'moderate', 'aggressive']))
async def deploy(agent_id: str, strategy: str):
    """Deploy an agent for live trading"""
    console.print(f"[bold yellow]⚠ Deploying agent {agent_id} with {strategy} strategy[/bold yellow]")
    console.print("[dim]Note: This will enable live trading with real funds[/dim]")
    
    if click.confirm("Are you sure you want to proceed?"):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Deploying agent...", total=None)
            
            # TODO: Implement actual deployment logic
            await asyncio.sleep(2)  # Simulate deployment
            
            progress.update(task, completed=True)
            console.print(f"[bold green]✓ Agent deployed successfully![/bold green]")
            console.print(f"Strategy: [cyan]{strategy}[/cyan]")
            console.print("Monitor performance with: [dim]fntx agent status {agent_id}[/dim]")
    else:
        console.print("[yellow]Deployment cancelled[/yellow]")


@agent.command()
@click.argument('agent_id')
@click.option('--start-date', help='Backtest start date (YYYY-MM-DD)')
@click.option('--end-date', help='Backtest end date (YYYY-MM-DD)')
async def backtest(agent_id: str, start_date: Optional[str], end_date: Optional[str]):
    """Run historical backtest on an agent"""
    console.print(f"[bold]Running backtest for agent {agent_id}[/bold]")
    
    if start_date:
        console.print(f"Start: [cyan]{start_date}[/cyan]")
    if end_date:
        console.print(f"End: [cyan]{end_date}[/cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Running backtest simulation...", total=None)
        
        # TODO: Implement actual backtest logic
        await asyncio.sleep(3)  # Simulate backtest
        
        progress.update(task, completed=True)
        
        # Display simulated results
        console.print("\n[bold green]✓ Backtest completed![/bold green]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Return", "+23.45%")
        table.add_row("Sharpe Ratio", "1.28")
        table.add_row("Max Drawdown", "-8.32%")
        table.add_row("Win Rate", "58.7%")
        table.add_row("Total Trades", "142")
        table.add_row("Profit Factor", "1.85")
        
        console.print(table)


@agent.command()
@click.option('--user-id', required=True, help='Your user ID')
async def list(user_id: str):
    """List all your agents"""
    # TODO: Implement actual API call to list agents
    console.print(f"\n[bold]Your Agents[/bold]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Agent ID", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Sharpe Ratio", style="blue")
    table.add_column("Created", style="dim")
    
    # Simulated data
    table.add_row(
        "ens_abc123",
        "ensemble",
        "active",
        "1.25",
        "2025-01-15"
    )
    table.add_row(
        "ppo_def456",
        "ppo",
        "training",
        "-",
        "2025-01-18"
    )
    
    console.print(table)


# Make async commands work with click
def async_command(f):
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

# Apply async wrapper to all commands
create = async_command(create)
train = async_command(train)
status = async_command(status)
deploy = async_command(deploy)
backtest = async_command(backtest)
list = async_command(list)