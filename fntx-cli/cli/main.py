"""
FNTX Agent CLI - Command Line Interface for the Utopian Machine
"""
import click
import asyncio
from rich.console import Console
from rich.panel import Panel

# Import command groups
from cli.commands.agent import agent
from cli.commands.wallet import wallet

console = Console()

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """FNTX Agent - Trading Intelligence Platform"""
    pass

# Register command groups
cli.add_command(agent)
cli.add_command(wallet)

@cli.command()
@click.option('--mode', type=click.Choice(['individual', 'enterprise']), 
              default='individual', help='Trading mode')
@click.option('--strategy', default='spy-0dte', help='Trading strategy to use')
def trade(mode, strategy):
    """Start trading with specified mode and strategy"""
    console.print(Panel(
        f"[bold green]Starting FNTX Agent[/bold green]\n"
        f"Mode: {mode}\n"
        f"Strategy: {strategy}",
        title="FNTX Trading Engine"
    ))
    
    if mode == 'enterprise':
        console.print("[yellow]Enterprise mode requires identity verification[/yellow]")
        # TODO: Implement Humanity Protocol check
    
    # TODO: Launch trading engine
    console.print("[dim]Trading engine not yet implemented[/dim]")

@cli.command()
@click.option('--port', default=8000, help='Port to run MCP server on')
def serve(port):
    """Start MCP server for Claude Code integration"""
    console.print(f"[bold cyan]Starting MCP server on port {port}[/bold cyan]")
    # TODO: Implement MCP server
    console.print("[dim]MCP server not yet implemented[/dim]")

@cli.command()
def verify():
    """Verify identity through Humanity Protocol"""
    console.print("[bold magenta]Starting identity verification process[/bold magenta]")
    # TODO: Implement Humanity Protocol integration
    console.print("[dim]Identity verification not yet implemented[/dim]")

@cli.command()
def stats():
    """View trading statistics and enterprise performance"""
    console.print("[bold blue]FNTX Enterprise Statistics[/bold blue]")
    # TODO: Implement statistics display
    console.print("[dim]Statistics not yet implemented[/dim]")

if __name__ == '__main__':
    cli()