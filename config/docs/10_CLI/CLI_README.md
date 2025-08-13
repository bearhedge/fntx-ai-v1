# FNTX Trading CLI

Professional trading terminal with both Terminal User Interface (TUI) and command-line interface for SPY 0DTE options trading with real-time market data, risk management, and AI-powered trade suggestions.

```
███████╗███╗   ██╗████████╗██╗  ██╗
██╔════╝████╗  ██║╚══██╔══╝╚██╗██╔╝
█████╗  ██╔██╗ ██║   ██║    ╚███╔╝ 
██╔══╝  ██║╚██╗██║   ██║    ██╔██╗ 
██║     ██║ ╚████║   ██║   ██╔╝ ██╗
╚═╝     ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝
```

## Installation

```bash
# Clone the repository
git clone https://github.com/fntx-ai/fntx-cli.git
cd fntx-cli

# Install using pip
pip install -e .

# Or install from the parent directory
cd /home/info/fntx-ai-v1/cli
pip install -e .
```

## Quick Start

### Terminal User Interface (TUI) Mode - NEW!

```bash
# Launch full TUI application (default)
fntx

# Or explicitly
fntx tui
```

This launches a full-screen terminal application with:
- Real-time market data updates
- Interactive navigation between screens
- Keyboard shortcuts (d=Dashboard, p=Positions, r=Risk, t=Trade, s=Settings, q=Quit)
- Live data refresh
- Professional trading terminal experience

### Command Line Interface (CLI) Mode

```bash
# Use CLI mode explicitly
fntx --cli

# Individual commands
fntx status
fntx positions
fntx risk
fntx trade
fntx config
```

## Commands

### `fntx status`
Display current market status and account overview.

```bash
fntx status              # Show once
fntx status --watch      # Auto-refresh mode
fntx status -w -i 5      # Refresh every 5 seconds
```

### `fntx positions`
View active positions with P&L calculations.

```bash
fntx positions                # Default table view
fntx positions --format json  # JSON output
fntx positions --sort pnl     # Sort by P&L
```

### `fntx risk`
Display risk manager panel with mandate compliance.

```bash
fntx risk                     # Show risk panel with VIX chart
fntx risk --no-vix-chart      # Hide VIX chart
fntx risk --details           # Show detailed compliance info
```

### `fntx trade`
Execute trades with interactive options chain (Demo Mode).

```bash
fntx trade                    # Trade SPY options
fntx trade TSLA --side call   # Trade TSLA calls only
fntx trade --quantity 5       # Trade 5 contracts
```

### `fntx monitor`
Launch live monitoring dashboard with real-time updates.

```bash
fntx monitor                  # Full dashboard
fntx monitor --layout compact # Compact view
fntx monitor -r 1            # 1-second refresh rate
```

### `fntx config`
Configure API connections and trading parameters.

```bash
fntx config                   # Interactive menu
fntx config show              # Display current config
fntx config api               # Configure API connections
fntx config trading           # Set trading parameters
fntx config --export cfg.json # Export configuration
```

## Configuration

Configuration is stored in `~/.fntx/config.json` and includes:

### API Settings
- **Theta Terminal**: Real-time options data
- **IBKR Gateway**: Trade execution
- **Database**: Historical data and ALM

### Trading Parameters
- Default quantity per trade
- Maximum position size
- Stop loss multiplier
- Delta limits
- VIX thresholds

### UI Settings
- Color themes
- Refresh rates
- Dashboard layouts
- ASCII art preferences

## Features

### Full Terminal User Interface (TUI)
- **Immersive Experience**: Full-screen terminal application
- **Multi-Panel Layout**: See all data simultaneously
- **Real-Time Updates**: Automatic data refresh
- **Keyboard Navigation**: Quick shortcuts for all screens
- **Interactive Elements**: Clickable buttons and scrollable tables
- **Professional Design**: Similar to Bloomberg Terminal

### Real-Time Market Data
- SPY price tracking
- VIX level monitoring
- Market open/close status
- Next session countdown

### Position Management
- Live P&L calculations
- USD/HKD conversion
- Stop loss tracking
- Risk warnings

### Risk Management
- 9-point mandate system
- Compliance tracking
- VIX chart visualization
- Position limits

### Professional ASCII UI
- Box drawing characters
- Color-coded status
- Progress indicators
- Interactive menus

## Demo Mode

The CLI runs in demo mode by default, using mock data for safe exploration of features. To connect to live data sources, configure your API connections using `fntx config`.

## Requirements

- Python 3.8+
- Terminal with UTF-8 support
- 80+ character width recommended

## Support

For issues and feature requests, please visit: https://github.com/fntx-ai/fntx-cli/issues

## License

Copyright © 2024 FNTX AI. All rights reserved.