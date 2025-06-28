# Automated Trade Logging System

This system automatically captures and logs all trades executed through Interactive Brokers (IBKR) with zero manual entry required.

## Components

1. **Database Schema** (`/database/trades_schema.sql`)
   - Stores all trade data automatically
   - Calculates P&L automatically
   - Tracks trade lifecycle (open → closed)

2. **IBKR Trade Logger Service** (`/backend/services/ibkr_trade_logger.py`)
   - Connects to IBKR Gateway/TWS
   - Listens for trade events
   - Automatically logs entries, exits, and P&L

3. **API Endpoints** (`/backend/api/main.py`)
   - `/api/trades/history` - Get trade history
   - `/api/trades/performance` - Get performance metrics
   - `/api/trades/active` - Get open trades
   - `/ws/trades` - WebSocket for real-time updates

4. **Frontend History Tab** (`/frontend/src/components/TradesList.tsx`)
   - Displays all trades automatically
   - Real-time updates via WebSocket
   - Shows P&L, status, and exit reasons

## Setup

1. **Create Database Tables**
```bash
psql -U postgres -d fntx_trading -f /home/info/fntx-ai-v1/database/trades_schema.sql
```

2. **Start Trade Logger Service**
```bash
cd /home/info/fntx-ai-v1/backend
python services/start_trade_logger.py
```

3. **Ensure IBKR Gateway is Running**
- The trade logger connects to IBKR on port 4001
- It uses client ID 10 to avoid conflicts

## How It Works

1. **Automatic Capture**: When you execute trades through IBKR, the trade logger automatically captures:
   - Order submissions
   - Executions
   - Commissions
   - Position changes

2. **Entry Logging**: When selling options (entry), it logs:
   - Contract details (strike, type, expiration)
   - Entry price and time
   - Market snapshot at entry

3. **Exit Detection**: When buying back options (exit), it:
   - Matches to the original trade
   - Calculates P&L including commissions
   - Records exit reason (manual, stopped out, etc.)

4. **Real-time Updates**: The frontend receives updates via WebSocket for:
   - New trades
   - Trade closures
   - P&L updates

## No Manual Entry Required

The system is fully automated. You just trade normally through IBKR, and all trades are logged automatically in the Records modal History tab.

## Monitoring

Check the trade logger logs:
```bash
tail -f trade_logger.log
```

## Troubleshooting

1. **No trades showing**: Check IBKR connection and database connection
2. **Missing trades**: Ensure trade logger service is running
3. **WebSocket errors**: Check that frontend is using correct protocol (ws/wss)