# 🧹 FNTX.ai Agent Architecture Cleanup Plan

## 🎯 **Objective**
Consolidate to exactly **5 agents** as designed, eliminate duplicates, and enhance EnvironmentWatcher for live IBKR market data.

## 📊 **Current State Analysis**

### ✅ **Keep These 5 Core Agents**
1. **`strategic_planner.py`** - StrategicPlannerAgent (Main strategy formulation)
2. **`executor.py`** - ExecutorAgent (Trade execution with IBKR)  
3. **`evaluator.py`** - EvaluatorAgent (Performance monitoring)
4. **`environment_watcher.py`** - EnvironmentWatcherAgent (Market monitoring)
5. **`reward_model.py`** - RewardModelAgent (RLHF & user preferences)

### ❌ **Remove These Duplicate/Legacy Files**
1. **`planner.py`** - Old simple rule-based planner (superseded by strategic_planner.py)
2. **`worker.py`** - Old basic IBKR API worker (superseded by executor.py)

### 🔧 **Support Files (Keep)**
- `orchestrator.py` - Coordinates all 5 agents
- `api_server.py` - REST API for frontend
- `demo_orchestration.py` - Testing and demos
- `test_executor.py` - Agent testing

## 🗑️ **Step 1: Remove Duplicate Files**

### Files to Delete:
```bash
rm /Users/jimmyhou/CascadeProjects/fntx-ai-v10/agents/planner.py
rm /Users/jimmyhou/CascadeProjects/fntx-ai-v10/agents/worker.py
```

### Why Delete These:
- **`planner.py`**: Simple 20-line rule-based planner, completely superseded by sophisticated `strategic_planner.py` with market analysis, risk assessment, and MCP integration
- **`worker.py`**: Basic IBKR API wrapper, superseded by comprehensive `executor.py` with bracket orders, risk management, and orchestration integration

## 🚀 **Step 2: Enhance EnvironmentWatcher for Live IBKR Data**

### Current State:
- Uses simulated market data
- Basic regime detection
- No real-time IBKR integration

### Enhancement Plan:
1. **Live Market Data Integration**
   - Connect to IBKR for real-time SPY prices
   - Real-time VIX data from IBKR
   - Live options chain data
   - Market hours detection

2. **Advanced Market Analysis**
   - Real support/resistance calculation
   - Volume profile analysis
   - Intraday volatility tracking
   - Options flow analysis

3. **Enhanced Regime Detection**
   - Real-time volatility regime changes
   - Market microstructure analysis
   - News sentiment integration (optional)
   - Economic calendar integration

## 📋 **Step 3: Final Agent Architecture**

### The Perfect 5-Agent System:

```
┌─────────────────────────────────────────────────────────────┐
│                    FNTX.ai Agent Architecture               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. EnvironmentWatcherAgent    2. StrategicPlannerAgent     │
│     - Live IBKR market data       - Strategy formulation   │
│     - VIX/SPY real-time           - Risk assessment        │
│     - Regime detection            - Market analysis        │
│     - Support/resistance          - Trade recommendations  │
│                                                             │
│  3. RewardModelAgent           4. ExecutorAgent            │
│     - RLHF learning              - IBKR trade execution    │
│     - User preferences           - Bracket orders          │
│     - Performance feedback       - Risk management         │
│     - Strategy optimization      - Position monitoring     │
│                                                             │
│  5. EvaluatorAgent                                          │
│     - Performance analysis                                  │
│     - Weekly reports                                        │
│     - Risk assessment                                       │
│     - Improvement suggestions                               │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                     Orchestrator                           │
│           Coordinates all 5 agents seamlessly              │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 **Implementation Steps**

### Phase 1: Cleanup (Immediate)
- [ ] Delete `planner.py` and `worker.py`
- [ ] Update any imports that reference old files
- [ ] Test orchestrator still works with 5 core agents
- [ ] Update documentation

### Phase 2: EnvironmentWatcher Enhancement (Next Priority)
- [ ] Add live IBKR market data connection
- [ ] Implement real-time VIX fetching
- [ ] Add live SPY options chain analysis
- [ ] Enhance regime detection with real data
- [ ] Add volume and volatility analysis

### Phase 3: Integration & Testing
- [ ] Test enhanced EnvironmentWatcher with live data
- [ ] Validate orchestration with real market feeds
- [ ] Performance test with live IBKR connection
- [ ] Update UI to show real market data

### Phase 4: Live Trading Readiness
- [ ] Switch from paper to live IBKR account
- [ ] Implement live trading safeguards
- [ ] Add real-time risk monitoring
- [ ] Deploy production orchestration

## 🎯 **Expected Benefits**

### After Cleanup:
- ✅ Clean, maintainable codebase
- ✅ No duplicate functionality
- ✅ Clear separation of concerns
- ✅ Exactly 5 specialized agents

### After EnvironmentWatcher Enhancement:
- 🔴 Real-time market data (live VIX, SPY)
- 🔴 Live options chain analysis
- 🔴 Accurate regime detection
- 🔴 Real support/resistance levels
- 🔴 Production-ready market monitoring

### After Live IBKR Integration:
- 💚 Real trading capability
- 💚 Live market responsiveness
- 💚 Accurate risk assessment
- 💚 Professional-grade execution

## ⚠️ **Risk Mitigation**

### During Cleanup:
- Backup current working system
- Test orchestrator after file removal
- Verify all imports and dependencies

### During EnvironmentWatcher Enhancement:
- Test with paper trading first
- Implement rate limiting for IBKR API
- Add connection failure fallbacks
- Monitor API usage limits

### Before Live Trading:
- Extensive testing with small positions
- Multiple safety checks and circuit breakers
- Real-time monitoring and alerts
- Emergency stop mechanisms

## 🚀 **Next Immediate Actions**

1. **Confirm cleanup approach** with user
2. **Delete duplicate files** (planner.py, worker.py)
3. **Test orchestrator** still works properly
4. **Begin EnvironmentWatcher enhancement** for live IBKR data
5. **Plan live account transition** strategy