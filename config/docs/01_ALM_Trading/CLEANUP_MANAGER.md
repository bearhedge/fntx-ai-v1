# Options Cleanup Manager - Automated Position Management System

## Overview

The Cleanup Manager is an automated system designed to monitor and close options positions at risk of exercise during the final trading hours. This is critical for traders operating from different time zones who cannot manually manage positions at market close.

## Problem Statement

When trading SPY options from Hong Kong (4 AM HKT market close), positions that are in-the-money (ITM) or near-the-money at expiration face automatic exercise risk. This can result in:
- Unwanted stock assignments requiring capital
- Margin calls from unexpected positions
- Additional fees and commissions
- Next-day settlement complications

## Solution Architecture

The Cleanup Manager operates as an automated guardian that:
1. Monitors all open options positions throughout the trading day
2. Calculates exercise risk based on moneyness and time to expiry
3. Automatically closes risky positions before market close
4. Converts stop-loss orders to market orders when necessary

## Technical Implementation

### Core Components

```
/home/info/fntx-ai-v1/rl-trading/spy_options/
├── cleanup_manager.py          # Original cleanup manager (IB Gateway only)
├── cleanup_manager_v2.py      # Enhanced version with ThetaData integration
├── stop_loss_enforcer.py      # Existing stop-loss monitoring
├── exercise_panel.py          # UI component for manual monitoring
└── data_pipeline/
    ├── feature_engine.py      # Moneyness calculation logic
    └── local_theta_connector.py # ThetaData market data connector
```

### V2 Architecture - ThetaData Integration

The enhanced V2 cleanup manager uses a hybrid approach:

1. **ThetaData Terminal** (Port 25510)
   - Real-time SPY price updates (1-second intervals)
   - Options chain data with Greeks
   - Continuous market monitoring
   - Cost: ~$600/month (already paid)

2. **IB Gateway** (Port 4002)
   - Position queries on scheduled intervals:
     - Normal: Every 30 minutes
     - With positions: Every 15 minutes
     - T-30 to T-5: Every 5 minutes
     - T-5 to close: Every 1 minute
   - Trade execution only
   - Minimal API usage to prevent rate limits

This architecture provides:
- Professional-grade real-time data from ThetaData
- Reduced IB Gateway load (scheduled checks vs streaming)
- Better performance and reliability
- Cost efficiency (leveraging existing $600/month subscription)

### Key Features

1. **Time-Based Triggers**
   - T-30 minutes: Initial assessment and warning
   - T-5 minutes: Aggressive monitoring mode
   - T-2 minutes: Emergency closure mode

2. **Risk Assessment Algorithm**
   ```python
   risk_score = (moneyness_factor * time_weight * volatility_adjustment)
   
   Where:
   - moneyness_factor: Distance from strike price (0-1 scale)
   - time_weight: Exponential increase as expiry approaches
   - volatility_adjustment: Market volatility consideration
   ```

3. **Position Closure Logic**
   - ITM positions: Immediate closure at T-5 minutes
   - Near-the-money (±0.5%): Closure at T-2 minutes
   - Stop-loss conversion: All stops become market orders at T-2

### Integration Points

1. **IB Gateway Connection**
   - Uses existing `options_trader.py` infrastructure
   - Port 4002 for live trading
   - Real-time position and price monitoring

2. **Database Integration**
   ```sql
   -- New table for cleanup actions
   CREATE TABLE alm_reporting.cleanup_actions (
       id SERIAL PRIMARY KEY,
       action_timestamp TIMESTAMPTZ NOT NULL,
       position_symbol VARCHAR(50),
       strike DECIMAL(10,2),
       expiry DATE,
       moneyness DECIMAL(5,4),
       action_taken VARCHAR(20),
       execution_price DECIMAL(10,2),
       success BOOLEAN
   );
   ```

3. **ALM Reporting Integration**
   - Cleanup actions logged as special events
   - P&L impact tracked separately
   - Daily narrative includes cleanup summary

## Configuration

### Environment Variables
```bash
# Cleanup Manager Settings
CLEANUP_ENABLED=true
CLEANUP_T30_MONEYNESS=0.02    # 2% threshold at T-30
CLEANUP_T5_MONEYNESS=0.01     # 1% threshold at T-5
CLEANUP_T2_MONEYNESS=0.005    # 0.5% threshold at T-2
CLEANUP_MAX_SLIPPAGE=0.10     # Maximum 10 cents slippage
```

### Systemd Timer Configuration
```ini
[Unit]
Description=Options Cleanup Manager
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/info/fntx-ai-v1/rl-trading/spy_options/cleanup_manager.py
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

[Timer]
OnCalendar=Mon-Fri 15:30 America/New_York
Persistent=true

[Install]
WantedBy=timers.target
```

## Operation Modes

### 1. Monitoring Mode (Default)
- Tracks positions without taking action
- Logs risk assessments
- Sends alerts but doesn't execute trades

### 2. Active Mode
- Executes trades based on risk thresholds
- Converts stop-losses to market orders
- Maintains audit trail of all actions

### 3. Emergency Mode
- Triggered manually or by extreme market conditions
- Closes all positions immediately
- Overrides normal risk thresholds

## Risk Management

### Safeguards
1. **Position Limits**: Maximum 10 closure attempts per position
2. **Slippage Control**: Rejects orders with >10 cents slippage
3. **Circuit Breaker**: Halts operations if >5 failures in 60 seconds
4. **Manual Override**: Dashboard kill switch for emergencies

### Moneyness Calculation
```python
def calculate_moneyness(spot_price: float, strike: float, option_type: str) -> float:
    """
    Calculate moneyness as percentage distance from strike
    Positive = ITM, Negative = OTM
    """
    if option_type == 'CALL':
        return (spot_price - strike) / strike
    else:  # PUT
        return (strike - spot_price) / strike
```

## Dashboard Integration

### Terminal UI Components
1. **Cleanup Status Panel**
   - Current positions at risk
   - Time until market close
   - Moneyness heat map
   - Action queue display

2. **Historical View**
   - Past cleanup actions
   - Success/failure rates
   - P&L impact analysis

3. **Configuration Panel**
   - Real-time threshold adjustment
   - Mode switching (Monitor/Active/Emergency)
   - Manual position closure

### Example UI Layout
```
┌─────────────── Cleanup Manager Status ───────────────┐
│ Mode: ACTIVE | Time to Close: 00:28:45              │
├──────────────────────────────────────────────────────┤
│ Positions at Risk:                                   │
│ SPY 635P | Moneyness: +0.8% | Risk: HIGH | T-5     │
│ SPY 638C | Moneyness: -1.2% | Risk: LOW  | Monitor │
├──────────────────────────────────────────────────────┤
│ Actions Queue:                                       │
│ [15:55:00] Close SPY 635P - PENDING                │
│ [15:58:00] Convert stops to market - SCHEDULED     │
└──────────────────────────────────────────────────────┘
```

## Testing Strategy

### Unit Tests
```python
# test_cleanup_manager.py
def test_moneyness_calculation():
    # Test ITM call
    assert calculate_moneyness(636, 635, 'CALL') > 0
    
def test_risk_assessment():
    # Test time-based risk escalation
    assert get_risk_score(0.01, 30) < get_risk_score(0.01, 2)
```

### Integration Tests
1. Mock IB Gateway connection
2. Simulate various market scenarios
3. Verify position closure logic
4. Test emergency mode activation

### Live Testing Protocol
1. Start in monitoring mode only
2. Test with single contract positions
3. Gradually increase to full automation
4. Maintain manual oversight for first week

## Operational Procedures

### Daily Checklist
- [ ] Verify IB Gateway connection at market open
- [ ] Check cleanup manager service status
- [ ] Review previous day's cleanup actions
- [ ] Confirm threshold settings appropriate for market conditions

### Emergency Procedures
1. **Service Failure**
   ```bash
   # Manual restart
   systemctl restart cleanup-manager
   
   # Check logs
   journalctl -u cleanup-manager -n 100
   ```

2. **Position Stuck**
   - Use manual override in terminal UI
   - Direct IB TWS intervention if needed
   - Document incident for post-mortem

## Performance Metrics

### Key Performance Indicators
1. **Exercise Prevention Rate**: Target >99%
2. **Average Closure Slippage**: Target <5 cents
3. **System Uptime**: Target >99.9%
4. **False Positive Rate**: Target <10%

### Monitoring Queries
```sql
-- Daily cleanup summary
SELECT 
    DATE(action_timestamp) as date,
    COUNT(*) as total_actions,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
    AVG(moneyness) as avg_moneyness
FROM alm_reporting.cleanup_actions
WHERE action_timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(action_timestamp)
ORDER BY date DESC;
```

## Future Enhancements

1. **Machine Learning Integration**
   - Predict exercise probability using historical data
   - Optimize closure timing for minimum slippage
   - Adaptive threshold adjustment

2. **Multi-Strategy Support**
   - Handle spreads and complex positions
   - Leg-by-leg risk assessment
   - Coordinated multi-leg closures

3. **Advanced Notifications**
   - SMS/Email alerts for high-risk positions
   - Telegram bot integration
   - Voice call for critical events

4. **Portfolio-Level Management**
   - Aggregate risk assessment
   - Capital preservation mode
   - Cross-position hedging suggestions

## Implementation Status

### ✅ Phase 1: Core Development (COMPLETED)
- [x] Created cleanup_manager.py with monitoring and active modes
- [x] Integrated with IB Gateway connection (port 4002)
- [x] Implemented moneyness calculation
- [x] Added database logging capability

### ✅ Phase 2: Risk Logic (COMPLETED)
- [x] Developed time-based risk assessment (T-30, T-5, T-2)
- [x] Implemented position closure logic in options_trader.py
- [x] Added stop-loss conversion feature
- [x] Created comprehensive logging to /var/log/cleanup-manager/

### ✅ Phase 3: Infrastructure (COMPLETED)
- [x] Created systemd service and timer files
- [x] Built installation script for easy deployment
- [x] Created SQL schema for cleanup_actions table
- [x] Developed unit tests with circuit breaker testing

### 🔄 Phase 4: Production Deployment (READY)
- [ ] Create database table: `psql -d trading_db -f create_cleanup_table.sql`
- [ ] Install service: `sudo ./install_cleanup_service.sh`
- [ ] Test in monitor mode: `python3 cleanup_manager.py --mode monitor`
- [ ] Enable active mode when confident

## Quick Start Guide

### 1. Database Setup
```bash
cd /home/info/fntx-ai-v1/rl-trading/spy_options
psql -U trader -d trading_db -f create_cleanup_table.sql
```

### 2. Test in Monitor Mode
```bash
# Activate virtual environment
source rl_venv/bin/activate

# Test V1 (IB Gateway only)
python3 cleanup_manager.py --mode monitor

# Test V2 (ThetaData + IB Gateway) - RECOMMENDED
python3 cleanup_manager_v2.py --mode monitor

# Check logs
tail -f /var/log/cleanup-manager/cleanup-actions.log
```

### Choosing Between V1 and V2

**Use V2 (cleanup_manager_v2.py) when:**
- ThetaData Terminal is running (normal operations)
- You want real-time price monitoring
- You need to minimize IB Gateway API usage
- Production trading environment

**Use V1 (cleanup_manager.py) when:**
- ThetaData Terminal is down
- Testing without ThetaData
- Emergency fallback mode

### 3. Install System Service
```bash
# Install systemd service (requires sudo)
sudo ./install_cleanup_service.sh

# Start the timer (runs 3:30-4:00 PM ET daily)
sudo systemctl start cleanup-manager.timer

# Check status
sudo systemctl status cleanup-manager.timer
sudo journalctl -u cleanup-manager -f
```

### 4. Configure for Production
Edit `/home/info/fntx-ai-v1/rl-trading/spy_options/cleanup_manager.py` to set database credentials:
```python
db_password: str = 'your_password_here'
```

Or create a config file:
```json
{
    "mode": "active",
    "db_password": "your_password",
    "t30_moneyness": 0.02,
    "t5_moneyness": 0.01,
    "t2_moneyness": 0.005
}
```

### 5. Monitor Performance
```sql
-- View today's cleanup actions
SELECT * FROM alm_reporting.cleanup_actions 
WHERE DATE(action_timestamp) = CURRENT_DATE
ORDER BY action_timestamp DESC;

-- View summary statistics
SELECT * FROM alm_reporting.cleanup_summary;
```

## Support & Maintenance

### Log Locations
```
/var/log/cleanup-manager/
├── cleanup-actions.log    # All closure attempts
├── risk-assessments.log   # Continuous risk monitoring
└── errors.log            # System errors and failures
```

### Troubleshooting Guide
| Issue | Diagnosis | Solution |
|-------|-----------|----------|
| No positions detected | Check IB connection | Restart options_trader service |
| Excessive false positives | Review thresholds | Adjust moneyness parameters |
| Closure failures | Check market liquidity | Increase slippage tolerance |
| Service crashes | Memory/resource issue | Check system resources |

## Conclusion

The Cleanup Manager provides essential automated protection against unwanted exercise events, allowing confident options trading across time zones. By monitoring positions and taking timely action, it prevents the significant capital requirements and complications of unexpected assignments.

Key benefits:
- **Peace of Mind**: Sleep soundly knowing positions are protected
- **Cost Savings**: Avoid assignment fees and margin interest
- **Risk Reduction**: Systematic approach to exercise prevention
- **Operational Efficiency**: Automated management frees trader focus

This system represents a critical component of professional options trading infrastructure, ensuring that geographic location doesn't compromise trading outcomes.