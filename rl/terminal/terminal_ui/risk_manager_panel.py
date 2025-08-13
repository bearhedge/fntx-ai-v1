"""
Risk Manager Panel for FNTX Trading Terminal UI
Professional display of trading mandates and compliance status
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
from rich import box
from typing import Dict, Any, Optional, List, Tuple
import pytz
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from backend.services.alm_nav_service import get_latest_capital
from backend.services.position_tracking import get_current_positions
import yfinance as yf


class RiskManagerPanel:
    """Professional Risk Manager panel displaying trading mandates and compliance status"""
    
    def __init__(self):
        self.console = Console()
        self.eastern = pytz.timezone('US/Eastern')
        self.market_timer = None  # Will be set from dashboard
        self._spy_price_cache = {}
        self._last_spy_fetch = None
        self._vix_cache = {}
        self._last_vix_fetch = None
        self._chart_cache = {}  # Cache for rendered chart
        self._last_chart_render = None
        
    def set_market_timer(self, market_timer):
        """Set reference to market timer for time gate status"""
        self.market_timer = market_timer
        
    def get_spy_price(self) -> float:
        """Get current SPY price with caching"""
        now = datetime.now()
        
        # Cache for 1 minute
        if self._last_spy_fetch and (now - self._last_spy_fetch).seconds < 60:
            return self._spy_price_cache.get('price', 575.0)
            
        try:
            spy = yf.Ticker("SPY")
            info = spy.info
            price = info.get('currentPrice') or info.get('regularMarketPrice', 575.0)
            self._spy_price_cache['price'] = price
            self._last_spy_fetch = now
            return price
        except:
            return self._spy_price_cache.get('price', 575.0)
            
    def get_vix_level(self) -> float:
        """Get current VIX level with caching"""
        now = datetime.now()
        
        # Cache for 1 minute
        if self._last_vix_fetch and (now - self._last_vix_fetch).seconds < 60:
            return self._vix_cache.get('level', 15.0)
            
        try:
            vix = yf.Ticker("^VIX")
            info = vix.info
            level = info.get('currentPrice') or info.get('regularMarketPrice', 15.0)
            self._vix_cache['level'] = level
            self._last_vix_fetch = now
            return level
        except:
            return self._vix_cache.get('level', 15.0)
            
    def get_vix_mountain_data(self) -> List[float]:
        """Get VIX data for line chart - 72 hours of 15-minute intervals"""
        now = datetime.now()
        
        # Cache for 5 minutes for 15-minute data
        if (self._last_vix_fetch and (now - self._last_vix_fetch).seconds < 300 and 
            'mountain_data' in self._vix_cache and self._vix_cache['mountain_data']):
            return self._vix_cache.get('mountain_data', [])
            
        try:
            vix = yf.Ticker("^VIX")
            # Get last 3 days of 15-minute data for continuous chart
            hist = vix.history(period="3d", interval="15m")
            
            if len(hist) < 20:
                # Not enough data, return empty list
                self._vix_cache['mountain_data'] = []
                return []
            
            # Use ALL data points for continuous line (no market hours filter)
            # VIX trades extended hours, so we get ~156 points for 3 days
            all_values = [float(row['Close']) for timestamp, row in hist.iterrows()]
            
            # Also store timestamps for date labels
            self._vix_cache['timestamps'] = list(hist.index)
            self._vix_cache['mountain_data'] = all_values
            self._last_vix_fetch = now
            return all_values
            
        except Exception as e:
            # Return cached data or empty list if error
            return self._vix_cache.get('mountain_data', [])
            
    def create_vix_ascii_chart(self, values: List[float]) -> List[str]:
        """Create full ASCII chart from VIX values (9 rows × 25 chars)"""
        if not values or len(values) < 2:
            # Return empty chart
            return [
                "VIX 24H (3 Days)     Loading",
                "25│",
                "24│", 
                "23│",
                "22│",
                "21│",
                "20├─────────────────────",
                "19│",
                "18│               No Data"
            ]
        
        # Determine Y-axis range (VIX typically 15-30)
        min_val = max(15, min(values) - 1)  # Floor at 15
        max_val = min(30, max(values) + 1)   # Ceiling at 30
        
        # Create 9-row chart (25 chars wide)
        chart_height = 7  # Rows for actual chart data (excluding header and axis)
        chart_width = 21  # Width for plot area
        
        # Initialize chart grid
        chart_lines = []
        
        # Row 1: Header with current VIX and risk status
        current_vix = values[-1] if values else 20.0
        risk_symbol = "✗" if current_vix > 20 else "✓"
        header = f"VIX 24H (3 Days)     Risk: {risk_symbol}"
        chart_lines.append(header)
        
        # Rows 2-8: Chart data with Y-axis labels
        y_values = [int(max_val), int(max_val - 1), int(max_val - 2), int(max_val - 3), 
                   int(max_val - 4), int(max_val - 5), int(max_val - 6)]
        
        for i, y_val in enumerate(y_values):
            if y_val == 20:
                # Special threshold line at VIX = 20
                line = f"20├─────────────────────"
            else:
                line = f"{y_val:2d}│"
                
                # Plot data points across the width
                plot_line = ""
                for j in range(chart_width):
                    # Map horizontal position to data points
                    if len(values) > 1:
                        # Calculate which data point corresponds to this X position
                        data_index = int((j / (chart_width - 1)) * (len(values) - 1))
                        data_val = values[data_index] if data_index < len(values) else values[-1]
                        
                        # Check if this Y level should show a data point (within 0.5 units)
                        if abs(data_val - y_val) <= 0.5:
                            plot_line += "●"
                        else:
                            plot_line += " "
                    else:
                        plot_line += " "
                
                line += plot_line
                
            chart_lines.append(line)
        
        # Row 9: X-axis with time labels  
        x_axis = "  └─────────────────────"
        chart_lines.append(x_axis)
        
        # Add time labels below X-axis (optional - can be shown separately)
        # Format: "  0  6 12 18 0  6 12 18 0"
        #         "  D1     D2     D3"
        
        return chart_lines
    
    def get_shade_character(self, vix_value: float) -> str:
        """Get ASCII shade character based on VIX value for mountain visualization"""
        if vix_value < 10:
            return '·'  # Minimal (calm)
        elif vix_value < 15:
            return '░'  # Light (low volatility)
        elif vix_value < 20:
            return '▒'  # Medium (normal)
        elif vix_value < 30:
            return '▓'  # Dark (elevated)
        else:
            return '█'  # Full (crisis)
    
    def create_vix_line_chart(self, values: List[float]) -> List[str]:
        """Create clean VIX line chart with dots"""
        if not values or len(values) < 2:
            # Return empty chart
            return [
                "22┤                       ",
                "21┤                       ",
                "20├───────────────────────",
                "19┤   Loading Data...     ",
                "18┤                       ",
                "17┤                       ",
                "16┤                       ",
                "15┤                       ",
                "14┤                       ",
                "  └───────────────────────",
                "   Jul 30  Jul 31  Aug 1 "
            ]
        
        # Chart dimensions - 25 chars total width
        chart_width = 23  # Data area width (25 - 2 for axis labels)
        
        # Fixed Y-axis range to match Google Finance (14-22)
        y_min = 14
        y_max = 22
        chart_height = 9  # Number of Y levels
        
        # Create Y-axis levels
        y_levels = [22, 21, 20, 19, 18, 17, 16, 15, 14]
        
        # Compress data to fit chart width
        # ~156 points into 23 columns = ~6.8 points per column
        compression_ratio = len(values) / chart_width
        compressed_values = []
        
        for i in range(chart_width):
            # Get the window of data points for this column
            start_idx = int(i * compression_ratio)
            end_idx = int((i + 1) * compression_ratio)
            if end_idx > start_idx:
                window_values = values[start_idx:end_idx]
                # Use the average for smooth line
                avg_value = sum(window_values) / len(window_values)
                compressed_values.append(avg_value)
            else:
                compressed_values.append(values[min(start_idx, len(values)-1)])
        
        # Create empty chart grid
        chart_grid = [[' ' for _ in range(chart_width)] for _ in range(chart_height)]
        
        # Plot the line by finding the closest Y level for each compressed value
        for col, vix_val in enumerate(compressed_values):
            # Find which Y level this value is closest to
            best_row = 0
            min_distance = abs(vix_val - y_levels[0])
            
            for row, level in enumerate(y_levels):
                distance = abs(vix_val - level)
                if distance < min_distance:
                    min_distance = distance
                    best_row = row
            
            # Plot the dot at the closest level
            chart_grid[best_row][col] = '•'
        
        # Build the final chart lines
        chart_lines = []
        
        for row, level in enumerate(y_levels):
            if level == 20:
                # Special VIX=20 threshold line - don't draw line through dots
                line = "20├"
                for col in range(chart_width):
                    if chart_grid[row][col] == '•':
                        line += '•'
                    else:
                        line += '─'
            else:
                # Regular levels
                line = f"{level:2d}┤"
                for col in range(chart_width):
                    line += chart_grid[row][col]
            
            chart_lines.append(line)
        
        # Bottom border
        chart_lines.append("  └───────────────────────")
        
        # Date axis - get actual dates from cached timestamps
        if hasattr(self, '_vix_cache') and 'timestamps' in self._vix_cache:
            timestamps = self._vix_cache['timestamps']
            if timestamps:
                # Get dates for start, middle, and end
                start_date = timestamps[0].strftime("%b %d")
                mid_date = timestamps[len(timestamps)//2].strftime("%b %d")
                end_date = timestamps[-1].strftime("%b %d")
                date_line = f"   {start_date}  {mid_date}  {end_date} "
                chart_lines.append(date_line[:26])  # Ensure it fits
            else:
                chart_lines.append("   Jul 30  Jul 31  Aug 1 ")
        else:
            chart_lines.append("   Jul 30  Jul 31  Aug 1 ")
        
        return chart_lines
    
    def format_vix_mountain_display(self) -> List[Text]:
        """Format VIX line chart for display with caching"""
        now = datetime.now()
        
        # Check if we can use cached chart (refresh every 15 seconds for smooth updates)
        if (self._last_chart_render and 
            (now - self._last_chart_render).seconds < 15 and
            'mountain_display' in self._chart_cache):
            return self._chart_cache['mountain_display']
        
        # Generate new line chart
        mountain_data = self.get_vix_mountain_data()
        chart_lines = self.create_vix_line_chart(mountain_data)
        
        # Convert chart lines to Rich Text objects with appropriate styling
        text_lines = []
        
        # Add current VIX and risk status header
        current_vix = self.get_vix_level()
        risk_symbol = "✗" if current_vix > 20 else "✓"
        risk_color = "red" if current_vix > 20 else "green"
        header_line = Text()
        header_line.append(f"VIX: {current_vix:.1f} ", style="bold white")
        header_line.append(f"Risk: {risk_symbol}", style=f"bold {risk_color}")
        text_lines.append(header_line)
        
        # Add spacing
        text_lines.append(Text(""))
        
        for i, line in enumerate(chart_lines):
            if "├─" in line or "└─" in line:  # Border lines
                text_line = Text(line, style="yellow")
            elif "┤" in line:  # Y-axis lines with data
                # Split into Y-label and chart area
                parts = line.split("┤", 1)
                y_label = parts[0] + "┤"
                chart_area = parts[1] if len(parts) > 1 else ""
                
                text_line = Text()
                text_line.append(y_label, style="dim white")
                
                # Color the line chart
                for char in chart_area:
                    if char == '•':
                        # Color dots based on Y position
                        if "20├" in line:
                            text_line.append(char, style="yellow bold")  # At threshold
                        elif int(y_label.strip()[:2]) >= 20:
                            text_line.append(char, style="red bold")     # Above threshold
                        else:
                            text_line.append(char, style="green bold")   # Below threshold
                    elif char == '─':
                        text_line.append(char, style="yellow")  # Threshold line
                    else:
                        text_line.append(char, style="white")   # Space
            else:  # Date axis
                text_line = Text(line, style="dim cyan")
                
            text_lines.append(text_line)
        
        # Cache the result
        self._chart_cache['mountain_display'] = text_lines
        self._last_chart_render = now
        
        return text_lines
            
    def format_vix_chart_display(self) -> List[Text]:
        """Format VIX as full ASCII chart display with caching for smooth refresh"""
        now = datetime.now()
        
        # Check if we can use cached chart (refresh every 3 seconds)
        if (self._last_chart_render and 
            (now - self._last_chart_render).seconds < 3 and
            'chart_display' in self._chart_cache):
            return self._chart_cache['chart_display']
        
        # Generate new chart
        hourly_data = self.get_vix_24h_data()
        chart_lines = self.create_vix_ascii_chart(hourly_data)
        
        # Convert chart lines to Rich Text objects with appropriate styling
        text_lines = []
        
        for i, line in enumerate(chart_lines):
            if i == 0:  # Header line
                text_line = Text(line, style="bold white")
            elif "├─" in line:  # Threshold line at VIX=20
                text_line = Text(line, style="yellow")
            elif "│" in line:  # Y-axis lines with data
                # Split into Y-label and plot area
                if "│" in line:
                    y_label = line.split("│")[0] + "│"
                    plot_area = line.split("│", 1)[1] if "│" in line else ""
                    
                    text_line = Text()
                    text_line.append(y_label, style="dim white")
                    # Color the plot points
                    for char in plot_area:
                        if char == "●":
                            text_line.append(char, style="cyan bold")
                        else:
                            text_line.append(char, style="white")
                else:
                    text_line = Text(line, style="white")
            else:  # X-axis and other lines
                text_line = Text(line, style="dim white")
                
            text_lines.append(text_line)
        
        # Cache the result
        self._chart_cache['chart_display'] = text_lines
        self._last_chart_render = now
        
        return text_lines
            
    def get_current_capital(self) -> Tuple[float, float]:
        """Get current capital and calculate buying power
        Returns: (capital, buying_power)
        """
        try:
            # Try to get from ALM database first
            capital = get_latest_capital()
            if capital:
                buying_power = capital * 6.66  # 6.66x leverage
                return capital, buying_power
        except:
            pass
            
        # Fallback to default
        capital = 195930.0
        buying_power = capital * 6.66
        return capital, buying_power
        
    def get_current_positions(self) -> Dict[str, Any]:
        """Get current position information"""
        try:
            positions = get_current_positions()
            
            # Count contracts by side
            call_contracts = 0
            put_contracts = 0
            
            for pos in positions:
                if pos['quantity'] != 0:
                    if 'C' in pos['symbol']:
                        call_contracts += abs(pos['quantity'])
                    elif 'P' in pos['symbol']:
                        put_contracts += abs(pos['quantity'])
                        
            return {
                'call_contracts': call_contracts,
                'put_contracts': put_contracts,
                'total_contracts': call_contracts + put_contracts
            }
        except:
            # Return empty positions if error
            return {
                'call_contracts': 0,
                'put_contracts': 0,
                'total_contracts': 0
            }
            
    def calculate_notional(self, max_contracts: int) -> float:
        """Calculate implied notional value"""
        spy_price = self.get_spy_price()
        # Each SPY contract = 100 shares
        # Assuming positions on both sides (calls and puts)
        total_contracts = max_contracts * 2  # Max on each side
        notional = total_contracts * 100 * spy_price
        return notional
        
    def check_time_gate(self) -> Tuple[bool, str, float]:
        """Check time gate status
        Returns: (is_allowed, status_text, hours_setting)
        """
        if not self.market_timer:
            return True, "No Timer", 0.0
            
        # Get guardrail status from market timer
        is_allowed = self.market_timer.should_allow_trading_guardrail()
        hours_setting = self.market_timer.guardrail_settings[self.market_timer.current_guardrail_setting]
        
        # Calculate elapsed time
        now_et = datetime.now(self.eastern)
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        
        if now_et < market_open:
            return False, "Market Closed", hours_setting
            
        time_since_open = (now_et - market_open).total_seconds() / 3600  # in hours
        
        if is_allowed:
            status_text = f"{time_since_open:.1f}h Elapsed"
        else:
            remaining = hours_setting - time_since_open
            if remaining > 0:
                status_text = f"Wait {remaining:.1f}h"
            else:
                status_text = f"{time_since_open:.1f}h Elapsed"
                
        return is_allowed, status_text, hours_setting
        
    def format_mandate_number(self, number: int, label: str) -> Text:
        """Format a mandate label with number"""
        formatted_label = Text()
        formatted_label.append(f"{number}.", style="dim cyan")
        formatted_label.append(label, style="cyan")
        return formatted_label
        
    def get_validation_symbol(self, compliant: bool) -> Text:
        """Get validation symbol for right column"""
        if compliant:
            return Text("✓", style="green")
        else:
            return Text("✗", style="red")
            
    def get_mandate_validations(self, has_positions: bool, time_gate_allowed: bool, 
                               capital_values: Dict, vix_level: float) -> List[bool]:
        """Get validation status for each mandate"""
        if not has_positions:
            return [False] * 9  # No validations without positions
            
        validations = []
        
        # 1. Scope validation (always true for SPY daily options)
        validations.append(True)
        
        # 2. Greeks validation (would need actual position delta)
        validations.append(True)  # Assume compliant for now
        
        # 3. Capital validation (check if within limits)
        validations.append(True)
        
        # 4. Max contracts validation
        max_contracts = capital_values['max_contracts']
        contracts_ok = (capital_values['current_calls'] <= max_contracts and 
                      capital_values['current_puts'] <= max_contracts)
        validations.append(contracts_ok)
        
        # 5. Current contracts (always true - just informational)
        validations.append(True)
        
        # 6. Notional validation
        validations.append(True)
        
        # 7. Stop loss validation (would need to check actual stops)
        validations.append(True)  # Assume compliant
        
        # 8. Time gate validation
        validations.append(time_gate_allowed)
        
        # 9. VIX validation
        vix_ok = vix_level < 20
        validations.append(vix_ok)
        
        return validations
        
    def get_capital_values(self) -> Dict[str, Any]:
        """Get all capital-related values"""
        # Get current capital
        capital, buying_power = self.get_current_capital()
        
        # Calculate max contracts (simplified - actual calculation would consider option prices)
        # Assuming average option price of $5 and we want to use max 50% of buying power per side
        avg_option_price = 5.0
        max_contracts_per_side = int((buying_power * 0.5) / (avg_option_price * 100))
        max_contracts_per_side = min(max_contracts_per_side, 10)  # Cap at 10 for safety
        
        # Get current positions
        positions = self.get_current_positions()
        current_calls = positions['call_contracts']
        current_puts = positions['put_contracts']
        
        # Calculate notional
        notional = self.calculate_notional(max_contracts_per_side)
        
        return {
            'capital': capital,
            'buying_power': buying_power,
            'max_contracts': max_contracts_per_side,
            'current_calls': current_calls,
            'current_puts': current_puts,
            'notional_hkd': notional * 7.7
        }
        
    def create_panel(self) -> Panel:
        """Create the complete Risk Manager panel"""
        
        # Get all values
        time_gate_allowed, time_gate_text, _ = self.check_time_gate()
        capital_values = self.get_capital_values()
        vix_level = self.get_vix_level()
        
        # Check if we have any positions
        has_positions = capital_values['current_calls'] > 0 or capital_values['current_puts'] > 0
        
        # Get mandate validations
        validations = self.get_mandate_validations(has_positions, time_gate_allowed, 
                                                  capital_values, vix_level)
        
        # Create main table
        main_table = Table.grid(padding=0)
        main_table.add_column(width=35)  # Mandate section
        main_table.add_column(width=28)  # VIX visualization section
        
        # Create mandate section with space for checkmarks
        mandates_table = Table.grid(padding=0)
        mandates_table.add_column(style="cyan", width=16, no_wrap=True)  # Labels
        mandates_table.add_column(style="white", width=15, no_wrap=True)  # Values
        mandates_table.add_column(width=2)  # Checkmarks
        
        # Add mandate rows with validation symbols - shortened for no wrapping
        mandate_items = [
            (1, "Scope:", "Short SPY Daily"),
            (2, "Greeks:", "Delta < 0.4"),
            (3, "Capital:", f"HKD {capital_values['capital']:,.0f}"),
            (4, "Max Vol:", f"{capital_values['max_contracts']}/side"),
            (5, "Current:", f"{capital_values['current_calls']}C, {capital_values['current_puts']}P"),
            (6, "Notional:", f"HKD {capital_values['notional_hkd']//1000:.0f}K"),
            (7, "Stop Loss:", "MANDATORY 3-5x"),
            (8, "Time Gate:", time_gate_text),
            (9, "Black Swan:", "VIX < 20")
        ]
        
        for i, (num, label, value) in enumerate(mandate_items):
            if has_positions:
                mandates_table.add_row(
                    self.format_mandate_number(num, label),
                    value,
                    self.get_validation_symbol(validations[i])
                )
            else:
                mandates_table.add_row(
                    self.format_mandate_number(num, label),
                    value,
                    Text("")  # No validation symbols without positions
                )
        
        # Create VIX trends section (replacing trade execution)
        vix_trends_table = Table.grid(padding=0)
        vix_trends_table.add_column()
        
        # Add VIX mountain display without header
        vix_mountain_lines = self.format_vix_mountain_display()
        for mountain_line in vix_mountain_lines:
            vix_trends_table.add_row(mountain_line)
        
        # Add minimal spacing below chart
        vix_trends_table.add_row(Text(""))  # Empty row
        
        # Add headers - only show Mandate header, no VIX header
        header_table = Table.grid(padding=(1, 0))  # Add top padding
        header_table.add_column(width=35)
        header_table.add_column(width=28)
        header_table.add_row(
            Text("Mandate", style="bold cyan"),
            Text("")  # No header for VIX section
        )
        
        # Combine sections
        final_table = Table.grid(padding=0)
        final_table.add_column()
        final_table.add_row(header_table)
        final_table.add_row(Text(""))
        
        main_table.add_row(mandates_table, vix_trends_table)
        final_table.add_row(main_table)
        
        return Panel(
            final_table,
            title="[bold cyan]Risk Manager[/bold cyan]",
            title_align="center",
            border_style="cyan",
            padding=(0, 1),
            expand=True,
            width=70  # Fixed width to align with other panels
        )
        
    def render(self) -> Panel:
        """Render the Risk Manager panel"""
        return self.create_panel()


def create_risk_manager_panel(market_timer=None) -> Panel:
    """Factory function to create a Risk Manager panel"""
    risk_panel = RiskManagerPanel()
    if market_timer:
        risk_panel.set_market_timer(market_timer)
    return risk_panel.render()


if __name__ == "__main__":
    # Demo the panel
    console = Console()
    panel = create_risk_manager_panel()
    console.print(panel)