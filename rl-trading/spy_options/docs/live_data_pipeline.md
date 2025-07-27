# Live Data Pipeline Documentation

## Overview

The live data pipeline bridges the gap between historical training data and real-time market data, enabling the AI model to make trading suggestions based on current market conditions.

## Architecture

```
Theta Terminal API → Data Connector → Feature Engine → AI Model → User Interface
        ↓                  ↓               ↓              ↓            ↓
   Market Data      Raw Quotes      8 Features     Prediction    Suggestion
```

## Components

### 1. Theta Data Connector (`theta_connector.py`)

**Purpose**: Connects to Theta Terminal for real-time options data

**Key Functions**:
- WebSocket connection for streaming quotes
- REST API for initial options chain
- Maintains current market snapshot
- Provides ATM options and Greeks

**Data Retrieved**:
- SPY spot price (last, bid, ask)
- 0DTE options chain (all strikes)
- Implied volatility for each option
- Greeks (delta, gamma, etc.)

### 2. Feature Engine (`feature_engine.py`)

**Purpose**: Converts raw market data to model features

**8 Features (matching training)**:
1. `minutes_since_open / 390` - Normalized time
2. `spy_price / 1000` - Normalized SPY price
3. `atm_iv` - At-the-money implied volatility
4. `has_position` - Binary (0 or 1)
5. `position_pnl / 1000` - Normalized P&L
6. `time_in_position / 390` - Normalized hold time
7. `risk_score` - Calculated risk (0-1)
8. `minutes_until_close / 390` - Time remaining

**Additional Components**:
- `PositionTracker`: Manages open positions and P&L
- Risk calculation based on position size, time, volatility
- Feature validation and normalization

### 3. Live Trading System (`live_trading_system.py`)

**Purpose**: Orchestrates all components for live trading

**Main Loop**:
1. Get market snapshot from Theta
2. Convert to 8-feature vector
3. Get AI model prediction
4. Check trading rules (wait times, risk)
5. Present suggestion to user
6. Log feedback for RLHF

## Usage

### Basic Test (Mock Data)

```bash
# Test data flow only
python test_live_system.py --data

# Test full system with mock data
python test_live_system.py --full
```

### Live Trading (Real Data)

```bash
# With real Theta Terminal connection
python -m data_pipeline.live_trading_system \
    --model models/gpu_trained/ppo_2m_final \
    --theta-key YOUR_API_KEY \
    --capital 80000 \
    --contracts 1
```

### Mock Trading (Testing)

```bash
# Use mock data for testing
python -m data_pipeline.live_trading_system \
    --model models/gpu_trained/ppo_2m_final \
    --mock \
    --capital 80000 \
    --contracts 1
```

## Data Flow Example

1. **Market Update** (from Theta):
   ```json
   {
     "spy_price": 628.50,
     "options_chain": [
       {"strike": 628, "type": "C", "bid": 2.45, "ask": 2.55, "iv": 0.15},
       {"strike": 628, "type": "P", "bid": 2.35, "ask": 2.45, "iv": 0.16}
     ]
   }
   ```

2. **Feature Vector** (to Model):
   ```
   [0.25, 0.628, 0.155, 0, 0, 0, 0.2, 0.75]
   ```

3. **Model Prediction**:
   ```
   Action: 2 (sell_put)
   ```

4. **User Suggestion**:
   ```
   [10:32 AM] TRADE SUGGESTION
   Action: SELL 1 SPY 628 PUT
   SPY Price: $628.50
   Option Bid/Ask: $2.35 / $2.45
   Risk Score: 0.20
   
   Execute? (y/n/skip):
   ```

## Integration with IB Gateway

The system is designed to be modular. IB Gateway connection happens separately:

```python
# ib_connector.py (to be implemented)
class IBConnector:
    def execute_trade(self, order_details):
        # Connect to IB Gateway via API
        # Place order
        # Return execution status
```

## Next Steps

1. **Implement IB Connector** for actual trade execution
2. **Add Theta Terminal credentials** for real market data
3. **Test with paper trading** before going live
4. **Collect feedback** for RLHF training

## Important Notes

- Model expects features in exact same format as training
- All time features are normalized to [0, 1]
- Risk management rules from training are enforced
- Position tracking is separate from broker state