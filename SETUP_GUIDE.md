# FNTX.AI Setup Guide

## Overview

This guide covers the complete setup for FNTX.AI trading system with clear, non-overlapping components.

## Components

### 1. VNC Desktop for IB Gateway
**Purpose**: Visual access to Interactive Brokers Gateway

**Setup** (one-time):
```bash
make vnc-setup
```

**Daily Use**:
- Connect with VNC viewer to `35.194.231.94:5901` (password: `fntx2024`)
- IB Gateway will be available on the desktop
- Configure API settings in IB Gateway

**Management**:
```bash
make vnc-status    # Check if running
make vnc-restart   # Restart if needed
make vnc-logs      # View logs
```

### 2. ThetaTerminal (Optional - Requires Paid Subscription)
**Purpose**: Real-time options data feed

**Setup**:
```bash
make setup-theta
```

**Daily Use**:
```bash
make start-trading  # Start ThetaTerminal
make stop-trading   # Stop ThetaTerminal
```

### 3. FNTX Application
**Purpose**: The main trading application

**Development**:
```bash
make start  # Start all FNTX services
make stop   # Stop all services
make dev    # Start in development mode
```

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  VNC Desktop    │     │   FNTX Backend   │     │ ThetaTerminal   │
│  (IB Gateway)   │────▶│   (Port 8000)    │◀────│  (Port 11000)   │
│  Port 5901      │     └──────────────────┘     └─────────────────┘
└─────────────────┘              │
                                 ▼
                          ┌──────────────────┐
                          │  FNTX Frontend   │
                          │   (Port 8080)    │
                          └──────────────────┘
```

## Quick Commands Reference

```bash
# VNC/IB Gateway
make vnc-setup      # One-time setup
make vnc-status     # Check status
make vnc-restart    # Restart VNC

# ThetaTerminal (if subscribed)
make setup-theta    # One-time setup
make start-trading  # Start
make stop-trading   # Stop

# FNTX Application
make install        # Install dependencies
make start          # Start application
make stop           # Stop application
make logs           # View logs
```

## Notes

- VNC runs as a system service (auto-starts on boot)
- IB Gateway settings persist between sessions
- ThetaTerminal requires active subscription
- All services can run independently