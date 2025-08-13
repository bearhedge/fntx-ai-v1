# ALM Capital Auto-Refresh Implementation

## Date: 2025-07-31

## Overview
Implemented automatic capital refresh functionality in the trading terminal dashboard to display the latest NAV (Net Asset Value) from the ALM database after 12 PM HKT daily.

## Components Created

### 1. ALM NAV Service (`backend/services/alm_nav_service.py`)
A new service that connects to the PostgreSQL database and fetches the latest NAV data from the `alm_reporting.daily_summary` table.

**Key Features:**
- Singleton pattern for efficient database connection management
- 5-minute caching to avoid excessive database queries
- Automatic refresh detection (after 12 PM HKT)
- Staleness checking (alerts if NAV data is more than 24 hours old)
- Error handling and logging

**Main Functions:**
- `get_latest_nav()`: Returns full NAV data including date, P&L, and cash flows
- `get_latest_capital()`: Convenience function that returns just the closing NAV amount
- `should_auto_refresh()`: Returns True if current time is after 12 PM HKT
- `is_nav_stale()`: Checks if NAV data needs updating

### 2. Dashboard Integration (`rl-trading/spy_options/terminal_ui/dashboard.py`)
Updated the trading dashboard to automatically refresh capital from the ALM database.

**Changes Made:**
- Added import for ALM NAV service with error handling
- Added `_refresh_capital_from_alm()` method to fetch latest capital
- Added automatic refresh on dashboard startup
- Added periodic refresh check every 5 minutes in the main update loop
- Capital source is now displayed (e.g., "ALM Database" vs "Default")

**Auto-Refresh Logic:**
- Checks every 5 minutes if conditions are met
- Only refreshes after 12 PM HKT (when ALM daily update has run)
- Updates both capital amount and source display
- Logs all refresh activities

## Testing

### Test Results:
- ✅ ALM NAV service successfully connects to database
- ✅ Latest NAV retrieved: 195,929.84 HKD (2025-07-30)
- ✅ Auto-refresh detection working (correctly identifies time after 12 PM HKT)
- ✅ Staleness checking operational
- ✅ Service integrated into dashboard initialization
- ✅ Periodic refresh logic added to main update loop

### Test Files Created:
- `backend/services/test_capital_refresh.py` - Comprehensive test suite
- `backend/services/test_alm_nav_simple.py` - Simple verification test

## Usage

The capital auto-refresh is now automatic and requires no user intervention:

1. **On Dashboard Start**: The system checks if it's after 12 PM HKT and fetches the latest NAV
2. **During Operation**: Every 5 minutes, the system checks if conditions are met and refreshes
3. **Display**: The header shows capital amount and source (e.g., "Capital: 195,929 HKD (ALM Database)")

## Benefits

1. **Accuracy**: Always displays the latest reconciled NAV from ALM calculations
2. **Automation**: No manual updates needed after daily ALM processing
3. **Transparency**: Shows the source of capital data
4. **Efficiency**: Caching prevents excessive database queries
5. **Reliability**: Error handling ensures dashboard continues working even if database is unavailable

## Technical Details

### Database Query:
```sql
SELECT 
    summary_date,
    closing_nav_hkd,
    opening_nav_hkd,
    total_pnl_hkd,
    net_cash_flow_hkd
FROM alm_reporting.daily_summary
WHERE closing_nav_hkd IS NOT NULL
ORDER BY summary_date DESC
LIMIT 1
```

### Connection Details:
- Database: `options_data`
- Table: `alm_reporting.daily_summary`
- User: `postgres`
- Host: `localhost`

### Timing:
- Auto-refresh enabled: After 12:00 PM HKT
- Refresh interval: Every 5 minutes
- Cache duration: 5 minutes

## Future Enhancements

1. Add configuration for refresh interval
2. Send notifications when capital changes significantly
3. Add historical NAV trend display
4. Implement fallback to previous day's NAV if current day not available
5. Add manual refresh button in UI

## Related Files
- `/home/info/fntx-ai-v1/backend/services/alm_nav_service.py` - ALM NAV service
- `/home/info/fntx-ai-v1/rl-trading/spy_options/terminal_ui/dashboard.py` - Updated dashboard
- `/home/info/fntx-ai-v1/backend/alm/alm_automation.py` - ALM daily update process
- `/home/info/fntx-ai-v1/backend/alm/calculation_engine_v1.py` - ALM calculation engine