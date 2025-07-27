"""
Exercise tracking panel for displaying option exercises
Shows recent exercises and their disposal status
"""
from datetime import datetime
from typing import List, Dict, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
import pytz


class ExercisePanel:
    """Panel for displaying option exercise tracking"""
    
    def __init__(self):
        self.console = Console()
        self.eastern = pytz.timezone('US/Eastern')
        self.hk = pytz.timezone('Asia/Hong_Kong')
        
    def create_panel(self, exercises: Optional[List[Dict]] = None) -> Panel:
        """Create exercise tracking panel
        
        Args:
            exercises: List of exercise/expiration records from IBKR
            
        Returns:
            Rich Panel with exercise information
        """
        if not exercises:
            return Panel(
                Align.center(
                    Text("No recent option events", style="dim"),
                    vertical="middle"
                ),
                title="[bold yellow]Option Events (Exercises/Expirations)[/bold yellow]",
                border_style="yellow"
            )
            
        # Create table
        table = Table(
            show_header=True,
            header_style="bold cyan",
            padding=(0, 1),
            expand=True
        )
        
        # Add columns
        table.add_column("Date", justify="center", width=10)
        table.add_column("Option", justify="center", width=12)
        table.add_column("Type", justify="center", width=12)
        table.add_column("Shares", justify="right", width=6)
        table.add_column("Impact", justify="right", width=10)
        table.add_column("Status", justify="center", width=12)
        
        # Add rows
        for ex in exercises:
            # Handle both database format and IBKR format
            if 'type' in ex:  # IBKR format
                # Format date
                date_str = ex['date'] if isinstance(ex['date'], str) else ex['date'].strftime('%Y-%m-%d')
                
                # Format option symbol
                option_str = ex['symbol']
                
                # Format event type with color
                event_type = ex['type']
                if event_type == 'Assignment':
                    type_str = Text("ASSIGNMENT", style="red bold")
                    shares_str = "100"  # Assignments always 100 shares
                    impact_str = Text(f"-${100 * float(option_str[:-1]):,.0f}", style="red")
                    status_str = Text("EXECUTED", style="red")
                elif event_type == 'Exercise':
                    type_str = Text("EXERCISE", style="green bold")
                    shares_str = "100"
                    impact_str = Text("+100 SPY", style="green")
                    status_str = Text("EXECUTED", style="green")
                elif event_type == 'Expiration':
                    type_str = Text("EXPIRATION", style="cyan")
                    shares_str = "-"
                    impact_str = Text("$0", style="dim")
                    status_str = Text("EXPIRED", style="dim")
                else:  # Pending
                    type_str = Text("PENDING", style="yellow")
                    shares_str = "?"
                    impact_str = Text("TBD", style="yellow")
                    status_str = Text("PENDING", style="yellow")
                    
            else:  # Database format (legacy)
                # Format date
                exercise_date = ex['exercise_date']
                if isinstance(exercise_date, str):
                    date_str = exercise_date[:10]
                else:
                    date_str = exercise_date.strftime('%Y-%m-%d')
                    
                # Format option symbol
                option_str = ex.get('display_symbol', f"{ex['strike_price']} {ex['option_type']}")
                
                # Event type based on option type
                if ex['option_type'] == 'PUT':
                    type_str = Text("PUT ASSIGN", style="red bold")
                else:
                    type_str = Text("CALL ASSIGN", style="green bold")
                
                # Format shares
                shares = ex['shares_received']
                shares_str = f"{shares:,}"
                
                # Format balance impact
                impact = ex.get('balance_impact', 0)
                if impact < 0:
                    impact_str = Text(f"-${abs(impact):,.0f}", style="red")
                else:
                    impact_str = Text(f"${impact:,.0f}", style="green")
                    
                # Format status with color
                status = ex['disposal_status']
                if status == 'PENDING':
                    status_str = Text("PENDING", style="yellow bold")
                elif status == 'ORDER_PLACED':
                    status_str = Text("ORDER SENT", style="cyan")
                elif status == 'FILLED':
                    status_str = Text("FILLED", style="green")
                else:
                    status_str = Text(status, style="dim")
                
            # Add row
            table.add_row(
                date_str,
                option_str,
                type_str,
                shares_str,
                impact_str,
                status_str
            )
            
        # Add summary row if multiple events
        if len(exercises) > 1:
            # Count by type
            assignments = sum(1 for ex in exercises if ex.get('type') == 'Assignment')
            expirations = sum(1 for ex in exercises if ex.get('type') == 'Expiration')
            table.add_row(
                "",
                "[bold]Summary[/bold]",
                f"[bold]{assignments} Assign, {expirations} Expire[/bold]",
                "",
                "",
                ""
            )
            
        # Create notes section
        notes = []
        
        # Count assignments needing disposal
        if any('type' in ex for ex in exercises):
            assignment_count = sum(1 for ex in exercises if ex.get('type') == 'Assignment')
            if assignment_count > 0:
                notes.append(f"[red]• {assignment_count} assignment(s) - shares received, disposal needed[/red]")
        else:
            # Legacy format
            pending_count = sum(1 for ex in exercises if ex['disposal_status'] in ['PENDING', 'ORDER_PLACED'])
            if pending_count > 0:
                notes.append(f"[yellow]• {pending_count} exercise(s) pending disposal[/yellow]")
            
        # Add timing info
        current_time = datetime.now(self.eastern)
        market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
        extended_start = current_time.replace(hour=4, minute=0, second=0, microsecond=0)
        extended_end = current_time.replace(hour=20, minute=0, second=0, microsecond=0)
        
        if extended_start <= current_time < market_open:
            notes.append("[cyan]• Pre-market trading active (4:00-9:30 ET)[/cyan]")
        elif market_close < current_time <= extended_end:
            notes.append("[cyan]• After-hours trading active (4:00-8:00 PM ET)[/cyan]")
        elif market_open <= current_time <= market_close:
            notes.append("[green]• Regular market hours[/green]")
        else:
            notes.append("[dim]• Markets closed[/dim]")
            
        # Combine table and notes
        content = [table]
        if notes:
            content.append("")  # Spacer
            content.extend(notes)
            
        return Panel(
            "\n".join(str(item) for item in content),
            title="[bold yellow]Option Events (Exercises/Expirations)[/bold yellow]",
            border_style="yellow"
        )
        
    def format_for_scrollable(self, exercises: Optional[List[Dict]] = None) -> str:
        """Format exercise data for scrollable display
        
        Returns string representation suitable for ScrollableContainer
        """
        if not exercises:
            return "[dim]No recent exercises[/dim]"
            
        lines = []
        lines.append("[bold yellow]EXERCISE TRACKING[/bold yellow]")
        lines.append("")
        
        for ex in exercises:
            # Format date
            exercise_date = ex['exercise_date']
            if isinstance(exercise_date, str):
                date_str = exercise_date[:10]
            else:
                date_str = exercise_date.strftime('%m/%d')
                
            # Format option
            option_str = ex.get('display_symbol', f"{ex['strike_price']} {ex['option_type']}")
            
            # Format status with color
            status = ex['disposal_status']
            if status == 'PENDING':
                status_str = "[yellow]PENDING[/yellow]"
            elif status == 'ORDER_PLACED':
                status_str = "[cyan]ORDER SENT[/cyan]"
            elif status == 'FILLED':
                status_str = "[green]FILLED[/green]"
            else:
                status_str = f"[dim]{status}[/dim]"
                
            # Format impact
            impact = ex.get('balance_impact', 0)
            impact_str = f"[red]-${abs(impact):,.0f}[/red]" if impact < 0 else f"[green]${impact:,.0f}[/green]"
            
            # Format time
            hours_since = ex.get('hours_since_detection')
            if hours_since is not None:
                if hours_since < 1:
                    time_str = f"{int(hours_since * 60)}m"
                elif hours_since < 24:
                    time_str = f"{hours_since:.1f}h"
                else:
                    days = int(hours_since / 24)
                    time_str = f"{days}d"
            else:
                time_str = ""
                
            # Add line
            lines.append(f"{date_str} {option_str:>10} x{ex['shares_received']:>4} {impact_str:>12} {status_str} {time_str:>5}")
            
        # Add summary
        if len(exercises) > 1:
            lines.append("")
            total_shares = sum(ex['shares_received'] for ex in exercises)
            total_impact = sum(ex.get('balance_impact', 0) for ex in exercises)
            lines.append(f"[bold]Total: {total_shares:,} shares, -${abs(total_impact):,.0f}[/bold]")
            
        return "\n".join(lines)