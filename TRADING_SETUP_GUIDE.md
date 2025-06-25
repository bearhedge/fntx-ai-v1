# FNTX.AI Trading Services Setup Guide

This guide covers setting up ThetaTerminal and IBKR for the FNTX.AI trading system.

## Overview

The FNTX.AI system requires two external services for trading:
1. **ThetaTerminal** - For real-time options data
2. **IB Gateway/TWS** - For trade execution

## Quick Start (Recommended)

### Option 1: Using Make Commands (Simplest)

```bash
# One-time setup
make setup-trading

# Daily usage
make start-trading    # Start ThetaTerminal
make start           # Start FNTX services
make stop-trading    # Stop ThetaTerminal
make stop           # Stop FNTX services
```

### Option 2: Using Docker (Most Consistent)

```bash
# Start everything
make docker-up

# View logs
make docker-logs

# Stop everything
make docker-down
```

## Detailed Setup Instructions

### 1. Install Dependencies

```bash
# Install Python dependencies
cd backend
pip3 install -r requirements.txt
```

### 2. ThetaTerminal Setup

#### First Time Setup:
1. Download ThetaTerminal from [thetadata.net](https://thetadata.net)
2. Place `ThetaTerminal.jar` in `~/fntx-trading/thetadata/`
3. Run the setup script: `./setup_trading_environment.sh`

#### Daily Usage:
```bash
# Start ThetaTerminal
make start-trading

# Or manually:
cd ~/fntx-trading/thetadata
java -jar ThetaTerminal.jar
```

ThetaTerminal runs on port 11000 by default.

### 3. IB Gateway Setup

#### Configuration:
1. Download IB Gateway from Interactive Brokers
2. Configure API settings:
   - Enable API connections
   - Set socket port to 4001
   - Disable read-only API
   - Add trusted IP: 127.0.0.1

#### Daily Usage:
1. Start IB Gateway
2. Login with your credentials
3. Ensure API is enabled (green status)

### 4. Verify Connections

Run the test script:
```bash
python3 test_trading_connections.py
```

Expected output:
- ThetaTerminal: ✅ Connected
- IBKR Gateway: ✅ Connected

## Service Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  ThetaTerminal  │────▶│   FNTX Backend   │────▶│   IB Gateway    │
│   (Port 11000)  │     │   (Port 8000)    │     │   (Port 4001)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  FNTX Frontend   │
                        │   (Port 5173)    │
                        └──────────────────┘
```

## Environment Variables

Create a `.env` file in the backend directory:

```env
# IBKR Configuration
IBKR_HOST=localhost
IBKR_PORT=4001
IBKR_CLIENT_ID=1

# ThetaData Configuration  
THETA_HOST=localhost
THETA_PORT=11000

# Other settings...
```

## Troubleshooting

### ThetaTerminal Issues
- **Not connecting**: Ensure Java is installed (`java -version`)
- **Port conflict**: Check if port 11000 is available (`lsof -i :11000`)
- **Data not loading**: Verify your ThetaData subscription is active

### IBKR Issues
- **Connection refused**: Check IB Gateway is running and API is enabled
- **Authentication failed**: Verify API settings allow local connections
- **Orders rejected**: Check account permissions and trading hours

### General Issues
- **Services not starting**: Check logs in `~/fntx-trading/logs/`
- **Dependencies missing**: Run `pip3 install -r backend/requirements.txt`

## Production Deployment

For production environments, consider:

1. **Using systemd services** for auto-restart:
   ```bash
   sudo cp ~/fntx-trading/thetadata/thetadata.service /etc/systemd/system/
   sudo systemctl enable thetadata
   sudo systemctl start thetadata
   ```

2. **Using Docker** for consistency:
   ```bash
   docker-compose up -d
   ```

3. **Setting up monitoring** for service health checks

## Daily Workflow

1. **Morning Setup**:
   ```bash
   make start-trading    # Start ThetaTerminal
   # Start IB Gateway manually
   make start           # Start FNTX services
   ```

2. **During Trading**:
   - Monitor logs: `tail -f logs/*.log`
   - Check service health: `http://localhost:8000/health`

3. **End of Day**:
   ```bash
   make stop           # Stop FNTX services
   make stop-trading   # Stop ThetaTerminal
   # Close IB Gateway manually
   ```

## Support

For issues:
1. Check logs in `logs/` and `~/fntx-trading/logs/`
2. Verify all services are running with correct ports
3. Ensure market data subscriptions are active
4. Check firewall settings for required ports