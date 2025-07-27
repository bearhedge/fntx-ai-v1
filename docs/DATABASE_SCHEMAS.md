# FNTX AI Database Schema Documentation

## Overview

The FNTX AI system uses PostgreSQL with multiple schemas for different functional areas:

1. **theta** - Options market data from ThetaTerminal
2. **trading** - Trade execution and tracking
3. **portfolio** - NAV reconciliation and cash movements
4. **financial** - ALM (Asset Liability Management) system

## Schema Relationships Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FNTX AI Database                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │   theta.*   │     │  trading.*   │     │ portfolio.*  │     │
│  │             │     │              │     │              │     │
│  │ Market Data │────>│ Trade Exec   │────>│ NAV Tracking │     │
│  │             │     │              │     │              │     │
│  └─────────────┘     └──────────────┘     └──────────────┘     │
│         │                    │                     │             │
│         └────────────────────┴─────────────────────┘             │
│                              │                                   │
│                     ┌────────────────┐                          │
│                     │  financial.*   │                          │
│                     │                │                          │
│                     │  ALM System    │                          │
│                     └────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. THETA Schema - Options Market Data

### Purpose
Stores historical options data from ThetaTerminal API including OHLC, Greeks, IV, and open interest.

### Tables

#### theta.options_contracts
Central registry of all SPY option contracts.

| Column | Type | Description |
|--------|------|-------------|
| contract_id | SERIAL | Primary key |
| symbol | VARCHAR(10) | Always 'SPY' |
| expiration | DATE | Option expiration date |
| strike | DECIMAL(10,2) | Strike price |
| option_type | CHAR(1) | 'C' for Call, 'P' for Put |
| created_at | TIMESTAMP | When contract was added |

**Unique constraint**: (symbol, expiration, strike, option_type)

#### theta.options_ohlc
Minute-by-minute price data for options.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| contract_id | INTEGER | FK to options_contracts |
| datetime | TIMESTAMP | Bar timestamp |
| open | DECIMAL(10,4) | Opening price |
| high | DECIMAL(10,4) | High price |
| low | DECIMAL(10,4) | Low price |
| close | DECIMAL(10,4) | Closing price |
| volume | BIGINT | Volume traded |
| trade_count | INTEGER | Number of trades |

**Sample data pattern**:
- ~30,925 unique contracts
- Data from 2017-01-01 to present
- 1-minute bars during market hours

#### theta.options_greeks
Greeks values for risk management.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| contract_id | INTEGER | FK to options_contracts |
| datetime | TIMESTAMP | Calculation time |
| delta | DECIMAL(8,6) | Price sensitivity |
| gamma | DECIMAL(8,6) | Delta sensitivity |
| theta | DECIMAL(10,4) | Time decay |
| vega | DECIMAL(10,4) | Volatility sensitivity |
| rho | DECIMAL(10,4) | Interest rate sensitivity |

**Coverage**: 99.9% of contracts with OHLC data

#### theta.options_iv
Implied volatility data.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| contract_id | INTEGER | FK to options_contracts |
| datetime | TIMESTAMP | Calculation time |
| implied_volatility | DECIMAL(8,6) | IV value |

---

## 2. TRADING Schema - Trade Execution

### Purpose
Tracks all trades executed through IBKR, including entries, exits, and P&L.

### Tables

#### trading.trades
Main trade tracking table.

| Column | Type | Description |
|--------|------|-------------|
| trade_id | UUID | Primary key |
| ibkr_order_id | INTEGER | IBKR order reference |
| symbol | VARCHAR(10) | 'SPY' |
| strike_price | DECIMAL(10,2) | Option strike |
| option_type | VARCHAR(4) | 'PUT' or 'CALL' |
| expiration | DATE | Option expiry |
| quantity | INTEGER | Contracts traded |
| entry_time | TIMESTAMPTZ | Trade entry time |
| entry_price | DECIMAL(10,4) | Entry price |
| exit_time | TIMESTAMPTZ | Trade exit time (null if open) |
| exit_price | DECIMAL(10,4) | Exit price |
| realized_pnl | DECIMAL(10,2) | Calculated P&L |
| status | VARCHAR(10) | 'open' or 'closed' |

**Relationships**: 
- Uses theta.options_contracts data for trade analysis
- Feeds into portfolio.daily_nav_snapshots for P&L

#### trading.executions
Tracks partial fills and execution details.

| Column | Type | Description |
|--------|------|-------------|
| execution_id | UUID | Primary key |
| trade_id | UUID | FK to trades |
| ibkr_exec_id | VARCHAR(50) | IBKR execution ID |
| execution_time | TIMESTAMPTZ | Fill time |
| quantity | INTEGER | Filled quantity |
| price | DECIMAL(10,4) | Fill price |

---

## 3. PORTFOLIO Schema - NAV & Cash Management

### Purpose
Tracks daily NAV, cash movements, and ensures proper reconciliation.

### Tables

#### portfolio.daily_nav_snapshots
Daily portfolio value tracking.

| Column | Type | Description |
|--------|------|-------------|
| snapshot_id | UUID | Primary key |
| snapshot_date | DATE | Trading date |
| opening_nav | DECIMAL(15,2) | Start of day NAV |
| closing_nav | DECIMAL(15,2) | End of day NAV |
| trading_pnl | DECIMAL(15,2) | Daily P&L from trades |
| is_reconciled | BOOLEAN | Reconciliation status |

**Relationships**:
- Aggregates trading.trades P&L
- Links to cash_movements for withdrawals

#### portfolio.cash_movements
Tracks deposits, withdrawals, and fees.

| Column | Type | Description |
|--------|------|-------------|
| movement_id | UUID | Primary key |
| movement_date | DATE | Transaction date |
| movement_type | VARCHAR(20) | DEPOSIT/WITHDRAWAL/FEE |
| amount | DECIMAL(15,2) | Amount (+ for deposits) |
| status | VARCHAR(20) | Transaction status |

---

## 4. FINANCIAL Schema - ALM System

### Purpose
Enterprise-grade double-entry accounting system for comprehensive financial tracking.

### Key Tables

#### financial.chart_of_accounts
Account structure following GAAP principles.

| Account Types |
|--------------|
| Assets (cash, securities) |
| Liabilities (margin debt) |
| Equity (capital, retained earnings) |
| Revenue (trading gains) |
| Expenses (commissions, fees) |

#### financial.journal_entries
Double-entry bookkeeping records.

#### financial.general_ledger
Account balances and transaction history.

---

## Data Flow

1. **Market Data Flow**:
   ```
   ThetaTerminal API → theta.options_* tables
   ```

2. **Trade Execution Flow**:
   ```
   IBKR Execution → trading.trades → portfolio.daily_nav_snapshots
   ```

3. **Financial Reporting Flow**:
   ```
   All transactions → financial.journal_entries → financial.general_ledger
   ```

---

## Key Relationships

1. **Contract Reference**:
   - All options data linked via `contract_id`
   - Consistent contract identification across schemas

2. **Time Series Alignment**:
   - Market data (theta) provides context for trades
   - Trades (trading) impact daily NAV (portfolio)
   - All financial events recorded in ALM (financial)

3. **Reconciliation Points**:
   - Daily NAV must match: opening + P&L + cash movements = closing
   - Trade P&L must match journal entries
   - Cash movements must balance in general ledger