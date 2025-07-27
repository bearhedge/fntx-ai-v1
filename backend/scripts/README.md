# Centralized Scripts Directory

All executable scripts for the FNTX AI project are organized here by function.

## Directory Structure

### setup/
One-time setup scripts for initial system configuration:
- `setup-vnc-trading.sh` - Installs VNC server, desktop environment, and IB Gateway
- `setup_trading_environment.sh` - Sets up ThetaTerminal and directory structure
- `setup_nav_reconciliation.sh` - Configures NAV reconciliation with IBKR
- `download-theta.sh` - Helper instructions for downloading ThetaTerminal.jar

### dev/
Development environment management:
- `start-dev.sh` - Starts all development services (frontend, API, agents)
- `stop-dev.sh` - Gracefully stops all development services

### data/
Data management scripts for market data downloads:
- `start_enhanced_download.sh` - Starts SPY options data downloader
- `stop_enhanced_download.sh` - Stops the data downloader
- `status_enhanced_download.sh` - Shows download progress and statistics

### monitoring/
Trading position monitoring and analysis:
- `check_spy_positions.py` - Monitors SPY positions and manages stop losses
- `spy_option_chain.py` - Displays real-time SPY option chains

### trade-logging/
Comprehensive trade history logging and import system:
- `historical_import.py` - Import historical trades from IBKR
- `cleanup_old_trades.py` - Clean up test data
- `import_trades.sh` - Quick IBKR Flex Query import
- Complete documentation in subdirectory README

## Usage

Most scripts are executable and can be run directly:
```bash
./scripts/dev/start-dev.sh
./scripts/monitoring/check_spy_positions.py
```

For Python scripts, ensure the virtual environment is activated:
```bash
source venv/bin/activate
python scripts/monitoring/spy_option_chain.py
```

## Best Practices

1. **Setup scripts** should only be run once during initial configuration
2. **Dev scripts** are for daily development use
3. **Data scripts** manage background data collection services
4. **Monitoring scripts** are run manually as needed
5. Always check script documentation before running

## Adding New Scripts

When adding new scripts:
1. Place in the appropriate category folder
2. Make executable: `chmod +x script.sh`
3. Add documentation header explaining purpose and usage
4. Update this README with the new script