# SPY Options RL Trading - Testing & Iteration Plan

## Phase 1: Initial Testing (Week 1)

### Monday Market Open Testing Setup

```python
# serve_model.py - Simple inference server
import numpy as np
from stable_baselines3 import PPO
from datetime import datetime
import json

class TradingModelServer:
    def __init__(self, model_path):
        self.model = PPO.load(model_path)
        self.positions = {'calls': 0, 'puts': 0}
        self.trades_today = []
        
    def get_recommendation(self, market_state):
        """
        Input: Current market state
        Output: Action (0=hold, 1=sell_call, 2=sell_put)
        """
        obs = self._prepare_observation(market_state)
        action, _ = self.model.predict(obs, deterministic=True)
        
        # Log decision
        self.log_decision(market_state, action)
        
        return {
            'action': int(action),
            'action_name': ['hold', 'sell_call', 'sell_put'][action],
            'confidence': self._get_confidence(obs),
            'timestamp': datetime.now().isoformat()
        }
```

### Testing Protocol

1. **Paper Trading Mode** (Week 1)
   ```bash
   # Run every 5 minutes during market hours
   python paper_trade.py --model ppo_2m --log results/week1/
   ```

2. **Metrics to Track**
   - Win rate (% profitable trades)
   - Average P&L per trade
   - Maximum drawdown
   - Sharpe ratio
   - Time in position
   - Risk score distribution

3. **Daily Review Process**
   ```python
   # end_of_day_analysis.py
   def analyze_day(date):
       trades = load_trades(date)
       print(f"Total trades: {len(trades)}")
       print(f"Calls sold: {sum(1 for t in trades if t['type']=='call')}")
       print(f"Puts sold: {sum(1 for t in trades if t['type']=='put')}")
       print(f"P&L: ${calculate_pnl(trades)}")
       print(f"Win rate: {calculate_win_rate(trades):.1%}")
   ```

## Phase 2: Model Refinement Plan

### A. Quick Fixes (No Retraining Needed)

1. **Adjust Risk Thresholds**
   ```python
   # config_override.py
   RISK_OVERRIDES = {
       'position_size': {
           'low_risk': 20,    # Instead of 30
           'medium_risk': 15, # Instead of 20
           'high_risk': 5     # Instead of 10
       },
       'delta_constraint': 0.15  # Tighter than 0.20
   }
   ```

2. **Time-Based Filters**
   ```python
   # Don't trade first/last 30 minutes
   if minutes_since_open < 30 or minutes_until_close < 30:
       return 'hold'
   ```

### B. Model Improvements (Requires Retraining)

#### Week 2: Ensemble Implementation
```python
# ensemble_trainer.py
models = {
    'ppo': PPO(**ppo_config),
    'a2c': A2C(**a2c_config),
    'dqn': DQN(**dqn_config)
}

# Train each model separately
for name, model in models.items():
    model.learn(total_timesteps=2_000_000)
    model.save(f"models/{name}_2m")

# Ensemble prediction
def ensemble_predict(market_state):
    predictions = {}
    for name, model in loaded_models.items():
        action = model.predict(market_state)[0]
        predictions[name] = action
    
    # Weighted voting
    weights = {'ppo': 0.5, 'a2c': 0.3, 'dqn': 0.2}
    return weighted_vote(predictions, weights)
```

#### Week 3: Add QQQ Data
```python
# 1. Collect QQQ options data
python collect_historical_data.py --symbol QQQ --start 2022-01-01

# 2. Create multi-asset environment
class MultiAssetOptionsEnv(SPY0DTEEnvironment):
    def __init__(self, symbols=['SPY', 'QQQ']):
        self.symbols = symbols
        self.current_symbol = None
        
    def reset(self):
        # Randomly select symbol for episode
        self.current_symbol = np.random.choice(self.symbols)
        return super().reset()

# 3. Retrain on combined dataset
python train_multi_asset.py --symbols SPY,QQQ --timesteps 4000000
```

### C. Advanced Refinements

#### 1. RLHF Implementation (Week 4+)
```python
# preference_learning.py
class PreferenceDataset:
    """Collect human preferences on trades"""
    
    def collect_feedback(self, trade_pair):
        # Show two trades
        display_trade_comparison(trade_pair)
        
        # Get preference
        preference = input("Which trade was better? (1/2): ")
        
        # Store for reward model training
        self.preferences.append({
            'trade_a': trade_pair[0],
            'trade_b': trade_pair[1],
            'preference': preference
        })

# Train reward model from preferences
reward_model = train_reward_model(preference_dataset)

# Fine-tune RL agent with learned rewards
model.learn(total_timesteps=500000, 
           reward_fn=reward_model.predict)
```

#### 2. Market Regime Adaptation
```python
# regime_detector.py
def detect_market_regime(market_data):
    """Identify current market conditions"""
    vix = market_data['vix']
    trend = calculate_trend(market_data['spy_prices'])
    
    if vix > 25:
        return 'high_volatility'
    elif trend > 0.02:
        return 'strong_uptrend'
    elif trend < -0.02:
        return 'strong_downtrend'
    else:
        return 'neutral'

# Use different models for different regimes
models = {
    'high_volatility': load_model('ppo_high_vol'),
    'strong_uptrend': load_model('ppo_uptrend'),
    'strong_downtrend': load_model('ppo_downtrend'),
    'neutral': load_model('ppo_neutral')
}
```

## Iteration Workflow

### 1. Daily Testing Cycle
```bash
# Morning (9:20 AM)
./scripts/start_paper_trading.sh

# During market hours
tail -f logs/paper_trades.log

# After close (4:15 PM)
python analyze_daily_performance.py --date today

# Evening review
python generate_improvement_report.py
```

### 2. Weekly Model Updates

**If performance is poor:**
```python
# 1. Analyze failure modes
python analyze_losses.py --week 1

# 2. Identify patterns
# - Losing trades cluster at certain times?
# - Specific market conditions?
# - Position sizing issues?

# 3. Quick fixes first
python update_config.py --reduce-risk --tighten-delta

# 4. Retrain if needed (weekend)
./scripts/weekend_retrain.sh
```

### 3. GPU VM Usage Pattern

```bash
# Weekly retraining schedule (Sundays)
0 18 * * 0 /home/info/scripts/weekly_retrain.sh

# weekly_retrain.sh:
#!/bin/bash
# Start GPU instance
aws ec2 start-instances --instance-ids i-xxxxx

# Wait for instance
sleep 60

# Transfer latest data
./scripts/transfer_week_data.sh

# SSH and retrain
ssh fntx-ai-gpu "cd spy_options && ./retrain_with_new_data.sh"

# Transfer model back
./scripts/post_training_transfer.sh

# Stop GPU instance
aws ec2 stop-instances --instance-ids i-xxxxx
```

## Success Metrics & Decision Points

### Week 1 Evaluation
- **Continue if:** Win rate > 60%, Positive P&L
- **Refine if:** Win rate 50-60%, Break-even P&L
- **Major changes if:** Win rate < 50%, Negative P&L

### Refinement Priority Order
1. **Risk management** (position sizing, stop losses)
2. **Entry timing** (avoid first/last 30 min)
3. **Market filters** (VIX, trend strength)
4. **Model ensemble** (if single model insufficient)
5. **Multi-asset** (add QQQ if SPY successful)
6. **RLHF** (once baseline profitable)

## Emergency Protocols

```python
# kill_switch.py
def emergency_stop():
    """Stop all trading if drawdown exceeds limit"""
    if calculate_drawdown() > 0.10:  # 10% drawdown
        print("EMERGENCY STOP ACTIVATED")
        disable_trading()
        send_alert("Trading halted due to drawdown")
```

## Timeline Summary

- **Week 1**: Paper trade single PPO model on SPY
- **Week 2**: Implement quick fixes based on results
- **Week 3**: Add ensemble if needed
- **Week 4**: Expand to QQQ if SPY successful
- **Month 2**: Implement RLHF with real trade feedback
- **Month 3**: Full production with regime adaptation