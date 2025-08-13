"""
Enhanced Market Timer Panel - Shows market timing, events, and trading restrictions
Displays critical market events (Fed meetings, economic data) and prevents trading during high volatility
"""
from datetime import datetime, timedelta, time
from typing import Dict, Optional, List, Tuple
import pytz
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group
from rich.align import Align
from rich import box
from rich.progress import Progress, BarColumn, TextColumn
import json
import os
import requests
from datetime import datetime


class MarketTimerPanel:
    """Enhanced market timer with event tracking and trading restrictions"""
    
    def __init__(self):
        self.eastern = pytz.timezone('US/Eastern')
        self.hongkong = pytz.timezone('Asia/Hong_Kong')
        # Try critical events file first, then fall back to general events
        self.critical_events_file = os.path.join(os.path.dirname(__file__), "market_events_critical.json")
        self.events_file = os.path.join(os.path.dirname(__file__), "market_events.json")
        self.load_events()
        
        # Trading guardrail settings (in hours)
        self.guardrail_settings = [1.5, 3.0, 4.5]
        self.current_guardrail_setting = 0  # Default to 1.5 hours
        
        # News cache and settings
        self._news_cache = []
        self._last_news_fetch = None
        self.news_keywords = ['trump', 'tariff', 'trade war', 'china trade', 'fed', 'interest rate']
        
    def load_events(self):
        """Load market events from JSON file"""
        # Default events - CRITICAL MARKET EVENTS
        # NOTE: These are hardcoded dates. For accurate dates:
        # 1. Set FRED_API_KEY environment variable (get free at https://fred.stlouisfed.org/)
        # 2. Run: python market_timer/collect_events.py
        all_events = [
            # FOMC meetings for 2025
            {
                "date": "2025-07-30",
                "time": "14:00",
                "type": "FOMC",
                "description": "FOMC Rate Decision",
                "risk_level": "EXTREME",
                "avg_volatility": 1.2,
                "blackout_start": "12:00",
                "blackout_end": "16:00"
            },
            {
                "date": "2025-09-17",
                "time": "14:00",
                "type": "FOMC",
                "description": "FOMC Rate Decision",
                "risk_level": "EXTREME",
                "avg_volatility": 1.2,
                "blackout_start": "12:00",
                "blackout_end": "16:00"
            },
            {
                "date": "2025-11-05",
                "time": "14:00",
                "type": "FOMC",
                "description": "FOMC Rate Decision",
                "risk_level": "EXTREME",
                "avg_volatility": 1.2,
                "blackout_start": "12:00",
                "blackout_end": "16:00"
            },
            {
                "date": "2025-12-17",
                "time": "14:00",
                "type": "FOMC",
                "description": "FOMC Rate Decision",
                "risk_level": "EXTREME",
                "avg_volatility": 1.2,
                "blackout_start": "12:00",
                "blackout_end": "16:00"
            },
            # NFP - First Friday of each month
            {
                "date": "2025-08-01",
                "time": "08:30",
                "type": "NFP",
                "description": "Jobs Report (NFP)",
                "risk_level": "EXTREME",
                "avg_volatility": 0.9,
                "blackout_start": "08:25",
                "blackout_end": "09:00"
            },
            # CPI - Monthly mid-month (typically Tuesday/Wednesday)
            {
                "date": "2025-08-12",
                "time": "08:30",
                "type": "CPI",
                "description": "Consumer Price Index",
                "risk_level": "HIGH",
                "avg_volatility": 0.7,
                "blackout_start": "08:25",
                "blackout_end": "09:00"
            },
            # GDP - Quarterly
            {
                "date": "2025-08-28",
                "time": "08:30",
                "type": "GDP",
                "description": "GDP Q2 Final",
                "risk_level": "HIGH",
                "avg_volatility": 0.6,
                "blackout_start": "08:25",
                "blackout_end": "09:00"
            },
            {
                "date": "2025-09-05",
                "time": "08:30",
                "type": "NFP",
                "description": "Jobs Report (NFP)",
                "risk_level": "EXTREME",
                "avg_volatility": 0.9,
                "blackout_start": "08:25",
                "blackout_end": "09:00"
            },
            {
                "date": "2025-10-03",
                "time": "08:30",
                "type": "NFP",
                "description": "Jobs Report (NFP)",
                "risk_level": "EXTREME",
                "avg_volatility": 0.9,
                "blackout_start": "08:25",
                "blackout_end": "09:00"
            },
            {
                "date": "2025-11-07",
                "time": "08:30",
                "type": "NFP",
                "description": "Jobs Report (NFP)",
                "risk_level": "EXTREME",
                "avg_volatility": 0.9,
                "blackout_start": "08:25",
                "blackout_end": "09:00"
            },
            {
                "date": "2025-12-05",
                "time": "08:30",
                "type": "NFP",
                "description": "Jobs Report (NFP)",
                "risk_level": "EXTREME",
                "avg_volatility": 0.9,
                "blackout_start": "08:25",
                "blackout_end": "09:00"
            }
        ]
        
        # Include FOMC, NFP, CPI, and GDP events
        self.events = [e for e in all_events if e['type'] in ['FOMC', 'NFP', 'CPI', 'GDP']]
        
        # Try to load from critical events file first
        if os.path.exists(self.critical_events_file):
            try:
                with open(self.critical_events_file, 'r') as f:
                    loaded_events = json.load(f)
                    # All events in critical file should be FOMC or NFP
                    self.events = loaded_events
            except:
                pass
        # Fall back to general events file
        elif os.path.exists(self.events_file):
            try:
                with open(self.events_file, 'r') as f:
                    loaded_events = json.load(f)
                    # Include FOMC, NFP, CPI, and GDP events
                    self.events = [e for e in loaded_events if e['type'] in ['FOMC', 'NFP', 'CPI', 'GDP']]
            except:
                pass
    
    def get_risk_color(self, risk_level: str) -> str:
        """Get color for risk level"""
        colors = {
            "LOW": "green",
            "MEDIUM": "yellow",
            "HIGH": "orange1",
            "EXTREME": "red bold"
        }
        return colors.get(risk_level, "white")
    
    def convert_to_hkt(self, et_datetime: datetime) -> datetime:
        """Convert ET datetime to HKT"""
        # Convert to HKT (ET + 13 hours during standard time)
        hkt_datetime = et_datetime.astimezone(self.hongkong)
        return hkt_datetime
    
    def get_trading_status(self, now_et: datetime) -> Tuple[str, str, str]:
        """Get current trading status based on events"""
        # Check if we're in any blackout period
        current_date = now_et.strftime("%Y-%m-%d")
        current_time = now_et.time()
        
        for event in self.events:
            if event["date"] == current_date:
                # Parse blackout times
                blackout_start = datetime.strptime(event["blackout_start"], "%H:%M").time()
                blackout_end = datetime.strptime(event["blackout_end"], "%H:%M").time()
                
                if blackout_start <= current_time <= blackout_end:
                    return "BLOCKED", "red bold blink", f"🚫 TRADING BLOCKED - {event['type']} Event"
                
                # Check if event is coming up soon (within 2 hours)
                event_time = datetime.strptime(event["time"], "%H:%M").time()
                event_dt = now_et.replace(hour=event_time.hour, minute=event_time.minute)
                time_to_event = (event_dt - now_et).total_seconds() / 3600
                
                if 0 < time_to_event <= 2:
                    return "CAUTION", "yellow bold", f"⚠️  CAUTION - {event['type']} in {time_to_event:.1f}h"
        
        # Check for end of day risk (last 15 minutes)
        market_close = now_et.replace(hour=16, minute=0, second=0)
        time_to_close = (market_close - now_et).total_seconds() / 60
        
        if 0 < time_to_close <= 15:
            return "HIGH_GAMMA", "orange1 bold", "⚠️  HIGH GAMMA RISK - Close positions"
        
        return "SAFE", "green", "✅ Safe to trade"
    
    def get_next_event(self, now_et: datetime) -> Optional[Dict]:
        """Get the next upcoming event"""
        current_dt = now_et
        next_event = None
        min_time_diff = float('inf')
        
        for event in self.events:
            event_date = datetime.strptime(event["date"], "%Y-%m-%d")
            event_time = datetime.strptime(event["time"], "%H:%M").time()
            event_dt = self.eastern.localize(
                event_date.replace(hour=event_time.hour, minute=event_time.minute)
            )
            
            # Only consider future events
            if event_dt > current_dt:
                time_diff = (event_dt - current_dt).total_seconds()
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    next_event = event
                    next_event["datetime"] = event_dt
                    next_event["hours_until"] = time_diff / 3600
        
        return next_event
    
    def create_guardrail_display(self, now_et: datetime, market_open: datetime) -> List:
        """Create the trading guardrail progress display"""
        # Calculate time since market open
        time_since_open = (now_et - market_open).total_seconds() / 60  # in minutes
        
        # Get current guardrail setting in minutes
        guardrail_minutes = self.guardrail_settings[self.current_guardrail_setting] * 60
        
        # Calculate progress percentage
        progress_pct = min(100, (time_since_open / guardrail_minutes) * 100)
        
        # Check if trading is allowed
        trading_allowed = time_since_open >= guardrail_minutes
        
        # Create display elements
        elements = []
        
        # No title needed
        
        # Status message - only show if NOT allowed
        if not trading_allowed:
            remaining_minutes = int(guardrail_minutes - time_since_open)
            if remaining_minutes >= 60:
                hours = remaining_minutes // 60
                mins = remaining_minutes % 60
                time_str = f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
            else:
                time_str = f"{remaining_minutes}m"
            status_text = Text(f"Time until trading: {time_str}", style="red")
            elements.append(status_text)
            elements.append(Text())  # Spacer
        
        # Progress bar BELOW (as requested)
        bar_width = 20
        filled = int((progress_pct / 100) * bar_width)
        empty = bar_width - filled
        
        bar_style = "green" if trading_allowed else "red"
        bar = Text()
        bar.append('█' * filled, style=bar_style)
        bar.append('░' * empty, style="dim")
        bar.append(f" {progress_pct:.0f}%", style=bar_style)
        elements.append(bar)
        
        # Setting info - show which trading mode we're in
        setting_text = f"{self.guardrail_settings[self.current_guardrail_setting]}h mode"
        elements.append(Text(setting_text, style="dim"))
        
        return elements
    
    def should_allow_trading_guardrail(self) -> bool:
        """Check if enough time has passed since market open"""
        now_et = datetime.now(self.eastern)
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        
        # If market not open yet, don't allow
        if now_et < market_open:
            return False
            
        time_since_open = (now_et - market_open).total_seconds() / 60  # in minutes
        guardrail_minutes = self.guardrail_settings[self.current_guardrail_setting] * 60
        
        return time_since_open >= guardrail_minutes
    
    def create_panel(self, market_data: Optional[Dict] = None) -> Panel:
        """Create enhanced market timer panel"""
        sections = []
        
        # Get current time in ET
        now_et = datetime.now(self.eastern)
        
        # Market hours (9:30 AM - 4:00 PM ET)
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        
        # Check if market is open
        is_market_open = market_open <= now_et < market_close
        
        if is_market_open:
            # Time to close
            time_to_close = (market_close - now_et).total_seconds() / 60
            hours = int(time_to_close // 60)
            minutes = int(time_to_close % 60)
            
            # Trading session phase
            time_since_open = (now_et - market_open).total_seconds() / 60
            
            if time_since_open < 30:
                session = "OPENING"
                session_desc = "Initial volatility"
            elif time_since_open < 60:
                session = "OPEN"
                session_desc = "Stabilizing"
            elif hours >= 2:
                if minutes <= 15:
                    session = "CLOSING"
                    session_desc = "High gamma risk"
                else:
                    session = "LATE"
                    session_desc = "Approaching close"
            else:
                session = "MIDDAY"
                session_desc = "Normal trading"
            
            # Get trading status
            status, status_style, status_text = self.get_trading_status(now_et)
            
            # Risk level based on status
            if status == "BLOCKED":
                risk_level = "EXTREME"
                risk_color = "red bold"
            elif status == "CAUTION":
                risk_level = "HIGH"
                risk_color = "orange1"
            elif status == "HIGH_GAMMA":
                risk_level = "HIGH"
                risk_color = "orange1"
            else:
                risk_level = "NORMAL"
                risk_color = "green"
            
            # Don't show any header for market session
            
            # Create two-column layout
            main_table = Table(show_header=False, box=None, expand=True, padding=(0, 1))
            main_table.add_column("Events", ratio=3)
            main_table.add_column("Guardrail", ratio=2)
            
            # Left column - Events
            events_content = []
            events_content.append(Text("Upcoming Events:", style="bold cyan"))
            
            # Get next 3 events
            future_events = []
            for event in self.events:
                event_date = datetime.strptime(event["date"], "%Y-%m-%d")
                event_time = datetime.strptime(event["time"], "%H:%M").time()
                event_dt = self.eastern.localize(
                    event_date.replace(hour=event_time.hour, minute=event_time.minute)
                )
                
                if event_dt > now_et:
                    future_events.append({
                        **event,
                        "datetime": event_dt,
                        "datetime_hkt": self.convert_to_hkt(event_dt),
                        "hours_until": (event_dt - now_et).total_seconds() / 3600
                    })
            
            # Sort by date and take first 3
            future_events.sort(key=lambda x: x["datetime"])
            
            for i, event in enumerate(future_events[:3]):
                # Format: 1. Aug 2, 2025 - NFP Report
                #            8:30 PM HKT Friday (8:30 AM ET)
                event_hkt = event["datetime_hkt"]
                event_et = event["datetime"]
                
                # Event header
                event_text = Text()
                event_text.append(f"{i+1}. ", style="cyan")
                event_text.append(event_hkt.strftime("%b %d, %Y"), style="white")
                event_text.append(" - ", style="dim")
                event_text.append(event["description"], style="bold yellow")
                
                # Removed time until event - no longer needed
                
                events_content.append(event_text)
                
                # Time line
                time_text = Text("   ")
                time_text.append(event_hkt.strftime("%I:%M %p HKT %A"), style="bold white")
                time_text.append(f" ({event_et.strftime('%I:%M %p ET')})", style="dim")
                events_content.append(time_text)
                
                # Only add spacer between events, not after the last one
                if i < 2 and i < len(future_events[:3]) - 1:
                    events_content.append(Text())
            
            # Right column - Trading Guardrail
            guardrail_content = self.create_guardrail_display(now_et, market_open)
            
            # Add columns to table
            main_table.add_row(
                Group(*events_content),
                Group(*guardrail_content)
            )
            
            sections.append(main_table)
            
            # Trading status - now includes both event status and guardrail
            sections.append(Text())  # Add space before trading status
            
            # Check guardrail status
            guardrail_allowed = self.should_allow_trading_guardrail()
            
            # Combine statuses - both must be OK to trade
            if status == "BLOCKED":
                final_status_text = status_text
                final_status_style = status_style
            elif not guardrail_allowed:
                final_status_text = "🚫 TRADING BLOCKED - Guardrail Active"
                final_status_style = "red bold"
            else:
                final_status_text = status_text
                final_status_style = status_style
                
            sections.append(Align.center(Text(final_status_text, style=final_status_style)))
            
        else:
            # Market closed
            closed_text = Text("MARKET CLOSED", style="red bold")
            sections.append(Align.center(closed_text))
            
            # Always show "tonight" for HKT users since market opens at 9:30 PM HKT
            if now_et.hour >= 16:  # After 4 PM ET
                tomorrow_open = market_open + timedelta(days=1)
                tomorrow_open_hkt = self.convert_to_hkt(tomorrow_open)
                next_text = Text(f"Opens tonight at {tomorrow_open_hkt.strftime('%I:%M %p')} HKT", style="yellow")
                sections.append(Align.center(next_text))
            else:  # Before market open
                market_open_hkt = self.convert_to_hkt(market_open)
                open_text = Text(f"Opens at {market_open_hkt.strftime('%I:%M %p')} HKT", style="yellow")
                sections.append(Align.center(open_text))
            
            # Show next 3 events
            sections.append(Text())
            sections.append(Text("Upcoming Events:", style="bold cyan"))
            
            # Get next 3 events
            future_events = []
            for event in self.events:
                event_date = datetime.strptime(event["date"], "%Y-%m-%d")
                event_time = datetime.strptime(event["time"], "%H:%M").time()
                event_dt = self.eastern.localize(
                    event_date.replace(hour=event_time.hour, minute=event_time.minute)
                )
                
                if event_dt > now_et:
                    future_events.append({
                        **event,
                        "datetime": event_dt,
                        "datetime_hkt": self.convert_to_hkt(event_dt)
                    })
            
            # Sort by date and take first 3
            future_events.sort(key=lambda x: x["datetime"])
            
            for i, event in enumerate(future_events[:3]):
                # Format: 1. Aug 2, 2025 - NFP Report
                #            8:30 PM HKT Friday (8:30 AM ET)
                event_hkt = event["datetime_hkt"]
                event_et = event["datetime"]
                
                # Event header
                event_text = Text()
                event_text.append(f"{i+1}. ", style="cyan")
                event_text.append(event_hkt.strftime("%b %d, %Y"), style="white")
                event_text.append(" - ", style="dim")
                event_text.append(event["description"], style="bold yellow")
                sections.append(event_text)
                
                # Time line
                time_text = Text("   ")
                time_text.append(event_hkt.strftime("%I:%M %p HKT %A"), style="bold white")
                time_text.append(f" ({event_et.strftime('%I:%M %p ET')})", style="dim")
                sections.append(time_text)
                sections.append(Text())  # Spacer
        
        # Add breaking news section
        sections.append(Text())  # Spacer before news
        news_line = self.format_news_line()
        sections.append(news_line)
        
        # Combine all sections
        content = Group(*sections)
        
        return Panel(
            content,
            title="[bold cyan]Market Timer[/bold cyan]",
            border_style="cyan",
            padding=(0, 1)  # Reduced padding to fit more content
        )
    
    def should_block_trading(self) -> Tuple[bool, str]:
        """Check if trading should be blocked"""
        now_et = datetime.now(self.eastern)
        status, _, message = self.get_trading_status(now_et)
        
        # Check event-based blocking
        if status == "BLOCKED":
            return True, message
        
        # Check guardrail blocking
        if not self.should_allow_trading_guardrail():
            guardrail_hours = self.guardrail_settings[self.current_guardrail_setting]
            return True, f"Trading guardrail active - {guardrail_hours}h minimum wait required"
        
        return False, ""
    
    def cycle_guardrail_setting(self):
        """Cycle through guardrail settings (1.5h -> 3h -> 4.5h -> 1.5h)"""
        self.current_guardrail_setting = (self.current_guardrail_setting + 1) % len(self.guardrail_settings)
        return self.guardrail_settings[self.current_guardrail_setting]
        
    def get_breaking_news(self) -> List[str]:
        """Get breaking news headlines focused on Trump/tariffs/Fed (cached for 5 minutes)"""
        now = datetime.now()
        
        # Check cache (5 minute expiry)
        if (self._last_news_fetch and 
            (now - self._last_news_fetch).total_seconds() < 300 and 
            self._news_cache):
            return self._news_cache
            
        try:
            # For demo purposes, return mock headlines
            # In production, this would connect to a news API like NewsAPI.org
            mock_headlines = [
                "Fed signals pause on rate cuts amid inflation concerns",
                "Trump proposes 25% tariffs on China imports", 
                "Market volatility rises ahead of trade talks",
                "Tech earnings mixed as trade tensions escalate"
            ]
            
            # Simulate API call delay and filtering
            filtered_headlines = []
            for headline in mock_headlines:
                # Filter by keywords
                if any(keyword.lower() in headline.lower() for keyword in self.news_keywords):
                    # Truncate to fit display (max 50 characters)
                    if len(headline) > 50:
                        headline = headline[:47] + "..."
                    filtered_headlines.append(headline)
                    
            # Limit to 2 headlines to fit display
            self._news_cache = filtered_headlines[:2]
            self._last_news_fetch = now
            
            return self._news_cache
            
        except Exception as e:
            # Fallback on error
            return ["News service unavailable"]
            
    def format_news_line(self) -> Text:
        """Format breaking news as a single compact line"""
        headlines = self.get_breaking_news()
        
        if not headlines or headlines == ["News service unavailable"]:
            return Text("News: Service unavailable", style="dim")
            
        # Create compact news line with pipe separators
        news_text = Text()
        news_text.append("News: ", style="bold cyan")
        
        for i, headline in enumerate(headlines):
            if i > 0:
                news_text.append(" | ", style="dim")
            news_text.append(headline, style="white")
            
        return news_text