"""
AI reasoning and decision transparency panel
Shows model predictions with explanations
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np
import pytz
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from rich.align import Align
from .rlhf_panel import RLHFPanel
from .exercise_panel import ExercisePanel
from .exercise_manager_panel import ExerciseManagerPanel


class ReasoningPanel:
    """Display AI model reasoning and decision process"""
    
    def __init__(self):
        self.action_names = {
            0: ("HOLD", "white"),
            1: ("SELL CALL", "green"), 
            2: ("SELL PUT", "red")
        }
        
        self.decision_history = []
        self.max_history = 10
        self.rlhf_panel = RLHFPanel()
        self.exercise_panel = ExercisePanel()
        self.exercise_manager_panel = ExerciseManagerPanel()
        self.cached_exercises = None
        self.exercises_cache_time = None
        self.cache_ttl = 300  # 5 minutes cache
        self.cleanup_manager = None
    
    def create_panel(self,
                    action: int,
                    action_probs: Optional[np.ndarray],
                    features: np.ndarray,
                    feature_dict: Dict[str, float],
                    constraints: Dict[str, bool],
                    current_suggestion: Optional[Dict] = None) -> Panel:
        """
        Create reasoning panel with AI decision explanation
        
        Args:
            action: Model's chosen action (0, 1, 2)
            action_probs: Probability distribution over actions
            features: Current feature vector
            feature_dict: Named features
            constraints: Trading constraints active
            
        Returns:
            Rich Panel object
        """
        # Record decision
        self._record_decision(action, action_probs, features)
        
        # Create content sections
        sections = []
        
        # Add RL API status section (show whenever RL integration is enabled)
        rl_enabled = constraints.get('rl_api_status') is not None
        if rl_enabled:
            sections.append(self._create_rl_status_section(constraints))
        
        # 1. Current Decision
        decision_section = self._create_decision_section(action, action_probs, features)
        sections.append(decision_section)
        
        # 2. RLHF Feedback Section (NEW - positioned after decision)
        if action_probs is not None:
            rlhf_section = self.rlhf_panel.create_panel(
                action=action,
                action_probs=action_probs.tolist() if hasattr(action_probs, 'tolist') else action_probs,
                is_interactive=False  # Set to True when user presses F
            )
            sections.append(rlhf_section)
        
        # 3. Reasoning Factors (moved down as requested)
        reasoning_section = self._create_reasoning_section(
            action, features, feature_dict, current_suggestion
        )
        sections.append(reasoning_section)
        
        # 4. Exercise Tracking (from IBKR FlexQuery)
        if hasattr(self, 'ibkr_exercises') and self.ibkr_exercises:
            exercise_section = self._create_ibkr_exercise_section(self.ibkr_exercises)
            sections.append(exercise_section)
        
        # 5. Cleanup Manager Status (replacing confidence analysis and history)
        if self.cleanup_manager:
            try:
                cleanup_status = self.cleanup_manager.get_cleanup_status()
                cleanup_section = self.exercise_manager_panel.create_panel(cleanup_status)
                sections.append(cleanup_section)
            except Exception as e:
                # If cleanup manager fails, show error message
                error_panel = Panel(
                    Text(f"Cleanup Manager Error: {str(e)}", style="red"),
                    title="[red]Cleanup Manager[/red]",
                    border_style="red",
                    padding=(0, 1)
                )
                sections.append(error_panel)
        else:
            # Show placeholder if cleanup manager not initialized
            placeholder_panel = Panel(
                Text("Cleanup Manager: Not initialized", style="dim"),
                title="[dim]Cleanup Manager[/dim]",
                border_style="dim",
                padding=(0, 1)
            )
            sections.append(placeholder_panel)
        
        # Combine all sections
        content = Group(*sections)
        
        return Panel(
            content,
            title="[bold cyan]AI Decision Reasoning[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )
    
    def create_mini_panel(self, 
                         action: int,
                         action_probs: Optional[np.ndarray]) -> Panel:
        """Create compact reasoning display"""
        action_name, color = self.action_names[action]
        
        # Create simple table
        table = Table(show_header=False, show_lines=False, expand=False)
        table.add_column("Label", width=12)
        table.add_column("Value", width=20)
        
        # Add decision
        table.add_row(
            "Decision:",
            f"[bold {color}]{action_name}[/bold {color}]"
        )
        
        # Add probabilities if available
        if action_probs is not None:
            for i, (name, _) in self.action_names.items():
                prob = action_probs[i]
                table.add_row(
                    f"{name}:",
                    f"{prob:.1%}"
                )
        
        return Panel(
            table,
            title="[cyan]AI Decision[/cyan]",
            border_style="cyan",
            padding=(0, 1)
        )
    
    def _create_decision_section(self, 
                                action: int,
                                action_probs: Optional[np.ndarray],
                                features: Optional[np.ndarray] = None) -> Panel:
        """Create decision display section"""
        # Dynamic action name for HOLD/WAIT
        if action == 0 and features is not None and len(features) > 3:
            has_position = features[3] > 0
            action_name = "HOLD" if has_position else "WAIT"
            color = "white"
        else:
            action_name, color = self.action_names[action]
        
        # Create decision text
        decision_text = Text()
        decision_text.append("Current Decision: ", style="bold")
        decision_text.append(action_name, style=f"bold {color}")
        
        # Add probability breakdown if available
        if action_probs is not None:
            prob_table = Table(show_header=False, show_lines=False, 
                             box=None, expand=False)
            prob_table.add_column("Action", width=15)
            prob_table.add_column("Probability", width=15)
            prob_table.add_column("Bar", width=20)
            
            for i, (name, col) in self.action_names.items():
                # Dynamic name for action 0
                if i == 0 and features is not None and len(features) > 3:
                    has_position = features[3] > 0
                    display_name = "HOLD" if has_position else "WAIT"
                else:
                    display_name = name
                    
                prob = action_probs[i]
                bar = self._create_prob_bar(prob, is_selected=(i == action))
                
                style = f"bold {col}" if i == action else col
                prob_table.add_row(
                    f"[{style}]{display_name}[/{style}]",
                    f"{prob:.1%}",
                    bar
                )
            
            content = Group(
                Align.center(decision_text),
                Text(""),
                prob_table
            )
        else:
            content = Align.center(decision_text)
        
        return Panel(
            content,
            title="Decision",
            border_style="bright_blue",
            padding=(0, 1)
        )
    
    def _create_reasoning_section(self,
                                 action: int,
                                 features: np.ndarray,
                                 feature_dict: Dict[str, float],
                                 current_suggestion: Optional[Dict] = None) -> Panel:
        """Create reasoning explanation section"""
        reasons = self._generate_reasoning(action, features, feature_dict, current_suggestion)
        
        # Create reasoning list
        reasoning_text = Text()
        for i, reason in enumerate(reasons, 1):
            reasoning_text.append(f"{i}. ", style="cyan")
            reasoning_text.append(reason + "\n")
        
        return Panel(
            reasoning_text,
            title="Key Factors",
            border_style="yellow",
            padding=(0, 1)
        )
    
    def _create_constraints_section(self, constraints: Dict[str, bool]) -> Panel:
        """Create constraints check section"""
        table = Table(show_header=False, show_lines=False, expand=False)
        table.add_column("Constraint", width=25)
        table.add_column("Status", width=10)
        
        constraint_checks = [
            ("Can sell calls", constraints.get('can_sell_call', True)),
            ("Can sell puts", constraints.get('can_sell_put', True)),
            ("Within position limits", not constraints.get('has_any_position', False)),
            ("Sufficient wait time", constraints.get('wait_time_ok', True)),
            ("Market hours OK", constraints.get('market_hours_ok', True))
        ]
        
        for constraint, status in constraint_checks:
            status_text = "[green]✓ OK[/green]" if status else "[red]✗ Blocked[/red]"
            table.add_row(constraint, status_text)
        
        return Panel(
            table,
            title="Trading Constraints",
            border_style="magenta",
            padding=(0, 1)
        )
    
    def _create_confidence_section(self,
                                  action: int,
                                  action_probs: Optional[np.ndarray],
                                  features: np.ndarray) -> Panel:
        """Create confidence analysis section"""
        # Calculate confidence metrics
        confidence_score = self._calculate_confidence(action, action_probs, features)
        confidence_level = self._get_confidence_level(confidence_score)
        
        # Create display
        table = Table(show_header=False, show_lines=False, expand=False)
        table.add_column("Metric", width=20)
        table.add_column("Value", width=25)
        
        # Add confidence score
        conf_color = "green" if confidence_score > 0.7 else "yellow" if confidence_score > 0.5 else "red"
        table.add_row(
            "Confidence Score:",
            f"[{conf_color}]{confidence_score:.1%}[/{conf_color}]"
        )
        
        # Add confidence level
        table.add_row(
            "Confidence Level:",
            confidence_level
        )
        
        # Add risk assessment
        risk_score = features[6]
        risk_text = "[green]Low[/green]" if risk_score < 0.3 else "[yellow]Medium[/yellow]" if risk_score < 0.6 else "[red]High[/red]"
        table.add_row(
            "Risk Assessment:",
            risk_text
        )
        
        return Panel(
            table,
            title="Confidence Analysis",
            border_style="bright_green",
            padding=(0, 1)
        )
    
    def _create_history_section(self) -> Panel:
        """Create recent decision history"""
        if not self.decision_history:
            return Panel(
                "[dim]No recent decisions[/dim]",
                title="Recent History",
                border_style="dim",
                padding=(0, 1)
            )
        
        table = Table(show_header=True, header_style="dim", 
                     show_lines=False, expand=False)
        table.add_column("Time", width=8)
        table.add_column("Decision", width=12)
        table.add_column("Probability", width=10)
        
        for entry in self.decision_history[-5:]:  # Last 5 decisions
            eastern = pytz.timezone('US/Eastern')
            time_str = entry['time'].astimezone(eastern).strftime('%H:%M:%S')
            action_name, color = self.action_names[entry['action']]
            conf = entry['confidence']
            
            # Show as probability rather than vague confidence
            prob_text = f"{conf:.0%}"
            prob_color = "green" if conf > 0.7 else "yellow" if conf > 0.5 else "dim"
            
            table.add_row(
                time_str,
                f"[{color}]{action_name}[/{color}]",
                f"[{prob_color}]{prob_text}[/{prob_color}]"
            )
        
        return Panel(
            table,
            title="Recent History",
            border_style="dim",
            padding=(0, 1)
        )
    
    def _generate_reasoning(self, 
                          action: int,
                          features: np.ndarray,
                          feature_dict: Dict[str, float],
                          current_suggestion: Optional[Dict] = None) -> List[str]:
        """Generate human-readable reasoning for decision"""
        reasons = []
        
        # Get actual market data from feature_dict
        vix = feature_dict.get('vix', 0)
        spy_price = feature_dict.get('spy_price', 0)
        
        # Time-based reasoning with Eastern timezone
        eastern = pytz.timezone('US/Eastern')
        current_time = datetime.now(eastern)
        hour = current_time.hour
        minute = current_time.minute
        
        # Calculate time since market open
        market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        time_since_open = (current_time - market_open).total_seconds() / 60
        
        if time_since_open < 30:
            reasons.append(f"[yellow]Initial 30-min wait period[/yellow] ({30 - time_since_open:.0f} min remaining)")
            reasons.append("Gathering market data for informed decisions")
        elif time_since_open < 60:
            reasons.append(f"Early session ({hour}:{minute:02d} ET) - Can trade but being selective")
        elif hour < 10:
            reasons.append(f"Early session ({hour}:{minute:02d} ET) - Higher volatility expected")
        elif hour >= 15 and minute >= 30:
            reasons.append(f"Late session ({hour}:{minute:02d} ET) - Gamma risk increasing")
        elif 11 <= hour <= 14:
            reasons.append(f"Midday ({hour}:{minute:02d} ET) - Typically lower volatility")
        
        # VIX-based reasoning with actual value
        if vix > 0:
            if vix < 12:
                reasons.append(f"VIX at {vix:.1f} (Very Low) - Limited premium available")
            elif vix < 15:
                reasons.append(f"VIX at {vix:.1f} (Low) - Below average volatility")
            elif vix < 20:
                reasons.append(f"VIX at {vix:.1f} (Normal) - Standard premium levels")
            elif vix < 25:
                reasons.append(f"VIX at {vix:.1f} (Elevated) - Good premium selling environment")
            else:
                reasons.append(f"VIX at {vix:.1f} (High) - Excellent premiums but higher risk")
        
        # SPY price momentum - removed misleading calculation
        # features[1] is normalized price, not price change
        # TODO: Calculate actual price change from market data if needed
        
        # Position and risk management
        if features[3] > 0:  # Has position
            reasons.append("Already have position - risk management priority")
        
        # Action-specific reasoning with context
        if action == 0:
            # Check if we have a position
            has_position = features[3] > 0 if len(features) > 3 else False
            action_word = "HOLD" if has_position else "WAIT"
            
            # More detailed reasoning
            if has_position:
                reasons.append(f"{action_word} - Managing existing position")
            elif vix < 12:
                reasons.append(f"{action_word} - Premiums too low for acceptable risk/reward")
            elif hour < 10:
                reasons.append(f"{action_word} - Initial volatility settling")
            elif features[6] > 0.5:  # High risk score
                reasons.append(f"{action_word} - Risk indicators elevated, protecting capital")
            else:
                reasons.append(f"{action_word} - No statistical edge at current option prices")
                
            # Add what we're looking for
            reasons.append("Monitoring for: Premium expansion or directional clarity")
        elif action == 1:
            if spy_price > 0:
                reasons.append(f"SELL CALL - SPY at ${spy_price:.2f}, upside resistance expected")
            else:
                reasons.append("SELL CALL - Bearish/neutral bias from model")
            
            # Add specific contract details if available
            if current_suggestion and current_suggestion.get('strike'):
                strike = current_suggestion['strike']
                delta = abs(current_suggestion.get('delta', 0))
                theta = current_suggestion.get('theta', 0)
                otm_pct = ((strike - spy_price) / spy_price * 100) if spy_price > 0 else 0
                
                reasons.append(f"Target: ${strike} strike ({abs(otm_pct):.1f}% OTM, {int(delta*100)}-delta)")
                if theta:
                    reasons.append(f"Theta decay: ${abs(theta*100):.2f}/day on 1 contract")
                    
        elif action == 2:
            if spy_price > 0:
                reasons.append(f"SELL PUT - SPY at ${spy_price:.2f}, downside support expected")
            else:
                reasons.append("SELL PUT - Bullish/neutral bias from model")
            
            # Add specific contract details if available
            if current_suggestion and current_suggestion.get('strike'):
                strike = current_suggestion['strike']
                delta = abs(current_suggestion.get('delta', 0))
                theta = current_suggestion.get('theta', 0)
                otm_pct = ((spy_price - strike) / spy_price * 100) if spy_price > 0 else 0
                
                reasons.append(f"Target: ${strike} strike ({abs(otm_pct):.1f}% OTM, {int(delta*100)}-delta)")
                if theta:
                    reasons.append(f"Theta decay: ${abs(theta*100):.2f}/day on 1 contract")
        
        return reasons[:4]  # Limit to top 4 reasons
    
    def _calculate_confidence(self,
                            action: int,
                            action_probs: Optional[np.ndarray],
                            features: np.ndarray) -> float:
        """Calculate confidence score for decision"""
        if action_probs is None:
            return 0.5
        
        # Base confidence from probability
        base_conf = action_probs[action]
        
        # Adjust for feature conditions
        risk_penalty = features[6] * 0.2  # High risk reduces confidence
        time_bonus = 0.1 if 0.15 < features[0] < 0.85 else 0  # Mid-day bonus
        
        confidence = base_conf - risk_penalty + time_bonus
        return np.clip(confidence, 0, 1)
    
    def _get_confidence_level(self, score: float) -> str:
        """Convert confidence score to text level"""
        if score >= 0.8:
            return "[bright_green]Very High[/bright_green]"
        elif score >= 0.6:
            return "[green]High[/green]"
        elif score >= 0.4:
            return "[yellow]Moderate[/yellow]"
        elif score >= 0.2:
            return "[orange1]Low[/orange1]"
        else:
            return "[red]Very Low[/red]"
    
    def _create_prob_bar(self, prob: float, is_selected: bool = False) -> str:
        """Create probability bar visualization"""
        bar_width = 15
        filled = int(prob * bar_width)
        empty = bar_width - filled
        
        if is_selected:
            bar = f"[bright_green]{'█' * filled}[/bright_green]"
        else:
            bar = f"[dim cyan]{'█' * filled}[/dim cyan]"
        
        bar += f"[dim]{'░' * empty}[/dim]"
        
        return bar
    
    def _record_decision(self, 
                       action: int,
                       action_probs: Optional[np.ndarray],
                       features: np.ndarray):
        """Record decision for history"""
        confidence = self._calculate_confidence(action, action_probs, features)
        
        self.decision_history.append({
            'time': datetime.now(),
            'action': action,
            'confidence': confidence,
            'features': features.copy()
        })
        
        # Keep only recent history
        if len(self.decision_history) > self.max_history:
            self.decision_history.pop(0)
    
    def _create_rl_status_section(self, constraints: Dict) -> Panel:
        """Create RL API status section"""
        table = Table(show_header=False, show_lines=False, expand=False)
        table.add_column("Item", width=20)
        table.add_column("Value", width=25)
        
        # RL API Status
        status = constraints.get('rl_api_status', 'unknown')
        if status == 'active':
            status_text = "[green]🤖 Active[/green]"
        elif status == 'updating':
            status_text = "[yellow]🔄 Updating...[/yellow]"
        elif status == 'waiting':
            status_text = "[dim]⏳ Waiting for data[/dim]"
        else:
            status_text = "[red]❌ Error[/red]"
            
        table.add_row(
            "RL API Status:",
            status_text
        )
        
        # Show different info based on status
        if status == 'active':
            # Confidence from RL model
            confidence = constraints.get('rl_confidence', 0)
            conf_color = "green" if confidence > 0.7 else "yellow" if confidence > 0.5 else "red"
            table.add_row(
                "RL Confidence:",
                f"[{conf_color}]{confidence:.1%}[/{conf_color}]"
            )
        
        return Panel(
            table,
            title="🤖 RL API Status",
            border_style="cyan",
            padding=(0, 1)
        )
    
    def set_db_position_tracker(self, db_position_tracker):
        """Set the database position tracker for exercise queries"""
        self._db_position_tracker = db_position_tracker
    
    def set_ibkr_exercises(self, exercises: List[Dict]):
        """Set IBKR exercises from FlexQuery"""
        self.ibkr_exercises = exercises
    
    def set_cleanup_manager(self, cleanup_manager):
        """Set the cleanup manager instance for status display"""
        self.cleanup_manager = cleanup_manager
    
    def _get_cached_exercises(self):
        """Get exercises with caching to avoid frequent DB queries"""
        import time
        current_time = time.time()
        
        # Check if cache is valid
        if (self.cached_exercises is not None and 
            self.exercises_cache_time is not None and
            current_time - self.exercises_cache_time < self.cache_ttl):
            return self.cached_exercises
        
        # Query database for new data
        if hasattr(self, '_db_position_tracker') and self._db_position_tracker:
            try:
                exercises = self._db_position_tracker.sync_tracker.get_recent_exercises(days=7)
                self.cached_exercises = exercises
                self.exercises_cache_time = current_time
                return exercises
            except Exception as e:
                # Return cached data on error
                return self.cached_exercises
        
        return None
    
    def _create_exercise_section(self, exercises: List[Dict]) -> Panel:
        """Create compact exercise tracking section"""
        if not exercises:
            return Panel(
                Text("No recent exercises", style="dim"),
                title="Exercise Tracking",
                border_style="yellow",
                padding=(0, 1)
            )
        
        # Create compact table
        table = Table(show_header=True, header_style="bold yellow", 
                     show_lines=False, expand=False)
        table.add_column("Date", width=10)
        table.add_column("Option", width=10)
        table.add_column("Status", width=12)
        table.add_column("Impact", width=10)
        
        # Show only last 3 exercises to save space
        for ex in exercises[:3]:
            # Format date
            exercise_date = ex['exercise_date']
            if isinstance(exercise_date, str):
                date_str = exercise_date[5:10]  # MM-DD
            else:
                date_str = exercise_date.strftime('%m-%d')
            
            # Format option
            option_str = f"{ex['strike_price']}{ex['option_type'][0]}"
            
            # Format status with color
            status = ex['disposal_status']
            if status == 'PENDING':
                status_str = Text("PENDING", style="red bold")
            elif status == 'ORDER_PLACED':
                status_str = Text("ORDER", style="yellow")
            elif status == 'FILLED':
                status_str = Text("FILLED", style="green")
            else:
                status_str = Text(status[:6], style="dim")
            
            # Format impact
            impact = ex.get('balance_impact', 0)
            impact_str = f"-${abs(impact):,.0f}" if impact < 0 else f"${impact:,.0f}"
            
            table.add_row(date_str, option_str, status_str, impact_str)
        
        # Add summary if pending
        pending_count = sum(1 for ex in exercises if ex['disposal_status'] in ['PENDING', 'ORDER_PLACED'])
        if pending_count > 0:
            table.add_row("", "", "", "")
            table.add_row("", "[yellow bold]Action Required[/yellow bold]", 
                         f"[yellow]{pending_count} pending[/yellow]", "")
        
        return Panel(
            table,
            title="[bold yellow]Exercise Tracking[/bold yellow]",
            border_style="yellow",
            padding=(0, 1)
        )
    
    def _create_ibkr_exercise_section(self, exercises: List[Dict]) -> Panel:
        """Create exercise section from IBKR FlexQuery data"""
        if not exercises:
            return Panel(
                Text("No exercises found in IBKR FlexQuery", style="dim"),
                title="Exercise Status",
                border_style="green",
                padding=(0, 1)
            )
        
        # Create table for exercises
        table = Table(show_header=True, header_style="bold yellow", 
                     show_lines=False, expand=False)
        table.add_column("Option", width=10)
        table.add_column("Date", width=10)
        table.add_column("Type", width=12)
        table.add_column("Status", width=15)
        
        has_pending = False
        has_exercise = False
        
        for ex in exercises:
            symbol = ex['symbol']
            date = ex['date']
            ex_type = ex['type']
            
            if ex_type == 'Pending':
                status_str = Text("⚠️ PENDING", style="red bold blink")
                has_pending = True
            elif ex_type in ['Exercise', 'Assignment']:
                status_str = Text("✅ EXERCISED", style="green bold")
                has_exercise = True
            else:
                status_str = Text(ex_type, style="yellow")
            
            table.add_row(symbol, date, ex_type, status_str)
        
        # Add summary
        if has_pending:
            table.add_row("", "", "", "")
            table.add_row("", "[red bold]ACTION REQUIRED[/red bold]", 
                         "", "[red]Check IBKR![/red]")
        
        border_style = "red" if has_pending else "green" if has_exercise else "yellow"
        title = "🚨 Exercise Alert" if has_pending or has_exercise else "Exercise Status"
        
        return Panel(
            table,
            title=f"[bold {border_style}]{title}[/bold {border_style}]",
            border_style=border_style,
            padding=(0, 1)
        )