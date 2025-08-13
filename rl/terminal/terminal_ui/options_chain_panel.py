"""
Options chain display panel using Rich
Shows OTM options with real-time updates
"""
from datetime import datetime
from typing import List, Dict, Optional
import numpy as np
import pytz
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from .data_filters import OTMFilter


class OptionsChainPanel:
    """Display OTM options chain with liquidity info"""
    
    def __init__(self, filter_config: Optional[OTMFilter] = None):
        self.filter = filter_config or OTMFilter()
        self.last_update = None
        self.update_count = 0
    
    def create_panel(self, 
                    options_chain: List[Dict],
                    spy_price: float,
                    vix: float = 0) -> Panel:
        """
        Create Rich panel with options chain display
        
        Args:
            options_chain: Raw options data
            spy_price: Current SPY price
            vix: Current VIX value
            
        Returns:
            Rich Panel object
        """
        # Filter to OTM only
        filtered = self.filter.filter_options_chain(options_chain, spy_price)
        
        # Create main table
        table = Table(show_header=True, header_style="bold cyan", 
                     show_lines=True, expand=False)
        
        # Add columns
        table.add_column("Strike", style="bold", justify="center", width=8)
        table.add_column("Bid", style="green", justify="right", width=8)
        table.add_column("Ask", style="red", justify="right", width=8)
        table.add_column("Mid", style="white", justify="right", width=8)
        table.add_column("Spread", justify="right", width=8)
        table.add_column("Volume", style="cyan", justify="right", width=10)
        table.add_column("OI", style="cyan", justify="right", width=10)
        table.add_column("IV", style="yellow", justify="right", width=8)
        table.add_column("Delta", style="magenta", justify="right", width=8)
        
        # Add SPY price row
        table.add_row(
            f"SPY",
            "",
            "",
            f"[bold yellow]{spy_price:.2f}[/bold yellow]",
            "",
            "",
            "",
            f"VIX: {vix:.1f}",
            ""
        )
        
        # Add separator
        table.add_row("", "", "", "", "", "", "", "", "")
        
        # Add CALLS header
        table.add_row(
            "[bold green]CALLS[/bold green]",
            "", "", "", "", "", "", "", ""
        )
        
        # Add call options
        for call in filtered['calls']:
            formatted = self.filter.format_option_display(call)
            spread_style = self._get_spread_style(formatted['spread_color'])
            
            table.add_row(
                formatted['strike'],
                formatted['bid'],
                formatted['ask'],
                formatted['mid'],
                f"[{spread_style}]{formatted['spread']}[/{spread_style}]",
                formatted['volume'],
                formatted['oi'],
                formatted['iv'],
                formatted['delta']
            )
        
        # Add separator
        table.add_row("", "", "", "", "", "", "", "", "")
        
        # Add PUTS header
        table.add_row(
            "[bold red]PUTS[/bold red]",
            "", "", "", "", "", "", "", ""
        )
        
        # Add put options
        for put in filtered['puts']:
            formatted = self.filter.format_option_display(put)
            spread_style = self._get_spread_style(formatted['spread_color'])
            
            table.add_row(
                formatted['strike'],
                formatted['bid'],
                formatted['ask'],
                formatted['mid'],
                f"[{spread_style}]{formatted['spread']}[/{spread_style}]",
                formatted['volume'],
                formatted['oi'],
                formatted['iv'],
                formatted['delta']
            )
        
        # Update tracking
        self.last_update = datetime.now()
        self.update_count += 1
        
        # Create title with update info
        title = self._create_title()
        
        # Return panel
        return Panel(
            Align.center(table),
            title=title,
            border_style="bright_blue",
            padding=(1, 2)
        )
    
    def create_mini_panel(self, 
                         options_chain: List[Dict],
                         spy_price: float) -> Panel:
        """Create smaller panel showing just best strikes"""
        filtered = self.filter.filter_options_chain(options_chain, spy_price)
        
        # Get best 3 strikes each
        best_calls = filtered['calls'][:3]
        best_puts = filtered['puts'][:3]
        
        # Create compact table
        table = Table(show_header=False, show_lines=False, expand=False)
        table.add_column("Type", width=6)
        table.add_column("Strike", width=6)
        table.add_column("Bid/Ask", width=14)
        table.add_column("Vol", width=8)
        
        # Add SPY price
        table.add_row(
            "[bold]SPY[/bold]",
            f"{spy_price:.1f}",
            "",
            ""
        )
        
        # Add best calls
        for call in best_calls:
            table.add_row(
                "[green]CALL[/green]",
                f"{call['strike']:.0f}",
                f"{call['bid']:.2f}/{call['ask']:.2f}",
                f"{call.get('volume', 0):,}"
            )
        
        # Add best puts
        for put in best_puts:
            table.add_row(
                "[red]PUT[/red]",
                f"{put['strike']:.0f}",
                f"{put['bid']:.2f}/{put['ask']:.2f}",
                f"{put.get('volume', 0):,}"
            )
        
        return Panel(
            table,
            title="[cyan]OTM Options[/cyan]",
            border_style="cyan",
            padding=(0, 1)
        )
    
    def _get_spread_style(self, color: str) -> str:
        """Convert color name to Rich style"""
        return {
            'green': 'bright_green',
            'yellow': 'yellow',
            'red': 'bright_red'
        }.get(color, 'white')
    
    def _create_title(self) -> str:
        """Create panel title with update info"""
        eastern = pytz.timezone('US/Eastern')
        time_str = self.last_update.astimezone(eastern).strftime('%H:%M:%S ET') if self.last_update else "N/A"
        
        return (
            f"[bold cyan]SPY 0DTE Options Chain[/bold cyan] | "
            f"[dim]Updated: {time_str} | "
            f"Refresh #{self.update_count}[/dim]"
        )
    
    def get_statistics(self, options_chain: List[Dict]) -> Dict[str, float]:
        """Calculate options chain statistics"""
        total_volume = sum(opt.get('volume', 0) for opt in options_chain)
        total_oi = sum(opt.get('open_interest', 0) for opt in options_chain)
        
        avg_spread_pcts = []
        for opt in options_chain:
            bid = opt.get('bid', 0)
            ask = opt.get('ask', 0)
            if bid > 0 and ask > 0:
                mid = (bid + ask) / 2
                spread_pct = (ask - bid) / mid
                avg_spread_pcts.append(spread_pct)
        
        avg_spread = np.mean(avg_spread_pcts) if avg_spread_pcts else 0
        
        return {
            'total_volume': total_volume,
            'total_oi': total_oi,
            'avg_spread_pct': avg_spread,
            'num_strikes': len(options_chain)
        }