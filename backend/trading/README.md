# FNTX Trading System

## Overview
Unified options trading system with proper data management and reusable components.

## Usage

### Check Current Positions
```bash
make trade-positions
```

### Get Option Price
```bash
make trade-price SYMBOL=SPY STRIKE=600 RIGHT=C
```

### Sell Single Option with Stop Loss
```bash
# Sell SPY 592 Put with 3x stop loss
make trade-sell SYMBOL=SPY STRIKE=592 RIGHT=P STOP=3

# Sell SPY 600 Call with 3x stop loss  
make trade-sell SYMBOL=SPY STRIKE=600 RIGHT=C STOP=3
```

### Sell Strangle (Put + Call)
```bash
# Sell SPY 592P and 600C with 3x stop losses
make trade-strangle SYMBOL=SPY PUT=592 CALL=600 STOP=3
```

## Components

### `options_trader.py`
- Main trading engine
- Handles IB Gateway connections
- Places orders with stop losses
- Manages positions

### `trade_cli.py` 
- Command line interface
- Unified entry point for all trades
- Argument parsing and validation

### `market_data.py`
- Market data fetching (extensible)
- Option chain data
- Price feeds integration

## Benefits Over Ad-hoc Scripts

✅ **Reusable**: One system handles all option trades
✅ **Maintainable**: Organized modules vs scattered scripts  
✅ **Extensible**: Easy to add new strategies
✅ **Testable**: Proper error handling and logging
✅ **Integrated**: Works with existing Makefile commands

## File Structure
```
backend/trading/
├── __init__.py
├── options_trader.py    # Core trading engine
├── trade_cli.py         # CLI interface  
├── market_data.py       # Data providers
└── README.md           # This file
```