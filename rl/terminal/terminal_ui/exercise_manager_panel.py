"""
Exercise Manager Panel for Terminal UI
Professional display for exercise risk management and HKT disposal planning
"""
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import pytz
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from rich.align import Align
from rich import box


class ExerciseManagerPanel:
    """Professional exercise risk manager status display"""
    
    def __init__(self):
        self.last_status = None
        self.position_confirmations = {}  # Track consecutive checks per position
        
    def format_status_item(self, number: int, label: str, value: str) -> Table:
        """Format a status item in the numbered list style"""
        table = Table.grid(padding=0)
        table.add_column(width=20, no_wrap=True)
        table.add_column(width=25, no_wrap=True)
        
        formatted_label = Text()
        formatted_label.append(f"{number}.", style="dim cyan")
        formatted_label.append(label, style="cyan")
        
        table.add_row(formatted_label, Text(value, style="white"))
        return table
        
    def calculate_10min_average(self, current_delta: float, position_key: str) -> float:
        """Calculate 10-minute delta average (placeholder for now)"""
        # In production, this would track historical delta values
        # For now, return current delta with small variation
        return current_delta
        
    def create_panel(self, cleanup_status: Optional[Dict]) -> Panel:
        """Create terminal UI panel for cleanup manager"""
        
        if not cleanup_status:
            return Panel(
                Text("Cleanup Manager Not Available", style="dim"),
                title="[bold cyan]Cleanup Manager[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
                width=70
            )
        
        sections = []
        
        # Get time information
        et_tz = pytz.timezone('America/New_York')
        now_et = datetime.now(et_tz)
        activation_time = now_et.replace(hour=15, minute=45, second=0)
        emergency_time = now_et.replace(hour=15, minute=55, second=0)
        
        time_to_close = cleanup_status.get('time_to_close', 0)
        time_to_emergency = cleanup_status.get('time_to_emergency', 0)
        
        # Determine system status
        if now_et >= emergency_time:
            system_status = "EMERGENCY"
            status_color = "red bold"
        elif now_et >= activation_time:
            system_status = "ACTIVE"
            status_color = "green"
        else:
            system_status = "INACTIVE"
            status_color = "yellow"
            
        # Create headers
        header_table = Table.grid(padding=(1, 0))
        header_table.add_column(width=35)
        header_table.add_column(width=35)
        header_table.add_row(
            Text("Exercise Risk Monitor", style="bold cyan"),
            Text("HKT Disposal Plan", style="bold cyan", justify="right")
        )
        sections.append(header_table)
        sections.append(Text(""))  # Spacer
        
        # Status information section
        status_section = Table.grid(padding=0)
        status_section.add_column(width=35)
        status_section.add_column(width=35)
        
        # Left column items - Exercise Risk
        left_items = []
        
        # 1. Exercise Risk Status
        status_value = Text(system_status, style=status_color)
        left_items.append(self.format_status_item(1, "Risk Status:", system_status))
        
        # 2. Exercise Window
        exercise_window_value = "3:45 PM - 4:00 PM ET"
        left_items.append(self.format_status_item(2, "Risk Window:", exercise_window_value))
        
        # Right column items - HKT Disposal
        right_items = []
        
        # HKT disposal time (2 PM HKT = 2 AM/3 AM ET depending on DST)
        hkt_time = "HKT 2:00 PM (Next Day)"
        right_items.append(Text(f"Disposal: {hkt_time}", style="white"))
        
        # Next scan time
        next_check = now_et + timedelta(seconds=3)
        next_check_text = f"Next Scan: {next_check.strftime('%H:%M:%S')} ET"
        right_items.append(Text(next_check_text, style="white"))
        
        # Add rows to status section
        for i in range(2):
            left = left_items[i] if i < len(left_items) else Text("")
            right = right_items[i] if i < len(right_items) else Text("")
            status_section.add_row(left, right)
            
        sections.append(status_section)
        
        # Emergency countdown and scan info
        emergency_section = Table.grid(padding=0)
        emergency_section.add_column(width=35)
        emergency_section.add_column(width=35)
        
        # 3. Exercise Alert
        if time_to_emergency > 0:
            alert_value = f"{int(time_to_emergency)} min to exercise"
        else:
            alert_value = "EXERCISE RISK!"
        emergency_section.add_row(
            self.format_status_item(3, "Exercise Alert:", alert_value),
            Text(f"ITM Scan: 3 seconds", style="white")
        )
        
        # 4. ITM Positions
        positions = cleanup_status.get('positions_at_risk', [])
        itm_count = sum(1 for p in positions if abs(p.get('delta', 0)) >= 0.95)
        positions_value = f"{len(positions)} monitored"
        emergency_section.add_row(
            self.format_status_item(4, "Positions:", positions_value),
            Text(f"ITM Risk: {itm_count}", style="red" if itm_count > 0 else "white")
        )
        
        sections.append(emergency_section)
        sections.append(Text(""))  # Spacer
        
        # Position monitoring table
        if positions:
            # Create position table
            pos_table = Table(
                show_header=True,
                header_style="bold",
                box=None,
                expand=True,
                padding=(0, 1)
            )
            pos_table.add_column("Strike", style="cyan", width=8)
            pos_table.add_column("Type", style="white", width=6)
            pos_table.add_column("Delta", width=8)
            pos_table.add_column("ITM Prob", style="dim", width=8)
            pos_table.add_column("Dispose", width=8)
            pos_table.add_column("Risk Level", width=12)
            
            # Sort positions by delta (highest risk first)
            positions_sorted = sorted(positions, key=lambda x: abs(x.get('delta', 0)), reverse=True)
            
            for pos in positions_sorted[:5]:  # Show top 5
                strike = f"{int(pos['strike'])}"
                option_type = pos['right']
                delta = abs(pos.get('delta', 0))
                position_key = f"{pos['symbol']}_{pos['strike']}_{pos['right']}"
                
                # Calculate ITM probability (simplified)
                itm_probability = min(delta * 100, 99.9)
                
                # Determine disposal plan
                if delta >= 0.95:
                    if system_status == "EMERGENCY":
                        dispose_plan = "NOW"
                    else:
                        dispose_plan = "3:55PM"
                elif delta >= 0.90:
                    dispose_plan = "WATCH"
                else:
                    dispose_plan = "HOLD"
                
                # Determine exercise risk level
                if system_status == "EMERGENCY" and delta >= 0.50:
                    risk_level = Text("EXERCISE!", style="red bold")
                elif delta >= 0.95:
                    if system_status == "ACTIVE":
                        risk_level = Text("HIGH RISK", style="red")
                    else:
                        risk_level = Text("MONITOR", style="yellow")
                elif delta >= 0.90:
                    risk_level = Text("MEDIUM", style="yellow")
                else:
                    risk_level = Text("LOW", style="green")
                
                # Format delta with color
                if delta >= 0.95:
                    delta_text = Text(f"{delta:.3f}", style="red bold")
                elif delta >= 0.90:
                    delta_text = Text(f"{delta:.3f}", style="yellow")
                else:
                    delta_text = Text(f"{delta:.3f}", style="white")
                
                # Format disposal plan
                if dispose_plan == "NOW":
                    dispose_text = Text(dispose_plan, style="red bold")
                elif dispose_plan == "3:55PM":
                    dispose_text = Text(dispose_plan, style="yellow")
                elif dispose_plan == "WATCH":
                    dispose_text = Text(dispose_plan, style="cyan")
                else:
                    dispose_text = Text(dispose_plan, style="green")
                
                pos_table.add_row(
                    strike,
                    option_type,
                    delta_text,
                    f"{itm_probability:.1f}%",
                    dispose_text,
                    risk_level
                )
            
            sections.append(pos_table)
        else:
            no_positions = Text("No positions monitored", style="dim", justify="center")
            sections.append(no_positions)
        
        sections.append(Text(""))  # Spacer
        
        # Recent exercise management actions
        actions = cleanup_status.get('recent_actions', [])
        if actions:
            sections.append(Text("Recent Exercise Actions:", style="bold"))
            
            for action in actions[-3:]:  # Last 3 actions
                time_str = action['time'].strftime('%H:%M:%S')
                message = action['message']
                
                action_line = Text()
                action_line.append(f"{time_str} - ", style="dim")
                action_line.append(message, style="white" if action['success'] else "red")
                sections.append(action_line)
        
        # Combine all sections
        content = Group(*sections)
        
        # Update last status
        self.last_status = cleanup_status
        
        return Panel(
            content,
            title="[bold cyan]Exercise Manager[/bold cyan]",
            title_align="center",
            border_style="cyan",
            padding=(0, 1),
            expand=True,
            width=70
        )
    
    def _create_countdown_text(self, time_to_emergency: float) -> Text:
        """Create countdown text with appropriate styling"""
        if time_to_emergency <= 0:
            return Text("🚨 3:55 PM EMERGENCY CLOSE ACTIVE", style="red bold blink")
        elif time_to_emergency <= 5:
            minutes = int(time_to_emergency)
            seconds = int((time_to_emergency - minutes) * 60)
            return Text(f"⚠️  {minutes}:{seconds:02d} to 3:55 PM", style="yellow bold")
        else:
            minutes = int(time_to_emergency)
            return Text(f"⏰ {minutes} min to 3:55 PM", style="cyan")
    
    def create_mini_panel(self, cleanup_status: Optional[Dict]) -> Panel:
        """Create compact exercise status for limited space"""
        if not cleanup_status:
            return Panel(
                Text("Exercise: N/A", style="dim"),
                title="[cyan]Exercise[/cyan]",
                border_style="cyan",
                padding=(0, 1)
            )
        
        mode = cleanup_status.get('mode', 'unknown')
        positions = cleanup_status.get('positions_at_risk', [])
        critical_count = sum(1 for p in positions if p['risk_level'] == 'CRITICAL')
        
        # Create simple status text
        if critical_count > 0:
            status_text = Text(f"🔴 {critical_count} CRITICAL", style="red bold")
        elif positions:
            status_text = Text(f"⚠️  {len(positions)} at risk", style="yellow")
        else:
            status_text = Text("✅ All safe", style="green")
        
        content = Group(
            Text(f"Mode: {mode.upper()}", style="bold"),
            status_text
        )
        
        return Panel(
            content,
            title="[cyan]Exercise[/cyan]",
            border_style="cyan",
            padding=(0, 1)
        )