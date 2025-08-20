# DASHBOARD Command - Real-Time Trading Monitor

## Executive Summary
The `dashboard` command launches a comprehensive real-time monitoring interface for automated options trading. It provides 10 specialized panels in a cyberpunk-themed terminal UI, enabling traders to monitor positions, analyze market conditions, and track AI decision-making in real-time.

## 🎯 Primary Purpose
- **Monitor**: Real-time options chains, positions, and P&L
- **Analyze**: Market conditions, volatility, and timing indicators  
- **Track**: AI reasoning, risk metrics, and performance statistics
- **Control**: Manual overrides and RLHF feedback collection

## 🚀 Quick Start

### Installation
```bash
# Install dependencies
pip install rich textual pandas numpy pytz psycopg2-binary

# Clone repository (if not already done)
git clone https://github.com/your-org/fntx-ai-v1.git
cd fntx-ai-v1

# Set up environment
cp config/.env.example config/.env
# Edit .env with your credentials
```

### Launch Dashboard
```bash
# From project root
python main.py dashboard

# Or directly
python rl/terminal/dashboard.py
```

## 🎨 UI/UX Architecture

### Login Flow
```
┌─────────────────────────────────────────────┐
│  ╔═╗╔╗╔╔╦╗═╗ ╦  Matrix Authentication      │
│  ╠╣ ║║║ ║ ╔╩╦╝  ┌─────────────────┐        │
│  ╚  ╝╚╝ ╩ ╩ ╚═  │ Username: _____ │        │
│                  │ Password: _____ │        │
│  [Matrix Rain]   └─────────────────┘        │
│  0 1 0 1 1 0    [LOGIN] [REGISTER]         │
└─────────────────────────────────────────────┘
```

### Main Dashboard Layout
```
┌──────────────────────────────────────────────────────────────┐
│                    FNTX TRADING DASHBOARD                     │
├────────────────┬────────────────┬────────────────────────────┤
│ Options Chain  │ Straddle View   │ Market Timer              │
│ [Live Data]    │ [ATM Analysis]  │ [09:30-16:00 ET]         │
├────────────────┼────────────────┼────────────────────────────┤
│ Features       │ AI Reasoning    │ Statistics                │
│ [Indicators]   │ [Logic Flow]    │ [Performance]             │
├────────────────┼────────────────┼────────────────────────────┤
│ MANDATE PANEL  │ Risk Manager    │ RLHF Feedback            │
│ [Guardrails]   │ [Positions]     │ [Human Input]            │
└────────────────┴────────────────┴────────────────────────────┘
```

## 📊 Panel Specifications

### 1. Options Chain Panel
- **Purpose**: Display real-time options chain with OTM filtering
- **Data**: Bid/Ask, Volume, OI, Greeks, IV
- **Update**: Every 3 seconds
- **Features**:
  - Color-coded by moneyness (ITM/ATM/OTM)
  - Volatility smile visualization
  - Strike selection highlighting

### 2. Straddle Options Panel  
- **Purpose**: Analyze ATM straddle opportunities
- **Data**: Combined premium, breakeven points, expected move
- **Visualization**: 12 strikes centered on ATM
- **Key Metrics**: Straddle cost, implied move, P&L scenarios

### 3. Features Panel
- **Purpose**: Market indicators and signals
- **Indicators**:
  - VIX level and trend
  - Put/Call ratio
  - Market breadth
  - Volume patterns
  - Technical indicators (RSI, MACD, etc.)

### 4. AI Reasoning Panel
- **Purpose**: Display AI decision logic in real-time
- **Content**:
  - Current market assessment
  - Trade recommendations
  - Risk/Reward analysis
  - Confidence scores
  - Decision tree visualization

### 5. Statistics Panel
- **Purpose**: Performance metrics and analytics
- **Metrics**:
  - Win rate, Sharpe ratio
  - Daily/Weekly/Monthly P&L
  - Maximum drawdown
  - Trade distribution
  - Success by time of day

### 6. Mandate Panel (Guardrails)
- **Purpose**: Display and enforce risk limits
- **Display Format**:
```
╔═══════════════════════════════╗
║      MANDATE STATUS           ║
╠═══════════════════════════════╣
║ Daily Loss Limit: $5,000      ║
║ Current Loss: $1,234 (25%)    ║
║ ▓▓▓▓▓░░░░░░░░░░░░░░░         ║
║                               ║
║ Max Positions: 10             ║
║ Open Positions: 3             ║
║ ▓▓▓░░░░░░░░░░░░░░░░          ║
║                               ║
║ Trading Hours: 09:30-16:00    ║
║ Status: ACTIVE ✓              ║
╚═══════════════════════════════╝
```

### 7. RLHF Panel
- **Purpose**: Collect human feedback on AI decisions
- **Features**:
  - Rate trade quality (1-5 stars)
  - Approve/Reject suggestions
  - Provide text feedback
  - Override AI decisions

### 8. Market Timer Panel
- **Purpose**: Optimal trading time indicators
- **Display**:
  - Current market session
  - Time to close
  - Liquidity indicators
  - Preferred trading windows (2-4 PM highlighted)

### 9. Risk Manager Panel
- **Purpose**: Position and risk monitoring
- **Features**:
  - Open positions with real-time P&L
  - Greeks aggregation
  - Portfolio heat map
  - Stop loss levels
  - Margin requirements

### 10. Human Feedback Panel
- **Purpose**: Manual intervention and overrides
- **Controls**:
  - Emergency stop button
  - Position adjustment
  - Strategy modification
  - Parameter tuning

## 🎨 Cyberpunk Theme

### Color Palette
```python
THEME = {
    'primary': '#00ff41',      # Matrix green
    'secondary': '#39ff14',    # Neon green
    'accent': '#ff00ff',       # Cyberpunk magenta
    'warning': '#ffff00',      # Yellow alert
    'danger': '#ff0040',       # Red alert
    'background': '#0a0a0a',   # Deep black
    'surface': '#1a1a2e',      # Dark blue
    'text': '#c0c0c0',         # Silver text
    'dim': '#606060'           # Dimmed text
}
```

### Visual Effects
- Matrix rain on login screen
- Glowing borders on active panels
- Pulsing indicators for live data
- Neon highlights on important metrics
- ASCII art headers and dividers

## 🔧 Technical Implementation

### Framework Integration
```python
# Unified Rich + Textual approach
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from textual.app import App
from textual.widgets import DataTable

class UnifiedDashboard:
    """Combines Rich panels with Textual interactivity"""
    
    def __init__(self):
        self.console = Console()
        self.panels = self._initialize_panels()
        
    def _initialize_panels(self):
        return {
            'options': OptionsChainPanel(),
            'straddle': StraddlePanel(),
            'features': FeaturesPanel(),
            'reasoning': ReasoningPanel(),
            'statistics': StatisticsPanel(),
            'mandate': MandatePanel(),
            'rlhf': RLHFPanel(),
            'timer': MarketTimerPanel(),
            'risk': RiskManagerPanel(),
            'feedback': HumanFeedbackPanel()
        }
```

### Data Flow Architecture
```
WebSocket/REST API
       ↓
Data Aggregator
       ↓
Panel Controllers → Update Cycle (3s)
       ↓                    ↓
Rich Layout          Textual Widgets
       ↓                    ↓
    Terminal Display (Unified)
```

### Real-Time Updates
```python
async def update_loop(self):
    """Main update loop running every 3 seconds"""
    while self.is_running:
        # Fetch latest data
        market_data = await self.fetch_market_data()
        positions = await self.fetch_positions()
        
        # Update all panels
        for panel in self.panels.values():
            panel.update(market_data, positions)
        
        # Refresh display
        self.console.refresh()
        
        await asyncio.sleep(3)
```

## 📁 Configuration

### Environment Variables (.env)
```bash
# Data Sources
THETA_API_KEY=your_theta_key
YAHOO_FINANCE_ENABLED=true

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trading_db
DB_USER=trader
DB_PASSWORD=secure_password

# Display Settings
THEME=cyberpunk
UPDATE_FREQUENCY=3
PANEL_LAYOUT=10_panel_grid

# Risk Parameters (for display)
MAX_DAILY_LOSS=5000
MAX_POSITIONS=10
TRADING_HOURS=09:30-16:00
```

### Custom Panel Configuration
```yaml
# config/dashboard.yaml
panels:
  options_chain:
    enabled: true
    position: top_left
    size: large
    strikes_to_show: 20
    
  mandate:
    enabled: true
    position: bottom_left
    size: medium
    highlight_violations: true
    
  market_timer:
    enabled: true
    position: top_right
    preferred_window: "14:00-16:00"
```

## 🚨 Monitoring & Alerts

### Visual Alerts
- **Red Flash**: Stop loss triggered
- **Yellow Pulse**: Approaching risk limit
- **Green Glow**: Profitable position
- **Magenta Border**: RLHF input required

### Audio Alerts (Optional)
```python
# Enable system beeps for critical events
AUDIO_ALERTS = {
    'stop_loss': 'beep_pattern_1',
    'risk_limit': 'beep_pattern_2',
    'trade_executed': 'beep_pattern_3'
}
```

## 🐛 Troubleshooting

### Common Issues

1. **Dashboard won't start**
   ```bash
   # Check dependencies
   pip list | grep -E "rich|textual|pandas"
   
   # Verify database connection
   psql -h localhost -U trader -d trading_db -c "SELECT 1"
   ```

2. **No data displayed**
   ```bash
   # Check data sources
   python -c "from data.theta_connector import test_connection; test_connection()"
   
   # Verify WebSocket connection
   python -c "import asyncio; from data.ws_client import test_ws; asyncio.run(test_ws())"
   ```

3. **Panels not updating**
   ```bash
   # Check update loop
   tail -f logs/dashboard.log | grep UPDATE
   
   # Monitor refresh rate
   python -c "from terminal.dashboard import check_refresh_rate; check_refresh_rate()"
   ```

### Debug Mode
```bash
# Launch with debug logging
DEBUG=1 python main.py dashboard

# Enable panel-specific debugging
DEBUG_PANELS=options,mandate python main.py dashboard
```

## 📈 Performance Optimization

### Resource Usage
- **CPU**: ~5-10% (normal operation)
- **Memory**: ~200-300 MB
- **Network**: ~50 KB/s (continuous streaming)

### Optimization Tips
1. Reduce update frequency for low-activity periods
2. Cache static data (strikes, expirations)
3. Use WebSocket instead of polling where possible
4. Implement panel lazy loading

## 🔐 Security Considerations

### Data Protection
- Never log sensitive credentials
- Use encrypted connections for all APIs
- Implement session timeouts
- Audit log all manual overrides

### Access Control
```python
# Implement role-based access
ROLES = {
    'viewer': ['read_only'],
    'trader': ['read', 'manual_override'],
    'admin': ['read', 'write', 'configure']
}
```

## 📚 Additional Resources

### Related Documentation
- [RUN_COMMAND.md](./RUN_COMMAND.md) - Automated trading execution
- [IBKR Integration Guide](../oauth/README.md)
- [Risk Management Framework](../risk/README.md)

### Support
- GitHub Issues: [github.com/your-org/fntx-ai-v1/issues](https://github.com)
- Documentation: [docs.fntx.ai](https://docs.fntx.ai)
- Community Discord: [discord.gg/fntx](https://discord.gg)

---

*Last Updated: December 2024*
*Version: 1.0.0*
*Maintained by: FNTX AI Team*