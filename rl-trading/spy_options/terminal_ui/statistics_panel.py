"""
Statistics panel displaying real probability metrics
Shows Probability of Touch (PoT), Expected Value (EV), and market statistics
Replaces vague confidence scores with meaningful statistical analysis
"""
from datetime import datetime
from typing import Dict, Optional
import pytz
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.columns import Columns
from rich.progress import Progress, BarColumn, TextColumn
from rich.console import Group
from rich.align import Align


class StatisticsPanel:
    """Display real statistical metrics for trading decisions"""
    
    def __init__(self):
        self.eastern = pytz.timezone('US/Eastern')
        
    def create_panel(self,
                    suggestion: Optional[Dict] = None,
                    market_stats: Optional[Dict] = None,
                    positions: Optional[Dict] = None,
                    model_prediction: Optional[Dict] = None,
                    options_chain: Optional[list] = None) -> Panel:
        """
        Create statistics panel with real probability metrics
        
        Args:
            suggestion: Current trade suggestion with statistical metrics
            market_stats: Market statistics (VIX regime, time of day)
            positions: Current positions and their metrics
            
        Returns:
            Rich Panel with statistical information
        """
        # Single column layout - no market context
        layout = Layout()
        
        # Create metrics section
        # Check if we have position manager data
        if positions and isinstance(positions, dict) and 'positions' in positions:
            # Risk management mode - show position metrics (keep as table for clarity)
            metrics_content = self._create_position_display(positions)
            panel_title = "[bold red]Position Risk Management[/bold red]"
            border_style = "red"
        elif suggestion and 'statistical_metrics' in suggestion:
            # Recommendation mode - show suggestion metrics (narrative)
            metrics_content = self._create_metrics_display(suggestion)
            panel_title = "[bold cyan]AI Trading Analysis[/bold cyan]"
            border_style = "cyan"
        else:
            # No data - show continuous analysis (narrative)
            spy_price = market_stats.get('spy_price', 0) if market_stats else 0
            metrics_content = self._create_empty_metrics(model_prediction, options_chain, spy_price)
            panel_title = "[bold cyan]AI Market Thinking[/bold cyan]"
            border_style = "cyan"
            
        # Wrap content in appropriate container
        if isinstance(metrics_content, Group):
            # For narrative content, add padding
            metrics_panel_content = Align.center(
                metrics_content,
                vertical="top",
                pad=True
            )
        else:
            # For tables, use as-is
            metrics_panel_content = metrics_content
            
        # Update main layout with metrics content
        metrics_panel = Panel(
            metrics_panel_content,
            title=panel_title,
            border_style=border_style,
            padding=(1, 2)
        )
        
        # Return the metrics panel directly
        return Panel(
            metrics_panel,
            title="[bold]Real Probabilities & Expected Value[/bold]",
            border_style="bright_blue",
            subtitle="[dim]Based on barrier option theory and statistical analysis[/dim]"
        )
        
    def _create_metrics_display(self, suggestion: Dict) -> Group:
        """Create narrative analysis for a specific trade suggestion"""
        stats = suggestion['statistical_metrics']
        narrative_parts = []
        
        # Opening assessment
        pot = stats['probability_of_touch']
        win_prob = stats['win_probability']
        ev = stats['expected_value']
        
        # Build opening narrative based on quality of the trade
        if ev > 20 and pot < 0.25:
            opening = "I've identified an excellent trading opportunity here. "
            style = "bold green"
        elif ev > 10 and pot < 0.35:
            opening = "I've found a solid trading setup. "
            style = "green"
        elif ev > 0:
            opening = "I see a marginal opportunity that meets minimum criteria. "
            style = "yellow"
        else:
            opening = "This setup barely meets our criteria, proceed with caution. "
            style = "red"
            
        # Detailed analysis
        opening += f"The probability of the underlying touching our strike is {pot:.1%}, which means we have a {win_prob:.1%} chance of keeping the full premium. "
        
        # Risk interpretation
        if pot < 0.20:
            opening += "This is a very conservative position with minimal touch risk. "
        elif pot < 0.30:
            opening += "The touch risk is well within acceptable parameters. "
        elif pot < 0.35:
            opening += "We're approaching the upper limit of acceptable touch risk. "
        else:
            opening += "The touch risk is elevated - consider passing on this trade. "
            
        narrative_parts.append(Text(opening, style=style))
        narrative_parts.append(Text(""))  # Blank line
        
        # Expected value narrative
        ev_per_risk = stats['ev_per_dollar_risked']
        rr_ratio = stats['risk_reward_ratio']
        
        ev_text = f"From a statistical perspective, this trade has an expected value of ${ev:.2f}, representing a {ev_per_risk:.1%} return on capital at risk. "
        ev_text += f"We're risking ${stats['loss_at_stop']:.0f} (at our 3.5x stop loss) to potentially make ${stats['profit_on_win']:.0f} in premium - "
        ev_text += f"that's a risk/reward ratio of 1:{rr_ratio:.1f}. "
        
        if ev_per_risk > 0.15:
            ev_text += "This is an exceptional return on risk that warrants strong consideration."
        elif ev_per_risk > 0.10:
            ev_text += "This represents a healthy return that justifies the risk."
        elif ev_per_risk > 0.05:
            ev_text += "The return is positive but modest - ensure you're comfortable with the risk."
        else:
            ev_text += "The return is marginal - only proceed if you have high conviction."
            
        narrative_parts.append(Text(ev_text, style="cyan"))
        narrative_parts.append(Text(""))  # Blank line
        
        # Kelly sizing narrative
        kelly = stats['kelly_fraction']
        kelly_pct = kelly * 100
        
        kelly_text = f"The Kelly Criterion suggests an optimal position size of {kelly_pct:.1f}% of capital for this trade. "
        if kelly_pct > 5:
            kelly_text += "This high Kelly percentage reflects strong positive expectancy. However, I recommend using a fraction of Kelly (typically 25-50%) for practical risk management."
        elif kelly_pct > 2:
            kelly_text += "This moderate Kelly percentage suggests reasonable confidence in the setup. Consider using 1-2% of capital for this position."
        else:
            kelly_text += "The low Kelly percentage indicates limited edge. Keep position size minimal, perhaps 0.5-1% of capital."
            
        narrative_parts.append(Text(kelly_text, style="magenta"))
        narrative_parts.append(Text(""))  # Blank line
        
        # Specific contract details
        if 'strike' in suggestion:
            contract_text = f"Specifically, I'm recommending selling the ${suggestion['strike']} {suggestion['type'].lower()} "
            if 'delta' in suggestion:
                delta = abs(suggestion['delta'])
                contract_text += f"(approximately {int(delta * 100)}-delta) "
            contract_text += f"for a mid-price of ${suggestion['mid_price']:.2f} per contract. "
            
            # Add Greeks interpretation
            if 'theta' in suggestion:
                theta = suggestion['theta']
                contract_text += f"This position will generate ${theta:.2f} in daily theta decay. "
                
            narrative_parts.append(Text(contract_text, style="bold"))
            
        return Group(*narrative_parts)
        
    def _create_position_display(self, positions_data: Dict) -> Table:
        """Create position display for risk management mode"""
        table = Table(show_header=True, show_lines=True, expand=True)
        table.add_column("Strike", style="cyan", width=10)
        table.add_column("Type", style="magenta", width=8)
        table.add_column("Entry", justify="right", width=10)
        table.add_column("Current", justify="right", width=10)
        table.add_column("P&L", justify="right", width=12)
        table.add_column("Stop Loss", justify="right", width=10)
        table.add_column("Risk", style="yellow", width=10)
        
        positions = positions_data.get('positions', [])
        summary = positions_data.get('summary', {})
        risk_metrics = positions_data.get('risk_metrics', {})
        
        # Add each position
        for pos in positions:
            strike = pos['strike']
            pos_type = pos['type']
            entry_price = pos['entry_price']
            current_price = pos['current_price']
            pnl = pos.get('pnl_per_contract', 0)
            stop_loss = pos['stop_loss']
            
            # Color P&L
            pnl_color = "green" if pnl > 0 else "red" if pnl < 0 else "white"
            
            # Calculate distance to stop
            if current_price > 0:
                distance_to_stop = (stop_loss - current_price) / current_price * 100
                risk_str = f"{distance_to_stop:.1f}%"
                risk_color = "red" if distance_to_stop < 50 else "yellow" if distance_to_stop < 100 else "green"
            else:
                risk_str = "N/A"
                risk_color = "dim"
            
            table.add_row(
                f"${strike}",
                pos_type,
                f"${entry_price:.2f}",
                f"${current_price:.2f}",
                f"[{pnl_color}]${pnl:.0f}[/{pnl_color}]",
                f"${stop_loss:.2f}",
                f"[{risk_color}]{risk_str}[/{risk_color}]"
            )
        
        # Add totals row
        if positions:
            table.add_row("", "", "", "", "", "", "")
            total_pnl = summary.get('total_pnl', 0)
            total_risk = risk_metrics.get('total_risk', 0)
            pnl_color = "green" if total_pnl > 0 else "red" if total_pnl < 0 else "white"
            
            table.add_row(
                "[bold]TOTAL[/bold]",
                f"[bold]{len(positions)} pos[/bold]",
                "",
                "",
                f"[bold {pnl_color}]${total_pnl:.0f}[/bold {pnl_color}]",
                "",
                f"[bold yellow]${total_risk:.0f}[/bold yellow]"
            )
        
        return table
        
    def _create_empty_metrics(self, model_prediction: Optional[Dict] = None, 
                            options_chain: Optional[list] = None,
                            spy_price: Optional[float] = None) -> Group:
        """Create continuous market analysis even without active suggestion"""
        # Show live analysis instead of placeholder
        return self._create_continuous_analysis(model_prediction, options_chain, spy_price)
        
    def _create_continuous_analysis(self, model_prediction: Optional[Dict] = None, 
                                   options_chain: Optional[list] = None,
                                   spy_price: Optional[float] = None) -> Group:
        """Create continuous analysis display showing REAL Greek analysis"""
        narrative_parts = []
        
        # If we have options chain data, analyze it
        if options_chain and spy_price and spy_price > 0:
            # Find best call and put based on Greeks and EV
            best_call = self._find_best_option(options_chain, spy_price, 'C')
            best_put = self._find_best_option(options_chain, spy_price, 'P')
            
            # Opening with real market analysis
            opening = Text("Real-time option chain analysis:", style="bold cyan")
            narrative_parts.append(opening)
            narrative_parts.append(Text(""))  # Blank line
            
            # Analyze best call option
            if best_call:
                call_analysis = self._analyze_option(best_call, spy_price, 'call')
                narrative_parts.append(Text(call_analysis, style="green"))
                narrative_parts.append(Text(""))
            
            # Analyze best put option  
            if best_put:
                put_analysis = self._analyze_option(best_put, spy_price, 'put')
                narrative_parts.append(Text(put_analysis, style="green"))
                narrative_parts.append(Text(""))
            
            # Compare opportunities
            if best_call and best_put:
                comparison = self._compare_opportunities(best_call, best_put, spy_price)
                narrative_parts.append(Text(comparison, style="magenta"))
                narrative_parts.append(Text(""))
        else:
            # No options data - show we're waiting for real data
            narrative_parts.append(Text("Waiting for live options chain data to analyze Greeks and expected values...", 
                                      style="yellow"))
            narrative_parts.append(Text(""))
        
        # Add model thinking if available
        if model_prediction:
            action = model_prediction.get('action', 0)
            action_probs = model_prediction.get('action_probs', [0.33, 0.33, 0.34])
            
            model_text = f"Model signal: {['HOLD', 'SELL CALL', 'SELL PUT'][action]} "
            model_text += f"(confidence: {action_probs[action]:.0%})"
            
            # Color based on action
            style = "yellow" if action == 0 else "red" if action == 1 else "green"
            narrative_parts.append(Text(model_text, style=style))
        
        return Group(*narrative_parts)
    
    def _find_best_option(self, options_chain: list, spy_price: float, option_type: str) -> Optional[Dict]:
        """Find the best option based on EV and Greeks"""
        # Filter by type and target delta (0.30 ± 0.05)
        candidates = []
        for opt in options_chain:
            if opt['type'] != option_type:
                continue
                
            # Check delta first - target 0.30 delta
            delta = abs(opt.get('delta', 0))
            if delta < 0.25 or delta > 0.35:  # Target 0.30 ± 0.05
                continue
                
            strike = opt['strike']
            if option_type == 'C':
                otm_pct = ((strike - spy_price) / spy_price) * 100
            else:
                otm_pct = ((spy_price - strike) / spy_price) * 100
                
            # Also check OTM range as secondary filter
            if 0.1 <= otm_pct <= 3.0:  # Allow closer to ATM for 30-delta
                # Calculate expected value
                opt['otm_pct'] = otm_pct
                opt['ev'] = self._calculate_expected_value(opt, spy_price)
                candidates.append(opt)
        
        # Sort by expected value
        if candidates:
            return max(candidates, key=lambda x: x['ev'])
        return None
    
    def _calculate_expected_value(self, option: Dict, spy_price: float) -> float:
        """Calculate expected value for an option"""
        # Get option details
        strike = option['strike']
        premium = option.get('last', (option['bid'] + option['ask']) / 2)
        delta = abs(option.get('delta', 0.2))
        
        # Calculate probability of touch (approximation)
        pot = delta * 2.5  # Rough approximation
        if pot > 1:
            pot = 0.95
            
        # Win probability
        win_prob = 1 - pot
        
        # Expected value calculation
        profit_on_win = premium * 100  # Per contract
        loss_at_stop = premium * 350  # 3.5x stop loss
        
        ev = (win_prob * profit_on_win) - (pot * loss_at_stop)
        return ev
    
    def _analyze_option(self, option: Dict, spy_price: float, option_name: str) -> str:
        """Create analysis text for a specific option"""
        strike = option['strike']
        otm_pct = option['otm_pct']
        premium = option.get('last', (option['bid'] + option['ask']) / 2)
        
        # Greeks
        delta = abs(option.get('delta', 0.2))
        gamma = option.get('gamma', 0.01)
        theta = option.get('theta', -0.05)
        vega = option.get('vega', 0.1)
        iv = option.get('iv', 0.2)
        
        # Build analysis
        analysis = f"Best {option_name}: ${strike} strike ({otm_pct:.1f}% OTM)\n"
        analysis += f"  Premium: ${premium:.2f} (bid: ${option['bid']:.2f}, ask: ${option['ask']:.2f})\n"
        analysis += f"  Greeks: Δ={delta:.2f}, Γ={gamma:.3f}, Θ=${theta*100:.0f}/day, Vega=${vega*100:.0f}/1%IV\n"
        analysis += f"  IV: {iv*100:.1f}% | Expected Value: ${option['ev']:.2f}\n"
        
        # Add dollar impact narratives
        spy_move_1 = delta * 100  # $1 SPY move impact per contract
        spy_move_10c = delta * 10  # $0.10 SPY move impact per contract
        daily_theta = abs(theta * 100)  # Daily theta in dollars
        
        analysis += f"\n  Impact Analysis:\n"
        analysis += f"    • $1 SPY move = ${spy_move_1:.0f} gain/loss\n"
        analysis += f"    • $0.10 SPY move = ${spy_move_10c:.0f} gain/loss\n"
        analysis += f"    • Daily theta collection: ${daily_theta:.0f}\n"
        
        # Add confidence narrative based on delta
        confidence = (1 - delta) * 100  # Probability of expiring worthless
        analysis += f"\n  Confidence: {confidence:.0f}% chance of keeping full premium\n"
        analysis += f"  (Based on {delta:.2f} delta ≈ {delta*100:.0f}% probability of touch)"
        
        return analysis
    
    def _compare_opportunities(self, call: Dict, put: Dict, spy_price: float) -> str:
        """Compare call vs put opportunities"""
        if call['ev'] > put['ev']:
            better = "call"
            diff = call['ev'] - put['ev']
        else:
            better = "put"
            diff = put['ev'] - call['ev']
            
        comparison = f"Better opportunity: Sell {better} (${diff:.2f} higher EV)\n"
        comparison += f"Call EV: ${call['ev']:.2f} | Put EV: ${put['ev']:.2f}"
        
        return comparison
    
    def _get_time_interpretation(self, minutes_since_open: float) -> str:
        """Get interpretation of time since market open"""
        if minutes_since_open < 0:
            return "Pre-market"
        elif minutes_since_open < 30:
            return "[red]Initial volatility period[/red]"
        elif minutes_since_open < 60:
            return "[yellow]Early session[/yellow]"
        elif minutes_since_open < 180:
            return "[green]Prime trading hours[/green]"
        elif minutes_since_open < 360:
            return "[yellow]Late session[/yellow]"
        else:
            return "[red]Near close - gamma risk[/red]"
            
    def _get_action_interpretation(self, action: int, probability: float) -> str:
        """Get interpretation of model action and probability"""
        if action == 0:  # HOLD
            if probability > 0.7:
                return "Strong hold signal"
            elif probability > 0.5:
                return "Moderate hold preference"
            else:
                return "Weak hold signal"
        elif action == 1:  # SELL CALL
            if probability > 0.7:
                return "Strong bearish signal"
            elif probability > 0.5:
                return "Moderate call opportunity"
            else:
                return "Weak call signal"
        else:  # SELL PUT
            if probability > 0.7:
                return "Strong bullish signal"
            elif probability > 0.5:
                return "Moderate put opportunity"
            else:
                return "Weak put signal"
        
    def _create_market_display(self, market_stats: Optional[Dict]) -> Table:
        """Create market context display"""
        table = Table(show_header=False, show_lines=False, expand=True)
        table.add_column("Metric", style="magenta", width=18)
        table.add_column("Value", justify="right", width=12)
        
        if market_stats:
            # VIX Level
            vix = market_stats.get('vix_level', 0)
            vix_regime = market_stats.get('volatility_regime', 'Unknown')
            vix_color = self._get_vix_color(vix)
            table.add_row(
                "VIX",
                f"[{vix_color}]{vix:.1f} ({vix_regime})[/{vix_color}]"
            )
            
            # VIX Percentile
            percentile = market_stats.get('vix_percentile', 0)
            table.add_row(
                "VIX Percentile",
                f"{percentile}th"
            )
            
            # Time Period
            time_period = market_stats.get('time_period', 'Unknown')
            table.add_row(
                "Trading Period",
                time_period
            )
            
            # Hours to Close
            hours_remaining = market_stats.get('hours_to_close', 0)
            table.add_row(
                "Time to Close",
                f"{hours_remaining:.1f}h"
            )
            
            # Add notes
            table.add_row("", "")
            regime_desc = market_stats.get('regime_description', '')
            if regime_desc:
                table.add_row(
                    "[dim]Regime[/dim]",
                    f"[dim]{regime_desc}[/dim]"
                )
                
            time_notes = market_stats.get('time_notes', '')
            if time_notes:
                table.add_row(
                    "[dim]Period[/dim]",
                    f"[dim]{time_notes}[/dim]"
                )
        else:
            # No market data
            now = datetime.now(self.eastern)
            table.add_row("Time", now.strftime("%H:%M ET"))
            table.add_row("", "[dim]Loading market data...[/dim]")
            
        return table
        
    def _get_pot_color(self, pot: float) -> str:
        """Get color based on PoT level"""
        if pot < 0.20:
            return "bright_green"
        elif pot < 0.30:
            return "green"
        elif pot < 0.35:
            return "yellow"
        elif pot < 0.40:
            return "orange1"
        else:
            return "red"
            
    def _get_pot_interpretation(self, pot: float) -> str:
        """Get interpretation of PoT level"""
        if pot < 0.20:
            return "Very low risk"
        elif pot < 0.30:
            return "Acceptable risk"
        elif pot < 0.35:
            return "Moderate risk"
        elif pot < 0.40:
            return "Elevated risk"
        else:
            return "High risk - consider passing"
            
    def _get_vix_color(self, vix: float) -> str:
        """Get color based on VIX level"""
        if vix < 15:
            return "green"
        elif vix < 20:
            return "yellow"
        elif vix < 25:
            return "orange1"
        else:
            return "red"
            
    def create_mini_panel(self, suggestion: Optional[Dict] = None) -> Panel:
        """Create compact statistics display"""
        if suggestion and 'statistical_metrics' in suggestion:
            stats = suggestion['statistical_metrics']
            
            table = Table(show_header=False, show_lines=False, expand=False)
            table.add_column("Metric", width=12)
            table.add_column("Value", width=10, justify="right")
            
            # Key metrics only
            pot = stats['probability_of_touch']
            ev = stats['expected_value']
            
            pot_color = self._get_pot_color(pot)
            ev_color = "green" if ev > 20 else "yellow" if ev > 0 else "red"
            
            table.add_row("PoT", f"[{pot_color}]{pot:.1%}[/{pot_color}]")
            table.add_row("EV", f"[{ev_color}]${ev:.0f}[/{ev_color}]")
            table.add_row("Win%", f"{stats['win_probability']:.0%}")
            
            return Panel(
                table,
                title="[cyan]Statistics[/cyan]",
                border_style="cyan"
            )
        else:
            return Panel(
                "[dim]No data[/dim]",
                title="[cyan]Statistics[/cyan]",
                border_style="cyan"
            )