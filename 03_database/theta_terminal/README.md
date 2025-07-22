# ThetaTerminal Historical Options Data

This directory contains SQL schemas for historical options data from ThetaTerminal.

## Tables
- `theta.options_ohlc` - Open/High/Low/Close data (215M+ rows)
- `theta.options_greeks` - Greeks calculations 
- `theta.options_iv` - Implied volatility data
- `theta.options_contracts` - Contract specifications

## Data Source
- Provider: ThetaTerminal
- Coverage: 8+ years of SPY options data
- Update frequency: Historical backfill in progress