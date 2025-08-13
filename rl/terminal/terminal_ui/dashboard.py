"""
Main terminal dashboard orchestrating all display panels
Updates every 3 seconds with live market data and AI decisions
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
import numpy as np
import pytz
import sys
import select
import termios
import tty
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich.prompt import Prompt

from .data_filters import OTMFilter
from .options_chain_panel import OptionsChainPanel
from .straddle_options_panel import StraddleOptionsPanel
from .feature_panel import FeaturePanel
from .reasoning_panel import ReasoningPanel
from .statistics_panel import StatisticsPanel
from .mandate_panel import MandatePanel
from .rlhf_panel import RLHFPanel
from .market_timer_panel import MarketTimerPanel
from .risk_manager_panel import RiskManagerPanel
from .human_feedback_panel import HumanFeedbackPanel

# Import RLHF feedback collector
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from rlhf.feedback_collector import FeedbackCollector

# Import stop loss enforcer - CRITICAL SAFETY MODULE
sys.path.append(str(Path(__file__).parent.parent))
from stop_loss_enforcer import StopLossEnforcer

# Import ALM NAV service for capital auto-refresh
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "backend" / "services"))
try:
    from alm_nav_service import get_latest_capital, get_nav_service
except ImportError:
    get_latest_capital = None
    get_nav_service = None
    logger.warning("ALM NAV service not available - capital auto-refresh disabled")


class TradingDashboard:
    """Main dashboard combining all UI panels"""
    
    def __init__(self, update_frequency: float = 3.0, capital: float = 80000):
        self.console = Console()
        self.update_frequency = update_frequency
        self.logger = logging.getLogger(__name__)
        self.capital = capital
        self.capital_source = "Default"  # Track where capital came from
        
        # Try to get capital from ALM database on startup
        self._refresh_capital_from_alm()
        
        # Initialize panels
        self.otm_filter = OTMFilter()
        self.options_panel = OptionsChainPanel(self.otm_filter)
        self.straddle_panel = StraddleOptionsPanel(num_strikes=12)  # Show 12 strikes
        self.feature_panel = FeaturePanel()
        self.reasoning_panel = ReasoningPanel()
        self.statistics_panel = StatisticsPanel()
        self.mandate_panel = MandatePanel()  # Shows active positions and risk
        self.rlhf_panel = RLHFPanel()  # Interactive feedback on decisions
        self.market_timer_panel = MarketTimerPanel()  # Market timing info
        self.risk_manager_panel = RiskManagerPanel()  # Risk management
        self.risk_manager_panel.set_market_timer(self.market_timer_panel)  # Connect to market timer
        self.human_feedback_panel = HumanFeedbackPanel()  # Human RLHF feedback
        # Try to connect mandate panel to database
        if self.mandate_panel.connect_database():
            self.logger.info("Mandate panel connected to database for position tracking")
        else:
            self.logger.warning("Mandate panel database connection failed")
        
        # State tracking
        self.is_running = False
        self.last_update = None
        self.update_count = 0
        self.last_capital_refresh = None  # Track when we last refreshed capital
        
        # Trading state
        self.current_position = None
        self.pending_suggestion = None
        self.stop_loss_violation = False  # Track stop loss violations
        self.ibkr_positions = {}  # Positions from IBKR FlexQuery
        self.ibkr_exercises = []  # Exercises from IBKR FlexQuery
        
        # RLHF feedback collector
        self.feedback_collector = FeedbackCollector()
        # Only connect to database if explicitly requested
        # self.feedback_collector.connect_database()
        self.current_feedback_id = None
        
        # CRITICAL: Stop loss enforcer for safety
        self.stop_loss_enforcer = StopLossEnforcer(stop_loss_multiple=3.5)
        self.logger.info("Stop Loss Enforcer initialized - 3.5x multiplier")
        
        # Track keyboard state
        self.feedback_mode = False
        self.original_terminal_settings = None
    
    def update_capital(self, capital: float, source: str = "Default"):
        """Update the displayed capital and its source"""
        self.capital = capital
        self.capital_source = source
        
    def _refresh_capital_from_alm(self) -> bool:
        """
        Refresh capital from ALM database if available and appropriate time
        
        Returns:
            True if capital was updated, False otherwise
        """
        if get_latest_capital is None:
            return False
            
        try:
            # Check if we should auto-refresh (after 12 PM HKT)
            nav_service = get_nav_service()
            if nav_service and nav_service.should_auto_refresh():
                # Get latest capital from ALM
                latest_capital = get_latest_capital()
                if latest_capital and latest_capital > 0:
                    self.update_capital(latest_capital, "ALM Database")
                    self.logger.info(f"Auto-refreshed capital from ALM: {latest_capital:,.2f} HKD")
                    return True
        except Exception as e:
            self.logger.error(f"Error refreshing capital from ALM: {e}")
            
        return False
    
    def set_ibkr_positions(self, positions: Dict[str, int]):
        """Set IBKR positions from FlexQuery (e.g., {'628C': -1, '626P': -1})"""
        self.ibkr_positions = positions
    
    def set_ibkr_exercises(self, exercises: List[Dict]):
        """Set IBKR exercises from FlexQuery"""
        self.ibkr_exercises = exercises
        
    def create_layout(self) -> Layout:
        """Create the main dashboard layout"""
        layout = Layout()
        
        # Define layout structure
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        # Split main area
        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        
        # Split left panel - Options chain on top, bottom area below
        layout["left"].split_column(
            Layout(name="options", ratio=3),
            Layout(name="bottom_left", ratio=1)
        )
        
        # Split bottom left into Active Positions (left) and Exercise Manager (right)
        layout["bottom_left"].split_row(
            Layout(name="positions", ratio=1),  # Active Positions (bottom left)
            Layout(name="cleanup", ratio=1)      # Exercise Manager (bottom right of left side)
        )
        
        # Right panel has 4 equal-height boxes
        layout["right"].split_column(
            Layout(name="decision", ratio=1),    # AI Trader/Action
            Layout(name="risk", ratio=1),        # Risk Manager
            Layout(name="timer", ratio=1),       # Market Timer
            Layout(name="feedback", ratio=1)     # Human Feedback
        )
        
        # Initialize ALL panels to prevent duplication issue
        layout["header"].update(Panel("Loading market data...", title="Market Status"))
        layout["options"].update(Panel("Loading options chain...", title="Options Chain"))
        layout["positions"].update(Panel("Loading positions...", title="Active Positions"))
        layout["cleanup"].update(Panel("Loading exercise manager...", title="Exercise Manager"))
        layout["footer"].update(Panel("Initializing controls...", title="Controls"))
        layout["decision"].update(Panel("Initializing...", title="AI Trader"))
        layout["timer"].update(Panel("Initializing...", title="Market Timer"))
        layout["risk"].update(Panel("Initializing...", title="Risk Manager"))
        layout["feedback"].update(Panel("Initializing...", title="Human Feedback"))
        
        return layout
    
    def update_display(self,
                      layout: Layout,
                      market_data: Dict,
                      features: np.ndarray,
                      feature_dict: Dict[str, float],
                      action: int,
                      action_probs: Optional[np.ndarray] = None,
                      constraints: Optional[Dict[str, bool]] = None) -> None:
        """Update all dashboard panels with new data"""
        
        # Update header
        layout["header"].update(self._create_header(market_data))
        
        # Update options chain (use straddle format)
        if market_data.get('options_chain'):
            # Use straddle panel for better display
            options_panel = self.straddle_panel.create_panel(
                market_data['options_chain'],
                market_data.get('spy_price', 0),
                market_data.get('spy_price_realtime', 0),
                market_data.get('vix', 0)
            )
            layout["options"].update(options_panel)
        
        # Get positions - check IBKR positions first, then database
        positions = None
        
        # First check if we have IBKR positions from FlexQuery
        if self.ibkr_positions:
            # Convert IBKR positions to display format
            position_list = []
            for symbol, quantity in self.ibkr_positions.items():
                # Parse symbol (e.g., '628C' -> strike=628, type='C')
                if len(symbol) >= 4:  # e.g., '628C' or '626P'
                    strike = symbol[:-1]
                    option_type = symbol[-1]
                    position_list.append({
                        'strike': int(strike),
                        'type': option_type,
                        'quantity': quantity,
                        'entry_price': 0,  # Not available from basic FlexQuery
                        'stop_loss': 0,    # Not available from basic FlexQuery
                    })
            
            if position_list:
                positions = {
                    'positions': position_list,
                    'summary': {
                        'total_pnl': 0,  # Would need current prices to calculate
                        'position_count': len(position_list)
                    },
                    'source': 'IBKR FlexQuery'
                }
        
        # If no IBKR positions, try database
        elif self.db_position_tracker and market_data.get('options_chain'):
            # Get positions from backend.data.database with P&L calculated from current prices
            try:
                position_summary = self.db_position_tracker.sync_tracker.get_position_summary(
                    market_data['options_chain']
                )
                if position_summary['total_positions'] > 0:
                    positions = {
                        'positions': position_summary['positions'],
                        'summary': {
                            'total_pnl': position_summary['total_pnl'],
                            'position_count': position_summary['total_positions']
                        },
                        'risk_metrics': {
                            'total_risk': sum(p['entry_price'] * 350 for p in position_summary['positions'])  # 3.5x stop loss
                        }
                    }
            except Exception as e:
                self.logger.error(f"Error getting database positions: {e}")
                
        elif self.position_manager:
            # Fallback to IB Gateway if available
            active_positions = self.position_manager.get_active_positions()
            if active_positions:
                positions = {
                    'positions': active_positions,
                    'summary': self.position_manager.get_position_summary(),
                    'risk_metrics': self.position_manager.get_risk_metrics()
                }
        # Remove the self.current_position fallback - it contains hardcoded test data
        # If no positions from IBKR or database, positions stays None
        
        # Update Active Positions panel
        if self.mandate_panel:
            positions_panel = self.mandate_panel.create_panel(
                positions=positions,
                pending_trade=self.pending_suggestion,
                violation_alert=self.stop_loss_violation,
                options_chain=market_data.get('options_chain', [])
            )
            layout["positions"].update(positions_panel)
        
        # Update Exercise Manager panel
        if hasattr(self, 'cleanup_manager') and self.cleanup_manager:
            # Import exercise manager panel
            from .exercise_manager_panel import ExerciseManagerPanel
            if not hasattr(self, 'exercise_panel'):
                self.exercise_panel = ExerciseManagerPanel()
            
            # Get cleanup status (still using same data source but renamed for clarity)
            exercise_status = self.cleanup_manager.get_cleanup_status()
            # Pass SPY price from market data
            exercise_status['spy_price'] = market_data.get('spy_price_realtime', 0) or market_data.get('spy_price', 0)
            exercise_status['threshold_dollars'] = exercise_status['spy_price'] * 0.0003 if exercise_status['spy_price'] > 0 else 0
            
            exercise_panel = self.exercise_panel.create_panel(exercise_status)
            layout["cleanup"].update(exercise_panel)
        else:
            layout["cleanup"].update(Panel("Exercise Manager Not Available", title="[cyan]Exercise Manager[/cyan]"))
        
        # Update right side panels - NEW PANELS
        # 1. Decision panel (keep existing)
        decision_panel = self._create_decision_panel(action, action_probs, features, constraints)
        layout["decision"].update(decision_panel)
        
        # 2. Risk Manager panel (NEW) - moved up from position 3
        if hasattr(self, 'risk_manager_panel'):
            risk_panel = self.risk_manager_panel.create_panel()
            layout["risk"].update(risk_panel)
        
        # 3. Market Timer panel (NEW) - moved down from position 2
        if hasattr(self, 'market_timer_panel'):
            timer_panel = self.market_timer_panel.create_panel(market_data)
            layout["timer"].update(timer_panel)
        
        # 4. Human Feedback panel (NEW)
        if hasattr(self, 'human_feedback_panel'):
            feedback_panel = self.human_feedback_panel.create_panel()
            layout["feedback"].update(feedback_panel)
        
        # Update footer
        layout["footer"].update(self._create_footer())
        
        # Track update
        self.last_update = datetime.now()
        self.update_count += 1
    
    def _create_header(self, market_data: Dict) -> Panel:
        """Create header with market status and timezone info"""
        # Get market status
        market_status = self._get_market_status()
        
        # Create header table
        table = Table(show_header=False, show_lines=False, 
                     box=None, expand=True)
        table.add_column("Status", justify="center")
        table.add_column("Market Info", justify="center")
        table.add_column("Time", justify="right")
        
        # Market open/closed status
        if market_status['is_open']:
            market_status_text = "[bold green]🟢 MARKET OPEN[/bold green]"
        else:
            market_status_text = f"[bold red]🔴 MARKET CLOSED[/bold red] (Opens in {market_status['hours_until']:.1f}h)"
        
        # Trading mode status
        if hasattr(self, 'trading_mode') and market_status['is_open']:
            # Use string comparison to avoid import
            if self.trading_mode.value == 'risk_management':
                # Get position count from position manager
                pos_count = len(self.position_manager.get_active_positions()) if self.position_manager else 1
                mode_text = f" | [bold red]🛡️ RISK MODE ({pos_count} pos)[/bold red]"
            elif self.trading_mode.value == 'closing':
                mode_text = " | [bold yellow]🔒 CLOSING[/bold yellow]"
            elif self.pending_suggestion:
                mode_text = " | [bold yellow]⏳ SUGGESTION[/bold yellow] | [magenta]RLHF[/magenta]"
            else:
                mode_text = " | [bold green]🔍 SEEKING[/bold green]"
        else:
            mode_text = ""
        
        status = market_status_text + mode_text
        
        # Market info with SPY and VIX (ALWAYS prefer Yahoo realtime)
        spy_price_theta = market_data.get('spy_price', 0)
        spy_price_yahoo = market_data.get('spy_price_realtime', 0)
        
        # CRITICAL: Use Yahoo price if available, it's the real-time price
        if spy_price_yahoo > 0:
            spy_price = spy_price_yahoo
            source = "Yahoo"
        else:
            spy_price = spy_price_theta
            source = "Theta"
            
        vix = market_data.get('vix', 0)
        
        # Debug logging
        self.logger.info(f"SPY prices - Theta: ${spy_price_theta:.2f}, Yahoo: ${spy_price_yahoo:.2f}, Using: ${spy_price:.2f} from {source}")
        
        if spy_price > 0:
            market_info = f"SPY: ${spy_price:.2f}"
            if vix > 0:
                market_info += f" | VIX: {vix:.1f}"
            # Add capital display
            capital_display = f"${self.capital:,.0f}"
            if self.capital_source != "Default":
                capital_display += f" ({self.capital_source})"
            market_info += f" | Capital: {capital_display}"
        else:
            market_info = "[dim]Loading...[/dim]"
        
        # Time display with both timezones
        time_info = f"{market_status['et_time']} | {market_status['hk_time']}"
        
        # Add next 5-min bar if market is open
        if market_status['is_open']:
            eastern = pytz.timezone('US/Eastern')
            eastern_time = datetime.now(eastern)
            current_minute = eastern_time.minute
            next_5min = ((current_minute // 5) + 1) * 5
            if next_5min >= 60:
                next_5min = 0
            mins_to_next = (next_5min - current_minute) % 60
            time_info += f" | Next: {mins_to_next}m"
        
        table.add_row(status, market_info, time_info)
        
        return Panel(
            table,
            title="[bold]SPY 0DTE Options Trading Terminal[/bold]",
            border_style="bright_blue",
            padding=(0, 1)
        )
    
    async def _collect_user_feedback(self, suggestion: Dict) -> str:
        """
        Collect detailed user feedback about a suggestion
        
        In a real implementation, this would:
        1. Display a feedback dialog box
        2. Allow user to type detailed feedback
        3. Categorize feedback (strike, timing, direction, risk, etc.)
        4. Return the feedback text
        
        Example feedback categories:
        - Strike selection (too close/far OTM)
        - Market direction concerns
        - Timing issues (too early/late in day)
        - Risk management (position too large/risky)
        - Volatility concerns (IV too high/low)
        - Technical analysis conflicts
        """
        # This would be implemented with Rich's input handling
        # or a separate input dialog
        
        # For now, return example feedback
        example_feedback = [
            "Strike too close to current price - prefer farther OTM",
            "Market showing bullish momentum - selling calls risky",
            "VIX too low for adequate premium collection",
            "Too late in day - gamma risk increasing",
            "Already have similar position - need diversification",
        ]
        
        import random
        return random.choice(example_feedback)
    
    def _create_footer(self) -> Panel:
        """Create footer with controls and stats"""
        # Create controls text
        controls = Table(show_header=False, show_lines=False, 
                        box=None, expand=True)
        controls.add_column("Controls", justify="left")
        controls.add_column("Stats", justify="right")
        
        # Controls - Added F for RLHF feedback
        control_text = (
            "[bold cyan]Controls:[/bold cyan] "
            "[green]Y[/green]=Accept  "
            "[red]N[/red]=Reject  "
            "[magenta]F[/magenta]=Add Feedback  "
            "[yellow]Q[/yellow]=Quit  "
            "[blue]P[/blue]=Pause"
        )
        
        # Stats including RLHF feedback
        feedback_summary = self.feedback_collector.get_session_summary()
        acceptance_rate = feedback_summary.get('acceptance_rate', 0)
        
        stats_text = (
            f"Cycles: {self.update_count} | "
            f"Rate: {self.update_frequency}s | "
            f"Accept: {acceptance_rate:.0%} | "
            f"[{'green' if self.is_running else 'red'}]"
            f"{'●' if self.is_running else '○'}"
            f"[/{'green' if self.is_running else 'red'}]"
        )
        
        controls.add_row(control_text, stats_text)
        
        return Panel(
            controls,
            border_style="dim",
            padding=(0, 2)
        )
    
    async def show_suggestion(self,
                            suggestion: Dict,
                            layout: Layout) -> Tuple[str, Optional[str]]:
        """
        Display trade suggestion and get user response with optional feedback
        
        Returns:
            Tuple of (response, feedback_text)
            response: 'y' for accept, 'n' for reject
            feedback_text: Optional detailed feedback if user provides it
        """
        self.pending_suggestion = suggestion
        
        # Create suggestion panel
        suggestion_panel = self._create_suggestion_panel(suggestion)
        
        # Temporarily replace reasoning panel
        layout["reasoning"].update(suggestion_panel)
        
        # In a real implementation, this would:
        # 1. Pause the Live display
        # 2. Get keyboard input from user (Y/N/F)
        # 3. If F pressed, show feedback dialog
        # 4. Resume Live display with results
        
        # Show suggestion with prompt
        print("\n" + "="*60)
        print("🤖 AI SUGGESTION")
        print("="*60)
        print(f"Action: SELL {suggestion['option_type']}")
        print(f"Strike: ${suggestion['strike']}")
        print(f"Premium: ${suggestion['premium']:.2f}")
        print(f"Confidence: {suggestion['confidence']:.1%}")
        print("="*60)
        print("Options:")
        print("  [Y] Accept trade")
        print("  [N] Reject trade") 
        print("  [F] Reject with feedback")
        print("="*60)
        
        # Get user input
        try:
            # Simple blocking input for now
            # In production, could use aioconsole or other async input methods
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: input("Your choice (Y/N/F): ").strip().upper()
            )
            
            self.pending_suggestion = None
            
            if response == 'Y':
                print("✅ Trade accepted!")
                return {
                    'accepted': True,
                    'response': 'y',
                    'feedback_text': None
                }
            elif response == 'F':
                # Get detailed feedback
                print("\n📝 Please provide feedback on why this suggestion was rejected:")
                print("(Examples: strike too far, wrong direction, timing, market conditions)")
                feedback = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: input("Feedback: ").strip()
                )
                print("✅ Feedback recorded. Thank you!")
                return {
                    'accepted': False,
                    'response': 'n',
                    'feedback_text': feedback if feedback else "User rejected with F key"
                }
            else:
                print("❌ Trade rejected")
                return {
                    'accepted': False,
                    'response': 'n',
                    'feedback_text': None
                }
                
        except Exception as e:
            self.logger.error(f"Error getting user input: {e}")
            self.pending_suggestion = None
            # Fallback to mock response if input fails
            mock_responses = [
                ("y", None),  # Accept
                ("n", "Too aggressive - market trending up"),  # Reject with feedback
                ("n", "Strike too close to current price"),  # Reject with feedback
                ("n", None),  # Reject without feedback
        ]
        
        # Return a mock response (would be actual user input)
        import random
        return random.choice(mock_responses)
    
    def _create_suggestion_panel(self, suggestion: Dict) -> Panel:
        """Create trade suggestion panel with detailed contract information"""
        # Create content
        content = Text()
        
        # Add title
        content.append("TRADE SUGGESTION\n\n", style="bold yellow")
        
        # Determine action and OTM details
        action = suggestion['action']
        spy_price = suggestion.get('spy_price', 0)
        strike = suggestion['strike']
        
        # Calculate OTM percentage
        if action == 1:  # Call
            otm_pct = ((strike - spy_price) / spy_price) * 100 if spy_price > 0 else 0
            content.append("SELL CALL", style="bold red")
            otm_desc = "out of the money" if otm_pct > 0 else "at the money"
        else:  # Put
            otm_pct = ((spy_price - strike) / spy_price) * 100 if spy_price > 0 else 0
            content.append("SELL PUT", style="bold green")
            otm_desc = "out of the money" if otm_pct > 0 else "at the money"
        
        # Add OTM description
        if abs(otm_pct) > 3:
            otm_desc = "far " + otm_desc
        content.append(f" ({abs(otm_pct):.1f}% {otm_desc})\n\n")
        
        # Contract specifics with Greeks
        content.append("Contract Details:\n", style="bold cyan")
        content.append(f"Strike Price: ${strike}\n")
        content.append(f"Premium: ${suggestion.get('mid_price', 0):.2f} (mid) | ")
        content.append(f"Bid: ${suggestion.get('bid', 0):.2f} | Ask: ${suggestion.get('ask', 0):.2f}\n")
        content.append(f"Position Size: {suggestion.get('position_size', 1)} contract\n\n")
        
        # Greeks section
        content.append("Greeks:\n", style="bold magenta")
        delta = suggestion.get('delta', 0)
        gamma = suggestion.get('gamma', 0)
        theta = suggestion.get('theta', 0)
        vega = suggestion.get('vega', 0)
        iv = suggestion.get('iv', 0)
        
        # Delta with interpretation
        content.append(f"Delta: {abs(delta):.2f} ", style="white")
        content.append(f"({int(abs(delta)*100)}-delta option)\n", style="dim")
        
        # Gamma with interpretation
        content.append(f"Gamma: {gamma:.3f} ", style="white")
        if abs(gamma) > 0.02:
            content.append("(high gamma risk)\n", style="yellow")
        else:
            content.append("(manageable gamma)\n", style="dim")
        
        # Theta with interpretation
        daily_theta = theta * 100  # Convert to dollar terms for 1 contract
        content.append(f"Theta: ${abs(daily_theta):.2f}/day ", style="green")
        content.append("(time decay income)\n", style="dim")
        
        # Vega with interpretation
        content.append(f"Vega: {vega:.2f} ", style="white")
        content.append(f"(${vega*100:.0f} per 1% IV move)\n", style="dim")
        
        # IV
        content.append(f"Implied Volatility: {iv*100:.1f}%\n\n", style="white")
        
        # Add statistical analysis
        if 'statistical_metrics' in suggestion:
            stats = suggestion['statistical_metrics']
            content.append("Statistical Analysis:\n", style="bold cyan")
            content.append(f"Probability of Touch: {stats['probability_of_touch']:.1%}\n", style="yellow")
            content.append(f"Win Probability: {stats['win_probability']:.1%}\n", style="green")
            content.append(f"Expected Value: ${stats['expected_value']:.2f}\n", style="bright_green")
            content.append(f"Risk/Reward: 1:{stats['risk_reward_ratio']:.1f}\n\n")
        
        # Add risk info with actual numbers and stop loss validation
        content.append("Position Details:\n", style="bold")
        premium = suggestion.get('premium', suggestion.get('mid_price', 0))
        premium_total = premium * 100  # 1 contract = 100 shares
        
        # Check if stop loss is included
        if 'stop_loss' in suggestion and suggestion['stop_loss'] > 0:
            stop_loss = suggestion['stop_loss']
            stop_loss_total = stop_loss * 100
            max_risk = (stop_loss - premium) * 100
            
            content.append(f"Premium Collected: ${premium_total:.0f}\n", style="green")
            content.append(f"Stop Loss @ ${stop_loss:.2f}: ${stop_loss_total:.0f} ", style="yellow")
            content.append(f"({stop_loss/premium:.1f}x)\n", style="dim")
            content.append(f"Max Risk: ${max_risk:.0f}\n", style="red")
            content.append("\n✅ Stop Loss Configured\n", style="bold green")
        else:
            # WARNING: No stop loss!
            stop_loss_required = premium * 3.5
            max_risk = (stop_loss_required - premium) * 100
            
            content.append(f"Premium Collected: ${premium_total:.0f}\n", style="green")
            content.append("⚠️  NO STOP LOSS SET!\n", style="bold red on yellow blink")
            content.append(f"Required Stop Loss (3.5x): ${stop_loss_required:.2f}\n", style="yellow")
            content.append(f"Potential Risk: ${max_risk:.0f}\n", style="red")
            content.append("\n❌ STOP LOSS WILL BE ADDED AUTOMATICALLY\n", style="bold yellow")
        
        # Add RLHF indicator
        content.append("\n[RLHF Active] ", style="bold magenta")
        content.append("Your feedback improves future recommendations\n\n", style="dim")
        
        # Add prompt with feedback option
        content.append("Accept this trade? (Y/N)\n", style="bold cyan")
        content.append("If rejecting, you can provide feedback to improve future suggestions\n", style="dim italic")
        content.append("Press F to provide detailed feedback after rejection\n", style="dim")
        
        return Panel(
            Align.center(content, vertical="middle"),
            title="[bold yellow]⚠️  ACTION REQUIRED ⚠️[/bold yellow]",
            border_style="yellow",
            padding=(2, 2)
        )
    
    def record_position(self, position: Dict) -> None:
        """Record active position"""
        self.current_position = position
    
    def close_position(self) -> None:
        """Mark position as closed"""
        self.current_position = None
    
    async def collect_feedback_modal(self, market_data: Dict, action: int = None, 
                                   action_probs: List[float] = None) -> bool:
        """Show modal dialog to collect RLHF feedback"""
        try:
            # Save the live display state
            self.feedback_mode = True
            
            # Clear the screen and show feedback prompt
            self.console.clear()
            self.console.print("\n" * 3)
            self.console.print("[bold cyan]═" * 60 + "[/bold cyan]")
            self.console.print("[bold cyan]HUMAN FEEDBACK COLLECTION[/bold cyan]", justify="center")
            self.console.print("[bold cyan]═" * 60 + "[/bold cyan]")
            self.console.print()
            
            # Show current market context
            spy_price = market_data.get('spy_price_realtime', 0) or market_data.get('spy_price', 0)
            vix = market_data.get('vix', 0)
            
            self.console.print(f"[cyan]Market Context:[/cyan]")
            self.console.print(f"  SPY: ${spy_price:.2f}")
            self.console.print(f"  VIX: {vix:.1f}")
            if action is not None:
                action_names = ["HOLD", "SELL CALL", "SELL PUT"]
                self.console.print(f"  AI Trader: {action_names[action]}")
            self.console.print()
            
            self.console.print("[yellow]Please provide your feedback (3-5 sentences):[/yellow]")
            self.console.print("[dim]Examples:[/dim]")
            self.console.print("[dim]- Market analysis or concerns[/dim]")
            self.console.print("[dim]- Trading strategy thoughts[/dim]")
            self.console.print("[dim]- Risk management observations[/dim]")
            self.console.print("[dim]- Disagreement with AI decisions[/dim]")
            self.console.print()
            
            # Get feedback using Rich prompt
            feedback_text = Prompt.ask("[magenta]Your feedback[/magenta]")
            
            if feedback_text and len(feedback_text.strip()) > 10:
                # Save the feedback
                success = self.human_feedback_panel.save_feedback(
                    feedback_text,
                    market_data,
                    ai_action=action,
                    ai_confidence=action_probs[action] if action_probs and action is not None else None
                )
                
                if success:
                    self.console.print("\n[green]✅ Feedback saved successfully![/green]")
                else:
                    self.console.print("\n[red]❌ Error saving feedback[/red]")
                
                await asyncio.sleep(1.5)
                return True
            else:
                self.console.print("\n[yellow]No feedback provided or too short[/yellow]")
                await asyncio.sleep(1)
                return False
                
        except Exception as e:
            self.logger.error(f"Error in feedback modal: {e}")
            return False
        finally:
            self.feedback_mode = False
            # Clear screen to return to dashboard
            self.console.clear()
    
    def check_keyboard_input(self) -> Optional[str]:
        """Non-blocking keyboard input check"""
        try:
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                return sys.stdin.read(1).lower()
            return None
        except:
            return None
    
    async def run(self,
                 data_connector,
                 feature_engine,
                 model,
                 smart_suggestion_engine,
                 rl_integration=None,
                 position_manager=None,
                 db_position_tracker=None,
                 cleanup_manager=None) -> None:
        """Run the dashboard with live updates"""
        self.is_running = True
        
        # Store position manager and database tracker references
        self.position_manager = position_manager
        self.db_position_tracker = db_position_tracker
        self.cleanup_manager = cleanup_manager
        
        # Set up position manager callbacks if available
        if self.position_manager:
            # Store reference to self for callbacks
            dashboard_ref = self
            
            def on_mode_change(mode):
                dashboard_ref.logger.info(f"Trading mode changed to: {mode.value}")
                dashboard_ref.trading_mode = mode
            
            def on_position_update(position):
                if position:
                    dashboard_ref.logger.info(f"Position updated: {position}")
                    # Manually record position for tracking
                    dashboard_ref.record_position(position)
                else:
                    dashboard_ref.logger.info("Position closed")
                    dashboard_ref.close_position()
            
            def on_risk_alert(alert):
                dashboard_ref.logger.warning(f"Risk alert: {alert}")
            
            self.position_manager.on_mode_change = on_mode_change
            self.position_manager.on_position_update = on_position_update
            self.position_manager.on_risk_alert = on_risk_alert
            
            # Set initial mode
            self.trading_mode = self.position_manager.mode
        else:
            # Create a mock enum-like object for trading mode
            class MockTradingMode:
                def __init__(self, value):
                    self.value = value
            self.trading_mode = MockTradingMode('recommendation')
        
        # Create layout
        layout = self.create_layout()
        
        # Create HTTP client for RL API if needed
        http_client = None
        if rl_integration:
            import httpx
            http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        
        # Use Rich Live display without screen buffer to prevent flashing
        # Use refresh_per_second based on update frequency (3 seconds = 0.33 refreshes per second)
        # Clear console once at start to ensure clean display
        self.console.clear()
        
        # Set terminal to non-blocking mode for keyboard input
        try:
            self.original_terminal_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        except:
            self.logger.warning("Could not set terminal to non-blocking mode")
        
        with Live(layout, console=self.console, 
                 auto_refresh=False, screen=True) as live:
            
            while self.is_running:
                try:
                    # Get market data
                    market_data = data_connector.get_current_snapshot()
                    self.logger.debug(f"Market data keys: {market_data.keys()}")
                    self.logger.debug(f"SPY price: {market_data.get('spy_price', 'MISSING')}")
                    self.logger.debug(f"SPY price realtime: {market_data.get('spy_price_realtime', 'MISSING')}")
                    self.logger.debug(f"Options chain length: {len(market_data.get('options_chain', []))}")
                    
                    # Log what we have
                    self.logger.info(f"Market data SPY price: {market_data.get('spy_price', 'MISSING')}, SPY realtime: {market_data.get('spy_price_realtime', 'MISSING')}")
                    
                    # Check for either price source
                    if not market_data.get('spy_price') and not market_data.get('spy_price_realtime'):
                        self.logger.warning("No SPY price in market data, skipping update")
                        await asyncio.sleep(0.5)
                        continue
                    
                    current_time = datetime.now()
                    spy_price = market_data.get('spy_price', 0) or market_data.get('spy_price_realtime', 0)
                    
                    # Auto-refresh capital from ALM database every 5 minutes after 12 PM HKT
                    if (self.last_capital_refresh is None or 
                        (current_time - self.last_capital_refresh) > timedelta(minutes=5)):
                        if self._refresh_capital_from_alm():
                            self.last_capital_refresh = current_time
                    
                    # Auto-close mechanism for exercise prevention (3:50-4:00 PM ET)
                    eastern = pytz.timezone('US/Eastern')
                    et_time = current_time.astimezone(eastern)
                    if et_time.hour == 15 and et_time.minute >= 50:  # 3:50 PM ET or later
                        # Check if we have positions that need auto-closing
                        if db_position_tracker and hasattr(db_position_tracker, 'sync_tracker'):
                            try:
                                positions = db_position_tracker.sync_tracker.get_open_positions()
                                for position in positions:
                                    strike = position.get('strike_price')
                                    option_type = position.get('option_type', '').lower()
                                    
                                    if strike and option_type in ['call', 'put']:
                                        # Calculate moneyness
                                        if option_type == 'call':
                                            moneyness = (spy_price - strike) / strike
                                        else:  # put
                                            moneyness = (strike - spy_price) / strike
                                        
                                        # Auto-close if too close to being ITM
                                        if abs(moneyness) < 0.005:  # Less than 0.5% from strike
                                            symbol = f"{strike}{option_type[0].upper()}"
                                            self.logger.warning(f"AUTO-CLOSE TRIGGERED: {symbol} moneyness={moneyness:.4f}")
                                            self.console.print(f"[bold red]🚨 AUTO-CLOSE: {symbol} at ${spy_price:.2f}, moneyness={moneyness:.4f}[/bold red]")
                                            
                                            # Log auto-close event for training
                                            if hasattr(self, 'feedback_collector'):
                                                self.feedback_collector.add_feedback({
                                                    'type': 'auto_close',
                                                    'time': current_time.isoformat(),
                                                    'symbol': symbol,
                                                    'strike': strike,
                                                    'spy_price': spy_price,
                                                    'moneyness': moneyness,
                                                    'features': features.tolist() if 'features' in locals() else []
                                                })
                                            
                                            # TODO: Implement actual close order via IBKR Web API
                                            # position_manager.close_position(position_id)
                            except Exception as e:
                                self.logger.error(f"Error checking positions for auto-close: {e}")
                    
                    # Update RL aggregator if enabled
                    if rl_integration:
                        # Feed tick data to aggregator
                        completed_bar = rl_integration.update_tick(spy_price, 1, current_time)
                        
                        # Check if we should get new RL prediction
                        if rl_integration.should_get_prediction(current_time) and http_client:
                            # Run RL API call in background
                            asyncio.create_task(
                                rl_integration.get_rl_prediction(market_data, current_time, http_client)
                            )
                    
                    # Get features
                    self.logger.debug("Calculating features...")
                    features = feature_engine.get_model_features(market_data)
                    feature_dict = feature_engine.features_to_dict(features)
                    self.logger.debug(f"Features calculated: {len(features)} values")
                    
                    # Determine action and probabilities
                    if rl_integration:
                        # Get RL prediction if available
                        rl_prediction = rl_integration.get_current_prediction(current_time)
                        if rl_prediction:
                            # Use RL model prediction
                            action = rl_prediction['action']
                            action_probs = rl_prediction.get('action_probabilities', [0.33, 0.33, 0.34])
                            self.logger.info(f"Using RL prediction: action={action}, probs={action_probs}")
                        else:
                            # No valid RL prediction, use local model or hold
                            action, _ = model.predict(features, deterministic=True)
                            action = int(action)
                            # For deterministic mode, create simple action probs based on action
                            action_probs = np.zeros(3)
                            action_probs[action] = 0.8  # High confidence for chosen action
                            action_probs[:] += 0.1  # Add baseline to all
                            action_probs /= action_probs.sum()  # Normalize
                    else:
                        # Use local model prediction
                        self.logger.debug("Using local model for prediction...")
                        action, _ = model.predict(features, deterministic=True)
                        action = int(action)
                        # For deterministic mode, create simple action probs based on action
                        action_probs = np.zeros(3)
                        action_probs[action] = 0.8  # High confidence for chosen action
                        action_probs[:] += 0.1  # Add baseline to all
                        action_probs /= action_probs.sum()  # Normalize
                        self.logger.debug(f"Model prediction: action={action}, probs={action_probs}")
                    
                    # Get constraints including RL status
                    constraints = smart_suggestion_engine.get_position_constraints()
                    constraints['wait_time_ok'] = smart_suggestion_engine.can_suggest_now()
                    constraints['market_hours_ok'] = self._is_market_hours()
                    
                    # Add RL status to constraints
                    if rl_integration:
                        rl_status = rl_integration.get_status(current_time)
                        constraints.update(rl_status)
                    
                    # Update display
                    self.logger.debug("Updating display panels...")
                    self.update_display(
                        layout,
                        market_data,
                        features,
                        feature_dict,
                        action,
                        action_probs,
                        constraints
                    )
                    self.logger.debug("Display updated successfully")
                    
                    # Manual refresh since auto_refresh is disabled
                    live.refresh()
                    
                    # Update market conditions in suggestion engine
                    if action_probs is not None:
                        model_confidence = float(action_probs[action])
                        smart_suggestion_engine.update_market_conditions(
                            market_data, action, model_confidence
                        )
                    
                    # Check for suggestion - only in recommendation mode
                    allow_suggestion = True
                    if self.position_manager:
                        allow_suggestion = self.position_manager.should_allow_new_recommendation()
                        constraints['position_allows'] = allow_suggestion
                        constraints['trading_mode'] = self.position_manager.mode.value
                    
                    # Check for data-driven suggestion triggers
                    should_override = False
                    if action_probs is not None:
                        should_override = smart_suggestion_engine.should_override_timing(
                            market_data, float(action_probs[action])
                        )
                    
                    # Log suggestion conditions
                    self.logger.info(f"Suggestion check: action={action}, wait_ok={constraints['wait_time_ok']}, "
                                   f"override={should_override}, market_ok={constraints['market_hours_ok']}, "
                                   f"allow={allow_suggestion}")
                    
                    if (action != 0 and 
                        (constraints['wait_time_ok'] or should_override) and
                        constraints['market_hours_ok'] and
                        allow_suggestion):
                        
                        self.logger.info(f"Preparing suggestion for action {action}")
                        
                        # Prepare suggestion
                        suggestion = smart_suggestion_engine.adjust_suggestion(
                            action, market_data
                        )
                        
                        self.logger.info(f"Suggestion result: {suggestion}")
                        
                        if suggestion:
                            # Use actual data from contract selector
                            # Position size is already set to 1 in contract selector
                            # Risk metrics are already calculated
                            suggestion['risk_score'] = features[6]
                            # Add SPY price for OTM calculation
                            suggestion['spy_price'] = spy_price
                            
                            # Store current suggestion for statistics panel
                            self.current_suggestion = suggestion
                            
                            # Store action probabilities for RLHF feedback
                            self.current_action_probs = action_probs.tolist() if hasattr(action_probs, 'tolist') else action_probs
                            
                            # Record suggestion in RLHF collector
                            self.current_feedback_id = self.feedback_collector.record_suggestion(
                                market_data,
                                {'action': action, 'confidence': model_confidence, 'action_probs': self.current_action_probs},
                                suggestion
                            )
                            
                            # Show suggestion and get response with optional feedback
                            response, feedback = await self.show_suggestion(suggestion, layout)
                            
                            # Process response
                            if response == 'y':
                                # CRITICAL: Validate stop loss before allowing trade
                                # Add stop loss to suggestion if not present
                                if 'stop_loss' not in suggestion or suggestion.get('stop_loss', 0) <= 0:
                                    premium = suggestion.get('premium', suggestion.get('mid_price', 0))
                                    suggestion['stop_loss'] = self.stop_loss_enforcer.calculate_stop_loss(premium)
                                    self.logger.warning(f"Added mandatory stop loss: ${suggestion['stop_loss']:.2f}")
                                
                                # Validate trade has proper stop loss
                                is_valid, validation_msg, validated_trade = self.stop_loss_enforcer.validate_trade(suggestion)
                                
                                if not is_valid:
                                    # STOP LOSS VIOLATION - BLOCK TRADE
                                    self.logger.error(f"STOP LOSS VIOLATION: {validation_msg}")
                                    self.stop_loss_violation = True
                                    
                                    # Update display to show violation
                                    self.update_display(
                                        layout,
                                        market_data,
                                        features,
                                        feature_dict,
                                        action,
                                        action_probs,
                                        constraints
                                    )
                                    
                                    # Don't execute trade - safety first!
                                    await asyncio.sleep(5)  # Show error for 5 seconds
                                    self.stop_loss_violation = False
                                    continue
                                
                                # Trade validated - proceed with execution
                                self.logger.info(f"Trade validated: {validation_msg}")
                                
                                # Record acceptance in RLHF
                                self.feedback_collector.record_user_response(
                                    self.current_feedback_id,
                                    'accepted'
                                )
                                
                                smart_suggestion_engine.process_acceptance(validated_trade)
                                self.record_position(validated_trade)
                                
                                # Record trade in database
                                if self.db_position_tracker:
                                    trade_details = {
                                        'strike': validated_trade['strike'],
                                        'right': 'P' if validated_trade['action'] == 2 else 'C',
                                        'position_size': validated_trade.get('position_size', 1),
                                        'entry_price': validated_trade.get('premium', validated_trade.get('mid_price', 0)),
                                        'stop_loss': validated_trade['stop_loss']  # Use validated stop loss
                                    }
                                    success = await self.db_position_tracker.record_trade(trade_details)
                                    if success:
                                        self.logger.info("Trade recorded in database")
                                    else:
                                        self.logger.warning("Failed to record trade in database")
                                
                                # Also notify position manager if available
                                if self.position_manager:
                                    trade_details = {
                                        'strike': validated_trade['strike'],
                                        'right': 'P' if validated_trade['action'] == 2 else 'C',
                                        'position_size': validated_trade.get('position_size', 1),
                                        'entry_price': validated_trade.get('premium', validated_trade.get('mid_price', 0)),
                                        'stop_loss': validated_trade['stop_loss']  # Use validated stop loss
                                    }
                                    self.position_manager.record_manual_trade(trade_details)
                            else:
                                # Use actual feedback if provided, otherwise generic rejection
                                feedback_reason = feedback if feedback else "User rejected - no specific reason provided"
                                
                                # Log feedback for debugging
                                if feedback:
                                    self.logger.info(f"User feedback: {feedback}")
                                
                                # Record rejection in RLHF with actual user feedback
                                self.feedback_collector.record_user_response(
                                    self.current_feedback_id,
                                    'rejected',
                                    feedback_reason
                                )
                                
                                # Process rejection with feedback to improve future suggestions
                                smart_suggestion_engine.process_rejection(
                                    suggestion, feedback_reason
                                )
                    
                    # Check for keyboard input (non-blocking)
                    key = self.check_keyboard_input()
                    if key:
                        if key == 'f' and not self.feedback_mode:
                            # Pause live display and collect feedback
                            live.stop()
                            await self.collect_feedback_modal(
                                market_data, 
                                action,
                                action_probs.tolist() if action_probs is not None else None
                            )
                            # Resume live display
                            live.start()
                            # Force refresh after returning from modal
                            self.update_display(
                                layout,
                                market_data,
                                features,
                                feature_dict,
                                action,
                                action_probs,
                                constraints
                            )
                            live.refresh()
                        elif key == 'q':
                            self.is_running = False
                            break
                        elif key == 'p':
                            # Toggle pause
                            self.console.print("\n[yellow]Dashboard paused. Press any key to resume...[/yellow]")
                            await asyncio.get_event_loop().run_in_executor(None, input)
                    
                    # Wait before next update
                    await asyncio.sleep(self.update_frequency)
                    
                except KeyboardInterrupt:
                    self.is_running = False
                    break
                except Exception as e:
                    error_msg = f"Update error: {str(e)}"
                    self.logger.error(error_msg)
                    
                    # Continue without showing error in UI
                    await asyncio.sleep(1)
        
        # Cleanup
        if http_client:
            await http_client.aclose()
        
        # Restore terminal settings
        if self.original_terminal_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_terminal_settings)
            except:
                pass
    
    def _is_market_hours(self) -> bool:
        """Check if US market is open (considering timezone)"""
        eastern = pytz.timezone('US/Eastern')
        now_et = datetime.now(eastern)
        
        # Check if weekend
        if now_et.weekday() > 4:  # Weekend
            return False
        
        # Market hours in Eastern Time
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= now_et <= market_close
    
    def _get_market_status(self) -> Dict[str, any]:
        """Get detailed market status including timezone info"""
        eastern = pytz.timezone('US/Eastern')
        hk = pytz.timezone('Asia/Hong_Kong')
        
        now_et = datetime.now(eastern)
        now_hk = datetime.now(hk)
        
        is_open = self._is_market_hours()
        
        # Calculate next market open
        if is_open:
            next_event = "Market Close"
            next_time = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        else:
            # Find next market open
            next_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
            if now_et >= now_et.replace(hour=16, minute=0):
                # After close, next open is tomorrow
                next_open += timedelta(days=1)
            while next_open.weekday() > 4:  # Skip weekends
                next_open += timedelta(days=1)
            next_event = "Market Open"
            next_time = next_open
            
        time_until = next_time - now_et
        hours_until = time_until.total_seconds() / 3600
        
        return {
            'is_open': is_open,
            'et_time': now_et.strftime('%I:%M %p ET'),
            'hk_time': now_hk.strftime('%I:%M %p HKT'),
            'next_event': next_event,
            'hours_until': hours_until,
            'next_time_et': next_time.strftime('%I:%M %p ET'),
            'status_text': 'OPEN' if is_open else 'CLOSED'
        }
    
    def _calculate_hours_to_close(self) -> float:
        """Calculate hours remaining until market close"""
        eastern = pytz.timezone('US/Eastern')
        now = datetime.now(eastern)
        
        # Market closes at 4 PM ET
        close_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        if now >= close_time:
            return 0.0
            
        time_remaining = close_time - now
        return time_remaining.total_seconds() / 3600
    
    def _create_decision_panel(self, action: int, action_probs: Optional[np.ndarray], 
                              features: np.ndarray, constraints: Dict) -> Panel:
        """Create AI decision display panel"""
        from rich.table import Table
        
        table = Table(show_header=False, show_lines=False, expand=True)
        table.add_column("Label", style="cyan", width=15)
        table.add_column("Value", justify="right")
        
        # Current action
        action_names = ["HOLD", "SELL CALL", "SELL PUT"]
        action_name = action_names[action]
        action_color = "yellow" if action == 0 else "red" if action == 1 else "green"
        table.add_row("Action:", f"[{action_color} bold]{action_name}[/{action_color} bold]")
        
        # Confidence
        if action_probs is not None:
            confidence = float(action_probs[action]) * 100
            conf_color = "green" if confidence > 70 else "yellow" if confidence > 50 else "red"
            table.add_row("Confidence:", f"[{conf_color}]{confidence:.0f}%[/{conf_color}]")
        
        # Risk score
        risk_score = features[6]
        risk_color = "green" if risk_score < 0.3 else "yellow" if risk_score < 0.6 else "red"
        table.add_row("Risk Score:", f"[{risk_color}]{risk_score:.2f}[/{risk_color}]")
        
        # Constraints
        if constraints.get('wait_time_ok'):
            table.add_row("Status:", "[green]Ready[/green]")
        else:
            table.add_row("Status:", "[yellow]Waiting[/yellow]")
        
        return Panel(
            table,
            title="[bold cyan]AI Trader[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )
    
    def _create_factors_panel(self, feature_dict: Dict, market_data: Dict) -> Panel:
        """Create key factors display panel"""
        from rich.table import Table
        
        table = Table(show_header=False, show_lines=False, expand=True)
        table.add_column("Factor", style="magenta", width=15)
        table.add_column("Value", justify="right")
        
        # Time progress
        time_progress = feature_dict.get('minutes_since_open', 0) / 390
        table.add_row("Day Progress:", f"{time_progress:.0%}")
        
        # ATM IV
        atm_iv = feature_dict.get('atm_iv', 0)
        table.add_row("ATM IV:", f"{atm_iv:.1%}")
        
        # Position status
        has_position = feature_dict.get('has_position', False)
        if has_position:
            table.add_row("Position:", "[green]Active[/green]")
            pnl = feature_dict.get('position_pnl', 0) * 1000
            pnl_color = "green" if pnl > 0 else "red"
            table.add_row("P&L:", f"[{pnl_color}]${pnl:+.0f}[/{pnl_color}]")
        else:
            table.add_row("Position:", "[dim]None[/dim]")
        
        # VIX if available
        vix = market_data.get('vix', 0)
        if vix > 0:
            vix_color = "green" if vix < 15 else "yellow" if vix < 20 else "red"
            table.add_row("VIX:", f"[{vix_color}]{vix:.1f}[/{vix_color}]")
        
        return Panel(
            table,
            title="[bold magenta]Key Factors[/bold magenta]",
            border_style="magenta",
            padding=(1, 2)
        )
    
    def _create_exercises_panel(self) -> Panel:
        """Create exercise monitor panel"""
        from rich.table import Table
        
        # Check for exercises from backend.data.database
        if hasattr(self, 'db_position_tracker') and self.db_position_tracker:
            try:
                exercises = self.db_position_tracker.sync_tracker.get_recent_exercises(days=1)
                
                if exercises:
                    table = Table(show_header=True, header_style="bold yellow", expand=True)
                    table.add_column("Option", width=8)
                    table.add_column("Status", width=10)
                    
                    pending_count = 0
                    for ex in exercises[:3]:  # Show last 3
                        option_str = f"{ex['strike_price']}{ex['option_type'][0]}"
                        status = ex['disposal_status']
                        
                        if status == 'PENDING':
                            status_str = Text("PENDING", style="red bold")
                            pending_count += 1
                        elif status == 'FILLED':
                            status_str = Text("FILLED", style="green")
                        else:
                            status_str = Text(status[:8], style="yellow")
                        
                        table.add_row(option_str, status_str)
                    
                    if pending_count > 0:
                        table.add_row("", "")
                        table.add_row("[red bold]ACTION[/red bold]", f"[red]{pending_count} pending[/red]")
                    
                    return Panel(
                        table,
                        title="[bold yellow]Exercise Monitor[/bold yellow]",
                        border_style="yellow" if pending_count == 0 else "red",
                        padding=(1, 2)
                    )
                    
            except Exception as e:
                self.logger.error(f"Error getting exercises: {e}")
        
        # Default empty state
        return Panel(
            Text("No exercises detected", style="dim"),
            title="[bold green]Exercise Monitor[/bold green]",
            border_style="green",
            padding=(1, 2)
        )