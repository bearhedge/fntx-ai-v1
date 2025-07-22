"""
RLHF Feedback Panel - Interactive feedback for AI decisions
Allows users to provide feedback on decision percentages (HOLD/SELL CALL/SELL PUT)
"""
from typing import Dict, Optional, List
from datetime import datetime
import pytz
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.console import Group
from rich import box


class RLHFPanel:
    """
    Interactive panel for providing feedback on AI decision probabilities
    Helps improve model through reinforcement learning from human feedback
    """
    
    def __init__(self):
        self.action_names = {
            0: ("HOLD", "white"),
            1: ("SELL CALL", "green"), 
            2: ("SELL PUT", "red")
        }
        self.eastern = pytz.timezone('US/Eastern')
        self.feedback_history = []
        self.pending_feedback = None
        
    def create_panel(self,
                    action: int,
                    action_probs: Optional[List[float]],
                    is_interactive: bool = False,
                    user_feedback: Optional[Dict] = None) -> Panel:
        """
        Create RLHF feedback panel
        
        Args:
            action: Current model action (0, 1, 2)
            action_probs: Probability distribution [hold, call, put]
            is_interactive: Whether to show interactive feedback options
            user_feedback: Previous feedback to display
            
        Returns:
            Rich Panel with RLHF interface
        """
        content_parts = []
        
        # Title section
        title_text = Text("RLHF - Help Improve Decisions", style="bold magenta")
        content_parts.append(Align.center(title_text))
        content_parts.append(Text(""))
        
        # Current decision display
        if action_probs:
            decision_table = Table(show_header=True, box=box.ROUNDED, expand=True)
            decision_table.add_column("Action", style="cyan", width=15)
            decision_table.add_column("Model %", justify="right", width=12)
            decision_table.add_column("Your View", justify="center", width=15)
            
            for idx, (name, color) in self.action_names.items():
                model_pct = action_probs[idx] * 100
                
                # Highlight the chosen action
                if idx == action:
                    row_style = f"bold {color}"
                    marker = "←"
                else:
                    row_style = color
                    marker = ""
                
                # Feedback options
                if is_interactive:
                    feedback_opts = "[↑] Higher [↓] Lower [✓] Good"
                else:
                    feedback_opts = "-"
                
                decision_table.add_row(
                    f"[{row_style}]{name} {marker}[/{row_style}]",
                    f"[{row_style}]{model_pct:.1f}%[/{row_style}]",
                    feedback_opts
                )
            
            content_parts.append(decision_table)
            content_parts.append(Text(""))
        
        # Feedback instructions
        if is_interactive:
            instructions = Table(show_header=False, box=None)
            instructions.add_column("Content")
            instructions.add_row(Text("Quick Feedback (Type letter + Enter):", style="bold yellow"))
            instructions.add_row("• Type 'A' + Enter to agree with percentages")
            instructions.add_row("• Type 'D' + Enter to suggest changes")
            instructions.add_row("• Type 'C' + Enter for detailed feedback")
            instructions.add_row("")
            instructions.add_row(Text("Specific Adjustments:", style="bold cyan"))
            instructions.add_row("• [1] ↑/↓ to adjust HOLD percentage")
            instructions.add_row("• [2] ↑/↓ to adjust SELL CALL percentage")
            instructions.add_row("• [3] ↑/↓ to adjust SELL PUT percentage")
            
            content_parts.append(Align.center(instructions))
        else:
            # Show recent feedback if available
            if self.feedback_history:
                recent_feedback = self._create_feedback_history()
                content_parts.append(recent_feedback)
            else:
                info_text = Text("Type 'F' + Enter during trade suggestions to provide feedback", 
                               style="dim italic")
                content_parts.append(Align.center(info_text))
        
        # Combine all parts
        content = Group(*content_parts)
        
        return Panel(
            content,
            title="[bold magenta]📝 RLHF Feedback[/bold magenta]",
            border_style="magenta",
            padding=(1, 1)
        )
    
    def create_feedback_dialog(self, 
                             action_probs: List[float],
                             current_action: int) -> Panel:
        """
        Create detailed feedback dialog for probability adjustments
        """
        content_parts = []
        
        # Header
        header = Text("Adjust Decision Probabilities", style="bold cyan")
        content_parts.append(Align.center(header))
        content_parts.append(Text(""))
        
        # Adjustment table
        adjust_table = Table(show_header=True, box=box.DOUBLE, expand=True)
        adjust_table.add_column("Action", style="cyan", width=15)
        adjust_table.add_column("Current", justify="right", width=10)
        adjust_table.add_column("Suggested", justify="right", width=10)
        adjust_table.add_column("Change", justify="center", width=10)
        
        # Allow user to modify probabilities
        suggested_probs = action_probs.copy()  # This would be modified by user input
        
        for idx, (name, color) in self.action_names.items():
            current_pct = action_probs[idx] * 100
            suggested_pct = suggested_probs[idx] * 100
            change = suggested_pct - current_pct
            
            change_str = f"{change:+.1f}%" if abs(change) > 0.1 else "-"
            change_color = "green" if change > 0 else "red" if change < 0 else "dim"
            
            adjust_table.add_row(
                f"[{color}]{name}[/{color}]",
                f"{current_pct:.1f}%",
                f"{suggested_pct:.1f}%",
                f"[{change_color}]{change_str}[/{change_color}]"
            )
        
        content_parts.append(adjust_table)
        content_parts.append(Text(""))
        
        # Reasoning input area
        reasoning_prompt = Text("Why do you think these percentages should be different?", 
                              style="yellow")
        content_parts.append(reasoning_prompt)
        content_parts.append(Text("[Type your reasoning...]", style="dim italic"))
        content_parts.append(Text(""))
        
        # Controls
        controls = Text("[Enter] Submit  [Esc] Cancel", style="bold")
        content_parts.append(Align.center(controls))
        
        content = Group(*content_parts)
        
        return Panel(
            content,
            title="[bold yellow]⚡ Probability Adjustment[/bold yellow]",
            border_style="yellow",
            padding=(2, 2)
        )
    
    def record_feedback(self,
                       action_probs: List[float],
                       user_agreement: bool,
                       suggested_probs: Optional[List[float]] = None,
                       reasoning: Optional[str] = None):
        """
        Record user feedback for later processing
        """
        feedback = {
            'timestamp': datetime.now(self.eastern),
            'model_probs': action_probs,
            'user_agreed': user_agreement,
            'suggested_probs': suggested_probs,
            'reasoning': reasoning
        }
        
        self.feedback_history.append(feedback)
        self.pending_feedback = feedback
        
        # Keep only recent history
        if len(self.feedback_history) > 10:
            self.feedback_history.pop(0)
    
    def _create_feedback_history(self) -> Panel:
        """
        Create display of recent feedback history
        """
        history_table = Table(show_header=True, box=box.SIMPLE, expand=True)
        history_table.add_column("Time", width=8)
        history_table.add_column("Feedback", width=20)
        history_table.add_column("Details", width=25)
        
        for feedback in self.feedback_history[-3:]:  # Last 3 feedbacks
            time_str = feedback['timestamp'].strftime("%H:%M")
            
            if feedback['user_agreed']:
                feedback_str = "[green]Agreed[/green]"
                details = "Model probs look good"
            else:
                feedback_str = "[yellow]Adjusted[/yellow]"
                if feedback['suggested_probs']:
                    # Show the biggest change
                    changes = []
                    for i, (orig, sugg) in enumerate(zip(feedback['model_probs'], 
                                                        feedback['suggested_probs'])):
                        diff = (sugg - orig) * 100
                        if abs(diff) > 5:  # Only show significant changes
                            action_name = self.action_names[i][0]
                            changes.append(f"{action_name} {diff:+.0f}%")
                    details = ", ".join(changes) if changes else "Minor adjustments"
                else:
                    details = feedback.get('reasoning', 'No details')[:25] + "..."
            
            history_table.add_row(time_str, feedback_str, details)
        
        return Panel(
            history_table,
            title="Recent Feedback",
            border_style="dim",
            padding=(0, 1)
        )
    
    def get_feedback_summary(self) -> Dict:
        """
        Get summary statistics of feedback session
        """
        total = len(self.feedback_history)
        agreed = sum(1 for f in self.feedback_history if f['user_agreed'])
        
        if total == 0:
            agreement_rate = 0
        else:
            agreement_rate = agreed / total
        
        return {
            'total_feedback': total,
            'agreements': agreed,
            'adjustments': total - agreed,
            'agreement_rate': agreement_rate,
            'has_pending': self.pending_feedback is not None
        }