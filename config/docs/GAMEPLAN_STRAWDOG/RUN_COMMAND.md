# RUN Command - Automated Trading Execution Engine

## Executive Summary
The `run` command launches the fully automated options trading system that executes wave-pattern spreading strategies through IBKR's headless gateway. It operates with AI-driven decision making, mandate-based risk controls, and selective timing optimization, preferring afternoon trading sessions for maximum liquidity.

## 🎯 Primary Purpose
- **Execute**: Automated options trades via IBKR OAuth + Gateway
- **Spread**: Wave-pattern ATM → OTM options distribution
- **Control**: Mandate system providing hard risk guardrails  
- **Optimize**: Selective trading with 2-4 PM ET preference
- **Automate**: Full plug-and-play operation with zero manual intervention

## 🚀 Quick Start

### Prerequisites
```bash
# Install trading dependencies
pip install ib_insync pandas numpy scikit-learn pytz
pip install asyncio websockets requests cryptography

# Install IBKR Gateway (headless mode)
wget https://download2.interactivebrokers.com/installers/ibgateway/latest-standalone/ibgateway-latest-standalone-linux-x64.sh
chmod +x ibgateway-latest-standalone-linux-x64.sh
./ibgateway-latest-standalone-linux-x64.sh -q

# Set up OAuth keys
cp config/keys/*.pem /home/info/fntx-ai-v1/config/keys/
```

### Launch Automated Trading
```bash
# Start IBKR Gateway first (runs on port 5000)
./scripts/start_gateway.sh

# Launch automated trading
python main.py run

# Or with specific parameters
python main.py run --mandate conservative --timing afternoon --wave-size 5
```

### Systemd Service (24/7 Operation)
```bash
# Install service
sudo cp config/systemd/fntx-trader.service /etc/systemd/system/
sudo systemctl enable fntx-trader
sudo systemctl start fntx-trader

# Check status
sudo systemctl status fntx-trader
```

## 🌊 Wave-Pattern Options Spreading Algorithm

### Core Concept
```
     ATM (Center)
         |
    ───────────────
   /    WAVE 1    \
  /    WAVE 2      \
 /    WAVE 3        \
OTM              OTM
```

### Algorithm Implementation
```python
class WavePatternSpreader:
    """
    Spreads options positions like ripples from ATM center
    """
    
    def __init__(self, symbol='SPY'):
        self.symbol = symbol
        self.wave_count = 5  # Number of concentric waves
        self.wave_size = [1, 2, 3, 2, 1]  # Contracts per wave
        self.strike_distance = [0, 1, 2, 3, 5]  # Strike offset from ATM
        
    def calculate_waves(self, current_price):
        """Calculate wave distribution from ATM"""
        atm_strike = round(current_price)
        waves = []
        
        for i in range(self.wave_count):
            wave = {
                'level': i + 1,
                'strikes': [],
                'contracts': self.wave_size[i],
                'type': 'straddle' if i == 0 else 'strangle'
            }
            
            if i == 0:  # ATM straddle
                wave['strikes'] = [atm_strike]
            else:  # OTM waves
                offset = self.strike_distance[i]
                wave['strikes'] = [
                    atm_strike - offset,  # Put strike
                    atm_strike + offset   # Call strike
                ]
            
            waves.append(wave)
        
        return waves
    
    def execute_wave_spread(self, waves, timing_score):
        """Execute the wave pattern with timing optimization"""
        orders = []
        
        for wave in waves:
            # Adjust size based on timing (prefer 2-4 PM)
            size_multiplier = 1.5 if timing_score > 0.8 else 1.0
            
            for strike in wave['strikes']:
                # Create both put and call orders
                for option_type in ['PUT', 'CALL']:
                    order = {
                        'symbol': self.symbol,
                        'strike': strike,
                        'type': option_type,
                        'quantity': int(wave['contracts'] * size_multiplier),
                        'action': 'BUY',
                        'order_type': 'LMT',
                        'price': self.calculate_fair_value(strike, option_type)
                    }
                    orders.append(order)
        
        return orders
```

### Wave Execution Patterns
1. **Wave 1 (ATM)**: Maximum premium collection, delta-neutral
2. **Wave 2 (Near OTM)**: Balanced risk/reward, moderate theta
3. **Wave 3 (Mid OTM)**: Higher probability of profit, lower premium
4. **Wave 4 (Far OTM)**: Tail risk hedging, lottery tickets
5. **Wave 5 (Deep OTM)**: Black swan protection, minimal cost

## 🛡️ Mandate System (Risk Guardrails)

### Mandate Levels
```yaml
conservative:
  max_daily_loss: $2,000
  max_positions: 5
  max_contract_size: 10
  allowed_strategies: [covered_calls, cash_secured_puts]
  trading_hours: "09:30-15:30"
  
moderate:
  max_daily_loss: $5,000
  max_positions: 10
  max_contract_size: 25
  allowed_strategies: [straddles, strangles, spreads]
  trading_hours: "09:30-16:00"
  
aggressive:
  max_daily_loss: $10,000
  max_positions: 20
  max_contract_size: 50
  allowed_strategies: [all]
  trading_hours: "09:30-16:00"
  after_hours: true
```

### Mandate Enforcement Engine
```python
class MandateSystem:
    """Hard guardrails that cannot be overridden"""
    
    def __init__(self, level='moderate'):
        self.mandate = self.load_mandate(level)
        self.daily_loss = 0
        self.open_positions = 0
        self.violations = []
        
    def check_trade_approval(self, order):
        """Pre-trade compliance check"""
        checks = {
            'daily_loss': self.check_loss_limit(),
            'position_count': self.check_position_limit(),
            'contract_size': self.check_size_limit(order),
            'strategy': self.check_strategy_allowed(order),
            'time': self.check_trading_hours(),
            'margin': self.check_margin_requirements(order)
        }
        
        # ALL checks must pass
        if all(checks.values()):
            return {'approved': True}
        else:
            violations = [k for k, v in checks.items() if not v]
            return {
                'approved': False,
                'violations': violations,
                'action': 'BLOCK_TRADE'
            }
    
    def emergency_stop(self):
        """Circuit breaker - immediate halt"""
        if self.daily_loss >= self.mandate['max_daily_loss']:
            self.close_all_positions()
            self.lock_trading_until_tomorrow()
            return "EMERGENCY_STOP_TRIGGERED"
```

### Risk Metrics Dashboard
```
╔══════════════════════════════════════╗
║         MANDATE ENFORCEMENT          ║
╠══════════════════════════════════════╣
║ Daily P&L: -$3,450 / -$5,000         ║
║ ████████████████░░░░░░░  [69%]       ║
║                                      ║
║ Open Positions: 7 / 10               ║
║ ███████████████░░░░░░░  [70%]        ║
║                                      ║
║ Buying Power: $45,000                ║
║ Margin Used: $12,000 (27%)           ║
║                                      ║
║ Status: ✅ TRADING ALLOWED           ║
║ Next Check: 30 seconds               ║
╚══════════════════════════════════════╝
```

## ⏰ Selective Trading Timing

### Optimal Trading Windows
```python
class TradingTimer:
    """Intelligent timing for trade execution"""
    
    OPTIMAL_WINDOWS = {
        'morning_open': {'start': '09:30', 'end': '10:00', 'score': 0.7},
        'mid_morning': {'start': '10:00', 'end': '11:30', 'score': 0.5},
        'lunch_lull': {'start': '11:30', 'end': '13:00', 'score': 0.3},
        'afternoon_setup': {'start': '13:00', 'end': '14:00', 'score': 0.6},
        'power_hour_prep': {'start': '14:00', 'end': '15:00', 'score': 0.9},
        'final_hour': {'start': '15:00', 'end': '16:00', 'score': 1.0}
    }
    
    def get_timing_score(self):
        """Calculate current timing score (0-1)"""
        current_time = datetime.now(pytz.timezone('US/Eastern'))
        time_str = current_time.strftime('%H:%M')
        
        for window, params in self.OPTIMAL_WINDOWS.items():
            if params['start'] <= time_str <= params['end']:
                # Additional factors
                volume_factor = self.get_volume_factor()
                volatility_factor = self.get_volatility_factor()
                
                # Weighted score
                score = (
                    params['score'] * 0.5 +
                    volume_factor * 0.3 +
                    volatility_factor * 0.2
                )
                
                return min(score, 1.0)
        
        return 0.1  # Outside trading hours
    
    def should_trade_now(self, threshold=0.7):
        """Decision: Trade now or wait"""
        score = self.get_timing_score()
        
        # Always allow if approaching day end
        if self.minutes_to_close() < 30:
            return True, "CLOSE_APPROACHING"
        
        # Prefer afternoon (2-4 PM bonus)
        current_hour = datetime.now(pytz.timezone('US/Eastern')).hour
        if 14 <= current_hour < 16:
            score *= 1.2  # 20% bonus for preferred window
        
        return score >= threshold, score
```

### Timing-Based Execution
```
09:30 ────┬──── 10:00 ──── 11:30 ──── 13:00 ──── 14:00 ──── 15:00 ──── 16:00
          │        │          │          │          │          │          │
   [HIGH] │  [MED] │   [LOW]  │   [MED]  │  [HIGH]  │  [MAX]   │  [CLOSE] │
     70%  │   50%  │    30%   │    60%   │    90%   │   100%   │    EOD   │
          │        │          │          │          │          │          │
          ▼        ▼          ▼          ▼          ▼          ▼          ▼
   Open   │  Scan  │   Wait   │  Setup   │ PRIMARY  │  POWER   │  Close   │
   Trades │  Only  │          │ Positions│ WINDOW   │  HOUR    │   All    │
```

## 🤖 IBKR Integration Architecture

### OAuth + Gateway Hybrid Model
```python
class IBKRTradingEngine:
    """
    Combines OAuth for auth + Gateway for execution
    """
    
    def __init__(self):
        # OAuth for authentication
        self.oauth = IBRestAuth(
            consumer_key='BEARHEDGE',
            realm='limited_poa'
        )
        
        # Gateway for trading (port 5000)
        self.gateway_url = 'https://localhost:5000/v1/api'
        self.session_token = None
        
    async def initialize(self):
        """Start gateway and establish session"""
        # 1. Start gateway in headless mode
        await self.start_gateway()
        
        # 2. Authenticate via OAuth
        self.session_token = self.oauth.get_session_token()
        
        # 3. Initialize gateway session
        response = requests.post(
            f'{self.gateway_url}/iserver/auth/ssodh/init',
            headers={'Authorization': f'Bearer {self.session_token}'},
            verify=False  # Self-signed cert
        )
        
        return response.json()
    
    async def execute_order(self, order):
        """Execute order through gateway"""
        # Format for IBKR gateway
        ibkr_order = {
            'acctId': self.account_id,
            'conid': order['conid'],
            'secType': 'OPT',
            'orderType': order['type'],
            'side': order['action'],
            'quantity': order['quantity'],
            'price': order['price'],
            'tif': 'DAY',
            'outsideRTH': False
        }
        
        # Submit through gateway
        response = requests.post(
            f'{self.gateway_url}/iserver/account/{self.account_id}/orders',
            json={'orders': [ibkr_order]},
            headers={'Authorization': f'Bearer {self.session_token}'},
            verify=False
        )
        
        # Handle reply (confirmations/warnings)
        if response.status_code == 200:
            data = response.json()
            if 'id' in data[0]:  # Needs confirmation
                return await self.confirm_order(data[0]['id'])
        
        return response.json()
```

### Gateway Automation
```yaml
# config/ibgateway/ibgateway.conf
[Gateway]
Mode=paper  # or live
Port=5000
ReadOnlyApi=false
LocalOnly=false
AllowedIPs=127.0.0.1

[Authentication]
UseOAuth=true
ConsumerKey=BEARHEDGE
Realm=limited_poa

[Trading]
AutoClosePositions=true
MaxOrdersPerMinute=60
EnableOptions=true
```

### Systemd Service Configuration
```ini
# /etc/systemd/system/ibkr-gateway.service
[Unit]
Description=IBKR Gateway Headless Service
After=network.target

[Service]
Type=simple
User=trader
WorkingDirectory=/home/info/fntx-ai-v1
Environment="DISPLAY=:99"
ExecStartPre=/usr/bin/Xvfb :99 -screen 0 1024x768x24 &
ExecStart=/opt/ibgateway/bin/ibgateway.sh -mode paper
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 📊 AI Decision Engine

### Reinforcement Learning Integration
```python
class RLTradingBrain:
    """AI brain using RL for decision making"""
    
    def __init__(self):
        self.model = self.load_trained_model()
        self.state_encoder = StateEncoder()
        self.action_decoder = ActionDecoder()
        
    def get_trading_decision(self, market_state):
        """Get AI decision for current market"""
        # Encode market state
        features = self.state_encoder.encode({
            'price': market_state['spy_price'],
            'vix': market_state['vix'],
            'volume': market_state['volume'],
            'options_chain': market_state['chain'],
            'time_features': self.get_time_features(),
            'position_features': self.get_position_features()
        })
        
        # Get action from RL model
        action = self.model.predict(features)
        
        # Decode to trading instructions
        trades = self.action_decoder.decode(action)
        
        # Apply mandate constraints
        trades = self.apply_mandate_filters(trades)
        
        return {
            'trades': trades,
            'confidence': float(action.confidence),
            'reasoning': self.generate_reasoning(features, action)
        }
    
    def generate_reasoning(self, features, action):
        """Explain AI decision in human terms"""
        reasoning = []
        
        if features['vix'] > 20:
            reasoning.append("High volatility detected - expanding strikes")
        
        if features['time_score'] > 0.8:
            reasoning.append("Optimal trading window - increasing size")
        
        if action.type == 'wave_spread':
            reasoning.append(f"Executing {action.wave_count}-wave spread pattern")
        
        return " | ".join(reasoning)
```

### RLHF Feedback Loop
```python
class RLHFFeedback:
    """Reinforcement Learning from Human Feedback"""
    
    def collect_feedback(self, trade_result):
        """Collect human feedback on trades"""
        feedback = {
            'trade_id': trade_result['id'],
            'timestamp': datetime.now(),
            'pnl': trade_result['pnl'],
            'human_rating': None,  # 1-5 stars
            'human_comment': None,
            'would_repeat': None  # boolean
        }
        
        # Show to human for rating (async)
        self.queue_for_review(feedback)
        
        return feedback
    
    def update_model(self, feedback_batch):
        """Update RL model with human feedback"""
        if len(feedback_batch) >= 100:
            # Retrain with human preferences
            rewards = self.calculate_hybrid_rewards(feedback_batch)
            self.model.update(rewards)
            
            print(f"Model updated with {len(feedback_batch)} feedback samples")
```

## 🎮 Automation Control Panel

### Command Line Interface
```bash
# Start automated trading
python main.py run --mandate moderate --waves 5

# With specific parameters
python main.py run \
  --symbol SPY \
  --mandate aggressive \
  --waves 7 \
  --timing afternoon \
  --max-loss 5000 \
  --debug

# Monitor only (no execution)
python main.py run --dry-run --verbose

# Emergency stop
python main.py stop --force
```

### Runtime Controls
```python
# Real-time parameter adjustment
runtime_config = {
    'pause_trading': False,
    'override_timing': False,
    'force_close_all': False,
    'wave_size_multiplier': 1.0,
    'allowed_symbols': ['SPY', 'QQQ'],
    'blacklist_strikes': [],
    'max_order_value': 10000
}

# Hot-reload configuration
signal.signal(signal.SIGUSR1, reload_config)
```

### Status Display
```
╔════════════════════════════════════════════════╗
║           AUTOMATED TRADING STATUS             ║
╠════════════════════════════════════════════════╣
║ Mode: LIVE | Mandate: MODERATE | Waves: 5      ║
║ Symbol: SPY @ $448.25 | VIX: 16.3             ║
╠────────────────────────────────────────────────╣
║ Timing Score: 0.92 (OPTIMAL)                   ║
║ ████████████████████████░░░  [92%]            ║
║                                                ║
║ Current Wave: 3 of 5                           ║
║ ░░░░░████████████░░░░░░░░░  [Wave 3]          ║
║                                                ║
║ Today's P&L: +$1,234 (7 trades)               ║
║ Win Rate: 71% | Sharpe: 1.8                   ║
╠────────────────────────────────────────────────╣
║ Next Action: BUY 2x SPY 450C @ $0.85          ║
║ Confidence: 87% | ETA: 14 seconds             ║
╚════════════════════════════════════════════════╝
```

## 🔒 Security & Safety

### Multi-Layer Protection
```python
SAFETY_LAYERS = {
    'pre_trade': [
        'mandate_check',      # Hard limits
        'margin_check',       # Buying power
        'pattern_check',      # Day trading rules
        'duplicate_check'     # Avoid duplicates
    ],
    'execution': [
        'price_validation',   # Sanity check
        'size_limits',        # Position sizing
        'slippage_control',   # Max slippage
        'timeout_control'     # 30s max wait
    ],
    'post_trade': [
        'fill_verification',  # Confirm execution
        'risk_update',        # Update exposure
        'stop_loss_placement', # Protective stops
        'alert_generation'    # Notifications
    ]
}
```

### Error Recovery
```python
async def handle_execution_error(self, error, order):
    """Graceful error handling"""
    
    if error.type == 'CONNECTION_LOST':
        await self.reconnect_gateway()
        await self.retry_order(order, max_attempts=3)
        
    elif error.type == 'MARGIN_INSUFFICIENT':
        await self.reduce_position_size(order)
        await self.retry_with_smaller_size(order)
        
    elif error.type == 'MARKET_CLOSED':
        await self.queue_for_next_session(order)
        
    elif error.type == 'MANDATE_VIOLATION':
        await self.log_violation(error)
        await self.notify_admin(error)
        # Do NOT retry - hard stop
        
    else:
        await self.emergency_shutdown()
```

## 📈 Performance Monitoring

### Real-Time Metrics
```python
PERFORMANCE_METRICS = {
    'execution': {
        'orders_per_minute': Monitor(window=60),
        'fill_rate': Monitor(window=300),
        'average_slippage': Monitor(window=900),
        'rejected_orders': Counter()
    },
    'pnl': {
        'realized_pnl': Accumulator(),
        'unrealized_pnl': LiveCalculator(),
        'win_rate': RollingAverage(100),
        'profit_factor': RollingRatio()
    },
    'risk': {
        'var_95': ValueAtRisk(0.95),
        'max_drawdown': DrawdownTracker(),
        'sharpe_ratio': SharpeCalculator(),
        'correlation': CorrelationMatrix()
    }
}
```

### Logging & Audit Trail
```python
# Comprehensive logging
logging.config = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/trading.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 30
        },
        'database': {
            'class': 'DatabaseLogHandler',
            'connection': 'postgresql://localhost/trading_log'
        },
        'alerts': {
            'class': 'AlertHandler',
            'channels': ['email', 'sms', 'discord']
        }
    },
    'loggers': {
        'trades': {'level': 'INFO', 'handlers': ['file', 'database']},
        'errors': {'level': 'ERROR', 'handlers': ['file', 'alerts']},
        'audit': {'level': 'DEBUG', 'handlers': ['database']}
    }
}
```

## 🐛 Troubleshooting

### Common Issues

1. **Gateway won't connect**
   ```bash
   # Check gateway status
   systemctl status ibkr-gateway
   
   # Test connection
   curl -k https://localhost:5000/v1/api/iserver/accounts
   
   # Check logs
   tail -f /var/log/ibgateway/gateway.log
   ```

2. **Orders rejected**
   ```bash
   # Check mandate violations
   python -c "from trading.mandate import check_violations; check_violations()"
   
   # Verify margin
   python -c "from trading.account import get_buying_power; print(get_buying_power())"
   ```

3. **No trades executing**
   ```bash
   # Check timing restrictions
   python -c "from trading.timer import should_trade_now; print(should_trade_now())"
   
   # Verify market hours
   python -c "from trading.market import is_market_open; print(is_market_open())"
   ```

### Debug Mode
```bash
# Maximum verbosity
DEBUG=1 LOGLEVEL=DEBUG python main.py run --debug --dry-run

# Specific module debugging
DEBUG_MODULES=waves,mandate,timer python main.py run

# Step-through mode
python -m pdb main.py run --step-through
```

## 🚀 Production Deployment

### Docker Container
```dockerfile
FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    openjdk-11-jre \
    curl

# Install IB Gateway
COPY scripts/install_gateway.sh /tmp/
RUN /tmp/install_gateway.sh

# Copy application
COPY . /app
WORKDIR /app

# Install Python packages
RUN pip install -r requirements.txt

# Entry point
CMD ["python", "main.py", "run", "--mandate", "moderate"]
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fntx-trader
spec:
  replicas: 1  # Single instance for trading
  template:
    spec:
      containers:
      - name: trader
        image: fntx/trader:latest
        env:
        - name: MANDATE_LEVEL
          value: "moderate"
        - name: TRADING_SYMBOL
          value: "SPY"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
```

## 📚 Additional Resources

### Related Documentation
- [DASHBOARD_COMMAND.md](./DASHBOARD_COMMAND.md) - Monitoring interface
- [IBKR OAuth Guide](../oauth/README.md) - Authentication setup
- [Wave Pattern Theory](../strategies/wave_pattern.md) - Algorithm details
- [Mandate Framework](../risk/mandate_system.md) - Risk controls

### Configuration Files
- `config/trading.yaml` - Main configuration
- `config/mandates/` - Mandate definitions
- `config/strategies/` - Strategy parameters
- `config/timing/` - Trading windows

### Support
- GitHub Issues: [github.com/your-org/fntx-ai-v1/issues](https://github.com)
- Documentation: [docs.fntx.ai](https://docs.fntx.ai)
- Emergency: [emergency@fntx.ai](mailto:emergency@fntx.ai)

---

*Last Updated: December 2024*
*Version: 1.0.0*
*Status: Production Ready*
*Maintained by: FNTX AI Team*