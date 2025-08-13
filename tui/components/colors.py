"""
Color Scheme and Styling for FNTX Trading CLI
"""

# Color Constants
COLORS = {
    # Primary Colors
    'primary': 'cyan',
    'secondary': 'white',
    'success': 'green',
    'danger': 'red',
    'warning': 'yellow',
    
    # Status Colors
    'profit': 'green',
    'loss': 'red',
    'neutral': 'white',
    'pending': 'yellow',
    
    # UI Elements
    'header': 'bold cyan',
    'label': 'cyan',
    'value': 'white',
    'dim': 'dim white',
    'highlight': 'bold white',
    
    # Risk Levels
    'low_risk': 'green',
    'medium_risk': 'yellow',
    'high_risk': 'orange1',
    'extreme_risk': 'bold red',
    
    # Market Status
    'market_open': 'green',
    'market_closed': 'red',
    'pre_market': 'yellow',
    'after_hours': 'yellow'
}

# Style Presets
STYLES = {
    'panel_title': 'bold cyan',
    'panel_border': 'cyan',
    'table_header': 'bold cyan on black',
    'table_row': 'white',
    'table_border': 'dim cyan',
    'success_message': 'bold green',
    'error_message': 'bold red',
    'warning_message': 'bold yellow',
    'info_message': 'cyan',
    'prompt': 'bold yellow'
}

def style_price(value, base=None):
    """Style a price value with color based on comparison to base"""
    if base is None:
        return f"[white]{value}[/white]"
    
    if value > base:
        return f"[green]{value}[/green]"
    elif value < base:
        return f"[red]{value}[/red]"
    else:
        return f"[white]{value}[/white]"

def style_pnl(value):
    """Style P&L value with appropriate color and sign"""
    if value > 0:
        return f"[green]+${value:,.0f}[/green]"
    elif value < 0:
        return f"[red]-${abs(value):,.0f}[/red]"
    else:
        return f"[white]${value:,.0f}[/white]"

def style_percentage(value):
    """Style percentage value with color"""
    if value > 0:
        return f"[green]+{value:.1f}%[/green]"
    elif value < 0:
        return f"[red]{value:.1f}%[/red]"
    else:
        return f"[white]{value:.1f}%[/white]"

def style_status(status):
    """Style status text based on type"""
    status_lower = status.lower()
    
    if status_lower in ['active', 'open', 'connected', 'online']:
        return f"[green]{status}[/green]"
    elif status_lower in ['closed', 'offline', 'disconnected', 'error']:
        return f"[red]{status}[/red]"
    elif status_lower in ['pending', 'waiting', 'processing']:
        return f"[yellow]{status}[/yellow]"
    else:
        return f"[white]{status}[/white]"

def style_risk_level(level):
    """Style risk level with appropriate color"""
    if level < 0.3:
        return f"[green]LOW ({level:.2f})[/green]"
    elif level < 0.6:
        return f"[yellow]MEDIUM ({level:.2f})[/yellow]"
    elif level < 0.8:
        return f"[orange1]HIGH ({level:.2f})[/orange1]"
    else:
        return f"[bold red]EXTREME ({level:.2f})[/bold red]"

def get_market_status_style(is_open):
    """Get style for market status"""
    if is_open:
        return "bold green"
    else:
        return "bold red"