# FNTX AI Agent Orchestration System

## 🚀 Overview

The FNTX AI Orchestration System coordinates 5 specialized AI agents to execute autonomous SPY options trading with full transparency and user control. Each trade journey is tracked step-by-step with real-time updates, risk assessments, and agent rationale.

## 🤖 Agent Architecture

### Core Agents
1. **EnvironmentWatcherAgent** - Market monitoring and regime detection
2. **StrategicPlannerAgent** - Strategy formulation and planning  
3. **RewardModelAgent** - RLHF and preference optimization
4. **ExecutorAgent** - Trade execution with IBKR integration
5. **EvaluatorAgent** - Performance monitoring and analysis

### Orchestration Flow
```
User Request → Environment Analysis → Strategic Planning → Reward Optimization → Execution → Evaluation
```

## 📁 File Structure

```
agents/
├── orchestrator.py              # Main orchestration engine
├── api_server.py               # REST API for frontend
├── demo_orchestration.py       # End-to-end demo script
├── strategic_planner.py        # Strategy planning agent
├── executor.py                 # Trade execution agent
├── evaluator.py               # Performance evaluation agent
├── environment_watcher.py      # Market monitoring agent
├── reward_model.py            # RLHF preference learning agent
├── requirements.txt           # Python dependencies
└── memory/                    # MCP-compatible memory files
    ├── trade_journey.json     # Real-time trade progression
    ├── shared_context.json    # Inter-agent communication
    ├── orchestrator_memory.json # Orchestration history
    ├── executor_memory.json   # Trade execution logs
    ├── reward_model_memory.json # User preferences & RLHF
    ├── evaluator_memory.json  # Performance analytics
    └── environment_watcher_memory.json # Market data & regime

src/components/Trading/
├── TradeOrchestrator.tsx      # Main orchestration UI
├── TradeStepper.tsx          # Step-by-step journey display
└── ...
```

## 🛠️ Setup & Installation

### 1. Install Python Dependencies
```bash
cd agents/
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
cp .env.example .env
```

Edit `.env` with your settings:
```bash
# Trading Mode
TRADING_MODE=paper  # Set to "live" for live trading

# Interactive Brokers Configuration
IBKR_HOST=127.0.0.1
IBKR_PORT=4002      # 4002 for paper trading
IBKR_CLIENT_ID=2

# API Keys
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Interactive Brokers Setup
1. Install TWS or IBKR Gateway
2. Configure for paper trading (port 4002)
3. Enable API connections in TWS/Gateway settings
4. Set socket port to 4002 for paper trading

### 4. Create Log Directory
```bash
mkdir -p logs/
```

## 🚀 Running the System

### Option 1: Full API Server (Recommended)
```bash
# Start the API server (includes orchestrator)
cd agents/
python api_server.py
```

API will be available at: `http://localhost:8000`

### Option 2: Demo Mode
```bash
# Run interactive demo
cd agents/
python demo_orchestration.py
```

### Option 3: Direct Orchestration
```bash
# Test orchestrator directly
cd agents/
python orchestrator.py
```

## 🖥️ Frontend Integration

### React Components

#### TradeOrchestrator Component
```tsx
import { TradeOrchestrator } from '@/components/Trading/TradeOrchestrator';

// In your app
<TradeOrchestrator />
```

#### TradeStepper Component
```tsx
import { TradeStepper } from '@/components/Trading/TradeStepper';

<TradeStepper 
  journeyData={tradeJourney}
  onRefresh={() => loadTradeJourney()}
/>
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/orchestrator/execute` | POST | Start new trade orchestration |
| `/api/orchestrator/journey/{trade_id}` | GET | Get trade journey details |
| `/api/orchestrator/current-journey` | GET | Get current active journey |
| `/api/orchestrator/stats` | GET | Get orchestration statistics |
| `/api/orchestrator/recent-trades` | GET | Get recent trade history |
| `/api/agents/{agent}/memory` | GET | Get agent memory state |
| `/api/shared-context` | GET | Get shared agent context |

### Example API Usage

#### Start Trade Orchestration
```javascript
const response = await fetch('/api/orchestrator/execute', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_request: "What's the best SPY PUT selling opportunity today?",
    timestamp: new Date().toISOString()
  })
});

const result = await response.json();
console.log('Trade ID:', result.trade_id);
```

#### Poll Trade Progress
```javascript
const pollTradeProgress = async (tradeId) => {
  const response = await fetch(`/api/orchestrator/journey/${tradeId}`);
  const journey = await response.json();
  
  console.log('Current phase:', journey.current_phase);
  console.log('Steps completed:', journey.steps.length);
  
  // Continue polling if not completed
  if (!journey.final_outcome) {
    setTimeout(() => pollTradeProgress(tradeId), 2000);
  }
};
```

## 📊 Trade Journey Structure

### Journey JSON Format
```json
{
  "trade_id": "FNTX_20241212_143022",
  "user_request": "What's the best SPY PUT selling opportunity today?",
  "initiated_at": "2024-12-12T14:30:22.000Z",
  "current_phase": "tactical_execution",
  "steps": [
    {
      "timestamp": "2024-12-12T14:30:25.000Z",
      "agent": "EnvironmentWatcherAgent",
      "action": "Market analysis completed",
      "rationale": "Market analysis complete: favorable_for_selling regime, VIX at 12.8",
      "status": "completed",
      "confidence_level": 0.85,
      "risk_assessment": {
        "market_regime": "favorable_for_selling",
        "vix_level": 12.8,
        "conditions_favorable": true
      },
      "execution_time": 3.2
    }
  ],
  "risk_assessment": {
    "overall_risk": "low",
    "confidence_level": 0.82,
    "max_exposure": 200.0,
    "stop_loss_level": 437.25
  },
  "final_outcome": {
    "success": true,
    "message": "Trade orchestration completed successfully",
    "completed_at": "2024-12-12T14:33:45.000Z",
    "total_steps": 5,
    "agent_statuses": {
      "environment_watcher": "completed",
      "strategic_planner": "completed",
      "reward_model": "completed",
      "executor": "completed",
      "evaluator": "completed"
    }
  },
  "execution_time": 203.4,
  "errors": []
}
```

## 🔧 Configuration Options

### Orchestrator Settings
```python
# In orchestrator.py
class FNTXOrchestrator:
    def __init__(self):
        self.max_execution_time = 300  # 5 minutes max
        self.enable_live_trading = False  # Paper trading by default
```

### Agent Memory Configuration
Each agent maintains MCP-compatible memory:
- **Persistent**: Survives restarts
- **Structured**: JSON schema validation  
- **Auditable**: Full transaction history
- **Shareable**: Inter-agent communication

### Risk Management
```python
# Default risk parameters
risk_parameters = {
    "max_daily_risk": 0.02,
    "position_limit": 3,
    "stop_loss_multiplier": 3.0,
    "take_profit_multiplier": 0.5
}
```

## 🧪 Testing & Demo

### Demo Scenarios
1. **Best SPY Trade Analysis** - Comprehensive market analysis
2. **Safe Premium Collection** - Conservative, high-probability trades  
3. **Market Regime Analysis** - Full environment assessment

### Running Demos
```bash
cd agents/
python demo_orchestration.py

# Choose option:
# 1. Quick status check
# 2. Single demo trade  
# 3. Full demo suite
# 4. Show memory files
```

### Test Commands
```bash
# Test individual agents
python strategic_planner.py
python environment_watcher.py
python reward_model.py

# Test executor (requires IBKR)
python executor.py

# Test API server
curl http://localhost:8000/api/health
```

## 📈 Monitoring & Analytics

### Real-Time Monitoring
- **Trade Progress**: Step-by-step execution tracking
- **Agent Status**: Individual agent health and performance
- **Risk Metrics**: Live risk assessment and exposure
- **Performance**: Win rates, execution times, success rates

### Log Files
```bash
logs/
├── orchestrator.log     # Main orchestration events
├── api_server.log       # API requests and responses  
├── executor.log         # Trade execution details
├── environment_watcher.log # Market monitoring
├── strategic_planner.log  # Strategy generation
├── reward_model.log     # RLHF and preferences
├── evaluator.log        # Performance analysis
└── demo.log            # Demo session logs
```

### Memory Inspection
```python
# View agent memory
import json

with open('agents/memory/trade_journey.json') as f:
    journey = json.load(f)
    print(f"Current phase: {journey['current_phase']}")
    print(f"Steps: {len(journey['steps'])}")
```

## 🔒 Security & Safety

### Paper Trading Default
- All trading defaults to paper mode
- Live trading requires explicit configuration
- Multiple safety checks before live execution

### Risk Controls
- Maximum position limits
- Stop-loss automation
- Exposure monitoring
- Circuit breakers for unusual conditions

### Data Security
- No sensitive data in logs
- API key encryption
- Secure memory storage
- Audit trail for all actions

## 🚨 Troubleshooting

### Common Issues

#### 1. IBKR Connection Failed
```bash
# Check TWS/Gateway is running
# Verify port 4002 is open
# Ensure API is enabled in TWS settings
```

#### 2. Agent Memory Errors
```bash
# Check file permissions
chmod 755 agents/memory/
# Verify JSON format
python -m json.tool agents/memory/shared_context.json
```

#### 3. API Server Not Starting
```bash
# Check port 8000 is available
lsof -i :8000
# Install dependencies
pip install -r agents/requirements.txt
```

#### 4. Frontend Connection Issues
```bash
# Verify CORS settings in api_server.py
# Check React dev server is on port 3000
# Confirm API base URL in frontend
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python api_server.py
```

### Memory Reset
```bash
# Clear all memory files (careful!)
rm agents/memory/*.json
# Agents will recreate with defaults
```

## 🔄 Development Workflow

### Adding New Agents
1. Create agent class with MCP memory interface
2. Add to orchestrator agent list  
3. Update UI stepper with agent icon/color
4. Add API endpoints for agent memory
5. Include in demo scenarios

### Extending Strategies
1. Add to `strategic_planner.py` default_strategies
2. Implement custom evaluation logic
3. Update risk assessment parameters
4. Test with demo orchestration

### UI Customization
1. Modify `TradeStepper.tsx` for new step types
2. Update `TradeOrchestrator.tsx` for new controls
3. Add agent icons and colors
4. Customize status displays

## 📚 Additional Resources

- [IBKR API Documentation](https://interactivebrokers.github.io/tws-api/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React TypeScript Guide](https://react-typescript-cheatsheet.netlify.app/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

## 🎯 Next Steps

1. **WebSocket Integration** - Real-time updates without polling
2. **Advanced Risk Models** - VaR, Monte Carlo simulations
3. **Multi-Asset Support** - QQQ, IWM options
4. **Backtesting Engine** - Historical strategy validation
5. **Mobile Interface** - Trade monitoring on mobile
6. **Advanced Analytics** - Performance attribution, correlation analysis

---

**⚠️ Important**: This system is for educational and paper trading purposes. Always thoroughly test with paper trading before considering live markets. Trading involves substantial risk of loss.

For support or questions, please check the [GitHub Issues](https://github.com/your-repo/fntx-ai/issues) or refer to the comprehensive logs in the `logs/` directory.