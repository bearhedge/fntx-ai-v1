"""
Feature engineering display panel
Shows real-time calculation of 8 model features
"""
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.columns import Columns
from rich.text import Text


class FeaturePanel:
    """Display real-time feature calculations with explanations"""
    
    def __init__(self):
        self.feature_names = [
            "Time Since Open",
            "SPY Price", 
            "ATM IV",
            "Has Position",
            "Position P&L",
            "Time in Position",
            "Risk Score",
            "Time Until Close"
        ]
        
        self.feature_descriptions = [
            "Minutes since 9:30 AM / 390",
            "Current SPY price / 1000",
            "At-the-money implied volatility",
            "1 if position open, 0 if flat",
            "Current P&L / 1000 (if position)",
            "Minutes in position / 390",
            "Composite risk (0=low, 1=high)",
            "Minutes until 4:00 PM / 390"
        ]
    
    def create_panel(self, 
                    features: np.ndarray,
                    feature_dict: Dict[str, float],
                    market_data: Dict) -> Panel:
        """
        Create feature display panel
        
        Args:
            features: Raw 8-feature numpy array
            feature_dict: Named feature dictionary
            market_data: Current market snapshot
            
        Returns:
            Rich Panel object
        """
        # Create main table
        table = Table(show_header=True, header_style="bold magenta",
                     show_lines=True, expand=False)
        
        table.add_column("Feature", style="cyan", width=20)
        table.add_column("Raw Value", justify="right", width=12)
        table.add_column("Normalized", justify="right", width=12)
        table.add_column("Description", style="dim", width=35)
        
        # Add each feature
        for i, (name, desc) in enumerate(zip(self.feature_names, self.feature_descriptions)):
            raw_val = self._get_raw_value(i, feature_dict, market_data)
            norm_val = features[i]
            
            # Color code normalized values
            norm_style = self._get_value_style(norm_val)
            
            table.add_row(
                name,
                f"{raw_val}",
                f"[{norm_style}]{norm_val:.4f}[/{norm_style}]",
                desc
            )
        
        # Add visual indicators
        indicators = self._create_indicators(features, feature_dict)
        
        # Combine table and indicators
        content = Columns([table, indicators], padding=2, expand=False)
        
        return Panel(
            content,
            title="[bold magenta]Feature Engineering[/bold magenta]",
            border_style="magenta",
            padding=(1, 2)
        )
    
    def create_mini_panel(self, features: np.ndarray) -> Panel:
        """Create compact feature display"""
        table = Table(show_header=False, show_lines=False, expand=False)
        table.add_column("Feature", width=15)
        table.add_column("Value", width=8)
        
        # Show key features only
        key_features = [
            ("Time Progress", features[0]),
            ("SPY Normalized", features[1]),
            ("ATM IV", features[2]),
            ("Risk Score", features[6])
        ]
        
        for name, value in key_features:
            style = self._get_value_style(value)
            table.add_row(name, f"[{style}]{value:.3f}[/{style}]")
        
        return Panel(
            table,
            title="[magenta]Key Features[/magenta]",
            border_style="magenta",
            padding=(0, 1)
        )
    
    def _get_raw_value(self, idx: int, feature_dict: Dict, market_data: Dict) -> str:
        """Get human-readable raw value"""
        if idx == 0:  # Time since open
            minutes = feature_dict.get('minutes_since_open', 0)
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}h {mins}m"
        
        elif idx == 1:  # SPY price
            return f"${market_data.get('spy_price', 0):.2f}"
        
        elif idx == 2:  # ATM IV
            return f"{feature_dict.get('atm_iv', 0):.1%}"
        
        elif idx == 3:  # Has position
            return "Yes" if feature_dict.get('has_position', 0) else "No"
        
        elif idx == 4:  # Position P&L
            pnl = feature_dict.get('position_pnl', 0) * 1000
            if pnl == 0:
                return "N/A"
            color = "green" if pnl > 0 else "red"
            return f"[{color}]${pnl:+.0f}[/{color}]"
        
        elif idx == 5:  # Time in position
            minutes = feature_dict.get('time_in_position', 0)
            if minutes == 0:
                return "N/A"
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}h {mins}m"
        
        elif idx == 6:  # Risk score
            risk = feature_dict.get('risk_score', 0)
            if risk < 0.3:
                return "[green]Low[/green]"
            elif risk < 0.6:
                return "[yellow]Medium[/yellow]"
            else:
                return "[red]High[/red]"
        
        elif idx == 7:  # Time until close
            minutes = feature_dict.get('minutes_until_close', 0)
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}h {mins}m"
        
        return "?"
    
    def _get_value_style(self, value: float) -> str:
        """Get color style based on normalized value"""
        if value <= 0.2:
            return "green"
        elif value <= 0.5:
            return "yellow"
        elif value <= 0.8:
            return "orange1"
        else:
            return "red"
    
    def _create_indicators(self, features: np.ndarray, feature_dict: Dict) -> Panel:
        """Create visual progress indicators"""
        indicators = []
        
        # Time progress bar
        time_progress = features[0]
        time_bar = self._create_progress_bar(
            "Day Progress", 
            time_progress,
            "🌅 Open" if time_progress < 0.5 else "🌆 Late"
        )
        indicators.append(time_bar)
        
        # Risk meter
        risk_score = features[6]
        risk_bar = self._create_progress_bar(
            "Risk Level",
            risk_score,
            "⚠️ " + ("Low" if risk_score < 0.3 else "Med" if risk_score < 0.6 else "High"),
            color="green" if risk_score < 0.3 else "yellow" if risk_score < 0.6 else "red"
        )
        indicators.append(risk_bar)
        
        # Position status
        if feature_dict.get('has_position', 0):
            pos_time = features[5]
            pos_bar = self._create_progress_bar(
                "Position Age",
                pos_time,
                "📊 Active",
                color="cyan"
            )
            indicators.append(pos_bar)
        
        # Combine indicators
        indicator_table = Table(show_header=False, show_lines=False, 
                               box=None, padding=0)
        indicator_table.add_column("Indicator")
        
        for ind in indicators:
            indicator_table.add_row(ind)
            indicator_table.add_row("")  # Spacing
        
        return Panel(
            indicator_table,
            title="[dim]Visual Indicators[/dim]",
            border_style="dim",
            padding=(1, 1)
        )
    
    def _create_progress_bar(self, label: str, value: float, 
                           status: str, color: str = "cyan") -> str:
        """Create a text-based progress bar"""
        bar_width = 20
        filled = int(value * bar_width)
        empty = bar_width - filled
        
        bar = f"[{color}]{'█' * filled}[/{color}]" + f"[dim]{'░' * empty}[/dim]"
        
        return f"{label:<15} {bar} {value:.1%} {status}"
    
    def get_feature_alerts(self, features: np.ndarray) -> List[str]:
        """Generate alerts based on feature values"""
        alerts = []
        
        # Time-based alerts
        if features[0] < 0.08:  # First 30 min
            alerts.append("🕐 Early session - limited data")
        elif features[7] < 0.08:  # Last 30 min
            alerts.append("⏰ Near close - increased volatility")
        
        # Risk alerts
        if features[6] > 0.7:
            alerts.append("⚠️ High risk environment")
        
        # Position alerts
        if features[3] > 0 and features[5] > 0.5:
            alerts.append("📊 Long position duration")
        
        return alerts