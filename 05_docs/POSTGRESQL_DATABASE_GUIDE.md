# PostgreSQL Database Guide for SPY Options Trading System

## Overview

This system uses **2 main databases**:

1. **fntx_trading** - The primary database containing:
   - Historical SPY options data for training (in various schemas)
   - AI memory system (in `ai_memory` schema)
   - Trade ledger and financial data
   
2. **options_data** - Legacy database with minimal data (827 rows in extract tables - can be ignored)

## Connecting to PostgreSQL

### Basic Connection

```bash
# Connect to PostgreSQL as default user
psql -U postgres

# Connect to a specific database
psql -U postgres -d fntx_trading     # Main database
psql -U postgres -d options_data     # Legacy (ignore)
```

### Common PostgreSQL Commands

```sql
-- List all databases
\l

-- Connect to a database
\c database_name

-- List all schemas in current database
\dn

-- List all tables in current schema
\dt

-- List all tables in a specific schema
\dt schema_name.*

-- Describe a table structure
\d table_name
\d schema_name.table_name

-- Exit psql
\q
```

## Database 1: fntx_trading (Main Database)

This is the primary database containing everything:

### Historical Market Data
The training data is stored in various schemas within fntx_trading (not in a separate database).

```sql
-- Connect to the database
\c fntx_trading

-- View all schemas
\dn

-- You'll see schemas like:
-- financial, ml, trading, portfolio, ai_memory, etc.
```

### Sample Market Data Queries

```sql
-- The exact table names depend on which schema has the options data
-- Check each schema for options-related tables:
\dt financial.*
\dt ml.*
\dt trading.*
```

This database has two main purposes:
1. Trade accounting/audit trail (existing tables)
2. AI memory system (ai_memory schema)

### Connect and View Structure

```sql
-- Connect to the database
\c fntx_trading

-- List all schemas
\dn

-- You should see:
-- public     (trade ledger tables)
-- ai_memory  (AI decision memory)
```

### AI Memory Schema Tables

```sql
-- Switch to ai_memory schema
SET search_path TO ai_memory;

-- List all AI memory tables
\dt

-- Or view from any schema
\dt ai_memory.*
```

#### AI Memory Tables:

1. **decisions** - Every AI suggestion made
```sql
-- View table structure
\d ai_memory.decisions

-- Recent AI decisions
SELECT 
    decision_id,
    timestamp,
    suggested_action,
    confidence,
    reasoning,
    was_executed,
    user_feedback
FROM ai_memory.decisions
ORDER BY timestamp DESC
LIMIT 10;

-- Count decisions by action type
SELECT 
    suggested_action,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence
FROM ai_memory.decisions
GROUP BY suggested_action;
```

2. **user_feedback** - Your responses to AI suggestions
```sql
-- View feedback structure
\d ai_memory.user_feedback

-- Recent feedback
SELECT 
    f.timestamp,
    f.action_taken,
    f.feedback_text,
    d.suggested_action,
    d.reasoning
FROM ai_memory.user_feedback f
JOIN ai_memory.decisions d ON f.decision_id = d.decision_id
ORDER BY f.timestamp DESC
LIMIT 10;

-- Acceptance rate
SELECT 
    COUNT(CASE WHEN action_taken = 'accepted' THEN 1 END)::float / 
    COUNT(*) * 100 as acceptance_rate
FROM ai_memory.user_feedback;
```

3. **learned_preferences** - AI's learned patterns
```sql
-- View preferences
\d ai_memory.learned_preferences

-- Current preferences
SELECT * FROM ai_memory.learned_preferences
WHERE is_active = true
ORDER BY confidence DESC;
```

4. **trade_outcomes** - Results of executed trades
```sql
-- View trade outcomes
\d ai_memory.trade_outcomes

-- Recent trade results
SELECT 
    trade_id,
    decision_id,
    entry_time,
    exit_time,
    pnl,
    pnl_percentage,
    exit_reason
FROM ai_memory.trade_outcomes
ORDER BY exit_time DESC
LIMIT 10;

-- Performance summary
SELECT 
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(pnl) as total_pnl,
    AVG(pnl) as avg_pnl,
    MAX(pnl) as best_trade,
    MIN(pnl) as worst_trade
FROM ai_memory.trade_outcomes;
```

5. **session_context** - Trading session information
```sql
-- View sessions
SELECT * FROM ai_memory.session_context
ORDER BY session_start DESC;
```

6. **adapter_weights** - Neural network adaptation weights
```sql
-- View latest adapter weights
SELECT 
    timestamp,
    layer_name,
    array_length(weights, 1) as num_weights,
    version
FROM ai_memory.adapter_weights
ORDER BY timestamp DESC;
```

### Trade Ledger Tables (public schema)

```sql
-- Switch back to public schema
SET search_path TO public;

-- View trade ledger tables
\dt

-- Example: View recent trades (if table exists)
SELECT * FROM trades
ORDER BY timestamp DESC
LIMIT 10;
```

## Database 2: options_data (Historical Theta Terminal Data)

This database contains the historical SPY options data downloaded from Theta Terminal - your training data!

```sql
-- Connect with password
PGPASSWORD=theta_data_2024 psql -h localhost -U postgres -d options_data

-- View schemas
\dn
-- Shows: public, theta, portfolio

-- View theta schema tables
\dt theta.*

-- Main tables:
-- theta.options_contracts (20,710 contracts)
-- theta.options_ohlc (1.4M timesteps)
-- theta.options_greeks
-- theta.options_iv
```

### Key Queries for Historical Data

```sql
-- Check data range
SELECT 
    MIN(datetime) as earliest,
    MAX(datetime) as latest,
    COUNT(*) as total_records
FROM theta.options_ohlc;

-- View contracts by expiration
SELECT 
    expiration,
    COUNT(*) as num_contracts
FROM theta.options_contracts
WHERE symbol = 'SPY'
GROUP BY expiration
ORDER BY expiration DESC
LIMIT 10;

-- Sample option data
SELECT 
    c.symbol, c.expiration, c.strike, c.option_type,
    o.datetime, o.open, o.high, o.low, o.close, o.volume
FROM theta.options_ohlc o
JOIN theta.options_contracts c ON o.contract_id = c.contract_id
WHERE c.symbol = 'SPY'
    AND c.expiration = CURRENT_DATE
ORDER BY o.datetime DESC
LIMIT 10;
```

## Useful Analysis Queries

### 1. AI Learning Progress
```sql
-- Connect to fntx_trading
\c fntx_trading

-- How AI's suggestions change over time
WITH weekly_stats AS (
    SELECT 
        DATE_TRUNC('week', d.timestamp) as week,
        d.suggested_action,
        COUNT(*) as suggestions,
        SUM(CASE WHEN f.action_taken = 'accepted' THEN 1 ELSE 0 END) as accepted
    FROM ai_memory.decisions d
    LEFT JOIN ai_memory.user_feedback f ON d.decision_id = f.decision_id
    GROUP BY week, suggested_action
)
SELECT 
    week,
    suggested_action,
    suggestions,
    accepted,
    ROUND(accepted::numeric / suggestions * 100, 2) as acceptance_rate
FROM weekly_stats
ORDER BY week DESC, suggested_action;
```

### 2. Memory Impact on Decisions
```sql
-- How memory features affect AI suggestions
SELECT 
    memory_features[1] as last_trade_outcome,
    memory_features[2] as recent_acceptance_rate,
    suggested_action,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence
FROM ai_memory.decisions
WHERE memory_features IS NOT NULL
GROUP BY memory_features[1], memory_features[2], suggested_action
ORDER BY count DESC;
```

### 3. Trading Performance by Hour
```sql
-- Best times for trading based on outcomes
SELECT 
    EXTRACT(HOUR FROM entry_time) as trading_hour,
    COUNT(*) as trades,
    AVG(pnl) as avg_pnl,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END)::float / COUNT(*) * 100 as win_rate
FROM ai_memory.trade_outcomes
GROUP BY trading_hour
ORDER BY trading_hour;
```

## Database Maintenance

### Check Database Sizes
```sql
-- Overall database sizes
SELECT 
    datname as database,
    pg_size_pretty(pg_database_size(datname)) as size
FROM pg_database
WHERE datname IN ('fntx_trading', 'options_data')
ORDER BY pg_database_size(datname) DESC;

-- Table sizes in current database
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Backup Commands
```bash
# Backup specific database
pg_dump -U postgres fntx_trading > fntx_trading_backup.sql
pg_dump -U postgres options_data > options_data_backup.sql  # Not needed

# Backup only AI memory schema
pg_dump -U postgres -n ai_memory fntx_trading > ai_memory_backup.sql

# Restore from backup
psql -U postgres database_name < backup_file.sql
```

## Python Access Example

```python
import psycopg2
import pandas as pd

# Connect to database
conn = psycopg2.connect(
    host="localhost",
    database="fntx_trading",
    user="postgres",
    password="your_password"
)

# Query AI decisions
query = """
SELECT 
    timestamp,
    features,
    memory_features,
    suggested_action,
    confidence,
    reasoning
FROM ai_memory.decisions
WHERE timestamp >= CURRENT_DATE
ORDER BY timestamp DESC
"""

# Load into pandas
df = pd.read_sql(query, conn)
print(df.head())

# Close connection
conn.close()
```

## Quick Reference Card

```bash
# Connect to databases
psql -U postgres -d fntx_trading     # Main database (historical data + AI memory + trades)
psql -U postgres -d options_data     # Legacy (ignore)

# Once connected:
\l                    # List databases
\c database_name      # Switch database
\dn                   # List schemas
\dt                   # List tables in current schema
\dt ai_memory.*       # List tables in specific schema
\d table_name         # Describe table
\q                    # Quit

# View AI memory tables
\c fntx_trading
\dt ai_memory.*

# Common queries
SELECT * FROM ai_memory.decisions ORDER BY timestamp DESC LIMIT 10;
SELECT * FROM ai_memory.user_feedback ORDER BY timestamp DESC LIMIT 10;
SELECT * FROM ai_memory.trade_outcomes ORDER BY exit_time DESC LIMIT 10;
```

---
*Created: January 5, 2025*
*System: SPY Options AI Trading System with Persistent Memory*