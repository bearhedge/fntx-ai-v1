# Setup Scripts

One-time setup scripts for initial system configuration.

## Scripts

### setup-vnc-trading.sh
Installs and configures VNC desktop environment for IB Gateway trading.

**What it does:**
- Installs VNC server and XFCE desktop
- Downloads and installs IB Gateway
- Configures systemd service for auto-start
- Sets up VNC password and security

**Usage:**
```bash
./setup-vnc-trading.sh
```

### setup_trading_environment.sh
Sets up the ThetaTerminal data service environment.

**What it does:**
- Creates necessary directories
- Downloads ThetaTerminal.jar if not present
- Configures environment for data collection

**Usage:**
```bash
./setup_trading_environment.sh
```

### setup_nav_reconciliation.sh
Configures NAV (Net Asset Value) reconciliation with IBKR.

**What it does:**
- Sets up database tables for NAV tracking
- Configures IBKR Flex Query integration
- Imports historical NAV data
- Sets up daily import schedule

**Usage:**
```bash
./setup_nav_reconciliation.sh
```

### download-theta.sh
Helper script with instructions for downloading ThetaTerminal.jar.

**What it does:**
- Provides multiple methods to download ThetaTerminal
- Shows gcloud, curl, VNC, and HTTP server options
- No actual downloads - just instructions

**Usage:**
```bash
./download-theta.sh
```

## Setup Order

For a new system, run scripts in this order:
1. `setup-vnc-trading.sh` (if using IB Gateway)
2. `setup_trading_environment.sh` (for ThetaTerminal)
3. `setup_nav_reconciliation.sh` (for portfolio tracking)

## Notes

- These scripts modify system configuration and install software
- Run with appropriate permissions
- Check logs if any step fails
- Most scripts are idempotent (safe to run multiple times)