# RL System Configuration Guide

## Overview
This document provides comprehensive configuration instructions for running the FNTX AI RL trading system with IB Gateway and Theta Terminal integration.

## System Components

### 1. VNC Server (for IB Gateway)
- **Status**: Running on port 5901 (VNC display :1)
- **Resolution**: 1920x1080
- **Service**: `vncserver@1.service`
- **Access**: Use VNC viewer to connect to `<server-ip>:5901`

### 2. IB Gateway
- **Purpose**: Execute trades and fetch account data
- **Connection**: Via VNC for GUI interaction
- **API Port**: 7497 (paper trading) or 7496 (live trading)
- **Configuration**:
  - Auto-restart enabled
  - API connections allowed from localhost
  - Read-only API disabled (for trading)

### 3. Theta Terminal
- **Purpose**: Real-time options data streaming
- **Port**: 25510 (local REST API)
- **Endpoint**: `http://localhost:25510`
- **Data Available**:
  - SPY spot price
  - 0DTE options chain
  - Greeks and implied volatility
  - Bid/ask spreads

### 4. RL Model Configuration

#### Memory System Database
- **Database**: `fntx_trading` (PostgreSQL)
- **Schema**: `ai_memory`
- **Tables**:
  - `decisions`: AI trading decisions
  - `user_feedback`: Human feedback on decisions
  - `learned_preferences`: Extracted preferences
  - `feature_memory`: Historical feature vectors

#### API Server
- **Port**: 8100 (FastAPI)
- **Endpoints**:
  - `/predict`: Get AI predictions with reasoning
  - `/feedback`: Submit user feedback
  - `/memory/similar`: Find similar past decisions
- **Location**: `/home/info/fntx-ai-v1/12_rl_trading/spy_options/api_server/`

#### Terminal UI
- **Location**: `/home/info/fntx-ai-v1/12_rl_trading/spy_options/terminal_ui/`
- **Entry Point**: `python run_terminal_ui.py`
- **Features**:
  - Live options chain display
  - Real-time feature calculations
  - AI reasoning transparency
  - Trade suggestion interface

## Starting the System

### 1. Ensure VNC is Running
```bash
sudo systemctl status vncserver@1
# If not running:
sudo systemctl start vncserver@1
```

### 2. Start IB Gateway (via VNC)
1. Connect to VNC: `vncviewer <server-ip>:5901`
2. Launch IB Gateway from desktop
3. Login with credentials
4. Verify API connection on port 7497

### 3. Verify Theta Terminal
```bash
# Check if Theta Terminal is running
curl http://localhost:25510/v2/snapshot/market/status
```

### 4. Start Memory System API
```bash
cd /home/info/fntx-ai-v1/12_rl_trading/spy_options/api_server
python main.py
```

### 5. Launch Terminal UI
```bash
cd /home/info/fntx-ai-v1/12_rl_trading/spy_options/terminal_ui
python run_terminal_ui.py
```

## Environment Variables

Create `.env` file in project root:
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fntx_trading
DB_USER=info

# IB Gateway
IB_HOST=localhost
IB_PORT=7497
IB_CLIENT_ID=1

# Theta Terminal
THETA_HOST=localhost
THETA_PORT=25510

# API Server
API_HOST=0.0.0.0
API_PORT=8100
```

## Automated Tasks

### Daily Trade Import (6 AM EST)
```bash
0 6 * * * /usr/bin/python3 /home/info/fntx-ai-v1/01_backend/scripts/daily_flex_import.py
```

### Weekly Model Retraining (Sunday 2 AM)
```bash
0 2 * * 0 /usr/bin/python3 /home/info/fntx-ai-v1/12_rl_trading/spy_options/automation/scheduled_retraining.py
```

## Data Flow

1. **Market Data**: Theta Terminal → Feature Engineering → AI Model
2. **Trade Execution**: AI Decision → IB Gateway → Market
3. **Learning**: User Feedback → Memory System → Weekly Retraining

## Monitoring

### Check System Health
```bash
# VNC Server
systemctl status vncserver@1

# API Server
curl http://localhost:8100/health

# Theta Terminal
curl http://localhost:25510/v2/snapshot/market/status

# Database
psql -U info -d fntx_trading -c "SELECT COUNT(*) FROM ai_memory.decisions;"
```

### View Logs
```bash
# API Server logs
tail -f /home/info/fntx-ai-v1/12_rl_trading/spy_options/logs/api_server.log

# Retraining logs
tail -f /home/info/fntx-ai-v1/12_rl_trading/spy_options/logs/evolution/latest.log

# Trade import logs
tail -f /home/info/fntx-ai-v1/logs/daily_flex_import.log
```

## Troubleshooting

### VNC Connection Issues
- Ensure firewall allows port 5901
- Check VNC password: `~/.vnc/passwd`
- Restart VNC: `sudo systemctl restart vncserver@1`

### IB Gateway Not Connecting
- Verify API settings in IB Gateway configuration
- Check firewall for port 7497
- Ensure "Enable ActiveX and Socket Clients" is checked

### Theta Terminal Not Responding
- Verify Theta Terminal desktop app is running
- Check REST API is enabled in settings
- Restart Theta Terminal if needed

### Memory System Errors
- Check PostgreSQL is running: `sudo systemctl status postgresql`
- Verify database exists: `psql -U info -d fntx_trading`
- Check schema: `\dn` in psql to list schemas

## Security Notes

- VNC is password protected but consider SSH tunneling for production
- IB Gateway API should only accept localhost connections
- Database uses local trust authentication
- API server should use authentication in production

## Performance Optimization

- Theta Terminal updates throttled to 1Hz for UI readability
- Memory queries use indexed lookups for similar decisions
- Adapter network runs on CPU (no GPU needed)
- Weekly retraining uses GPU for ~3 hours

## Contact & Support

For issues or questions:
- Logs are in `/home/info/fntx-ai-v1/logs/`
- Configuration files in respective component directories
- Database schema in `/home/info/fntx-ai-v1/12_rl_trading/spy_options/memory_system/`