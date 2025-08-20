# FNTX Terminal 🚀

A cyberpunk-themed trading terminal for options and equities, featuring a Matrix-style interface with real-time market data visualization.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-beta-yellow)

## ✨ Features

- 🎭 **Matrix Rain Login** - Cyberpunk authentication screen with falling code
- 📊 **10-Panel Dashboard** - Comprehensive trading interface
- 🔄 **Real-Time Updates** - Live market data every 3 seconds
- 🎨 **Cyberpunk Theme** - Neon green aesthetics with customizable themes
- 🤖 **AI Integration** - Display trading logic and reasoning
- 📈 **Options Chain** - Live options data with Greeks
- 🛡️ **Risk Management** - Position monitoring and guardrails
- 🎮 **Demo Mode** - Try without connecting to real data

## 🚀 Quick Start

### Install from GitHub

```bash
# Install directly from GitHub
pip install git+https://github.com/fntx-ai/fntx-terminal.git

# Or clone and install locally
git clone https://github.com/fntx-ai/fntx-terminal.git
cd fntx-terminal
pip install -e .
```

### Run the Terminal

```bash
# Launch FNTX Terminal
fntx

# Or use the full name
fntx-terminal
```

## 🎮 Demo Mode

The terminal runs in demo mode by default, perfect for trying out the interface:

```bash
# Run with demo data (default)
fntx

# Explicitly run in demo mode
fntx --demo
```

## 🔌 Live Mode

To connect to real trading data:

1. Create a configuration file:
```bash
mkdir -p ~/.fntx
cat > ~/.fntx/config.toml << EOF
[database]
host = "localhost"
port = 5432
name = "options_data"
user = "postgres"
password = "your_password"

[api]
base_url = "http://localhost:8080"
theta_key = "your_theta_api_key"
EOF
```

2. Run in live mode:
```bash
fntx --live
```

## 🎨 Screenshots

### Matrix Login Screen
```
╔════════════════════════════════════════╗
║         FNTX TRADING TERMINAL          ║
║  ╔═╗╔╗╔╔╦╗═╗ ╦                        ║
║  ╠╣ ║║║ ║ ╔╩╦╝    [Matrix Rain]       ║
║  ╚  ╝╚╝ ╩ ╩ ╚═                        ║
║                                        ║
║  Username: ________________            ║
║  Password: ________________            ║
║                                        ║
║       [ENTER THE MATRIX]               ║
╚════════════════════════════════════════╝
```

### Trading Dashboard
```
┌──────────────┬────────────────┬──────────────┐
│ Options Chain│ Straddle View  │ Market Timer │
│ SPY 450C/P   │ ATM Analysis   │ 09:30-16:00  │
├──────────────┼────────────────┼──────────────┤
│ Features     │ AI Reasoning   │ Statistics   │
│ VIX: 18.5    │ Confidence: 85%│ Win Rate: 72%│
├──────────────┼────────────────┼──────────────┤
│ Mandate      │ Risk Manager   │ RLHF Panel   │
│ Limits: OK   │ 3 Positions    │ Feedback: A+ │
└──────────────┴────────────────┴──────────────┘
```

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Tab` / `Shift+Tab` | Navigate between panels |
| `Enter` | Submit/Select |
| `Escape` | Back/Cancel |
| `Q` | Quit application |
| `R` | Refresh all panels |
| `Space` | Pause/Resume updates |
| `1-9` | Jump to panel |

## 🛠️ Configuration

### Themes

Create custom themes in `~/.fntx/themes/`:

```toml
# ~/.fntx/themes/custom.toml
[colors]
primary = "#00ff41"      # Matrix green
secondary = "#39ff14"    # Neon green
accent = "#ff00ff"       # Magenta
background = "#0a0a0a"   # Deep black
```

Load your theme:
```bash
fntx --theme custom
```

### Update Frequency

Control refresh rate (default: 3 seconds):
```bash
fntx --refresh 5  # Update every 5 seconds
```

## 📦 Installation Options

### For Development

```bash
# Clone the repository
git clone https://github.com/fntx-ai/fntx-terminal.git
cd fntx-terminal

# Install in development mode with extras
pip install -e ".[dev,live]"

# Run tests
pytest

# Format code
black src/
ruff check src/
```

### Dependencies Only

Core dependencies:
- `textual` - Terminal UI framework
- `rich` - Terminal formatting
- `pandas` - Data handling
- `numpy` - Numerical operations

Optional (for live mode):
- `psycopg2-binary` - PostgreSQL connection
- `asyncpg` - Async database operations

## 🐛 Troubleshooting

### Terminal Issues

If the UI looks broken:
```bash
# Check terminal capabilities
echo $TERM

# Set to a capable terminal
export TERM=xterm-256color

# Run again
fntx
```

### Connection Issues

For live mode connection problems:
```bash
# Test database connection
fntx --test-connection

# Check configuration
fntx --show-config

# Run with debug logging
fntx --debug
```

### Performance

If updates are slow:
```bash
# Reduce update frequency
fntx --refresh 10

# Disable animations
fntx --no-animations

# Use simpler theme
fntx --theme minimal
```

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/fntx-terminal.git

# Create feature branch
git checkout -b feature/amazing-feature

# Make changes and test
pip install -e ".[dev]"
pytest

# Submit PR
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- [Documentation](https://docs.fntx.ai/terminal)
- [GitHub Repository](https://github.com/fntx-ai/fntx-terminal)
- [Issue Tracker](https://github.com/fntx-ai/fntx-terminal/issues)
- [Discord Community](https://discord.gg/fntx)

## 🙏 Acknowledgments

- Built with [Textual](https://github.com/Textualize/textual)
- Styled with [Rich](https://github.com/Textualize/rich)
- Inspired by cyberpunk aesthetics and The Matrix

---

**FNTX Terminal** - *Enter the Matrix of Trading*

Made with 💚 by the FNTX AI Team