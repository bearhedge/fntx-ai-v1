# Mandatory Stop Loss System Documentation

## Critical Safety Feature

This system prevents unlimited risk exposure by enforcing mandatory stop losses on ALL trades.

## System Components

### 1. Stop Loss Enforcer (`stop_loss_enforcer.py`)
- Validates all trades have stop losses before execution
- Enforces 3.5x premium multiplier (configurable)
- Blocks trades without proper risk management
- Creates bracket orders for IB execution
- Tracks violations for compliance

### 2. Stop Loss Mandate Panel (`terminal_ui/stop_loss_panel.py`)
- Visual display of stop loss status
- Red alerts for violations
- Real-time position risk monitoring
- Shows which positions have/lack stop losses

### 3. Dashboard Integration (`terminal_ui/dashboard.py`)
- Automatic stop loss validation on trade acceptance
- Visual stop loss panel on right side of screen
- Blocks trades without stop losses
- 5-second violation alert display

### 4. IB Execution (`execute_ib_trade.py`)
- Mandatory stop loss parameter
- Creates bracket orders (parent + stop)
- Validates before sending to IB
- Returns order IDs for tracking

### 5. Database Tracking (`add_stop_loss_columns.py`)
- stop_loss_order_id: IB order tracking
- stop_loss_status: Order state monitoring
- stop_loss_validated: Enforcement flag
- risk_at_entry: Max loss tracking
- Audit table for compliance

## How It Works

1. **Trade Suggestion**: System suggests a trade with calculated stop loss
2. **User Acceptance**: User presses 'Y' to accept
3. **Validation**: Stop loss enforcer validates:
   - Stop loss exists
   - Stop loss >= 3.5x premium
   - Risk metrics calculated
4. **Execution**: If valid, trade executes with bracket order
5. **Blocking**: If invalid, trade is BLOCKED with red alert

## Key Features

- **No Exceptions**: Every trade MUST have a stop loss
- **Automatic Calculation**: System calculates 3.5x stop loss
- **Visual Warnings**: Red alerts for missing stop losses
- **Audit Trail**: All violations tracked in database
- **Bracket Orders**: Parent order + stop loss sent together

## Usage Examples

### Valid Trade
```
Premium: $2.00
Stop Loss: $7.00 (3.5x)
Max Risk: $500
Result: ✅ TRADE EXECUTED
```

### Blocked Trade
```
Premium: $2.00
Stop Loss: NONE
Result: ❌ TRADE BLOCKED - NO STOP LOSS!
```

## Testing

Run test suite:
```bash
python3 test_stop_loss_system.py
```

## Database Migration

Add stop loss columns:
```bash
python3 add_stop_loss_columns.py
```

## Safety First

This system prioritizes account safety over all else. No trade can execute without proper risk management. This prevents catastrophic losses from unlimited risk exposure.

## Configuration

Default stop loss multiplier: 3.5x
To change: Modify `StopLossEnforcer(stop_loss_multiplier=3.5)`

## Emergency Stop

If system is compromised:
```python
enforcer.emergency_stop_all()
```

This blocks ALL trades until manually reset.