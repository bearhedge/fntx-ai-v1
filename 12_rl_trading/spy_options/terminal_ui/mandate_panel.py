"""
Mandate Panel - Shows active positions and risk status
Tracks real positions from database with stop loss protection
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
    Shows real positions from database (not IB Gateway)
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
        
    def create_panel(self, 
                    positions: Optional[Dict] = None,
                    pending_trade: Optional[Dict] = None,
                    violation_alert: bool = False) -> Panel:
        """
        Create mandate panel showing current positions and risk status
        
        Args:
            positions: Positions data (can be from database or passed in)
            pending_trade: Trade waiting for execution
            violation_alert: True if showing stop loss violation
        """
        content = Table(show_header=False, box=None, expand=True)
        content.add_column("Content", justify="center")
        
        # Get positions from database if not provided
        if positions is None and self.connected:
            db_positions = self.db_tracker.get_open_positions()
            if db_positions:
                positions = {
                    'positions': [
                        {
                            'strike': pos['strike'],
                            'right': pos['type'],
                            'entry_price': pos['entry_price'],
                            'stop_loss': pos['stop_loss'],
                            'position_size': pos['quantity'],
                            'entry_time': pos.get('entry_time'),
                            'commission': pos.get('entry_commission', 0),
                            'credit_received': pos['entry_price'] * pos['quantity'] * 100,
                            'max_risk': (pos['stop_loss'] - pos['entry_price']) * pos['quantity'] * 100 if pos.get('stop_loss') else None,
                            'expiration': pos.get('expiration'),
                            'underlying_price': pos.get('underlying_price_at_entry')
                        }
                        for pos in db_positions
                    ]
                }
        
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
            # Normal status display
            status_table = Table(show_header=True, box=box.ROUNDED, 
                                title="📊 Active Positions",
                                title_style="bold cyan")
            status_table.add_column("Position", style="white")
            status_table.add_column("Entry", style="green", justify="right")
            status_table.add_column("Credit", style="cyan", justify="right")
            status_table.add_column("Stop", style="yellow", justify="right")
            status_table.add_column("Max Risk", style="red", justify="right")
            status_table.add_column("Comm", style="dim", justify="right")
            status_table.add_column("Status", justify="center")
            
            # Show active positions
            if positions and 'positions' in positions:
                for pos in positions['positions']:
                    strike = pos.get('strike', 0)
                    right = pos.get('right', '?')
                    entry = pos.get('entry_price', 0)
                    stop = pos.get('stop_loss', 0)
                    size = pos.get('position_size', 1)
                    credit = pos.get('credit_received', 0)
                    commission = pos.get('commission', 0)
                    
                    # Format position string
                    position_str = f"Short {strike}{right}"
                    entry_str = f"${entry:.2f}"
                    credit_str = f"${credit:.0f}" if credit else "-"
                    comm_str = f"${commission:.2f}" if commission else "-"
                    
                    if stop and stop > 0:
                        stop_str = f"${stop:.2f}"
                        risk = (stop - entry) * 100 * size  # Per contract risk
                        risk_str = f"${risk:.0f}"
                        status = Text("✅ Protected", style="bold green")
                    else:
                        stop_str = "NONE"
                        risk_str = "UNLIMITED"
                        status = Text("❌ EXPOSED", style="bold red blink")
                    
                    status_table.add_row(position_str, entry_str, credit_str, stop_str, risk_str, comm_str, status)
                
                # Add summary row
                if len(positions['positions']) > 0:
                    status_table.add_row("", "", "", "", "", "", "")
                    total_positions = len(positions['positions'])
                    protected = sum(1 for p in positions['positions'] if p.get('stop_loss', 0) > 0)
                    exposed = total_positions - protected
                    total_credit = sum(p.get('credit_received', 0) for p in positions['positions'])
                    total_commission = sum(p.get('commission', 0) for p in positions['positions'])
                    
                    summary_text = f"{total_positions} position{'s' if total_positions > 1 else ''}"
                    if exposed > 0:
                        summary_style = "bold red"
                        summary_text += f" ({exposed} EXPOSED)"
                    else:
                        summary_style = "bold green"
                        summary_text += " (All Protected)"
                    
                    status_table.add_row(
                        Text(f"Total: {total_positions}", style="bold"),
                        "", 
                        f"${total_credit:.0f}" if total_credit else "",
                        "", "",
                        f"${total_commission:.2f}" if total_commission else "",
                        Text(summary_text, style=summary_style)
                    )
            else:
                # No positions
                status_table.add_row("No Active Positions", "-", "-", "-", "-", "-",
                                   Text("✅", style="green"))
            
            content.add_row(status_table)
            content.add_row("")
            
            # Show recently expired positions
            recent_expirations = self.expiration_manager.get_recent_expirations(days_back=2)
            if recent_expirations:
                exp_table = Table(show_header=True, box=box.ROUNDED,
                                 title="📅 Recent Expirations",
                                 title_style="bold yellow")
                exp_table.add_column("Position", style="white")
                exp_table.add_column("Exit Time", style="dim")
                exp_table.add_column("P&L", justify="right")
                exp_table.add_column("Status", justify="center")
                
                for exp in recent_expirations:
                    position_str = f"Short {exp['position']}"
                    exit_time = exp['exit_time'].strftime('%m/%d %H:%M')
                    pnl = exp['pnl']
                    pnl_str = f"${pnl:+.0f}"
                    pnl_style = "green" if pnl >= 0 else "red"
                    
                    if exp['status'] == 'expired_worthless':
                        status_text = Text("✓ Expired OTM", style="green")
                    elif exp['status'] == 'expired_itm':
                        status_text = Text("⚠️  Expired ITM", style="yellow")
                    else:
                        status_text = Text(exp['status'], style="dim")
                    
                    exp_table.add_row(
                        position_str,
                        exit_time,
                        Text(pnl_str, style=pnl_style),
                        status_text
                    )
                
                content.add_row(exp_table)
                content.add_row("")
            
            # Trading rules reminder
            rules = Table(show_header=False, box=None)
            rules.add_column("Rule")
            rules.add_row(Text("POSITION RULES:", style="bold yellow"))
            rules.add_row("• Maximum 1 position at a time")
            rules.add_row("• All positions require stop loss")
            rules.add_row("• Stop loss = 3.5x premium")
            rules.add_row("• Risk management priority")
            
            content.add_row(Align.center(rules))
            
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
                border_style = "bright_green"
        
        return Panel(
            content,
            title="[bold]Trading Mandate[/bold]",
            border_style=border_style,
            padding=(1, 1)
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