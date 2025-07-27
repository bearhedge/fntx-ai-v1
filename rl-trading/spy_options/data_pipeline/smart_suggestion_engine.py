"""
Smart suggestion engine that learns from rejections and retries
Like a pitching machine that adjusts based on your swings/misses
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
import pytz
from .contract_selector import ContractSelector


class SmartSuggestionEngine:
    """Manages suggestions with feedback-based adjustments"""
    
    def __init__(self, min_wait_minutes: int = 90):
        # Timing controls - make dynamic based on market conditions
        self.min_wait_minutes = min_wait_minutes  # 1.5 hours default
        self.last_suggestion_time = None
        self.last_execution_time = None
        
        # Data-driven suggestion triggers
        self.volatility_threshold = 0.15  # Min IV to consider trades
        self.edge_threshold = 10.0  # Min expected value
        self.confidence_threshold = 0.65  # Min model confidence
        
        # Track market conditions for sporadic suggestions
        self.last_vix_level = None
        self.volatility_spike_detected = False
        self.consecutive_hold_bars = 0
        
        # 5-minute interval sync
        self.bar_interval_minutes = 5
        self.last_bar_suggestion_time = None
        
        # Position tracking (1 contract per side max)
        self.positions = {
            'call': None,  # Can have 1 call
            'put': None    # AND 1 put at same time
        }
        
        # Rejection tracking
        self.recent_rejections = []
        self.rejection_reasons = {
            'strike_high': 0,
            'strike_low': 0,
            'wrong_direction': 0,
            'bad_timing': 0,
            'low_vol': 0
        }
        
        # Adjustment parameters
        self.strike_adjustment = 0  # Strikes away from ATM
        self.direction_preference = None  # 'call', 'put', or None
        self.vol_threshold = 0.15  # Minimum IV
        
        # Initialize contract selector with statistical filtering
        self.contract_selector = ContractSelector(
            target_delta=0.30,  # 30-delta options (user preference)
            min_premium=0.50,   # Minimum $0.50 premium
            max_spread_pct=0.10, # Max 10% bid-ask spread
            max_pot=0.35,       # Max 35% probability of touch
            min_ev=10.0         # Min $10 expected value per contract
        )
        
    def can_suggest_now(self) -> bool:
        """Check if enough time has passed AND market conditions warrant a suggestion"""
        if not self.last_suggestion_time:
            # First suggestion after 30 min
            market_open = datetime.now().replace(hour=9, minute=30)
            return datetime.now() > market_open + timedelta(minutes=30)
            
        # Check minimum wait time
        time_since = (datetime.now() - self.last_suggestion_time).seconds / 60
        
        # Make wait time dynamic based on market conditions
        adjusted_wait = self.min_wait_minutes
        if self.volatility_spike_detected:
            # Reduce wait time during volatility spikes
            adjusted_wait = max(30, self.min_wait_minutes // 2)
        elif self.consecutive_hold_bars > 10:
            # Increase wait time during quiet periods
            adjusted_wait = min(180, self.min_wait_minutes * 1.5)
            
        return time_since >= adjusted_wait
        
    def can_suggest_on_bar_completion(self, bar_completion_time: datetime) -> bool:
        """Check if we can suggest when a 5-minute bar completes"""
        # Must pass regular timing checks first
        if not self.can_suggest_now():
            return False
            
        # Check if we already suggested on this bar
        if self.last_bar_suggestion_time:
            # Same bar if within 5 minutes
            time_diff = (bar_completion_time - self.last_bar_suggestion_time).total_seconds() / 60
            if time_diff < self.bar_interval_minutes:
                return False
                
        # Check market hours (9:30 AM to 4:00 PM)
        market_open = bar_completion_time.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = bar_completion_time.replace(hour=16, minute=0, second=0, microsecond=0)
        
        if bar_completion_time < market_open or bar_completion_time > market_close:
            return False
            
        # Don't suggest in first 30 minutes or last 30 minutes
        if (bar_completion_time - market_open).total_seconds() < 30 * 60:
            return False
        if (market_close - bar_completion_time).total_seconds() < 30 * 60:
            return False
            
        return True
        
    def get_position_constraints(self) -> Dict[str, bool]:
        """Check what positions we can open"""
        return {
            'can_sell_call': self.positions['call'] is None,
            'can_sell_put': self.positions['put'] is None,
            'has_any_position': any(self.positions.values())
        }
        
    def adjust_suggestion(self, base_action: int, market_data: dict) -> Optional[dict]:
        """Adjust suggestion based on recent feedback"""
        constraints = self.get_position_constraints()
        
        # Can't suggest if position already exists
        if base_action == 1 and not constraints['can_sell_call']:
            return None
        if base_action == 2 and not constraints['can_sell_put']:
            return None
            
        # Apply direction preference from feedback
        if self.direction_preference:
            if self.direction_preference == 'call' and base_action == 2:
                base_action = 1  # Switch to call
            elif self.direction_preference == 'put' and base_action == 1:
                base_action = 2  # Switch to put
                
        # Check if we can actually do this action
        if base_action == 1 and not constraints['can_sell_call']:
            base_action = 2  # Try put instead
        elif base_action == 2 and not constraints['can_sell_put']:
            base_action = 1  # Try call instead
            
        # Use contract selector to find the best contract
        options_chain = market_data.get('options_chain', [])
        if not options_chain:
            return None
            
        recommendation = self.contract_selector.select_contract(
            action=base_action,
            options_chain=options_chain,
            spy_price=market_data.get('spy_price', 0),
            vix=market_data.get('vix', 0)
        )
        
        if recommendation:
            recommendation['adjusted'] = self.strike_adjustment != 0 or self.direction_preference is not None
            
        return recommendation
        
    def process_rejection(self, suggestion: dict, feedback: str):
        """Learn from rejection feedback"""
        self.recent_rejections.append({
            'time': datetime.now(),
            'suggestion': suggestion,
            'feedback': feedback
        })
        
        # Parse feedback for patterns
        feedback_lower = feedback.lower()
        
        # Strike adjustments
        if 'high' in feedback_lower or 'far' in feedback_lower:
            self.rejection_reasons['strike_high'] += 1
            self.strike_adjustment -= 1  # Move strikes closer
        elif 'low' in feedback_lower or 'close' in feedback_lower:
            self.rejection_reasons['strike_low'] += 1
            self.strike_adjustment += 1  # Move strikes farther
            
        # Direction preferences
        if 'put' in feedback_lower and suggestion['action'] == 1:
            self.rejection_reasons['wrong_direction'] += 1
            self.direction_preference = 'put'
        elif 'call' in feedback_lower and suggestion['action'] == 2:
            self.rejection_reasons['wrong_direction'] += 1
            self.direction_preference = 'call'
            
        # Timing adjustments
        if 'early' in feedback_lower or 'wait' in feedback_lower:
            self.rejection_reasons['bad_timing'] += 1
            self.min_wait_minutes = min(180, self.min_wait_minutes + 15)
            
        # Volatility preferences
        if 'vol' in feedback_lower or 'vix' in feedback_lower:
            self.rejection_reasons['low_vol'] += 1
            self.vol_threshold += 0.02
            
        # Shorten wait time for adjusted suggestions
        self.last_suggestion_time = datetime.now() - timedelta(minutes=30)
        
    def process_acceptance(self, suggestion: dict):
        """Record successful suggestion"""
        option_type = 'call' if suggestion['action'] == 1 else 'put'
        self.positions[option_type] = {
            'strike': suggestion['strike'],
            'entry_time': datetime.now()
        }
        
        # Reset adjustments on success
        self.strike_adjustment = 0
        self.direction_preference = None
        self.last_execution_time = datetime.now()
        
        # Normal wait time after execution
        self.min_wait_minutes = 120  # 2 hours
        
    def close_position(self, option_type: str):
        """Mark position as closed"""
        self.positions[option_type] = None
        
    def get_status(self) -> dict:
        """Get current engine status"""
        return {
            'positions': self.positions,
            'can_suggest': self.can_suggest_now(),
            'time_until_next': self._time_until_next_suggestion(),
            'adjustments': {
                'strike_offset': self.strike_adjustment,
                'direction': self.direction_preference,
                'vol_threshold': self.vol_threshold
            },
            'recent_rejections': len(self.recent_rejections)
        }
        
    def _time_until_next_suggestion(self) -> str:
        """Calculate time until next suggestion allowed"""
        if not self.last_suggestion_time:
            return "Ready"
            
        elapsed = (datetime.now() - self.last_suggestion_time).seconds / 60
        
        # Use adjusted wait time
        adjusted_wait = self.min_wait_minutes
        if self.volatility_spike_detected:
            adjusted_wait = max(30, self.min_wait_minutes // 2)
        elif self.consecutive_hold_bars > 10:
            adjusted_wait = min(180, self.min_wait_minutes * 1.5)
            
        remaining = max(0, adjusted_wait - elapsed)
        
        if remaining == 0:
            return "Ready"
        elif remaining < 60:
            return f"{int(remaining)} min"
        else:
            return f"{remaining/60:.1f} hours"
            
    def update_market_conditions(self, market_data: dict, action: int, confidence: float):
        """Update market condition tracking for data-driven suggestions"""
        # Track VIX changes
        current_vix = market_data.get('vix', 0)
        if self.last_vix_level and current_vix > 0:
            vix_change = abs(current_vix - self.last_vix_level) / self.last_vix_level
            # Detect 10%+ VIX spike as significant
            self.volatility_spike_detected = vix_change > 0.10
        self.last_vix_level = current_vix
        
        # Track consecutive holds
        if action == 0:  # HOLD
            self.consecutive_hold_bars += 1
        else:
            self.consecutive_hold_bars = 0
            
        # Update thresholds based on market feedback
        if self.volatility_spike_detected:
            # Lower confidence threshold during volatility
            self.confidence_threshold = 0.55
        else:
            # Normal confidence threshold
            self.confidence_threshold = 0.65
            
    def should_override_timing(self, market_data: dict, model_confidence: float) -> bool:
        """Check if market conditions warrant overriding normal timing"""
        # Check for exceptional opportunities
        vix = market_data.get('vix', 0)
        
        # High VIX + High confidence = override timing
        if vix > 25 and model_confidence > 0.75:
            return True
            
        # Volatility spike + good confidence
        if self.volatility_spike_detected and model_confidence > 0.65:
            return True
            
        # Very high expected value opportunities
        # This would need to be calculated from options chain
        # For now, use VIX as proxy
        if vix > 20 and model_confidence > 0.70:
            return True
            
        return False


class EnhancedTradingSystem:
    """Enhanced system with smart suggestion management"""
    
    def __init__(self, model, data_connector, capital=80000):
        self.model = model
        self.data_connector = data_connector
        self.capital = capital
        
        # Smart suggestion engine
        self.suggestion_engine = SmartSuggestionEngine()
        
        # Session stats
        self.suggestions_made = 0
        self.suggestions_accepted = 0
        self.trades_today = []
        
    async def trading_loop(self):
        """Main loop with smart suggestions"""
        while self.is_market_open():
            try:
                # Show status
                status = self.suggestion_engine.get_status()
                self._display_status(status)
                
                # Check if we can suggest
                if not status['can_suggest']:
                    await asyncio.sleep(60)  # Check every minute
                    continue
                    
                # Get market data and model prediction
                market_data = self.data_connector.get_current_snapshot()
                features = self.get_features(market_data)
                base_action, _ = self.model.predict(features)
                
                # Skip if model says hold
                if base_action == 0:
                    await asyncio.sleep(300)  # Wait 5 min
                    continue
                    
                # Adjust suggestion based on feedback
                suggestion = self.suggestion_engine.adjust_suggestion(
                    int(base_action), market_data
                )
                
                if suggestion:
                    await self.present_suggestion(suggestion, market_data)
                    
                await asyncio.sleep(60)
                
            except KeyboardInterrupt:
                break
                
    async def present_suggestion(self, suggestion: dict, market_data: dict):
        """Present adjusted suggestion"""
        self.suggestions_made += 1
        action_name = 'CALL' if suggestion['action'] == 1 else 'PUT'
        
        print("\n" + "="*50)
        print(f"[{datetime.now().strftime('%I:%M %p')}] SUGGESTION #{self.suggestions_made}")
        if suggestion.get('adjusted'):
            print("(Adjusted based on your feedback)")
        print("="*50)
        print(f"SELL 1 SPY {suggestion['strike']} {action_name}")
        print(f"SPY: ${market_data['spy_price']:.2f}")
        
        # Show current positions
        positions = self.suggestion_engine.positions
        if positions['call'] or positions['put']:
            print("\nCurrent Positions:")
            if positions['call']:
                print(f"  Call: Strike {positions['call']['strike']}")
            if positions['put']:
                print(f"  Put: Strike {positions['put']['strike']}")
                
        response = input("\nExecute? (y/n): ").lower().strip()
        
        if response == 'y':
            filled = input("Filled? (y/n): ").lower()
            if filled == 'y':
                fill_price = float(input("Fill price: $"))
                self.suggestion_engine.process_acceptance(suggestion)
                self.suggestions_accepted += 1
                print("✓ Position opened")
        else:
            # Get feedback on rejection
            feedback = input("Why not? (or press Enter to skip): ").strip()
            if feedback:
                self.suggestion_engine.process_rejection(suggestion, feedback)
                print("✓ Feedback recorded, adjusting future suggestions...")
            else:
                # Just update timing, no adjustments
                self.suggestion_engine.last_suggestion_time = datetime.now()
                
    def _display_status(self, status: dict):
        """Show current status line"""
        time_str = datetime.now().strftime('%H:%M')
        pos_str = "No positions"
        
        positions = status['positions']
        if positions['call'] and positions['put']:
            pos_str = "Call + Put"
        elif positions['call']:
            pos_str = "Call only"
        elif positions['put']:
            pos_str = "Put only"
            
        next_str = status['time_until_next']
        
        print(f"\r[{time_str}] {pos_str} | Next: {next_str} | "
              f"Suggested: {self.suggestions_made} | "
              f"Accepted: {self.suggestions_accepted}", end='', flush=True)