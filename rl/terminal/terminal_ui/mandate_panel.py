"""
Mandate Panel - Shows active positions and risk status
Tracks real positions from backend.data.database with stop loss protection
"""
from typing import Dict, List, Optional
from datetime import datetime
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))
from data_pipeline.database_position_tracker import DatabasePositionTracker
from expiration_manager import ExpirationManager


class MandatePanel:
    """
    Displays active trading positions and their risk status
    Shows real positions from backend.data.database (not IB Gateway)
    """
    
    def __init__(self):
        self.db_tracker = DatabasePositionTracker()
        self.expiration_manager = ExpirationManager()
        self.connected = False
        self.last_positions = []
        
    def connect_database(self) -> bool:
        """Connect to database for position tracking"""
        self.connected = self.db_tracker.connect()
        if self.connected:
            self.expiration_manager.connect()
        return self.connected
        
    def get_current_price_from_chain(self, strike: float, option_type: str, options_chain: List[Dict]) -> Optional[float]:
        """
        Find current price for an option from the options chain
        
        Args:
            strike: Strike price
            option_type: 'C' or 'P' (or 'CALL'/'PUT')
            options_chain: List of option data
            
        Returns:
            Mid price if found, None otherwise
        """
        if not options_chain:
            return None
            
        # Normalize option type
        opt_type = option_type[0].upper() if option_type else 'C'
        
        # Search for matching option
        for option in options_chain:
            if (option.get('strike') == strike and 
                option.get('type', '').upper().startswith(opt_type)):
                
                bid = option.get('bid', 0)
                ask = option.get('ask', 0)
                
                # Calculate mid price
                if bid > 0 and ask > 0:
                    return (bid + ask) / 2
                elif bid > 0:
                    return bid
                elif ask > 0:
                    return ask
                    
        return None
        
    def create_panel(self, 
                    positions: Optional[Dict] = None,
                    pending_trade: Optional[Dict] = None,
                    violation_alert: bool = False,
                    options_chain: Optional[List[Dict]] = None) -> Panel:
        """
        Create mandate panel showing current positions and risk status
        
        Args:
            positions: Positions data (can be from backend.data.database or passed in)
            pending_trade: Trade waiting for execution
            violation_alert: True if showing stop loss violation
            options_chain: Current options chain data for P&L calculation
        """
        content = Table(show_header=False, box=None, expand=True)
        content.add_column("Content", justify="center")
        
        # Get positions from backend.data.database if not provided
        if positions is None and self.connected:
            # Query the trading.trades table for open positions
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                
                # Use config from parent directory
                sys.path.append(str(Path(__file__).parent.parent))
                from config import DB_CONFIG
                
                conn = psycopg2.connect(
                    host=DB_CONFIG['host'],
                    port=DB_CONFIG['port'],
                    database=DB_CONFIG['database'],
                    user=DB_CONFIG['user'],
                    password=DB_CONFIG['password']
                )
                
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Query for ACTIVE positions - only today's trades that are still open
                    cur.execute("""
                        SELECT 
                            strike_price as strike,
                            option_type as type,
                            quantity,
                            entry_price,
                            stop_loss_price as stop_loss,
                            entry_time,
                            entry_commission,
                            expiration
                        FROM trading.trades
                        WHERE status = 'open'
                        AND symbol = 'SPY'
                        AND entry_time::date = CURRENT_DATE  -- Only TODAY's trades
                        AND expiration >= CURRENT_DATE  -- Not expired
                        ORDER BY entry_time DESC
                    """)
                    
                    db_positions = cur.fetchall()
                    
                    if db_positions:
                        positions = {
                            'positions': [
                                {
                                    'strike': pos['strike'],
                                    'right': pos['type'][0],  # CALL -> C, PUT -> P
                                    'type': pos['type'][0],
                                    'quantity': abs(pos['quantity']),
                                    'entry_price': float(pos['entry_price']),
                                    'stop_loss': float(pos['stop_loss']) if pos['stop_loss'] else None,
                                    'position_size': abs(pos['quantity']),
                                    'entry_time': pos.get('entry_time'),
                                    'commission': float(pos.get('entry_commission', 0)),
                                    'current_price': float(pos['entry_price']),  # Will be updated with market data
                                    'pnl_per_contract': 0  # Will be calculated with market data
                                }
                                for pos in db_positions
                            ]
                        }
                        
                conn.close()
                
            except Exception as e:
                # If database fails, continue with no positions
                positions = None
        
        # Title
        if violation_alert:
            title_text = Text("⚠️  RISK VIOLATION ⚠️", style="bold red blink")
            content.add_row(Align.center(title_text))
            content.add_row("")
            
            # Big warning message
            warning = Text("TRADE BLOCKED!\n\nNO STOP LOSS ATTACHED\n\nUNLIMITED RISK EXPOSURE", 
                         style="bold red on yellow")
            content.add_row(Align.center(warning))
            content.add_row("")
            
            border_style = "bold red"
            
        else:
            # Normal status display - Active Positions only
            status_table = Table(show_header=True, box=box.ROUNDED, expand=True)
            # Make columns WIDE and CLEAR
            status_table.add_column("STRIKE", style="cyan", width=8, no_wrap=True)
            status_table.add_column("TYPE", style="white", width=6, no_wrap=True)
            status_table.add_column("QTY", style="magenta", width=5, justify="center", no_wrap=True)
            status_table.add_column("ENTRY", style="green", width=8, justify="right", no_wrap=True)
            status_table.add_column("CURRENT", style="yellow", width=8, justify="right", no_wrap=True)
            status_table.add_column("P&L", width=8, justify="right", no_wrap=True)
            status_table.add_column("STOP", style="red", width=8, justify="right", no_wrap=True)
            
            # Show active positions
            if positions and 'positions' in positions:
                total_pnl = 0
                for pos in positions['positions']:
                    strike = pos.get('strike', 0)
                    right = pos.get('type', pos.get('right', '?'))
                    entry = pos.get('entry_price', 0)
                    stop = pos.get('stop_loss', 0)
                    quantity = abs(pos.get('quantity', pos.get('position_size', 1)))
                    
                    # Get current price from options chain
                    current = entry  # Default to entry if no market data
                    if options_chain:
                        market_price = self.get_current_price_from_chain(strike, right, options_chain)
                        if market_price is not None:
                            current = market_price
                    
                    # Calculate P&L - FOR SOLD OPTIONS IT'S REVERSED!
                    # When you SELL, you want the price to go DOWN
                    # P&L = (Entry Price - Current Price) × 100 × Quantity
                    pnl_per_contract = (entry - current) * 100
                    total_pos_pnl = pnl_per_contract * quantity
                    total_pnl += total_pos_pnl
                    pnl_color = "green" if total_pos_pnl > 0 else "red" if total_pos_pnl < 0 else "white"
                    
                    # Format columns without dollar signs
                    strike_str = str(strike)
                    type_str = right
                    volume_str = str(quantity)
                    entry_str = f"{entry:.2f}"
                    current_str = f"{current:.2f}" if current else "N/A"
                    pnl_str = f"{total_pos_pnl:+,.0f}"
                    
                    if stop and stop > 0:
                        stop_str = f"{stop:.2f}"
                    else:
                        stop_str = "NONE"
                    
                    status_table.add_row(
                        strike_str,
                        type_str,
                        volume_str,
                        entry_str,
                        current_str,
                        Text(pnl_str, style=pnl_color),
                        stop_str
                    )
                
                # Add summary row
                if len(positions['positions']) > 0:
                    status_table.add_row("", "", "", "", "", "", "")
                    total_positions = len(positions['positions'])
                    total_volume = sum(abs(p.get('quantity', p.get('position_size', 1))) for p in positions['positions'])
                    protected = sum(1 for p in positions['positions'] if p.get('stop_loss', 0) > 0)
                    exposed = total_positions - protected
                    
                    pnl_color = "green" if total_pnl > 0 else "red" if total_pnl < 0 else "white"
                    
                    if exposed > 0:
                        summary_stops = f"{exposed} UNPROTECTED"
                        stop_style = "bold yellow"
                    else:
                        summary_stops = ""
                        stop_style = "dim"
                    
                    status_table.add_row(
                        Text("TOTAL", style="bold"),
                        f"{total_positions}p",
                        str(total_volume),
                        "",
                        "",
                        Text(f"{total_pnl:+,.0f}", style=f"bold {pnl_color}"),
                        Text(summary_stops, style=stop_style)
                    )
                    
                    # Add HKD conversion line
                    hkd_pnl = total_pnl * 7.7  # USD to HKD conversion
                    hkd_color = "green" if hkd_pnl > 0 else "red" if hkd_pnl < 0 else "white"
                    status_table.add_row(
                        Text("HKD P&L", style="dim"),
                        "",
                        "",
                        "",
                        "",
                        Text(f"{hkd_pnl:+,.0f}", style=f"dim {hkd_color}"),
                        Text("(@ 7.7)", style="dim")
                    )
            else:
                # No positions
                status_table.add_row("", "", "", "No Active", "Positions", "", "")
            
            content.add_row(status_table)
            
            # Pending trade warning
            if pending_trade:
                content.add_row("")
                pending_text = Text("⏳ PENDING TRADE - VALIDATING", 
                                  style="bold yellow blink")
                content.add_row(Align.center(pending_text))
            
            # Set border color based on position status
            if positions and any(p.get('stop_loss', 0) == 0 for p in positions.get('positions', [])):
                border_style = "yellow"
            else:
                border_style = "cyan"
        
        return Panel(
            content,
            title="[bold cyan]Active Positions (USD)[/bold cyan]", 
            border_style=border_style,
            padding=(0, 1),
            expand=True
        )
    
    def format_risk_metrics(self, positions: List[Dict]) -> Dict:
        """Calculate and format portfolio risk metrics"""
        total_risk = 0
        unprotected_risk = 0
        protected_count = 0
        
        for pos in positions:
            entry = pos.get('entry_price', 0)
            stop = pos.get('stop_loss', 0)
            size = pos.get('position_size', 1)
            
            if stop > 0:
                # Protected position
                risk = (stop - entry) * 100 * size
                total_risk += risk
                protected_count += 1
            else:
                # Unprotected - could lose everything
                # Assume max loss of $10 per contract (SPY going to 0)
                unprotected_risk += 1000 * size  # $10 * 100 shares
        
        return {
            'total_positions': len(positions),
            'protected_positions': protected_count,
            'unprotected_positions': len(positions) - protected_count,
            'total_risk': total_risk,
            'unprotected_risk': unprotected_risk,
            'risk_status': 'SAFE' if protected_count == len(positions) else 'EXPOSED'
        }