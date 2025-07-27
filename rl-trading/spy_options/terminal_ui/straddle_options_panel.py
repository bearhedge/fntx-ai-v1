"""
Options chain display in straddle format with calls and puts side-by-side
Professional trading terminal style display
"""
from datetime import datetime
from typing import List, Dict, Optional
import numpy as np
import pytz
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align


class StraddleOptionsPanel:
    """Display options chain in standard straddle format"""
    
    def __init__(self, num_strikes: int = 10):
        self.num_strikes = num_strikes
        self.last_update = None
        self.update_count = 0
    
    def create_panel(self, 
                    options_chain: List[Dict],
                    spy_price: float,
                    spy_price_realtime: float = None,
                    vix: float = 0) -> Panel:
        """
        Create Rich panel with straddle-format options chain
        
        Args:
            options_chain: Raw options data
            spy_price: Current SPY price (may be delayed)
            spy_price_realtime: Real-time SPY price from Yahoo
            vix: Current VIX value
            
        Returns:
            Rich Panel object
        """
        # Use real-time price if available
        current_price = spy_price_realtime if spy_price_realtime else spy_price
        
        # Organize options by strike
        strikes_data = self._organize_by_strike(options_chain)
        
        # Get strikes around ATM
        atm_strike = int(current_price)
        display_strikes = self._get_display_strikes(strikes_data, atm_strike)
        
        # Create straddle table
        table = Table(show_header=True, header_style="bold cyan", 
                     show_lines=True, expand=False)
        
        # Add columns - Calls on left, strike in middle, puts on right
        # CALLS side
        table.add_column("Volume", style="dim", justify="right", width=8)
        table.add_column("OI", style="dim", justify="right", width=8)
        table.add_column("IV", style="yellow", justify="right", width=6)
        table.add_column("Delta", style="blue", justify="right", width=6)
        table.add_column("Bid", style="green", justify="right", width=8)
        table.add_column("Ask", style="green", justify="right", width=8)
        
        # STRIKE column (center)
        table.add_column("Strike", style="bold white", justify="center", width=8)
        
        # PUTS side
        table.add_column("Bid", style="red", justify="right", width=8)
        table.add_column("Ask", style="red", justify="right", width=8)
        table.add_column("Delta", style="magenta", justify="right", width=6)
        table.add_column("IV", style="yellow", justify="right", width=6)
        table.add_column("OI", style="dim", justify="right", width=8)
        table.add_column("Volume", style="dim", justify="right", width=8)
        
        # Add header row
        table.add_row(
            "[bold green]CALLS[/bold green]", "", "", "", "", "",
            "",
            "", "", "", "", "", "[bold red]PUTS[/bold red]"
        )
        
        # Add options rows
        for strike in display_strikes:
            call = strikes_data.get(strike, {}).get('C')
            put = strikes_data.get(strike, {}).get('P')
            
            # Format strike with ATM indicator
            if strike == atm_strike:
                strike_display = f"[bold yellow]{strike} ★[/bold yellow]"
            else:
                strike_display = str(strike)
            
            # Format call data
            if call:
                call_row = [
                    f"{call.get('volume', 0):,}",
                    f"{call.get('open_interest', 0):,}",
                    f"{call.get('iv', 0)*100:.1f}",
                    f"{call.get('delta', 0):.2f}",
                    f"${call.get('bid', 0):.2f}",
                    f"${call.get('ask', 0):.2f}"
                ]
            else:
                call_row = ["", "", "", "", "", ""]
            
            # Format put data
            if put:
                put_row = [
                    f"${put.get('bid', 0):.2f}",
                    f"${put.get('ask', 0):.2f}",
                    f"{put.get('delta', 0):.2f}",
                    f"{put.get('iv', 0)*100:.1f}",
                    f"{put.get('open_interest', 0):,}",
                    f"{put.get('volume', 0):,}"
                ]
            else:
                put_row = ["", "", "", "", "", ""]
            
            # Add complete row
            table.add_row(*call_row, strike_display, *put_row)
        
        # Update tracking
        self.last_update = datetime.now()
        self.update_count += 1
        
        # Create title with market info
        title = self._create_title(spy_price, spy_price_realtime, vix)
        
        # Return panel
        return Panel(
            Align.center(table),
            title=title,
            border_style="bright_blue",
            padding=(1, 2)
        )
    
    def _organize_by_strike(self, options_chain: List[Dict]) -> Dict[int, Dict[str, Dict]]:
        """Organize options by strike price"""
        strikes = {}
        
        for option in options_chain:
            strike = option['strike']
            opt_type = option['type']
            
            if strike not in strikes:
                strikes[strike] = {}
            
            strikes[strike][opt_type] = option
        
        return strikes
    
    def _get_display_strikes(self, strikes_data: Dict, atm_strike: int) -> List[int]:
        """Get strikes to display around ATM"""
        all_strikes = sorted(strikes_data.keys())
        
        if not all_strikes:
            return []
        
        # Find strikes around ATM
        strikes_to_show = []
        
        # Get strikes below ATM
        below = [s for s in all_strikes if s < atm_strike]
        strikes_to_show.extend(below[-(self.num_strikes//2):])
        
        # Add ATM if exists
        if atm_strike in all_strikes:
            strikes_to_show.append(atm_strike)
        
        # Get strikes above ATM
        above = [s for s in all_strikes if s > atm_strike]
        strikes_to_show.extend(above[:self.num_strikes//2])
        
        return sorted(strikes_to_show)
    
    def _create_title(self, spy_price: float, spy_price_realtime: float, vix: float) -> str:
        """Create panel title with market info"""
        eastern = pytz.timezone('US/Eastern')
        time_str = self.last_update.astimezone(eastern).strftime('%H:%M:%S ET') if self.last_update else "N/A"
        
        # Simple title without SPY/VIX since it's shown in the header
        return f"[bold cyan]SPY 0DTE Options Chain[/bold cyan] [dim]({time_str})[/dim]"
    
    def get_straddle_prices(self, options_chain: List[Dict], strike: int) -> Dict[str, float]:
        """Get straddle prices for a specific strike"""
        call_price = 0
        put_price = 0
        
        for option in options_chain:
            if option['strike'] == strike:
                mid = (option['bid'] + option['ask']) / 2
                if option['type'] == 'C':
                    call_price = mid
                else:
                    put_price = mid
        
        return {
            'straddle': call_price + put_price,
            'call': call_price,
            'put': put_price
        }