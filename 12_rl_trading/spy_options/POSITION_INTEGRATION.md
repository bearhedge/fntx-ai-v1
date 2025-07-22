# Position Integration System

## Overview

This document explains how the SPY 0DTE Options Trading Terminal integrates with Interactive Brokers Gateway to create a unified trading experience where all components communicate seamlessly.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Terminal Dashboard                         │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │   Header    │  │ Options Chain│  │  AI Reasoning       │   │
│  │ (Mode/Status)│  │              │  │                     │   │
│  └─────────────┘  └──────────────┘  └─────────────────────┘   │
│  ┌─────────────────────────────────┐  ┌─────────────────────┐   │
│  │     Statistics Panel            │  │   Risk Alerts       │   │
│  │ (Suggestions/Positions)         │  │                     │   │
│  └─────────────────────────────────┘  └─────────────────────┘   │
└────────────────────────┬───────────────────────────────────────┘
                         │
                    ┌────▼─────┐
                    │ Position │
                    │ Manager  │
                    └────┬─────┘
                         │
              ┌──────────▼──────────┐
              │   IB Position       │
              │   Monitor           │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │  IB Gateway         │
              │  (Port 4001)        │
              └─────────────────────┘
```

## Components

### 1. IB Position Monitor (`ib_position_monitor.py`)
- Connects to IB Gateway on port 4001
- Monitors all SPY option positions in real-time
- Tracks P&L, current prices, and stop loss levels
- Fires callbacks when positions change

### 2. Position Manager (`position_manager.py`)
- Coordinates between IB Gateway and Dashboard
- Manages trading mode transitions:
  - **RECOMMENDATION**: Looking for new trades
  - **RISK_MANAGEMENT**: Managing active positions
  - **CLOSING**: Closing out positions
  - **PAUSED**: Temporarily disabled
- Stores position history
- Calculates risk metrics

### 3. Dashboard Integration
- Receives position updates via callbacks
- Updates display based on trading mode
- Shows different information in each mode:
  - **Recommendation Mode**: Trade suggestions, PoT, EV
  - **Risk Management Mode**: Position P&L, stop loss distances, total risk

## Communication Flow

### When You Execute a Trade

1. **Manual Execution** (via `execute_625_put.py`):
   ```
   IB Gateway → Order Placed → Position Created
   ```

2. **Position Detection**:
   ```
   IB Position Monitor → Detects New Position → Callback to Position Manager
   ```

3. **Mode Transition**:
   ```
   Position Manager → Changes Mode to RISK_MANAGEMENT → Notifies Dashboard
   ```

4. **Dashboard Update**:
   ```
   Dashboard → Updates Header Status → Shows Position Info → Blocks New Suggestions
   ```

### Real-Time Updates

Every second, the system:
1. IB Gateway reports position changes
2. Position Monitor updates P&L and prices
3. Position Manager checks stop loss distances
4. Dashboard refreshes display with latest data

### When Positions Close

1. Position reaches stop loss or manual close
2. IB Position Monitor detects position = 0
3. Position Manager transitions back to RECOMMENDATION mode
4. Dashboard resumes showing trade suggestions

## Usage

### Starting with IB Integration

```bash
# Start dashboard with IB monitoring enabled
python run_terminal_ui.py --local-theta --enable-ib

# Optional: specify different IB port
python run_terminal_ui.py --local-theta --enable-ib --ib-port 7496
```

### Without IB Integration

```bash
# Run in standalone mode (no position detection)
python run_terminal_ui.py --local-theta
```

## Features

### Automatic Position Detection
- No manual entry needed
- Detects trades executed through any IB interface
- Updates within 1-2 seconds of execution

### Risk Management Mode
- Shows real-time P&L for each position
- Monitors distance to stop loss
- Calculates total portfolio risk
- Prevents conflicting trade recommendations

### Stop Loss Alerts
- Warns when price approaches stop loss (within 20%)
- Color-coded risk indicators
- Automatic position tracking

### Trade History
- Saves all closed positions
- Tracks final P&L
- Persistent across sessions

## Example Workflow

1. **Dashboard starts in Recommendation Mode**
   - Shows "🔍 SEEKING OPPORTUNITIES"
   - Generates trade suggestions every 5 minutes
   - Displays PoT, EV, and statistical analysis

2. **You execute SPY 625 Put trade**
   ```bash
   python execute_625_put.py
   ```

3. **Dashboard automatically detects position**
   - Header changes to "🛡️ RISK MANAGEMENT (1 position)"
   - Statistics panel shows position details
   - No new suggestions generated

4. **Real-time monitoring**
   - P&L updates as option price changes
   - Stop loss distance shown as percentage
   - Total risk displayed

5. **Position closed (manually or stop loss)**
   - Dashboard returns to "🔍 SEEKING OPPORTUNITIES"
   - Resumes generating suggestions
   - Position saved to history

## Troubleshooting

### Dashboard doesn't detect trades
1. Check IB Gateway is running on correct port
2. Verify API connections enabled in IB Gateway
3. Ensure --enable-ib flag is used
4. Check logs for connection errors

### Position data not updating
1. Verify market data subscriptions in IB
2. Check if position is for SPY options (others ignored)
3. Ensure IB Gateway has live data permissions

### Multiple IB instances
- Use --ib-port to specify correct port
- Default is 4001 (matches execute scripts)
- Common ports: 4001, 7496 (live), 7497 (paper)

## Benefits

1. **Unified Experience**: Execute trades anywhere, dashboard knows immediately
2. **Safety**: Prevents conflicting recommendations when positions active
3. **Risk Awareness**: Always see total risk and P&L
4. **Automation**: No manual position entry needed
5. **Persistence**: Position history saved across sessions