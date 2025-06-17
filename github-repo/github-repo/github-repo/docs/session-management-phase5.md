# Phase 5: Session Management System

## Overview

The Session Management System provides comprehensive lifecycle management for trading sessions in FNTX.ai. It enables stateful trading operations with full persistence, recovery capabilities, and multi-agent coordination across sessions.

## Architecture

### Core Components

1. **Session Lifecycle Manager** (`lifecycle_manager.py`)
   - Creates and manages trading sessions
   - Handles state transitions (active, paused, suspended, closed)
   - Coordinates agent initialization and shutdown
   - Implements auto-start/stop conditions
   - Manages session templates

2. **Session State Manager** (`state_manager.py`)
   - Persists session state across storage tiers
   - Creates and manages checkpoints
   - Handles session recovery and restoration
   - Validates state integrity
   - Archives historical sessions

3. **Session Schemas** (`schemas.py`)
   - Defines all session-related data models
   - Provides type safety and validation
   - Ensures consistency across components

### Storage Architecture

```
┌─────────────────┐
│  Active Session │
│    (Memory)     │
└────────┬────────┘
         │
    ┌────▼─────┐
    │  Redis   │ ◄── Hot Storage (7 days)
    │  Cache   │
    └────┬─────┘
         │
  ┌──────▼──────┐
  │ PostgreSQL  │ ◄── Warm Storage (30 days)
  │  Database   │
  └──────┬──────┘
         │
   ┌─────▼─────┐
   │    GCS    │ ◄── Cold Storage (Archive)
   │  Archive  │
   └───────────┘
```

## Key Features

### 1. Session Lifecycle Management

```python
# Create a new session
session = await lifecycle_manager.create_session(
    session_type=SessionType.REGULAR,
    config={
        "close_positions_on_stop": True,
        "allow_overnight_positions": False
    }
)

# Start trading
await lifecycle_manager.start_session(session.session_id)

# Pause during volatile conditions
await lifecycle_manager.pause_session(session.session_id, reason="high_volatility")

# Resume when conditions improve
await lifecycle_manager.resume_session(session.session_id)

# Stop and close positions
await lifecycle_manager.stop_session(session.session_id)
```

### 2. Checkpoint & Recovery

```python
# Automatic checkpointing every 15 minutes
checkpoint = await state_manager.create_checkpoint(session)

# List available checkpoints
checkpoints = await state_manager.list_checkpoints(session_id, limit=10)

# Restore from checkpoint
success = await state_manager.restore_from_checkpoint(session, checkpoint_id)

# Create recovery plan
plan = await state_manager.create_recovery_plan(session_id)

# Execute recovery
success = await state_manager.execute_recovery_plan(plan)
```

### 3. Session Templates

```python
# Use pre-defined templates
session = await lifecycle_manager.create_session_from_template(
    "Regular Trading",
    overrides={"position_limit": 5}
)

# Templates include:
# - Regular Trading: Standard market hours SPY options
# - Extended Hours: Pre/post market trading
# - Paper Trading: Simulated trades for testing
# - Backtest: Historical data analysis
# - Manual Override: Human-in-the-loop trading
```

### 4. Multi-Agent Coordination

```python
# Agents automatically initialized based on session type
# Regular session includes:
# - StrategicPlannerAgent
# - TacticalExecutorAgent  
# - EnvironmentWatcherAgent
# - RiskManagerAgent
# - EvaluatorAgent

# Agents receive session lifecycle events:
# - session_created
# - session_started
# - session_paused
# - session_resumed
# - session_stopped
```

### 5. State Persistence

```python
# Session state saved automatically:
# - Every 5 seconds during active trading
# - On every state transition
# - Before shutdown

# State includes:
# - Agent states and internal data
# - Market conditions snapshot
# - Open positions and orders
# - Risk metrics and limits
# - Performance metrics
```

## Usage Examples

### Basic Trading Session

```python
from backend.session import SessionLifecycleManager, SessionType

# Initialize manager
lifecycle_manager = SessionLifecycleManager(mcp_manager, state_manager)
await lifecycle_manager.initialize()

# Create and start session
session = await lifecycle_manager.create_session(SessionType.REGULAR)
await lifecycle_manager.start_session(session.session_id)

# Monitor session
while session.status == SessionStatus.ACTIVE:
    metrics = await lifecycle_manager.get_session_metrics(session.session_id)
    print(f"P&L: ${metrics.net_pnl}, Trades: {metrics.total_trades}")
    await asyncio.sleep(60)

# Stop when done
await lifecycle_manager.stop_session(session.session_id)
```

### Recovery from Failure

```python
# System crashes...

# On restart:
lifecycle_manager = SessionLifecycleManager(mcp_manager, state_manager)
await lifecycle_manager.initialize()

# Recover session
recovered_session = await lifecycle_manager.recover_session(
    session_id="abc123",
    checkpoint_id=None  # Uses latest checkpoint
)

# Resume trading
await lifecycle_manager.resume_session(recovered_session.session_id)
```

### Custom Session Configuration

```python
# Create session with custom configuration
session = await lifecycle_manager.create_session(
    session_type=SessionType.REGULAR,
    config={
        "close_positions_on_stop": True,
        "allow_overnight_positions": False,
        "max_position_hold_time": 240,  # 4 hours
        "require_confirmation": False,
        "use_limit_orders_only": True
    }
)

# Override risk parameters
session.risk_parameters = {
    "max_daily_risk": 0.01,  # 1% instead of 2%
    "position_limit": 2,     # 2 positions instead of 3
    "stop_loss_multiplier": 2.0,  # Tighter stops
    "take_profit_multiplier": 0.3  # Quicker profits
}

await lifecycle_manager.start_session(session.session_id)
```

## Session States

### State Diagram

```
┌──────────────┐
│ INITIALIZING │
└──────┬───────┘
       │
       ▼
   ┌────────┐     ┌────────┐     ┌───────────┐
   │ ACTIVE │ ◄──►│ PAUSED │     │ SUSPENDED │
   └───┬────┘     └────────┘     └─────┬─────┘
       │                                │
       ▼                                ▼
  ┌─────────┐                     ┌─────────┐
  │ CLOSING │                     │  ERROR  │
  └────┬────┘                     └─────────┘
       │
       ▼
  ┌────────┐
  │ CLOSED │
  └────────┘
```

### State Transitions

| From State | To State | Trigger | Description |
|------------|----------|---------|-------------|
| INITIALIZING | ACTIVE | start_session | Begin trading operations |
| ACTIVE | PAUSED | pause_session | Temporarily halt trading |
| PAUSED | ACTIVE | resume_session | Resume trading |
| ACTIVE | SUSPENDED | health_check_failed | System issue detected |
| ACTIVE | CLOSING | stop_session | Begin shutdown |
| CLOSING | CLOSED | finalization_complete | Session ended |
| ANY | ERROR | exception | Unrecoverable error |

## Auto-Management Features

### Auto-Start Conditions

Sessions can automatically start when conditions are met:

```python
auto_start_conditions = [
    {"condition": "market_open", "value": True},
    {"condition": "vix_below", "value": 30},
    {"condition": "time_after", "value": "09:35:00"}
]
```

### Auto-Stop Conditions

Sessions automatically stop for safety:

```python
auto_stop_conditions = [
    {"condition": "daily_loss_exceeded", "value": True},
    {"condition": "market_close", "value": True},
    {"condition": "error_rate_above", "value": 0.1}
]
```

### Health Monitoring

Continuous monitoring ensures session integrity:

- Agent health checks every minute
- State validation on each save
- Automatic recovery from checkpoints
- Resource usage tracking
- Performance metrics calculation

## Integration Points

### 1. MCP Memory System

```python
# Sessions store key decisions in MCP
await mcp.store_memory(
    "SessionLifecycleManager",
    MemorySlice(
        memory_type=MemoryType.EXECUTION,
        content={'session_transition': transition.dict()},
        importance=MemoryImportance.MEDIUM
    )
)
```

### 2. Agent Coordination

```python
# Notify agents of session events
await mcp.share_context(
    "SessionLifecycleManager",
    ["StrategicPlannerAgent", "TacticalExecutorAgent"],
    {
        "session_event": "status_changed",
        "session_id": session_id,
        "from_status": "paused",
        "to_status": "active"
    }
)
```

### 3. Market Awareness

```python
# Sessions react to market conditions
if market_state.market_regime == "high_volatility":
    await lifecycle_manager.pause_session(session_id, "market_conditions")
```

## Performance Considerations

### Resource Usage

- **Memory**: ~50MB per active session
- **Storage**: ~10MB per checkpoint
- **CPU**: Minimal overhead (< 1%)
- **Network**: Updates every 5 seconds

### Optimization Strategies

1. **Checkpoint Pruning**: Keep only recent checkpoints in hot storage
2. **State Compression**: Compress checkpoints before archival
3. **Lazy Loading**: Load agent states only when needed
4. **Batch Operations**: Group database writes for efficiency

## Security & Reliability

### Data Protection

- All session data encrypted at rest
- Secure credential storage for API keys
- Audit trail for all state changes
- Role-based access control

### Failure Handling

- Automatic checkpoint creation
- Multiple recovery fallbacks
- Local backup for critical failures
- Graceful degradation

## Monitoring & Debugging

### Key Metrics

```python
# Session metrics available
metrics = SessionMetrics(
    total_trades=42,
    winning_trades=31,
    net_pnl=1250.50,
    max_drawdown=-500.00,
    error_rate=0.02,
    decision_latency_ms=145
)
```

### Debug Information

```python
# Validate session state
validation = await state_manager.validate_session_state(session)
if not validation["valid"]:
    logger.error(f"Validation errors: {validation['errors']}")
```

### Event Tracking

All session events are logged with:
- Timestamp
- Event type and category
- Severity level
- Source agent
- Impact assessment

## Best Practices

1. **Always Initialize**: Call `initialize()` before using managers
2. **Handle Transitions**: Wrap state changes in try-except blocks
3. **Monitor Health**: Check session health regularly
4. **Clean Shutdown**: Always call `shutdown()` when done
5. **Use Templates**: Leverage templates for consistency
6. **Regular Checkpoints**: Don't disable automatic checkpointing
7. **Test Recovery**: Regularly test recovery procedures

## Future Enhancements

1. **Session Clustering**: Group related sessions
2. **Distributed Sessions**: Multi-node session support
3. **Session Analytics**: Advanced performance analysis
4. **Template Marketplace**: Share session templates
5. **Real-time Replication**: Cross-region backup
6. **Session Replay**: Replay historical sessions
7. **A/B Testing**: Compare session configurations

## Conclusion

The Session Management System provides a robust foundation for stateful trading operations. It ensures continuity across restarts, enables safe experimentation, and provides comprehensive monitoring of all trading activities. The system is designed to scale from single-session operations to managing hundreds of concurrent sessions with different strategies and risk profiles.