# 0DTE Options Database Analysis Guide

## Table of Contents
1. [Database Schema Overview](#database-schema-overview)
2. [Common Query Patterns](#common-query-patterns)
3. [Analysis Examples](#analysis-examples)
4. [Tips for Non-SQL Users](#tips-for-non-sql-users)
5. [Ready-to-Use Queries](#ready-to-use-queries)
6. [Data Export Guide](#data-export-guide)
7. [Troubleshooting](#troubleshooting)

## Database Schema Overview

The 0DTE options data is stored in PostgreSQL with three main schemas:

### 1. `theta` Schema (Market Data)
This is where all the raw options data from ThetaData lives.

#### Key Tables:
- **`options_contracts`**: The master table for all option contracts
  - `contract_id`: Unique identifier
  - `symbol`: Always 'SPY' for our data
  - `expiration`: Option expiration date
  - `strike`: Strike price (e.g., 450)
  - `option_type`: 'C' for Call, 'P' for Put

- **`options_ohlc`**: Price and volume data (5-minute bars)
  - Links to contract via `contract_id`
  - `datetime`: Timestamp of the bar
  - `open`, `high`, `low`, `close`: Prices
  - `volume`: Number of contracts traded

- **`options_greeks`**: The Greeks (theoretical values)
  - `delta`: Price sensitivity (-1 to 1)
  - `gamma`: Delta change rate
  - `theta`: Time decay (negative)
  - `vega`: IV sensitivity
  - `rho`: Interest rate sensitivity

- **`options_iv`**: Implied Volatility
  - `implied_volatility`: The IV value
  - `is_interpolated`: TRUE if value was filled by LOCF

### 2. `trading` Schema (Trade Execution)
Records of actual trades and performance.

#### Key Tables:
- **`trades`**: Every trade executed
- **`performance_metrics`**: Aggregated statistics

### 3. `financial` Schema (Accounting)
Portfolio management and financial reporting.

## Common Query Patterns

### Connect to Database
```bash
psql -U theta_user -d theta_data
```

### Find Specific Contracts
```sql
-- Find all SPY 450 PUTs for a specific date
SELECT 
    contract_id,
    symbol,
    strike,
    option_type,
    expiration
FROM theta.options_contracts
WHERE symbol = 'SPY'
    AND expiration = '2024-01-03'  -- YYYY-MM-DD format
    AND strike = 450
    AND option_type = 'P';  -- 'C' for Call, 'P' for Put
```

### Get Price Data for a Contract
```sql
-- Get all price data for a specific contract
SELECT 
    o.datetime,
    o.open,
    o.high,
    o.low,
    o.close,
    o.volume
FROM theta.options_ohlc o
JOIN theta.options_contracts c ON o.contract_id = c.contract_id
WHERE c.symbol = 'SPY'
    AND c.expiration = '2024-01-03'
    AND c.strike = 450
    AND c.option_type = 'P'
ORDER BY o.datetime;
```

### Get Complete Market Data (OHLC + Greeks + IV)
```sql
-- Full data for analysis
SELECT 
    o.datetime,
    o.open,
    o.high,
    o.low,
    o.close,
    o.volume,
    g.delta,
    g.gamma,
    g.theta,
    g.vega,
    iv.implied_volatility,
    iv.is_interpolated
FROM theta.options_ohlc o
JOIN theta.options_contracts c ON o.contract_id = c.contract_id
LEFT JOIN theta.options_greeks g ON o.contract_id = g.contract_id 
    AND o.datetime = g.datetime
LEFT JOIN theta.options_iv iv ON o.contract_id = iv.contract_id 
    AND o.datetime = iv.datetime
WHERE c.symbol = 'SPY'
    AND c.expiration = '2024-01-03'
    AND c.strike = 450
    AND c.option_type = 'P'
ORDER BY o.datetime;
```

## Analysis Examples

### 1. Find High Volume Contracts
```sql
-- Top 20 most traded contracts in January 2024
SELECT 
    c.expiration::date as trade_date,
    c.strike,
    c.option_type,
    SUM(o.volume) as total_volume,
    AVG(o.close) as avg_price,
    COUNT(*) as data_points
FROM theta.options_contracts c
JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
WHERE c.expiration >= '2024-01-01' 
    AND c.expiration < '2024-02-01'
GROUP BY c.expiration, c.strike, c.option_type
HAVING SUM(o.volume) > 10000
ORDER BY total_volume DESC
LIMIT 20;
```

### 2. Analyze IV Patterns
```sql
-- Average IV by strike for a specific day
SELECT 
    c.strike,
    c.option_type,
    AVG(iv.implied_volatility) as avg_iv,
    COUNT(iv.implied_volatility) as iv_data_points,
    SUM(CASE WHEN iv.is_interpolated THEN 1 ELSE 0 END) as interpolated_count
FROM theta.options_contracts c
JOIN theta.options_iv iv ON c.contract_id = iv.contract_id
WHERE c.expiration = '2024-01-03'
    AND iv.implied_volatility IS NOT NULL
GROUP BY c.strike, c.option_type
ORDER BY c.strike;
```

### 3. Find ATM Options
```sql
-- Find At-The-Money options based on average delta
SELECT 
    c.expiration::date as trade_date,
    c.strike,
    c.option_type,
    AVG(ABS(g.delta)) as avg_abs_delta,
    AVG(o.volume) as avg_volume
FROM theta.options_contracts c
JOIN theta.options_greeks g ON c.contract_id = g.contract_id
JOIN theta.options_ohlc o ON c.contract_id = o.contract_id 
    AND g.datetime = o.datetime
WHERE c.expiration >= '2024-01-01'
    AND c.expiration < '2024-01-08'
GROUP BY c.expiration, c.strike, c.option_type
HAVING AVG(ABS(g.delta)) BETWEEN 0.45 AND 0.55
ORDER BY trade_date, avg_abs_delta;
```

### 4. Data Quality Check
```sql
-- Check data completeness for a month
SELECT 
    DATE_TRUNC('day', c.expiration) as trade_date,
    COUNT(DISTINCT c.contract_id) as contracts,
    COUNT(DISTINCT o.datetime) as ohlc_bars,
    COUNT(DISTINCT g.datetime) as greek_bars,
    COUNT(DISTINCT iv.datetime) as iv_bars,
    COUNT(iv.implied_volatility) as non_null_ivs,
    ROUND(100.0 * COUNT(iv.implied_volatility) / 
        NULLIF(COUNT(iv.datetime), 0), 2) as iv_coverage_pct
FROM theta.options_contracts c
LEFT JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
LEFT JOIN theta.options_greeks g ON c.contract_id = g.contract_id
LEFT JOIN theta.options_iv iv ON c.contract_id = iv.contract_id
WHERE c.expiration >= '2024-01-01' 
    AND c.expiration < '2024-02-01'
GROUP BY DATE_TRUNC('day', c.expiration)
ORDER BY trade_date;
```

### 5. Trading Performance Analysis
```sql
-- Get daily P&L summary
SELECT 
    trade_date,
    total_realized_pnl,
    total_trades,
    win_rate,
    avg_profit_per_trade
FROM trading.daily_performance
WHERE trade_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY trade_date DESC;

-- Analyze by strike
SELECT * FROM trading.strike_analysis LIMIT 20;

-- Analyze by entry hour
SELECT * FROM trading.time_analysis ORDER BY entry_hour;
```

## Tips for Non-SQL Users

### 1. Use a GUI Tool
- **DBeaver**: Free, cross-platform database tool
- **pgAdmin**: Official PostgreSQL admin tool
- **TablePlus**: Modern, user-friendly interface

### 2. Python Alternative
```python
import pandas as pd
import psycopg2

# Connect to database
conn = psycopg2.connect(
    host="localhost",
    database="theta_data",
    user="theta_user",
    password="your_password"
)

# Load data into pandas
query = """
SELECT * FROM theta.options_contracts 
WHERE expiration = '2024-01-03'
"""
df = pd.read_sql(query, conn)

# Now work with df using pandas
print(df.head())
```

### 3. Export to Excel
```python
# Export query results to Excel
df.to_excel('options_data.xlsx', index=False)
```

## Ready-to-Use Queries

### Query 1: Daily Summary Report
```sql
-- Complete daily summary for all contracts
WITH daily_summary AS (
    SELECT 
        c.expiration::date as trade_date,
        c.strike,
        c.option_type,
        MIN(o.datetime) as first_bar,
        MAX(o.datetime) as last_bar,
        COUNT(DISTINCT o.datetime) as total_bars,
        SUM(o.volume) as total_volume,
        MIN(o.low) as day_low,
        MAX(o.high) as day_high,
        FIRST_VALUE(o.open) OVER (PARTITION BY c.contract_id ORDER BY o.datetime) as opening_price,
        LAST_VALUE(o.close) OVER (PARTITION BY c.contract_id ORDER BY o.datetime 
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as closing_price
    FROM theta.options_contracts c
    JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
    WHERE c.expiration = '2024-01-03'  -- Change this date
    GROUP BY c.contract_id, c.expiration, c.strike, c.option_type, o.open, o.close
)
SELECT * FROM daily_summary
ORDER BY strike, option_type;
```

### Query 2: Find Profitable Setups
```sql
-- Find contracts that expired worthless (good for sellers)
WITH final_prices AS (
    SELECT 
        c.contract_id,
        c.strike,
        c.option_type,
        c.expiration,
        MAX(o.datetime) as final_time,
        LAST_VALUE(o.close) OVER (
            PARTITION BY c.contract_id 
            ORDER BY o.datetime 
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) as final_price
    FROM theta.options_contracts c
    JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
    WHERE c.expiration >= '2024-01-01' 
        AND c.expiration < '2024-02-01'
    GROUP BY c.contract_id, c.strike, c.option_type, c.expiration, o.datetime, o.close
)
SELECT 
    expiration::date as trade_date,
    strike,
    option_type,
    final_price,
    CASE 
        WHEN final_price < 0.05 THEN 'Expired Worthless'
        ELSE 'Had Value'
    END as outcome
FROM final_prices
WHERE final_time = (SELECT MAX(final_time) FROM final_prices f2 WHERE f2.contract_id = final_prices.contract_id)
ORDER BY expiration, strike;
```

### Query 3: Volume Profile Analysis
```sql
-- Analyze volume distribution throughout the day
SELECT 
    EXTRACT(HOUR FROM o.datetime) as hour,
    EXTRACT(MINUTE FROM o.datetime) as minute,
    SUM(o.volume) as total_volume,
    AVG(o.volume) as avg_volume,
    COUNT(*) as data_points
FROM theta.options_ohlc o
JOIN theta.options_contracts c ON o.contract_id = c.contract_id
WHERE c.expiration >= '2024-01-01' 
    AND c.expiration < '2024-01-08'
GROUP BY hour, minute
ORDER BY hour, minute;
```

## Data Export Guide

### Export to CSV
```sql
-- In psql, use \copy command
\copy (
    SELECT c.expiration, c.strike, c.option_type, o.datetime, o.close, o.volume
    FROM theta.options_contracts c
    JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
    WHERE c.expiration = '2024-01-03'
) TO '/tmp/options_data.csv' WITH CSV HEADER;
```

### Export Large Datasets
```bash
# Use pg_dump for large exports
pg_dump -U theta_user -d theta_data \
    -t theta.options_contracts \
    -t theta.options_ohlc \
    --data-only \
    --column-inserts \
    > options_backup.sql
```

## Troubleshooting

### Common Issues

1. **"No data returned"**
   - Check date format: Use 'YYYY-MM-DD'
   - Verify the date is a trading day
   - Ensure data has been downloaded for that date

2. **"Query is slow"**
   - Add indexes on frequently queried columns
   - Use EXPLAIN ANALYZE to check query plan
   - Consider creating materialized views

3. **"NULL values in IV"**
   - This is expected for some contracts
   - Use `WHERE iv.implied_volatility IS NOT NULL`
   - Check `is_interpolated` flag for filled values

### Performance Tips
```sql
-- Create useful indexes
CREATE INDEX idx_contracts_expiration ON theta.options_contracts(expiration);
CREATE INDEX idx_ohlc_datetime ON theta.options_ohlc(datetime);
CREATE INDEX idx_ohlc_contract_datetime ON theta.options_ohlc(contract_id, datetime);
```

### Check Database Status
```sql
-- Check how much data is loaded
SELECT 
    MIN(expiration) as earliest_date,
    MAX(expiration) as latest_date,
    COUNT(DISTINCT expiration) as total_days,
    COUNT(*) as total_contracts
FROM theta.options_contracts;

-- Check download progress
SELECT * FROM checkpoints_v2.master_progress_v2;
```

## Need Help?

1. **Check if download is running**: 
   ```bash
   ps aux | grep master_0dte_orchestrator_v2
   ```

2. **View download progress**:
   ```bash
   cat checkpoints_v2/master_progress_v2.json | python -m json.tool | grep -E "(completed_months|total_months)"
   ```

3. **Database connection issues**:
   ```bash
   psql -U theta_user -d theta_data -c "SELECT 1;"
   ```

Remember: The database is live and being updated. You can query while downloads are running!