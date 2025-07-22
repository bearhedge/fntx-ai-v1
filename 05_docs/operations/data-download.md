# ThetaTerminal Data Download Instructions

## Current Status
The download is now running in the background and will continue even if you disconnect.

## Monitor Progress

### 1. Watch Live Logs
```bash
tail -f /home/info/fntx-ai-v1/backend/data/download.log
```

### 2. Run Progress Monitor
```bash
cd /home/info/fntx-ai-v1/backend/data
python3 monitor_download.py
```

### 3. Quick Database Check
```bash
sudo -u postgres psql -d options_data -c "
SELECT COUNT(*) as records, 
       COUNT(DISTINCT contract_id) as contracts,
       pg_size_pretty(pg_database_size('options_data')) as size
FROM theta.options_ohlc;"
```

## Download Details

- **Start Time**: Just started
- **Estimated Duration**: 12-24 hours
- **Data Period**: January 2021 - June 2025
- **Expected Records**: ~52 million
- **Expected Size**: 3-4 GB

## What's Happening

The downloader is:
1. Going through each month from 2021-2025
2. Finding all SPY option expirations (Mon/Wed/Fri)
3. For each expiration, downloading strikes from $370-$470 (2021) up to $550-$650 (2025)
4. Getting 1-minute OHLC data for each contract
5. Storing in PostgreSQL with proper indexing

## If Download Stops

The system automatically resumes from where it left off:
```bash
# Restart if needed
cd /home/info/fntx-ai-v1/backend/data
nohup python3 theta_downloader.py > download.log 2>&1 &
```

## After Download Completes

1. Verify data integrity:
```bash
python3 -c "
from options_ml_dataloader import OptionsMLDataLoader
loader = OptionsMLDataLoader()
df = loader.load_ohlc_data('2021-01-01', '2025-06-30')
print(f'Total records: {len(df):,}')
print(f'Date range: {df.datetime.min()} to {df.datetime.max()}')
"
```

2. Start using for AI:
- See `demo_theta_system.py` for examples
- Use `spy_options_recommender.py` for trading recommendations

## Current Processing Rate

Based on the logs, the system is processing approximately:
- 1.5 contracts per second
- 90 contracts per minute
- 5,400 contracts per hour
- ~130,000 contracts per day

With ~134,000 total contracts to download, this will take approximately 24 hours.