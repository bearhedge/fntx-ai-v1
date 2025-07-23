"""
FNTX CLI - Simple test
"""
import click
from rich.console import Console
from rich.panel import Panel

console = Console()

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """FNTX - Test CLI"""
    pass

@cli.command()
def test():
    """Test that FNTX CLI is installed and working"""
    console.print(Panel(
        "[bold green]✓ FNTX CLI is installed and working![/bold green]\n\n"
        "You successfully installed the FNTX command line tool.\n"
        "Version: 0.1.0\n\n"
        "[yellow]Next steps:[/yellow]\n"
        "- This is just a test command\n"
        "- Real trading functionality will be added later",
        title="FNTX CLI Test"
    ))

if __name__ == '__main__':
    cli()