# Data Management Scripts

This directory contains scripts for managing market data downloads and updates.

## Scripts

### start_enhanced_download.sh
Starts the enhanced SPY options data downloader service that runs in the background.
- Downloads historical SPY options data
- Includes OHLC, Greeks, and IV data
- Runs as a background process

### stop_enhanced_download.sh
Stops the running data downloader service gracefully.

### status_enhanced_download.sh
Shows the current status of the data download process:
- Download progress
- Number of contracts processed
- Current expiration being downloaded
- Error count

## Usage

```bash
# Start downloading data
./start_enhanced_download.sh

# Check progress
./status_enhanced_download.sh

# Stop the download
./stop_enhanced_download.sh
```

## Notes

- Data is downloaded from ThetaData service
- Downloads are incremental and can be resumed
- Progress is saved in checkpoint files
- Data is stored in the ML database for analysis