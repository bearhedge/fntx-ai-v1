# Market Timer System - Complete Documentation

## Overview

The Market Timer system is a comprehensive event tracking and trading restriction system designed to prevent costly trading mistakes during high-volatility market events. It monitors Federal Reserve meetings, economic data releases, and other market-moving events to provide real-time warnings and automated trading blocks.

## System Architecture

### Directory Structure
```
/home/info/fntx-ai-v1/rl-trading/spy_options/market_timer/
├── README.md                    # User documentation
├── market_timer.py             # Core logic and event management
├── market_timer_panel.py       # Terminal UI panel (enhanced)
├── fed_calendar.py             # Federal Reserve events for 2025
├── economic_calendar.py        # Economic data releases (CPI, NFP, GDP)
├── create_events_table.sql     # Database schema for event tracking
└── logs/                       # Operational logs
```

### Integration Points
- **Terminal UI**: Enhanced panel in the trading dashboard
- **Trading System**: Blocks suggestions during high-risk periods
- **Database**: Logs all trading restrictions for compliance
- **RLHF System**: Captures feedback during event-driven volatility

## Key Features

### 1. Event Tracking

#### Federal Reserve Events (EXTREME Risk)
- **FOMC Meetings**: 8 scheduled meetings in 2025
  - January 29, March 19, May 1, June 11, July 30, September 17, November 5, December 17
  - Blackout Period: 12:00 PM - 4:00 PM ET
  - Average Volatility: 1.0-1.8% moves
  - Special Note: SEP meetings (March, June, September, December) have extended volatility

- **Jackson Hole Symposium**: August 22, 2025
  - Full day blackout (9:00 AM - 4:00 PM ET)
  - Historical volatility: 2.0% average
  - Major policy shifts often announced

- **Congressional Testimony**: 
  - February 26-27, July 9-10
  - Blackout: 9:30 AM - 12:00 PM ET
  - Q&A sessions can cause sudden moves

#### Economic Data Releases (HIGH Risk)
- **CPI (Consumer Price Index)**: Monthly, typically mid-month
  - Time: 8:30 AM ET
  - Blackout: 8:25 AM - 9:00 AM ET
  - Average Volatility: 0.7-0.8%
  - Core CPI often more important than headline

- **NFP (Non-Farm Payrolls)**: First Friday of each month
  - Time: 8:30 AM ET
  - Blackout: 8:25 AM - 9:00 AM ET
  - Average Volatility: 0.8-0.9%
  - Watch unemployment rate changes

- **GDP**: Quarterly releases (Advance, Second, Final)
  - Time: 8:30 AM ET
  - Blackout: 8:25 AM - 9:00 AM ET (Advance only)
  - Average Volatility: 0.6-0.7%

- **PCE (Personal Consumption Expenditures)**: Monthly
  - Fed's preferred inflation gauge
  - Average Volatility: 0.6%

### 2. Risk Assessment

#### Risk Levels
```
🟢 LOW       - Normal trading conditions
🟡 MEDIUM    - Exercise caution, reduce position sizes
🟠 HIGH      - Consider avoiding new positions
🔴 EXTREME   - Trading blocked or strongly discouraged
```

#### Trading Status
```
✅ SAFE      - Clear to trade
⚠️  CAUTION  - Event approaching (within 2 hours)
🚫 BLOCKED   - No trading allowed
```

### 3. Automated Trading Restrictions

#### Blackout Rules
1. **FOMC Days**: 
   - Pre-meeting (9:30 AM - 12:00 PM): CAUTION status
   - During meeting (12:00 PM - 2:00 PM): BLOCKED
   - Post-announcement (2:00 PM - 4:00 PM): BLOCKED

2. **Economic Data (8:30 AM releases)**:
   - Pre-market: No trading capability
   - First 30 minutes (9:30 AM - 10:00 AM): BLOCKED for HIGH risk
   - After 10:00 AM: CAUTION status

3. **End of Day**:
   - Last 15 minutes (3:45 PM - 4:00 PM): HIGH GAMMA warning
   - Last 10 minutes (3:50 PM - 4:00 PM): BLOCKED

### 4. Visual Display

The Market Timer panel shows:
```
╭─────────────────── Market Timer & Events ───────────────────╮
│                                                              │
│  Close: 54m  |  Session: MIDDAY  |  Risk: EXTREME           │
│  ════════════════════════════════════════════════════════   │
│                                                              │
│  🔴 NEXT EVENT: FOMC - Fed Rate Decision                     │
│  └─ In: 0h 55m (2:00 PM ET)                                │
│  └─ Risk: EXTREME                                           │
│  └─ Avg Impact: ±1.1% in 30min                              │
│  └─ TRADING BLOCKED: 12:00 PM - 4:00 PM ET                  │
│                                                              │
│  Upcoming Events:                                            │
│  • Jul 31: GDP Release Q2 (8:30 AM)         HIGH RISK       │
│  • Aug 02: NFP Report (8:30 AM)             HIGH RISK       │
│  • Aug 13: CPI Data (8:30 AM)               MEDIUM RISK     │
│                                                              │
│  🚫 TRADING BLOCKED - FOMC Event                             │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

## Implementation Details

### Core Classes

#### MarketTimer (market_timer.py)
```python
class MarketTimer:
    def get_current_risk_assessment() -> Dict
    def should_block_trading() -> Tuple[bool, str, Optional[Dict]]
    def get_next_major_event() -> Optional[Dict]
    def get_trading_windows(date: datetime) -> List[Dict]
    def log_trading_restriction(restriction_type: str, event: Dict)
```

#### FedCalendar (fed_calendar.py)
- Tracks all Federal Reserve events
- Provides risk assessment for Fed-specific events
- Includes FOMC meetings, speeches, testimony

#### EconomicCalendar (economic_calendar.py)
- Tracks economic data releases
- Covers CPI, NFP, GDP, PCE, PPI, ISM
- Pre-market event detection

#### MarketTimerPanel (market_timer_panel.py)
- Terminal UI integration
- Real-time countdown display
- Color-coded risk indicators
- Trading status messages

### Database Schema

```sql
-- Market events table
CREATE TABLE market_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    event_date DATE NOT NULL,
    event_time TIME NOT NULL,
    timezone VARCHAR(20) DEFAULT 'US/Eastern',
    speaker VARCHAR(100),
    description TEXT NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    avg_volatility DECIMAL(5,2),
    blackout_start TIME NOT NULL,
    blackout_end TIME NOT NULL,
    notes TEXT
);

-- Historical impacts tracking
CREATE TABLE event_impacts (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES market_events(id),
    actual_date DATE NOT NULL,
    spy_move_pct DECIMAL(5,2),
    vix_change DECIMAL(5,2),
    duration_minutes INTEGER,
    notes TEXT
);

-- Trading restrictions log
CREATE TABLE trading_restrictions (
    id SERIAL PRIMARY KEY,
    restriction_time TIMESTAMP NOT NULL,
    event_id INTEGER REFERENCES market_events(id),
    restriction_type VARCHAR(50) NOT NULL,
    spy_price DECIMAL(10,2),
    vix_level DECIMAL(5,2),
    override BOOLEAN DEFAULT FALSE,
    override_reason TEXT
);
```

## Usage Examples

### Check Current Trading Status
```python
from market_timer import MarketTimer

timer = MarketTimer()
should_block, reason, event = timer.should_block_trading()

if should_block:
    print(f"Trading blocked: {reason}")
else:
    print("Trading allowed")
```

### Get Today's Events
```python
import datetime
events = timer.get_all_events(datetime.datetime.now())
for event in events:
    print(f"{event['time']} - {event['type']}: {event['description']}")
```

### Find Safe Trading Windows
```python
windows = timer.get_trading_windows(datetime.datetime.now())
for window in windows:
    print(f"{window['start']} - {window['end']}: {window['risk']} risk")
```

## Trading Guidelines

### Before Each Trading Day
1. Check Market Timer for scheduled events
2. Note all blackout periods
3. Plan position exits before restrictions
4. Set calendar alerts for major events

### During Event Days

#### FOMC Days
- Close all positions by 11:30 AM ET
- No new positions after 11:00 AM ET
- Resume trading next day only
- Monitor for delayed market reactions

#### Economic Data Days (8:30 AM releases)
- Avoid overnight positions before major data
- Wait until after 10:00 AM to enter positions
- Use wider stops due to volatility
- Monitor for trend reversals

#### End of Day Rules
- Begin position reduction at 3:30 PM ET
- Close all positions by 3:45 PM ET
- Never hold into final 10 minutes
- Gamma risk increases exponentially

### Risk Management

#### Position Sizing
- Reduce size by 50% on event days
- Use 25% of normal size during CAUTION periods
- No new positions during BLOCKED periods
- Consider closing profitable positions early

#### Stop Loss Adjustments
- Widen stops by 2x on HIGH risk days
- Use time-based stops near events
- Implement trailing stops after events
- Never remove stops during events

## Historical Event Examples

### July 30, 2025 - FOMC "No Cut" Decision
- Time: 2:00 PM ET announcement
- Market Impact: SPY dropped 0.6% in 30 minutes (636 → 633)
- Positions Affected: 635 Put options went ITM
- Lesson: Always respect FOMC blackout periods

### Past Volatility Patterns
- FOMC with SEP: 1.5-2.0% average moves
- CPI surprises: 0.8-1.2% initial spikes
- NFP misses: 0.5-1.0% within first hour
- GDP shocks: 0.6-0.8% sustained moves

## Best Practices

### System Integration
1. Market Timer checks before all trades
2. Automated position closure at 3:45 PM
3. Event alerts 2 hours before restrictions
4. Compliance logging for all overrides

### Manual Overrides
- Require explicit acknowledgment
- Document override reasoning
- Log for compliance review
- Higher stop loss requirements

### Continuous Improvement
1. Track actual vs expected volatility
2. Adjust blackout periods based on data
3. Update risk levels quarterly
4. Review restriction effectiveness

## Troubleshooting

### Common Issues

1. **Events Not Displaying**
   - Verify market_events.json exists
   - Check date format (YYYY-MM-DD)
   - Ensure timezone is US/Eastern

2. **Trading Not Blocked**
   - Confirm system time is accurate
   - Check blackout period configuration
   - Verify event is marked active

3. **False Restrictions**
   - Update event calendar monthly
   - Account for daylight saving time
   - Review risk level assignments

### Support Checklist
1. Check logs in `market_timer/logs/`
2. Verify database connectivity
3. Confirm event data is current
4. Test with known FOMC date

## Future Enhancements

1. **Real-time Updates**
   - Economic calendar API integration
   - Push notifications for changes
   - Emergency event detection

2. **Machine Learning**
   - Predict volatility patterns
   - Optimize blackout timing
   - Personalize risk thresholds

3. **Advanced Features**
   - Options Greeks adjustments
   - Multi-asset correlations
   - Automated hedging strategies

## Conclusion

The Market Timer system provides essential protection against trading during high-volatility events. By respecting blackout periods and following the guidelines, traders can avoid significant losses from unexpected market moves during Fed announcements and economic data releases.