# Synchronized Live Streaming & RL API Trading System

## Overview
This system provides synchronized live streaming SPY options data with RL (Reinforcement Learning) API integration. It solves the frequency mismatch between real-time data (500ms updates) and the RL model's 5-minute training intervals.

## Architecture

### Data Flow
```
Theta Terminal (500ms) → Real-time UI Updates (immediate)
                      ↓
                DataAggregator → 5-min OHLC bar complete
                      ↓
                Feature Calculation → 8-feature vector
                      ↓
                RL API Call → Trade Recommendation
                      ↓
                UI Update → Show recommendation for 5 minutes
```

### Key Components
1. **DataAggregator**: Converts real-time ticks to 5-minute OHLC bars
2. **SynchronizedTradingSystem**: Orchestrates streaming and RL API calls
3. **RL API Server**: FastAPI server serving the trained model
4. **Terminal UI**: Rich-based dashboard with real-time updates

## Setup Instructions

### Prerequisites
- Theta Terminal running locally on port 25510
- Python 3.11+ with required packages
- IB Gateway (optional, for live trading)

### Installation
```bash
cd /home/info/fntx-ai-v1/12_rl_trading/spy_options
# Use existing virtual environment
source /home/info/fntx-ai-v1/11_venv/bin/activate
```

### Running the System

#### Terminal 1: Start RL API Server
```bash
cd /home/info/fntx-ai-v1/12_rl_trading/spy_options/api_server
/home/info/fntx-ai-v1/11_venv/bin/python main.py
```

**Expected Output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8100
```

#### Terminal 2: Start Synchronized Trading UI
```bash
cd /home/info/fntx-ai-v1/12_rl_trading/spy_options
/home/info/fntx-ai-v1/11_venv/bin/python run_synchronized_ui.py
```

**Expected Output:**
```
🔧 Initializing synchronized trading system...
✓ Data connector started
✓ All components initialized
⏳ Waiting for initial market data...
✓ Receiving data - SPY: $620.45
============================================================
🚀 Starting synchronized trading system
============================================================
```

### Command Line Options

#### RL API Server Options
- `--port`: API server port (default: 8100)
- `--host`: API server host (default: 0.0.0.0)

#### Synchronized UI Options
- `--rl-api-url`: RL API endpoint (default: http://localhost:8100/predict)
- `--update-rate`: Dashboard refresh rate in seconds (default: 1.0)

### Example Usage
```bash
# Custom RL API URL
/home/info/fntx-ai-v1/11_venv/bin/python run_synchronized_ui.py --rl-api-url http://localhost:8100/predict

# Faster dashboard updates
/home/info/fntx-ai-v1/11_venv/bin/python run_synchronized_ui.py --update-rate 0.5
```

## System Behavior

### Real-time Updates
- Dashboard refreshes every 1 second (default)
- Live SPY price, VIX, and options chain data
- Immediate response to market movements

### RL Model Integration
- RL API called **only** when 5-minute bars complete
- Predictions valid for exactly 5 minutes
- Countdown timer shows time until next prediction
- 8-feature vector calculated from aggregated OHLC data

### Timing Synchronization
- 5-minute bars align with clock times: 9:30, 9:35, 9:40, etc.
- RL predictions triggered at exact 5-minute boundaries
- No recommendations during first/last 30 minutes of trading
- Minimum 90-minute wait between suggestions

## Dashboard Features

### Real-time Panels
- **SPY Options Chain**: Live bid/ask prices, volume, open interest
- **Feature Engineering**: 8 model features with live calculations
- **RL API Status**: Prediction confidence, timing, countdown
- **Trade Reasoning**: Model decision explanation

### RL API Status Panel
```
🤖 RL API Status
┌────────────────────────────────────────────┐
│ RL API Status:    🤖 Active                │
│ RL Confidence:    85.3%                    │
│ Prediction Time:  14:25:00                 │
│ Next Update:      3m 15s                   │
└────────────────────────────────────────────┘
```

## Configuration

### RL Model Features (8-vector)
1. **Time Progress**: 0-1 from market open to close
2. **5-min Return**: Recent price return
3. **15-min Return**: Medium-term return (3 bars)
4. **30-min Return**: Longer-term return (6 bars)
5. **Volume Ratio**: Current vs average volume
6. **5-min Volatility**: Short-term volatility
7. **15-min Volatility**: Medium-term volatility
8. **Risk Score**: Combined volatility and time risk

### API Endpoints
- `GET /`: Health check and status
- `POST /predict`: Get RL model prediction
- `POST /feedback`: Submit user feedback
- `GET /memory/similar`: Find similar contexts
- `POST /session/new`: Start new trading session

## Troubleshooting

### Common Issues

#### 1. "No market data available"
- Check Theta Terminal is running on port 25510
- Verify REST API is enabled in Theta Terminal settings
- Ensure market is open or using historical data

#### 2. "RL API request failed"
- Verify RL API server is running on port 8100
- Check API server logs for errors
- Ensure database connection is working

#### 3. "Module not found" errors
- Use the full path to Python virtual environment
- Install missing dependencies in virtual environment

### Testing
```bash
# Run component tests
cd /home/info/fntx-ai-v1/12_rl_trading/spy_options
/home/info/fntx-ai-v1/11_venv/bin/python test_synchronized_system.py
```

### Performance Monitoring
- **Total Ticks**: Real-time data points received
- **Completed Bars**: Number of 5-minute bars processed
- **RL API Calls**: Successful predictions requested
- **RL API Errors**: Failed API calls
- **Success Rate**: API reliability percentage

## System Statistics
The system displays real-time statistics on shutdown:
```
📊 Session Statistics
============================================================
Total Ticks: 1,247
Completed 5-min Bars: 12
RL API Calls: 12
RL API Errors: 0
RL API Success Rate: 100.0%
============================================================
```

## Next Steps
1. Configure live trading with IB Gateway integration
2. Add trade execution confirmation dialogs
3. Implement user feedback collection
4. Add position monitoring and P&L tracking
5. Create trade logging and performance analytics

## Files Modified
- `data_pipeline/data_aggregator.py`: Enhanced with RL feature calculation
- `data_pipeline/smart_suggestion_engine.py`: Added 5-minute interval sync
- `terminal_ui/reasoning_panel.py`: Added RL API status display
- `run_synchronized_ui.py`: New orchestrated system (main entry point)
- `test_synchronized_system.py`: Component testing script