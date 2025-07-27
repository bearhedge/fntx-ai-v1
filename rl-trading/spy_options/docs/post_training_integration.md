# Post-Training Integration Workflow

## Phase 1: Model Transfer & Basic Setup (Hour 1 after training)

### 1.1 Transfer Model to CPU
```bash
# On CPU VM
./scripts/post_training_transfer.sh

# Creates:
# - models/gpu_trained/ppo_2m_final.zip
# - models/gpu_trained/training_metadata.json
```

### 1.2 Create Inference API
```python
# serve_model_api.py
from fastapi import FastAPI
from stable_baselines3 import PPO

app = FastAPI()
model = PPO.load("models/gpu_trained/ppo_2m_final")

@app.post("/predict")
def predict(state: MarketState):
    obs = prepare_observation(state)
    action, _ = model.predict(obs)
    return {"action": int(action), "confidence": float(_)}
```

## Phase 2: Broker Integration (Hour 2-3)

### 2.1 Connect to Broker API
```python
# broker_connector.py
class BrokerConnector:
    def __init__(self, broker_type='alpaca'):
        if broker_type == 'alpaca':
            self.api = AlpacaAPI()
        elif broker_type == 'tdameritrade':
            self.api = TDAmeritradeAPI()
        # etc
    
    def get_spy_quote(self):
        return self.api.get_quote('SPY')
    
    def get_0dte_options(self):
        today = datetime.now().strftime('%Y-%m-%d')
        return self.api.get_options_chain('SPY', expiry=today)
    
    def place_order(self, symbol, quantity, order_type):
        return self.api.submit_order(...)
```

### 2.2 Real-time Data Feed
```python
# market_data_feed.py
class MarketDataFeed:
    def __init__(self):
        self.ws = WebSocketClient()
        self.current_state = {}
    
    def start_feed(self):
        self.ws.subscribe(['SPY', 'VIX'])
        self.ws.on_message = self.update_state
    
    def get_current_state(self):
        return {
            'spy_price': self.current_state['SPY']['last'],
            'spy_bid': self.current_state['SPY']['bid'],
            'spy_ask': self.current_state['SPY']['ask'],
            'vix': self.current_state['VIX']['last'],
            'timestamp': datetime.now()
        }
```

## Phase 3: RLHF Feedback System (Day 1-2)

### 3.1 Feedback Collection Database
```sql
-- feedback_schema.sql
CREATE TABLE suggestions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    market_state JSONB,
    model_action INTEGER,
    user_decision VARCHAR(10),
    user_comment TEXT,
    executed BOOLEAN,
    fill_price DECIMAL(10,2)
);

CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    suggestion_id INTEGER REFERENCES suggestions(id),
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    entry_price DECIMAL(10,2),
    exit_price DECIMAL(10,2),
    pnl DECIMAL(10,2),
    user_rating INTEGER,
    user_feedback TEXT
);
```

### 3.2 Comment Analysis for RLHF
```python
# comment_analyzer.py
from transformers import pipeline

class CommentAnalyzer:
    def __init__(self):
        self.sentiment = pipeline("sentiment-analysis")
        self.classifier = pipeline("zero-shot-classification")
    
    def analyze_feedback(self, comment):
        # Sentiment
        sentiment = self.sentiment(comment)[0]
        
        # Classify reason for decision
        labels = ["timing", "volatility", "trend", "risk", "other"]
        classification = self.classifier(comment, labels)
        
        # Extract specific signals
        signals = {
            'too_early': 'early' in comment.lower(),
            'too_risky': 'risk' in comment.lower(),
            'wrong_direction': any(w in comment.lower() for w in ['wrong', 'opposite']),
            'good_setup': any(w in comment.lower() for w in ['good', 'perfect', 'nice'])
        }
        
        return {
            'sentiment': sentiment,
            'primary_reason': classification['labels'][0],
            'signals': signals
        }
```

## Phase 4: Complete Integration (Day 2-3)

### 4.1 Main Trading Interface
```python
# main_trading_interface.py
class TradingInterface:
    def __init__(self):
        self.model_api = ModelAPI()
        self.broker = BrokerConnector()
        self.data_feed = MarketDataFeed()
        self.feedback_db = FeedbackDatabase()
        self.state_manager = TradeStateManager()
        
    def run(self):
        print("SPY 0DTE Trading System")
        print("-" * 40)
        
        self.data_feed.start_feed()
        
        while market_is_open():
            state = self.state_manager.current_state
            
            if state == 'NO_POSITION':
                self.check_for_opportunities()
            elif state == 'POSITION_OPEN':
                self.manage_position()
            elif state == 'POSITION_CLOSED':
                self.collect_feedback()
            
            time.sleep(1)
    
    def check_for_opportunities(self):
        # Get market data
        market_state = self.data_feed.get_current_state()
        
        # Get model prediction
        prediction = self.model_api.predict(market_state)
        
        if prediction['action'] != 0:  # Not hold
            self.present_suggestion(prediction, market_state)
    
    def present_suggestion(self, prediction, market_state):
        # Format suggestion
        action_type = ['hold', 'sell_call', 'sell_put'][prediction['action']]
        
        print(f"\n[{datetime.now().strftime('%H:%M')}] SUGGESTION")
        print(f"Action: {action_type}")
        print(f"SPY: ${market_state['spy_price']:.2f}")
        print(f"VIX: {market_state['vix']:.1f}")
        
        # Get user decision with comment
        decision = input("Execute? (y/n/skip): ")
        comment = input("Comment (optional): ") if decision != 'skip' else ''
        
        # Save to database
        suggestion_id = self.feedback_db.save_suggestion(
            market_state, prediction, decision, comment
        )
        
        if decision == 'y':
            self.execute_trade(suggestion_id, action_type)
```

### 4.2 Weekend Retraining Pipeline
```python
# retrain_with_feedback.py
def retrain_with_rlhf():
    # 1. Load original model
    base_model = PPO.load("models/gpu_trained/ppo_2m_final")
    
    # 2. Load feedback data
    feedback_data = load_feedback_from_db()
    
    # 3. Create reward model from feedback
    reward_model = train_reward_model(feedback_data)
    
    # 4. Fine-tune with new rewards
    model = PPO.load("models/gpu_trained/ppo_2m_final")
    model.learn(
        total_timesteps=100000,  # Short fine-tuning
        callback=RLHFCallback(reward_model)
    )
    
    # 5. Save new version
    model.save(f"models/rlhf/model_v{get_next_version()}")
```

## Phase 5: Production Guardrails

### 5.1 Risk Limits
```python
PRODUCTION_LIMITS = {
    'max_daily_trades': 2,
    'max_position_size': 1,  # For $80k account
    'max_daily_loss': 500,   # Dollar stop
    'required_time_between_trades': 7200,  # 2 hours
    'blackout_times': [
        (9, 30, 10, 0),   # First 30 min
        (15, 30, 16, 0)   # Last 30 min
    ]
}
```

### 5.2 Emergency Controls
```python
class EmergencyControls:
    def check_limits(self):
        if self.daily_loss > PRODUCTION_LIMITS['max_daily_loss']:
            self.shutdown("Daily loss limit hit")
        
        if self.consecutive_losses > 3:
            self.shutdown("3 consecutive losses")
        
        if self.model_confidence < 0.6:
            self.pause("Low model confidence")
```

## Implementation Timeline

**Day 0 (Today)**: Model training completes
**Day 1 (Monday)**:
- Morning: Transfer model, test basic predictions
- Afternoon: Connect broker API, test data feeds

**Day 2 (Tuesday)**:
- Implement suggestion interface
- Start collecting feedback

**Week 1**: 
- Collect 50-100 feedback samples
- First RLHF retrain on weekend

**Week 2**:
- Refined model with your preferences
- Gradual increase in trust/automation