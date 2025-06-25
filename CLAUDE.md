# CLAUDE.md - Project Instructions

## CRITICAL RULES
1. DO NOT DO RANDOM THINGS WITHOUT BEING TOLD
2. Only execute what is explicitly requested
3. No proactive code generation unless asked

## Project Context
- Trading 0DTE SPY options (daily expiration)
- Need real-time Greeks from IBKR during market hours
- Need historical expired options data from ThetaData for backtesting
- ThetaData Standard subscription activates July 18th

## Data Sources
- IBKR: Real-time Greeks, live trading data ($65/month)
- ThetaData: Historical expired options, backtesting ($75/month Standard)
- Strategy: Use both - IBKR for live trading, ThetaData quarterly downloads

## Key Files
- `/backend/api/theta_options_endpoint.py` - ThetaData integration
- `/backend/services/ibkr_unified_service.py` - IBKR integration
- `/frontend/src/components/Trading/SPYOptionsTable.tsx` - Options display

## Current Issues
- ThetaData Standard features (Greeks/IV) not available until July 18th billing cycle
- Volume and Open Interest now working (fixed)
- SPY price now showing real data (fixed)