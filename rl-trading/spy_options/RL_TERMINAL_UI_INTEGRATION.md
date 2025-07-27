# RL API Integration in Terminal UI

## Overview
The existing terminal UI now supports optional RL API integration, displaying real-time recommendations that refresh every 5 minutes with a countdown timer.

## How It Works

### Data Flow
```
Terminal UI (1Hz updates) → Track real-time prices
                         ↓
                   DataAggregator → Builds 5-minute bars
                         ↓
                   Every 5 minutes → Call RL API
                         ↓
                   Cache prediction → Display for 5 minutes
                         ↓
                   Countdown timer → Auto-refresh at 0:00
```

### Display Updates
1. **Real-time data**: Updates every second (SPY price, options chain)
2. **RL predictions**: Update every 5 minutes at bar boundaries
3. **Countdown timer**: Shows time until next RL update
4. **Auto-refresh**: Automatically calls RL API when timer expires

## Running the Enhanced Terminal UI

### Prerequisites
1. Start the RL API server:
```bash
cd /home/info/fntx-ai-v1/12_rl_trading/spy_options/api_server
/home/info/fntx-ai-v1/11_venv/bin/python main.py
```

2. Ensure Theta Terminal is running on port 25510

### Launch Commands

#### With RL API Integration:
```bash
cd /home/info/fntx-ai-v1/12_rl_trading/spy_options
/home/info/fntx-ai-v1/11_venv/bin/python run_terminal_ui.py --local-theta --enable-rl
```

#### With Custom RL API URL:
```bash
/home/info/fntx-ai-v1/11_venv/bin/python run_terminal_ui.py --local-theta --enable-rl --rl-api-url http://localhost:8100/predict
```

#### Without RL API (original behavior):
```bash
/home/info/fntx-ai-v1/11_venv/bin/python run_terminal_ui.py --local-theta
```

## What You'll See

### RL API Status Panel
Located below "AI Decision Reasoning" and above "Current Decision":

```
┌─ 🤖 RL API Status ──────────────────────┐
│ RL API Status:    🤖 Active             │
│ RL Confidence:    85.3%                 │
│ Prediction Time:  14:25:00              │
│ Next Update:      3m 15s                │
└─────────────────────────────────────────┘
```

### Status States

1. **Active** (🤖 Active)
   - RL prediction is current and valid
   - Shows confidence percentage
   - Countdown timer running

2. **Updating** (⏳ Updating...)
   - Brief state when calling RL API
   - Shows "Loading..." for countdown
   - Lasts ~1-2 seconds

3. **Waiting** (No RL API panel shown)
   - Waiting for first 5-minute bar to complete
   - Shows time until next bar

### Auto-Refresh Behavior

When the countdown reaches 0:00:
1. Automatically triggers RL API call
2. Shows "Updating..." briefly
3. Updates with new prediction
4. Resets countdown to 5:00

Example sequence:
```
14:24:58 → Next Update: 0m 02s
14:24:59 → Next Update: 0m 01s
14:25:00 → Next Update: Loading... (⏳ Updating...)
14:25:01 → Next Update: 4m 59s (New prediction!)
```

### Decision Changes

The recommendation can change with each 5-minute update:
- **14:25:00**: SELL CALL (85.3% confidence)
- **14:30:00**: SELL PUT (72.1% confidence)
- **14:35:00**: HOLD (91.2% confidence)

## Configuration Options

### Command Line Arguments
- `--enable-rl`: Enable RL API integration
- `--rl-api-url URL`: Custom RL API endpoint (default: http://localhost:8100/predict)
- `--local-theta`: Use local Theta Terminal
- `--update-rate SECONDS`: Dashboard refresh rate (default: 1.0)

### Session Statistics
When you exit (Ctrl+C), you'll see:
```
Session Summary
============================================================
Total Updates: 1,247
Duration: 0:20:47
Suggestions Made: 3

RL API Statistics:
  RL API Calls: 4
  RL API Errors: 0
  Success Rate: 100.0%
============================================================
```

## Troubleshooting

### "RL API request failed"
- Check RL API server is running on port 8100
- Verify network connectivity
- Check API server logs

### No RL predictions showing
- Ensure `--enable-rl` flag is used
- Wait for first 5-minute bar to complete
- Check market hours (predictions only during trading hours)

### Countdown stuck
- RL API call may have failed
- Check console for error messages
- Predictions will retry on next 5-minute boundary

## Architecture Notes

### Non-blocking Design
- RL API calls run in background tasks
- UI remains responsive during API calls
- Async HTTP client for efficient networking

### Caching Strategy
- Predictions cached for exactly 5 minutes
- No redundant API calls
- Graceful fallback to local model if API fails

### Time Synchronization
- 5-minute bars align with clock: :00, :05, :10, etc.
- Consistent with RL model training data
- Automatic boundary detection

## Next Steps
1. Add trade execution based on RL recommendations
2. Implement user feedback collection
3. Add performance tracking for RL vs local model
4. Create alert system for high-confidence predictions