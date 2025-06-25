# ThetaTerminal Options Data System

## Overview
Complete system for downloading, storing, and analyzing 4 years of SPY options data using ThetaTerminal.

## System Architecture

### 1. Database (PostgreSQL)
- **Schema**: Modular design ready for Greeks/IV when Standard subscription activates
- **Tables**:
  - `options_contracts`: Contract metadata
  - `options_ohlc`: Historical OHLC data (currently available)
  - `options_greeks`: Greeks data (ready for July 18+)
  - `options_iv`: Implied volatility (ready for July 18+)
  - `download_status`: Track download progress

### 2. Data Downloader (`backend/data/theta_downloader.py`)
- Downloads historical OHLC data in batches
- Handles rate limiting and retries
- Tracks progress and resumes from interruptions
- Currently downloading ~40-50k records per hour

### 3. ML DataLoader (`backend/data/options_ml_dataloader.py`)
- Loads data efficiently for ML training
- Engineers features from OHLC data
- Calculates moneyness, time decay, volume patterns
- Prepares data for AI model training

### 4. Options Recommender (`backend/models/spy_options_recommender.py`)
- Analyzes historical win rates
- Recommends OTM strikes for selling
- Backtests strategies
- Will integrate Greeks when available

## Storage Requirements
- **4 years of SPY options**: ~3-4 GB
- **With Greeks (future)**: ~5 GB
- **Available space**: 179 GB ✓

## Current Status
- ✅ Database schema created
- ✅ Downloader tested and working
- ✅ ML dataloader functional
- ✅ Basic recommender system ready
- ⏳ Downloading full 4-year dataset (run overnight)
- 🔜 Greeks/IV integration (July 18+)

## Quick Start

### 1. Download Historical Data
```bash
cd /home/info/fntx-ai-v1/backend/data
python3 theta_downloader.py  # Run overnight for full dataset
```

### 2. Check Data Status
```bash
sudo -u postgres psql -d options_data -c "
SELECT COUNT(*) as records, 
       COUNT(DISTINCT contract_id) as contracts,
       MIN(datetime) as earliest,
       MAX(datetime) as latest
FROM theta.options_ohlc;"
```

### 3. Test ML System
```bash
cd /home/info/fntx-ai-v1
python3 demo_theta_system.py
```

### 4. Get Trading Recommendations
```bash
cd /home/info/fntx-ai-v1/backend/models
python3 spy_options_recommender.py
```

## Data Access Levels

### Current (Value Subscription)
- Historical OHLC data ✓
- Volume data ✓
- Open Interest ✓

### Future (Standard Subscription - July 18+)
- Greeks (delta, gamma, theta, vega) 
- Implied Volatility
- Better AI predictions

## AI Integration
The system is designed to:
1. Learn from 4 years of options patterns
2. Identify optimal OTM strikes for selling
3. Predict expiration probabilities
4. Recommend entry/exit timing

When Greeks become available, the AI will also:
- Use delta for precise strike selection
- Monitor gamma for explosion risk
- Track theta decay acceleration
- Analyze IV for premium optimization

## Database Credentials
- Host: localhost
- Database: options_data
- User: postgres
- Password: theta_data_2024

## Next Steps
1. Let the downloader run overnight to get full dataset
2. Train ML models on historical patterns
3. Integrate with live trading system
4. Add Greeks/IV when subscription upgrades