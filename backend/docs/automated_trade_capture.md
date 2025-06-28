# Automated Trade Capture System

## Overview
This system provides comprehensive trade capture functionality that automatically logs ALL trades executed through FNTX AI, whether initiated via:
- UI chatbot
- Manual trade buttons
- Automated orchestrator
- Direct API calls

## Key Components

### 1. IBKR Flex Query Integration (`ibkr_flex_query.py`)
- Retrieves complete historical trade data from IBKR
- Solves the API limitation of only showing closing trades
- Matches opening and closing trades to calculate accurate P&L
- Supports both on-demand and scheduled imports

### 2. Trade Import Scripts
- `import_flex_trades.py`: Automated import via Flex Query API
- `import_trades_csv.py`: Manual CSV file import
- Both scripts prevent duplicates and validate data

### 3. Integrated Trade Capture (`integrated_trade_capture.py`)
- Real-time capture of trades as they're executed
- Links stop loss and take profit orders
- Tracks trade lifecycle from entry to exit

### 4. Enhanced Database Schema
- Added Flex Query tracking fields
- Import history tables
- Performance views for analytics

### 5. API Endpoints (`trade_import_api.py`)
- `/api/trades/import/flex` - Trigger Flex Query import
- `/api/trades/import/csv` - Upload CSV files
- `/api/trades/import/status/{id}` - Check import status
- `/api/trades/import/history` - View import history

## How It Works

### Real-Time Trade Capture
1. When a trade is placed through any system component:
   - ExecutorAgent places the order with IBKR
   - Trade capture hook is triggered
   - Trade details are immediately logged to database
   - Stop loss and take profit orders are linked

2. When a trade is closed:
   - Exit details are captured
   - P&L is automatically calculated
   - Trade status is updated to 'closed'

### Historical Trade Import
1. **Via Flex Query API**:
   ```bash
   # Import last 30 days
   curl -X POST http://localhost:8000/api/trades/import/flex \
     -H "Content-Type: application/json" \
     -d '{"days_back": 30}'
   ```

2. **Via CSV Upload**:
   ```bash
   # Upload CSV file
   curl -X POST http://localhost:8000/api/trades/import/csv \
     -F "file=@trades.csv"
   ```

## Setup Requirements

### 1. Database Migration
```bash
# Run the Flex Query schema update
psql -U info -d fntx_trading -f database/flex_query_update.sql
```

### 2. Environment Variables
```bash
# Add to .env file
IBKR_FLEX_TOKEN=your_flex_token
IBKR_FLEX_QUERY_ID=your_query_id
```

### 3. IBKR Configuration
- Create Flex Query in IBKR Account Management
- Include Trade Confirmations with all fields
- Get Flex Web Service token

## Integration Points

### 1. ExecutorAgent Enhancement
The `ExecutorAgentWithCapture` extends the base ExecutorAgent to automatically capture all trades:

```python
# Use the enhanced executor in orchestrator
from backend.agents.executor_with_capture import get_executor_with_capture

executor = get_executor_with_capture()
```

### 2. Trade Logger Service
The standalone `IBKRTradeLogger` can run as a separate service for 24/7 capture:

```python
# Enable in main API server
app.state.trade_logger = IBKRTradeLogger(db_config, websocket_manager=manager)
asyncio.create_task(app.state.trade_logger.start())
```

## Benefits

1. **Complete Trade History**: No more missing opening trades
2. **Accurate P&L**: Includes all commissions and fees
3. **Automated Capture**: No manual entry required
4. **Multiple Import Methods**: API, CSV, or real-time
5. **Audit Trail**: Full history of all trades with timestamps
6. **Performance Analytics**: Built-in views for win rate, P&L, etc.

## Usage Examples

### Check Recent Trades
```sql
-- View complete trades with P&L
SELECT * FROM trading.complete_trades 
ORDER BY entry_time DESC 
LIMIT 10;

-- Check performance metrics
SELECT * FROM trading.performance_metrics;
```

### Monitor Open Positions
```sql
-- View current open positions
SELECT * FROM trading.trades 
WHERE status = 'open' 
ORDER BY entry_time DESC;
```

### Trade Source Analysis
```sql
-- See trade sources breakdown
SELECT * FROM trading.trade_sources;
```

## Troubleshooting

### Missing Trades
1. Check Flex Query configuration includes all required fields
2. Verify date range covers the period needed
3. Check for import errors in logs

### Duplicate Prevention
- System checks `ibkr_exec_id` to prevent duplicates
- Manual CSV imports check by date and strike

### Real-Time Capture Issues
1. Ensure ExecutorAgentWithCapture is used
2. Check database connection settings
3. Verify trade capture hook is initialized

## Future Enhancements

1. **Scheduled Imports**: Daily automatic Flex Query pulls
2. **Trade Analytics**: Advanced performance metrics
3. **Risk Monitoring**: Real-time position tracking
4. **Export Features**: Generate reports for tax purposes
5. **Multi-Account Support**: Handle multiple IBKR accounts