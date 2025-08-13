"""
ASCII Table Formatting for FNTX Trading CLI
"""
from rich.table import Table
from rich.text import Text
from rich import box
from .colors import COLORS, style_pnl, style_percentage

def create_positions_table(positions_data):
    """Create a styled positions table"""
    table = Table(
        title="Active Positions (USD)",
        box=box.ASCII,
        title_style="bold cyan",
        border_style="cyan",
        header_style="bold cyan",
        show_lines=True
    )
    
    # Add columns
    table.add_column("STRIKE", style="cyan", width=8)
    table.add_column("TYPE", style="cyan", width=6)
    table.add_column("QTY", style="magenta", width=5)
    table.add_column("ENTRY", style="white", width=8)
    table.add_column("CURRENT", style="yellow", width=8)
    table.add_column("P&L", width=10)
    table.add_column("STOP", style="white", width=8)
    
    # Add rows
    for position in positions_data:
        pnl_styled = style_pnl(position['pnl'])
        table.add_row(
            str(position['strike']),
            position['type'],
            str(position['qty']),
            f"${position['entry']:.2f}",
            f"${position['current']:.2f}",
            pnl_styled,
            f"${position['stop']:.2f}" if position['stop'] else "[red]NONE[/red]"
        )
    
    return table

def create_options_chain_table(chain_data):
    """Create an options chain table"""
    table = Table(
        title="SPY 0DTE Options Chain",
        box=box.DOUBLE_EDGE,
        title_style="bold cyan",
        border_style="cyan",
        show_header=True,
        header_style="bold cyan on black"
    )
    
    # Calls columns
    table.add_column("Volume", style="dim white", width=8)
    table.add_column("OI", style="dim white", width=8)
    table.add_column("IV", style="yellow", width=6)
    table.add_column("Delta", style="cyan", width=6)
    table.add_column("Bid", style="green", width=8)
    table.add_column("Ask", style="red", width=8)
    
    # Strike column (center)
    table.add_column("STRIKE", style="bold white", width=8, justify="center")
    
    # Puts columns
    table.add_column("Bid", style="green", width=8)
    table.add_column("Ask", style="red", width=8)
    table.add_column("Delta", style="cyan", width=6)
    table.add_column("IV", style="yellow", width=6)
    table.add_column("OI", style="dim white", width=8)
    table.add_column("Volume", style="dim white", width=8)
    
    # Add header row
    table.add_row(
        "CALLS", "", "", "", "", "",
        "",
        "", "", "", "", "", "PUTS",
        style="bold yellow"
    )
    
    # Add data rows
    for option in chain_data:
        strike_display = f"{option['strike']} ★" if option.get('atm') else str(option['strike'])
        
        table.add_row(
            str(option['call_volume']),
            str(option['call_oi']),
            f"{option['call_iv']:.1f}",
            f"{option['call_delta']:.2f}",
            f"${option['call_bid']:.2f}",
            f"${option['call_ask']:.2f}",
            strike_display,
            f"${option['put_bid']:.2f}",
            f"${option['put_ask']:.2f}",
            f"{option['put_delta']:.2f}",
            f"{option['put_iv']:.1f}",
            str(option['put_oi']),
            str(option['put_volume'])
        )
    
    return table

def create_simple_table(headers, rows, title=""):
    """Create a simple ASCII table with headers and rows"""
    table = Table(
        title=title,
        box=box.ASCII,
        border_style="cyan",
        header_style="bold cyan"
    )
    
    # Add headers
    for header in headers:
        table.add_column(header)
    
    # Add rows
    for row in rows:
        table.add_row(*[str(cell) for cell in row])
    
    return table

def format_ascii_table(headers, rows, widths=None):
    """Format a basic ASCII table without using Rich"""
    if widths is None:
        widths = [max(len(str(h)), max(len(str(row[i])) for row in rows)) + 2 
                 for i, h in enumerate(headers)]
    
    lines = []
    
    # Top border
    lines.append('┌' + '┬'.join('─' * w for w in widths) + '┐')
    
    # Headers
    header_cells = []
    for i, header in enumerate(headers):
        cell = f" {header} ".ljust(widths[i])
        header_cells.append(cell)
    lines.append('│' + '│'.join(header_cells) + '│')
    
    # Header separator
    lines.append('├' + '┼'.join('─' * w for w in widths) + '┤')
    
    # Data rows
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            cell_str = f" {cell} ".ljust(widths[i])
            cells.append(cell_str)
        lines.append('│' + '│'.join(cells) + '│')
    
    # Bottom border
    lines.append('└' + '┴'.join('─' * w for w in widths) + '┘')
    
    return '\n'.join(lines)