# SPY Options AI System - Complete Architecture Documentation

## Overview

This document describes the complete AI trading system for SPY 0DTE options, including all components, data flows, and how memory/learning works.

## System Components

### 1. Core Directories

```
/home/info/fntx-ai-v1/12_rl_trading/spy_options/
├── models/                     # Trained AI models
│   ├── gpu_trained/           # Models from GPU training
│   ├── production/            # Current production model
│   └── adapter_network.pt     # User preference adapter
├── data_pipeline/             # Real-time data processing
│   ├── theta_connector.py     # Connects to Theta Terminal
│   ├── feature_engine.py      # Converts market data to features
│   └── live_trading_system.py # Orchestrates live trading
├── memory_system/             # AI's memory and learning
│   ├── database_schema.sql    # PostgreSQL schema
│   ├── memory_manager.py      # Stores/retrieves AI memories
│   └── context_encoder.py     # Adds memory to predictions
├── api_server/                # Model serving API
│   ├── main.py               # FastAPI endpoints
│   ├── model_service.py      # Integrates model + memory
│   └── adapter_network.py    # CPU learning layer
├── terminal_ui/              # User interface
│   ├── dashboard.py          # Main terminal display
│   └── run_terminal_ui.py    # Entry point
└── automation/               # Scheduled tasks
    └── scheduled_retraining.py # Weekly model updates
```

### 2. Three Databases

**Historical Market Data (theta_terminal)**
- Purpose: Training data from 2022-2025
- Tables: spy_ohlc, options_ohlc, greeks_minute
- Usage: Read-only for model training

**Trade Ledger (fntx_trading)**
- Purpose: Actual trade records, P&L tracking
- Schema: trading.*
- Usage: Accounting, audit trail

**AI Memory (fntx_ai_memory)**
- Purpose: AI's decisions, user feedback, learning
- Schema: ai_memory.*
- Tables:
  - decisions: Every AI suggestion with context
  - user_feedback: Your responses to suggestions
  - learned_preferences: Patterns AI has learned
  - market_patterns: Recognized market conditions
  - session_memory: Daily trading context

## How the System Works

### Monday Morning Trading Flow

1. **Start Terminal UI**
   ```bash
   python run_terminal_ui.py --mock  # For testing
   python run_terminal_ui.py --theta-key YOUR_KEY  # Live data
   ```

2. **Data Flow**
   - Theta Terminal → Live market data (SPY price, options chain)
   - Feature Engine → Converts to 8 features
   - Memory System → Adds 12 memory features (20 total)
   - Model + Adapter → Makes prediction
   - Terminal UI → Shows suggestion with reasoning

3. **Your Decision**
   - Accept → Recorded in memory, executed if configured
   - Reject → Reason recorded, adapter learns immediately

### Memory Features (12 Additional)

The AI remembers context by adding these to the original 8 features:

1-5. Last 5 trade outcomes (win/loss/neutral)
6. Recent acceptance rate (how often you agree)
7. Same hour win rate (historical performance at this time)
8. P&L trend (improving/declining)
9. Days since similar market setup
10. Session suggestion count
11. Risk tolerance score (based on your feedback)
12. Market regime encoding (trending/choppy)

### Learning Process

**Immediate (CPU - Every Session)**
- Adapter network updates based on your feedback
- Learns patterns like "user avoids morning calls"
- Takes < 1 second after each session

**Weekly (GPU - Automated)**
- Sunday 2 AM: Scheduled retraining runs
- Incorporates week's experiences into base model
- Takes ~3 hours on rented GPU
- Costs ~$20/month

## Running the Complete System

### 1. Create Memory Database
```bash
createdb -U info fntx_ai_memory
psql -U info -d fntx_ai_memory -f memory_system/database_schema.sql
```

### 2. Start API Server
```bash
cd api_server
./run_api_server.sh
# Runs on http://localhost:8100
```

### 3. Run Terminal UI
```bash
python run_terminal_ui.py --mock
# Shows live options chain + AI decisions
```

### 4. Schedule Weekly Retraining
```bash
# Add to crontab
0 2 * * 0 /home/info/fntx-ai-v1/12_rl_trading/spy_options/automation/scheduled_retraining.py
```

## API Endpoints

**GET http://localhost:8100/**
- Status and statistics

**POST http://localhost:8100/predict**
```json
{
  "features": [0.25, 0.628, 0.16, 0, 0, 0, 0.3, 0.75],
  "market_data": {"spy_price": 628.50, "vix": 15.2}
}
```

**POST http://localhost:8100/feedback**
```json
{
  "decision_id": "uuid-here",
  "accepted": false,
  "rejection_reason": "strike_too_high",
  "user_comment": "Prefer closer strikes"
}
```

## How Memory Prevents "Amnesia"

**Without Memory (Current)**
- Monday: AI suggests PUT 628 → You accept
- Tuesday: AI has no memory of Monday

**With Memory (New System)**
- Monday: AI suggests PUT 628 → You accept → Saved to memory
- Tuesday: AI thinks "Similar setup yesterday, user accepted PUT, it worked"
- Suggestion influenced by Monday's success

## Cost Structure

- API Server: $0 (runs on your existing VM)
- Database: $0 (uses your 1TB storage)
- Weekly GPU: ~$20/month (3 hours × 4 weeks)
- **Total: $20/month**

## File Purposes

**memory_system/**
- `database_schema.sql`: Creates all memory tables
- `memory_manager.py`: Saves/retrieves AI memories
- `context_encoder.py`: Converts memories to features

**api_server/**
- `main.py`: REST API for predictions
- `model_service.py`: Combines model + memory + adapter
- `adapter_network.py`: Learns your preferences on CPU
- `run_api_server.sh`: Startup script

**automation/**
- `scheduled_retraining.py`: Runs every Sunday 2 AM
- Exports week's data → Rents GPU → Retrains → Updates model

## Troubleshooting

**"No memory features"**
- Check database connection
- Ensure memory_manager initialized

**"Adapter not learning"**
- Check feedback is being recorded
- Verify adapter network loaded

**"Model not updating"**
- Check cron job running
- Review logs in automation/logs/

## Next Steps

1. **IB Gateway Integration**
   - Add execution layer for approved trades
   - Currently manual execution only

2. **Enhanced Learning**
   - Add outcome tracking (actual P&L)
   - Learn from position results, not just acceptance

3. **Multi-Strategy**
   - Train separate models for different market regimes
   - Switch based on detected conditions