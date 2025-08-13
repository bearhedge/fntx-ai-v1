# Market Timer Data Aggregation System

## Overview

The Market Timer Data Aggregation System automatically collects scheduled market events from official sources to prevent trading during high-volatility periods. This system focuses on **predictable, scheduled events** that can be known days or weeks in advance.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                              │
├─────────────────┬─────────────────┬─────────────────────────┤
│   FRED API      │  Federal Reserve │   IEX Cloud / Yahoo     │
│ (Economic Data) │  (FOMC Schedule) │  (Earnings Calendar)    │
└────────┬────────┴────────┬────────┴────────┬────────────────┘
         │                 │                 │
         └─────────────────┴─────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Event       │
                    │  Collector   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  PostgreSQL  │
                    │  Database    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Terminal UI │
                    │  Dashboard   │
                    └─────────────┘
```

## Data Sources

### 1. FRED API (Federal Reserve Economic Data)
- **Type**: Official government source
- **Cost**: Free (requires API key)
- **Data**: CPI, NFP, GDP, PCE, PPI, Retail Sales, etc.
- **Update Frequency**: Real-time release schedules
- **Reliability**: 99.9% (official source)
- **Get API Key**: https://fred.stlouisfed.org/docs/api/api_key.html

### 2. Federal Reserve Official Sources
- **Type**: Official government source
- **Cost**: Free (no API key required)
- **Data**: FOMC meetings, Fed speeches, Jackson Hole
- **Sources**:
  - JSON: `https://www.federalreserve.gov/json/ne-fomc.json`
  - RSS: `https://www.federalreserve.gov/feeds/press_all.xml`
- **Reliability**: 99.9% (official source)

### 3. IEX Cloud (Earnings Calendar)
- **Type**: Market data provider
- **Cost**: Free tier available (50,000 messages/month)
- **Data**: Earnings dates for all US stocks
- **Focus**: $1T+ tech companies (AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA)
- **Get Token**: https://iexcloud.io/

### 4. Backup Sources
- **Yahoo Finance**: Web scraping for earnings validation
- **Nasdaq.com**: Official exchange earnings calendar
- **Alpha Vantage**: Alternative earnings API (500 calls/day free)

## Database Schema

### Core Tables

```sql
-- Main events storage
market_events_v2
├── event_date (DATE)
├── event_time (TIME)
├── event_type (VARCHAR) -- 'FOMC', 'CPI', 'NFP', 'EARNINGS'
├── ticker (VARCHAR) -- For earnings events
├── description (TEXT)
├── importance (VARCHAR) -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
└── data_source (VARCHAR)

-- Data source tracking
data_sources
├── source_name
├── source_type -- 'OFFICIAL', 'MARKET_DATA'
├── last_successful_fetch
└── is_active

-- Economic indicators reference
economic_indicators
├── indicator_code -- 'CPI', 'NFP', etc.
├── fred_series_id
└── typical_release_pattern

-- Earnings details
earnings_events
├── symbol
├── company_name
├── market_cap_billions
├── earnings_time -- 'BMO', 'AMC'
└── consensus_eps
```

## Implementation Files

### Directory Structure
```
/home/info/fntx-ai-v1/rl-trading/spy_options/market_timer/
├── enhanced_schema.sql         # Database schema
├── fred_api_client.py         # FRED API integration
├── fed_data_fetcher.py        # Federal Reserve data
├── earnings_fetcher.py        # Earnings calendar
├── collect_events.py          # Main aggregator
├── market_timer_panel_v2.py   # Enhanced UI display
├── setup_cron.sh             # Automation setup
└── logs/                     # Collection logs
```

## Setup Instructions

### 1. Environment Variables
Add to `~/.bashrc` or create `.env` file:
```bash
# Required for database
export DB_HOST='localhost'
export DB_NAME='trading_db'
export DB_USER='trading_user'
export DB_PASSWORD='your_password'

# API Keys (get free keys from providers)
export FRED_API_KEY='your_fred_key'      # https://fred.stlouisfed.org/
export IEX_TOKEN='your_iex_token'        # https://iexcloud.io/
```

### 2. Database Setup
```bash
# Create database and apply schema
psql -U postgres -c "CREATE DATABASE trading_db;"
psql -U postgres -d trading_db -f enhanced_schema.sql
```

### 3. Install Dependencies
```bash
pip install psycopg2-binary requests beautifulsoup4 pytz rich
```

### 4. Test Manual Collection
```bash
cd /home/info/fntx-ai-v1/rl-trading/spy_options/market_timer/
python3 collect_events.py
```

### 5. Setup Automation
```bash
# Run the setup script
./setup_cron.sh

# Verify cron jobs
crontab -l
```

## Usage

### Manual Event Collection
```bash
# Collect events for next 30 days (default)
python3 collect_events.py

# The script will:
# 1. Fetch from all configured sources
# 2. Deduplicate events
# 3. Store in database
# 4. Display summary
```

### View in Terminal UI
```python
# In your trading dashboard
from market_timer_panel_v2 import MarketTimerPanelV2
panel = MarketTimerPanelV2()
# Panel will display events from database
```

### Query Database Directly
```sql
-- Get today's events
SELECT * FROM upcoming_events WHERE timing_bucket = 'TODAY';

-- Get critical events for next week
SELECT * FROM upcoming_events 
WHERE importance = 'CRITICAL' 
AND event_date <= CURRENT_DATE + INTERVAL '7 days';

-- Get earnings for tech giants
SELECT * FROM upcoming_events 
WHERE event_type = 'EARNINGS' 
AND ticker IN ('AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA');
```

## Event Categories & Importance

### Critical Events (Trading Blocked)
- **FOMC Meetings**: 8 per year, 2:00 PM ET announcements
- **Jackson Hole**: Annual Fed symposium (late August)
- **Mega-cap Earnings**: $1T+ companies (AAPL, MSFT, etc.)

### High Impact Events (Caution Required)
- **CPI/Core CPI**: Monthly, 8:30 AM ET (mid-month)
- **NFP (Jobs Report)**: Monthly, 8:30 AM ET (first Friday)
- **GDP**: Quarterly, 8:30 AM ET (end of month)
- **PCE (Fed's preferred inflation)**: Monthly, 8:30 AM ET

### Medium Impact Events
- **PPI**: Producer prices (day after CPI)
- **Retail Sales**: Consumer spending indicator
- **Fed Speeches**: Especially testimony to Congress

## Automation Schedule

### Daily Collection (5 AM ET)
- Fetches all events for next 90 days
- Updates existing events
- Logs to `logs/collect_events.log`

### Weekly Deep Refresh (Sunday 6 AM ET)
- Complete refresh of all data sources
- Validates historical accuracy
- Logs to `logs/weekly_refresh.log`

### Optional: Hourly Updates
- During market hours (9:30 AM - 4:00 PM ET)
- For catching late-breaking schedule changes
- Uncomment in cron to enable

## Data Quality & Validation

### Deduplication
- Events are unique by: (date, time, type, ticker)
- Multiple sources validated against each other
- Conflicts resolved by source priority

### Source Priority
1. FRED API (economic data)
2. Federal Reserve (FOMC dates)
3. IEX Cloud (earnings)
4. Backup sources (validation only)

### Manual Verification
- Monthly spot-checks recommended
- Compare against official calendars
- Add custom events as needed

## Troubleshooting

### No Events Collected
1. Check API keys are set: `echo $FRED_API_KEY`
2. Test database connection: `psql -U trading_user -d trading_db -c "SELECT 1;"`
3. Check logs: `tail -f logs/collect_events.log`
4. Verify network access to APIs

### Missing Specific Events
1. Check data source status: `SELECT * FROM data_sources;`
2. Manually run specific fetcher in Python
3. Verify API limits not exceeded
4. Check event date range (default 90 days)

### Database Errors
1. Ensure schema is applied: `psql -d trading_db -f enhanced_schema.sql`
2. Check permissions: `GRANT ALL ON ALL TABLES IN SCHEMA public TO trading_user;`
3. Verify connection parameters in environment

## Future Enhancements

### Phase 1 (Current)
- ✅ Official scheduled events
- ✅ Automated collection
- ✅ Database storage
- ✅ Terminal UI display

### Phase 2 (Planned)
- Historical impact analysis
- Volatility predictions
- Options flow integration
- International markets

### Phase 3 (Future)
- Machine learning predictions
- Real-time news integration
- Automated trading rules
- Mobile notifications

## Key Benefits

1. **Prevents Volatility Losses**: No more surprises like Fed decisions
2. **100% Automated**: Set and forget with cron jobs
3. **Official Sources**: Reliable, accurate data
4. **Minimal Cost**: Uses free tiers and official APIs
5. **Extensible**: Easy to add new event types

## Support

For issues or questions:
1. Check logs in `market_timer/logs/`
2. Verify all environment variables are set
3. Ensure database schema is current
4. Test each data source individually