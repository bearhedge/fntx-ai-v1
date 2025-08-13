"""
Human Feedback Panel - Shows RLHF feedback interface
Displays last feedback and prompts for new entries
"""
from datetime import datetime, date
from typing import Dict, Optional, List
import pytz
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group
from rich.align import Align
import json
import os


class HumanFeedbackPanel:
    """Display and collect human feedback for RLHF training"""
    
    def __init__(self):
        self.eastern = pytz.timezone('US/Eastern')
        self.feedback_file = os.path.expanduser("~/.rlhf_feedback.json")
        self.today_count = 0
        self.last_feedback = None
        self._load_today_feedback()
        
    def create_panel(self, last_feedback: Optional[Dict] = None) -> Panel:
        """Create human feedback panel"""
        sections = []
        
        # Header with session info
        header_text = Text()
        header_text.append("Session: ", style="bold")
        header_text.append(f"#{self.today_count + 1}", style="cyan")
        header_text.append(" | ", style="dim")
        header_text.append("Saved: ", style="bold")
        header_text.append(f"{self.today_count} entries today", style="green")
        sections.append(header_text)
        
        sections.append(Text(""))  # Spacer
        
        # Display last feedback
        if self.last_feedback:
            time_str = self.last_feedback['timestamp'].strftime('%I:%M %p')
            
            # Combine all text into one prose paragraph
            feedback_text = Text()
            feedback_text.append(f"Last Feedback ({time_str}): ", style="bold dim")
            feedback_text.append(f'"{self.last_feedback["text"]}"', style="italic")
            sections.append(feedback_text)
        else:
            no_feedback = Text("No feedback today", style="dim italic")
            sections.append(Align.center(no_feedback))
        
        sections.append(Text(""))  # Spacer
        
        # Instructions
        instruction = Text()
        instruction.append("Press ", style="dim")
        instruction.append("'F'", style="bold cyan")
        instruction.append(" to add new feedback", style="dim")
        sections.append(Align.center(instruction))
        
        # Today's entry count
        if self.today_count > 0:
            count_text = Text(f"Today's entries: {self.today_count}", style="green")
            sections.append(Align.center(count_text))
        
        # Combine all sections
        content = Group(*sections)
        
        return Panel(
            content,
            title="[bold cyan]Human Feedback[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )
    
    def save_feedback(self, feedback_text: str, market_data: Dict, ai_action: int = None, 
                     ai_confidence: float = None) -> bool:
        """Save feedback to file and update state"""
        try:
            # Create feedback entry
            entry = {
                'id': self.today_count + 1,
                'timestamp': datetime.now(self.eastern).isoformat(),
                'date': date.today().isoformat(),
                'text': feedback_text.strip(),
                'ai_action': ai_action,
                'ai_confidence': ai_confidence,
                'spy_price': market_data.get('spy_price', 0),
                'vix_level': market_data.get('vix', 0),
                'char_count': len(feedback_text)
            }
            
            # Load existing feedback
            feedback_data = self._load_all_feedback()
            
            # Add new entry
            today_key = date.today().isoformat()
            if today_key not in feedback_data:
                feedback_data[today_key] = []
            
            feedback_data[today_key].append(entry)
            
            # Save to file
            with open(self.feedback_file, 'w') as f:
                json.dump(feedback_data, f, indent=2)
            
            # Update state
            self.last_feedback = {
                'text': feedback_text,
                'timestamp': datetime.now(self.eastern)
            }
            self.today_count += 1
            
            return True
            
        except Exception as e:
            print(f"Error saving feedback: {e}")
            return False
    
    def get_today_feedback(self) -> List[Dict]:
        """Get all feedback entries from today"""
        feedback_data = self._load_all_feedback()
        today_key = date.today().isoformat()
        return feedback_data.get(today_key, [])
    
    def _load_today_feedback(self):
        """Load today's feedback count and last entry"""
        feedback_data = self._load_all_feedback()
        today_key = date.today().isoformat()
        
        if today_key in feedback_data:
            today_entries = feedback_data[today_key]
            self.today_count = len(today_entries)
            
            if today_entries:
                last_entry = today_entries[-1]
                self.last_feedback = {
                    'text': last_entry['text'],
                    'timestamp': datetime.fromisoformat(last_entry['timestamp'])
                }
    
    def _load_all_feedback(self) -> Dict:
        """Load all feedback from file"""
        if os.path.exists(self.feedback_file):
            try:
                with open(self.feedback_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _wrap_text(self, text: str, width: int = 40) -> List[str]:
        """Simple text wrapping for display"""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > width:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)
            else:
                current_line.append(word)
                current_length += len(word) + 1
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines[:5]  # Limit to 5 lines
    
    def export_for_database(self) -> List[Dict]:
        """Export feedback in format ready for database insertion"""
        all_feedback = []
        feedback_data = self._load_all_feedback()
        
        for date_key, entries in feedback_data.items():
            for entry in entries:
                db_entry = {
                    'created_at': entry['timestamp'],
                    'session_date': entry['date'],
                    'feedback_text': entry['text'],
                    'ai_action': entry.get('ai_action'),
                    'ai_confidence': entry.get('ai_confidence'),
                    'spy_price': entry.get('spy_price'),
                    'vix_level': entry.get('vix_level'),
                    'character_count': entry.get('char_count', len(entry['text']))
                }
                all_feedback.append(db_entry)
        
        return all_feedback