# Options Data Inspection Guide

This guide provides SQL commands to inspect the downloaded 1-minute options data from Theta Terminal.

## Database Connection Info
```bash
Database: options_data
User: postgres
Password: theta_data_2024
Host: localhost
Port: 5432
```

## 1. View All Contracts for a Specific Day with Moneyness Classification

```sql
-- Example: December 14, 2022
PGPASSWORD='theta_data_2024' psql -U postgres -h localhost -d options_data -c "
WITH spy_price AS (
    SELECT close as spy_close 
    FROM public.spy_prices_raw 
    WHERE date = '2022-12-14'
)
SELECT 
    c.strike,
    c.option_type,
    CASE 
        WHEN c.option_type = 'C' AND c.strike < sp.spy_close - 2 THEN 'ITM'
        WHEN c.option_type = 'C' AND c.strike > sp.spy_close + 2 THEN 'OTM'
        WHEN c.option_type = 'P' AND c.strike > sp.spy_close + 2 THEN 'ITM'
        WHEN c.option_type = 'P' AND c.strike < sp.spy_close - 2 THEN 'OTM'
        ELSE 'ATM'
    END as moneyness,
    COUNT(DISTINCT o.datetime) as data_points,
    MIN(o.low) as day_low,
    MAX(o.high) as day_high,
    AVG(o.close) as avg_price,
    SUM(o.volume) as total_volume
FROM theta.options_contracts c
JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
CROSS JOIN spy_price sp
WHERE c.symbol = 'SPY' 
  AND c.expiration = '2022-12-14'
  AND o.datetime::date = '2022-12-14'
GROUP BY c.strike, c.option_type, sp.spy_close
ORDER BY c.strike, c.option_type;"
```

## 2. Show ATM Contracts with Intraday Price Movement

```sql
PGPASSWORD='theta_data_2024' psql -U postgres -h localhost -d options_data -c "
WITH spy_price AS (
    SELECT close as spy_close FROM public.spy_prices_raw WHERE date = '2022-12-14'
)
SELECT 
    o.datetime::time as time,
    c.strike,
    c.option_type,
    o.open,
    o.high,
    o.low,
    o.close,
    o.volume
FROM theta.options_ohlc o
JOIN theta.options_contracts c ON o.contract_id = c.contract_id
CROSS JOIN spy_price sp
WHERE c.symbol = 'SPY' 
  AND c.expiration = '2022-12-14'
  AND o.datetime::date = '2022-12-14'
  AND c.strike BETWEEN sp.spy_close - 1 AND sp.spy_close + 1
  AND o.datetime::time BETWEEN '09:30:00' AND '10:00:00'
ORDER BY c.strike, c.option_type, o.datetime;"
```

## 3. Summary by Moneyness for a Specific Day

```sql
PGPASSWORD='theta_data_2024' psql -U postgres -h localhost -d options_data -c "
WITH spy_data AS (
    SELECT date, open, high, low, close 
    FROM public.spy_prices_raw 
    WHERE date = '2022-12-14'
),
classified_options AS (
    SELECT 
        c.*,
        o.*,
        CASE 
            WHEN c.option_type = 'C' THEN
                CASE 
                    WHEN c.strike < sd.close - 5 THEN 'Deep ITM'
                    WHEN c.strike < sd.close - 1 THEN 'ITM'
                    WHEN c.strike <= sd.close + 1 THEN 'ATM'
                    WHEN c.strike <= sd.close + 5 THEN 'OTM'
                    ELSE 'Deep OTM'
                END
            ELSE -- Puts
                CASE 
                    WHEN c.strike > sd.close + 5 THEN 'Deep ITM'
                    WHEN c.strike > sd.close + 1 THEN 'ITM'
                    WHEN c.strike >= sd.close - 1 THEN 'ATM'
                    WHEN c.strike >= sd.close - 5 THEN 'OTM'
                    ELSE 'Deep OTM'
                END
        END as moneyness
    FROM theta.options_contracts c
    JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
    CROSS JOIN spy_data sd
    WHERE c.symbol = 'SPY' 
      AND c.expiration = '2022-12-14'
      AND o.datetime::date = '2022-12-14'
)
SELECT 
    moneyness,
    option_type,
    COUNT(DISTINCT strike) as num_strikes,
    SUM(volume) as total_volume,
    AVG(close) as avg_premium
FROM classified_options
GROUP BY moneyness, option_type
ORDER BY 
    CASE moneyness 
        WHEN 'Deep ITM' THEN 1
        WHEN 'ITM' THEN 2
        WHEN 'ATM' THEN 3
        WHEN 'OTM' THEN 4
        WHEN 'Deep OTM' THEN 5
    END,
    option_type;"
```

## 4. Show Specific Strike Prices Throughout the Day

```sql
-- Change strike and option_type as needed
PGPASSWORD='theta_data_2024' psql -U postgres -h localhost -d options_data -c "
SELECT 
    o.datetime,
    o.open,
    o.high,
    o.low,
    o.close,
    o.volume,
    g.delta,
    g.theta,
    g.vega
FROM theta.options_ohlc o
LEFT JOIN theta.options_greeks g ON o.contract_id = g.contract_id AND o.datetime = g.datetime
JOIN theta.options_contracts c ON o.contract_id = c.contract_id
WHERE c.symbol = 'SPY' 
  AND c.strike = 400  -- Change this to any strike
  AND c.option_type = 'C'  -- or 'P' for puts
  AND c.expiration = '2022-12-14'
  AND o.datetime::date = '2022-12-14'
ORDER BY o.datetime;"
```

## 5. Find Most Actively Traded Contracts for a Day

```sql
PGPASSWORD='theta_data_2024' psql -U postgres -h localhost -d options_data -c "
SELECT 
    c.strike,
    c.option_type,
    SUM(o.volume) as total_volume,
    COUNT(*) as trades,
    MIN(o.low) as day_low,
    MAX(o.high) as day_high,
    AVG(o.close) as avg_price
FROM theta.options_contracts c
JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
WHERE c.symbol = 'SPY' 
  AND c.expiration = '2022-12-14'
  AND o.datetime::date = '2022-12-14'
GROUP BY c.strike, c.option_type
HAVING SUM(o.volume) > 0
ORDER BY total_volume DESC
LIMIT 10;"
```

## 6. Show SPY Price for Reference

```sql
PGPASSWORD='theta_data_2024' psql -U postgres -h localhost -d options_data -c "
SELECT date, open, high, low, close, volume
FROM public.spy_prices_raw 
WHERE date BETWEEN '2022-12-12' AND '2022-12-16'
ORDER BY date;"
```

## 7. Automated Daily Analysis Script

Create this script at `/home/info/fntx-ai-v1/backend/data/theta_download/inspect_day.sh`:

```bash
#!/bin/bash
# Usage: ./inspect_day.sh 2022-12-14

DATE=${1:-2022-12-14}
DB_PASS='theta_data_2024'

echo "=== SPY Price on $DATE ==="
PGPASSWORD=$DB_PASS psql -U postgres -h localhost -d options_data -t -c "
SELECT 'SPY: Open=' || open || ', High=' || high || ', Low=' || low || ', Close=' || close
FROM public.spy_prices_raw WHERE date = '$DATE';"

echo -e "\n=== Options Summary by Moneyness ==="
PGPASSWORD=$DB_PASS psql -U postgres -h localhost -d options_data -c "
WITH spy_price AS (
    SELECT close as spy_close FROM public.spy_prices_raw WHERE date = '$DATE'
)
SELECT 
    CASE 
        WHEN c.option_type = 'C' AND c.strike < sp.spy_close - 2 THEN 'ITM Call'
        WHEN c.option_type = 'C' AND c.strike > sp.spy_close + 2 THEN 'OTM Call'
        WHEN c.option_type = 'P' AND c.strike > sp.spy_close + 2 THEN 'ITM Put'
        WHEN c.option_type = 'P' AND c.strike < sp.spy_close - 2 THEN 'OTM Put'
        WHEN c.option_type = 'C' THEN 'ATM Call'
        ELSE 'ATM Put'
    END as type,
    COUNT(DISTINCT c.strike) as strikes,
    SUM(o.volume) as volume,
    ROUND(AVG(o.close)::numeric, 2) as avg_premium
FROM theta.options_contracts c
JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
CROSS JOIN spy_price sp
WHERE c.symbol = 'SPY' 
  AND c.expiration = '$DATE'
  AND o.datetime::date = '$DATE'
GROUP BY 1
ORDER BY 1;"

echo -e "\n=== Most Active Contracts ==="
PGPASSWORD=$DB_PASS psql -U postgres -h localhost -d options_data -c "
SELECT 
    c.strike || c.option_type as contract,
    SUM(o.volume) as volume,
    ROUND(AVG(o.close)::numeric, 2) as avg_price,
    ROUND(MIN(o.low)::numeric, 2) || '-' || ROUND(MAX(o.high)::numeric, 2) as range
FROM theta.options_contracts c
JOIN theta.options_ohlc o ON c.contract_id = o.contract_id
WHERE c.symbol = 'SPY' 
  AND c.expiration = '$DATE'
  AND o.datetime::date = '$DATE'
GROUP BY c.strike, c.option_type
HAVING SUM(o.volume) > 0
ORDER BY volume DESC
LIMIT 10;"
```

Make it executable:
```bash
chmod +x /home/info/fntx-ai-v1/backend/data/theta_download/inspect_day.sh
```

## Usage Examples

1. **Inspect a specific day:**
   ```bash
   ./inspect_day.sh 2022-12-14
   ```

2. **Check ITM options only:**
   ```sql
   -- Modify the WHERE clause to filter by moneyness
   AND c.strike < sp.spy_close - 2  -- for ITM calls
   ```

3. **Look at specific time ranges:**
   ```sql
   -- Add time filter
   AND o.datetime::time BETWEEN '14:00:00' AND '16:00:00'  -- Last 2 hours
   ```

## Key Tables

- `public.spy_prices_raw`: Non-adjusted SPY daily prices
- `theta.options_contracts`: Contract definitions (symbol, strike, expiration, type)
- `theta.options_ohlc`: 1-minute OHLC price data with volume
- `theta.options_greeks`: Greeks data (delta, theta, vega, rho)
- `theta.options_iv`: Implied volatility data

## Moneyness Definitions

- **ITM (In The Money)**:
  - Calls: Strike < SPY price - $2
  - Puts: Strike > SPY price + $2

- **ATM (At The Money)**:
  - Both: Strike within $2 of SPY price

- **OTM (Out of The Money)**:
  - Calls: Strike > SPY price + $2
  - Puts: Strike < SPY price - $2

## Data Quality Notes

1. The data uses non-adjusted SPY prices for accurate strike alignment
2. Only contracts with trading volume are downloaded
3. Greeks data may have 0 values for the first minute (9:30)
4. Buffer of 0.5% is applied to daily SPY range for strike selection