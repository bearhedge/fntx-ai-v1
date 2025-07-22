# Exercise Detection & Disposal Workflow

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    OPTION EXERCISE WORKFLOW                  │
└─────────────────────────────────────────────────────────────┘

Friday Night (US Market Close)
    │
    ▼
[5:30 AM Saturday HKT] ─── Option Exercise Finalized by OCC
    │                      (Not visible in TWS yet!)
    │
    ▼
[7:00 AM Saturday HKT] ─── Exercise Detection Runs
    │                      ├─ Calls IBKR FlexQuery API
    │                      ├─ Parses XML for exercises
    │                      └─ Saves to database
    │
    ▼
[7:01 AM Saturday HKT] ─── Disposal Script Triggered
    │                      ├─ Reads pending exercises
    │                      ├─ Gets last SPY close price
    │                      ├─ Calculates limit (0.1% below)
    │                      └─ Places extended hours order
    │
    ▼
[7:02 AM Saturday HKT] ─── Order Placed Successfully
    │                      ├─ Good Till 8 PM ET
    │                      ├─ Extended hours enabled
    │                      └─ Database updated
    │
    ▼
[4:00 PM Monday HKT] ───── Pre-Market Opens
    │                      └─ Order can now fill
    │
    ▼
[4:01 PM Monday HKT] ───── Shares Disposed! ✅
    │
    │
[2:00 PM Saturday HKT] ─── Exercise finally visible in TWS
                           (But we already handled it!)
```

## Database State Transitions

```
1. DETECTION PHASE
   ┌────────────────┐
   │   No Record    │ ──── Exercise Detected ───▶ ┌────────────────┐
   └────────────────┘                             │    PENDING     │
                                                  └────────────────┘
                                                          │
2. DISPOSAL PHASE                                        ▼
   ┌────────────────┐                             ┌────────────────┐
   │ ORDER_PLACED   │ ◀─── Order Submitted ────── │    PENDING     │
   └────────────────┘                             └────────────────┘
           │
           ▼
   ┌────────────────┐
   │    FILLED      │ ──── Order Executed ✅
   └────────────────┘
```

## Key Components

### 1. Exercise Detector (`exercise_detector.py`)
```python
# Runs at 7:00 AM HKT
# Looks for these XML indicators:
- Notes containing "Ex", "Assigned", "Exercise"
- Option trades with 0 price (exercise close)
- New 100-share stock positions
```

### 2. Disposal Script (`exercise_disposal_asap.py`)
```python
# Triggered by detector
# Places orders with:
- Extended hours flag: True
- Time in force: GTD (Good Till Date)
- Limit price: Last close - 0.1%
```

### 3. Database Table (`option_exercises`)
```sql
Fields track:
- exercise_date: When option was exercised
- disposal_status: PENDING → ORDER_PLACED → FILLED
- disposal_order_id: IB order reference
- disposal_time: When order was placed
```

## Timing Advantages

| Event | Traditional Method | Our System | Advantage |
|-------|-------------------|------------|-----------|
| Exercise Occurs | Friday Night | Friday Night | - |
| Detection | Saturday 2 PM HKT | Saturday 7 AM HKT | **7 hours earlier** |
| Order Placement | Monday 9:30 PM HKT | Saturday 7 AM HKT | **62.5 hours earlier** |
| Potential Fill | Monday 9:30 PM HKT | Monday 4 PM HKT | **5.5 hours earlier** |

## Why This Matters

1. **Weekend Risk**: Holding assigned shares over weekend = market gap risk
2. **Early Detection**: FlexQuery API shows exercises before TWS UI
3. **Extended Hours**: Access liquidity when others can't trade
4. **Automation**: No manual monitoring required

## Configuration Requirements

```bash
# .env file
IBKR_FLEX_TOKEN=your_token_here
IBKR_FLEX_QUERY_ID=your_query_id_here

# IB Gateway
- Port: 4001
- Client ID: 20 (for disposal orders)

# Database
- PostgreSQL with portfolio schema
- option_exercises table installed
```

## Monitoring

```bash
# Real-time logs
tail -f logs/exercise_detection.log
tail -f logs/exercise_disposal.log

# Check status
python3 scripts/check_exercises.py

# Database query
psql -d fntx_trading -c "SELECT * FROM portfolio.option_exercises ORDER BY exercise_date DESC;"
```