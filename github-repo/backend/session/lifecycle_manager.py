"""
Session Lifecycle Manager
Manages the complete lifecycle of trading sessions.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Callable
from datetime import datetime, timedelta
from enum import Enum
import json

from ..mcp.context_manager import MCPContextManager
from ..mcp.schemas import MemorySlice, MemoryType, MemoryImportance
from .schemas import (
    TradingSession, SessionStatus, SessionType, SessionEvent,
    SessionTransition, AgentState, MarketState, TradingState,
    SessionMetrics, SessionTemplate
)
from .state_manager import SessionStateManager

logger = logging.getLogger(__name__)


class TransitionError(Exception):
    """Raised when a session transition fails."""
    pass


class SessionLifecycleManager:
    """
    Manages the lifecycle of trading sessions from creation to closure.
    """
    
    def __init__(self, mcp_manager: MCPContextManager, state_manager: SessionStateManager):
        self.mcp = mcp_manager
        self.state_manager = state_manager
        
        # Active sessions
        self.active_sessions: Dict[str, TradingSession] = {}
        self.session_tasks: Dict[str, asyncio.Task] = {}
        
        # Session templates
        self.templates: Dict[str, SessionTemplate] = {}
        self._load_default_templates()
        
        # Lifecycle hooks
        self.lifecycle_hooks: Dict[str, List[Callable]] = {
            'on_create': [],
            'on_start': [],
            'on_pause': [],
            'on_resume': [],
            'on_stop': [],
            'on_error': []
        }
        
        # Configuration
        self.max_concurrent_sessions = 5
        self.session_timeout = timedelta(hours=8)
        self.checkpoint_interval = timedelta(minutes=15)
        
        # Background tasks
        self._monitor_task: Optional[asyncio.Task] = None
        self._checkpoint_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the lifecycle manager."""
        # Register with MCP
        await self.mcp.register_agent(
            "SessionLifecycleManager",
            ["session_lifecycle", "session_orchestration", "state_transitions"]
        )
        
        # Start background tasks
        self._monitor_task = asyncio.create_task(self._monitor_sessions())
        self._checkpoint_task = asyncio.create_task(self._checkpoint_sessions())
        
        # Recover any sessions from previous run
        await self._recover_sessions()
        
        logger.info("Session Lifecycle Manager initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the lifecycle manager."""
        # Stop all active sessions
        for session_id in list(self.active_sessions.keys()):
            await self.stop_session(session_id)
            
        # Cancel background tasks
        if self._monitor_task:
            self._monitor_task.cancel()
        if self._checkpoint_task:
            self._checkpoint_task.cancel()
            
        await asyncio.gather(
            self._monitor_task,
            self._checkpoint_task,
            return_exceptions=True
        )
        
        logger.info("Session Lifecycle Manager shut down")
        
    # Session Creation
    
    async def create_session(self, session_type: SessionType,
                           template_id: Optional[str] = None,
                           config: Optional[Dict[str, Any]] = None) -> TradingSession:
        """
        Create a new trading session.
        
        Args:
            session_type: Type of session to create
            template_id: Optional template to use
            config: Optional configuration overrides
            
        Returns:
            Created session
        """
        # Check concurrent session limit
        if len(self.active_sessions) >= self.max_concurrent_sessions:
            raise RuntimeError(f"Maximum concurrent sessions ({self.max_concurrent_sessions}) reached")
            
        # Use template if provided
        if template_id and template_id in self.templates:
            template = self.templates[template_id]
            session = self._create_from_template(template, session_type)
        else:
            session = TradingSession(
                session_type=session_type,
                config=config or {},
                risk_parameters={
                    'max_daily_risk': 0.02,
                    'position_limit': 3,
                    'stop_loss_multiplier': 3.0,
                    'take_profit_multiplier': 0.5
                },
                enabled_strategies=['SPY_PUT_SELL']
            )
            
        # Apply config overrides
        if config:
            session.config.update(config)
            
        # Initialize agent states
        await self._initialize_agents(session)
        
        # Set initial market state
        session.market_state = await self._get_current_market_state()
        
        # Initialize trading state
        session.trading_state = TradingState(
            max_daily_loss_remaining=10000.0,  # $10k daily loss limit
            position_limit_remaining=3
        )
        
        # Add creation event
        event = SessionEvent(
            session_id=session.session_id,
            event_type="session_created",
            event_category="lifecycle",
            severity="info",
            description=f"Session created with type {session_type.value}",
            data={"config": session.config}
        )
        session.events.append(event)
        
        # Save initial state
        await self.state_manager.save_session_state(session, create_checkpoint=True)
        
        # Add to active sessions
        self.active_sessions[session.session_id] = session
        
        # Call lifecycle hooks
        await self._call_hooks('on_create', session)
        
        # Share creation with agents
        await self._notify_session_creation(session)
        
        logger.info(f"Created session {session.session_id} of type {session_type.value}")
        
        return session
        
    async def create_session_from_template(self, template_name: str,
                                         overrides: Optional[Dict[str, Any]] = None) -> TradingSession:
        """Create a session from a named template."""
        template = None
        for t in self.templates.values():
            if t.template_name == template_name:
                template = t
                break
                
        if not template:
            raise ValueError(f"Template not found: {template_name}")
            
        session = await self.create_session(
            session_type=template.session_type,
            template_id=template.template_id,
            config=overrides
        )
        
        # Update template usage
        template.last_used = datetime.utcnow()
        template.usage_count += 1
        
        return session
        
    # Session Lifecycle Operations
    
    async def start_session(self, session_id: str) -> None:
        """
        Start a trading session.
        
        Args:
            session_id: ID of session to start
        """
        session = self.active_sessions.get(session_id)
        if not session:
            # Try to load from storage
            session = await self.state_manager.load_session_state(session_id)
            if session:
                self.active_sessions[session_id] = session
            else:
                raise ValueError(f"Session not found: {session_id}")
                
        # Validate transition
        self._validate_transition(session, SessionStatus.ACTIVE)
        
        # Perform transition
        await self._transition_session(session, SessionStatus.ACTIVE, "manual_start")
        
        # Start session task
        if session_id not in self.session_tasks:
            task = asyncio.create_task(self._run_session(session))
            self.session_tasks[session_id] = task
            
        # Update timestamps
        session.started_at = datetime.utcnow()
        
        # Enable trading
        if session.trading_state:
            session.trading_state.trading_enabled = True
            
        # Call lifecycle hooks
        await self._call_hooks('on_start', session)
        
        # Save state
        await self.state_manager.save_session_state(session)
        
        logger.info(f"Started session {session_id}")
        
    async def pause_session(self, session_id: str, reason: str = "manual") -> None:
        """Pause a running session."""
        session = self._get_session(session_id)
        
        # Validate transition
        self._validate_transition(session, SessionStatus.PAUSED)
        
        # Perform transition
        await self._transition_session(session, SessionStatus.PAUSED, f"pause_{reason}")
        
        # Disable trading
        if session.trading_state:
            session.trading_state.trading_enabled = False
            
        # Pause agents
        await self._pause_agents(session)
        
        # Call lifecycle hooks
        await self._call_hooks('on_pause', session)
        
        # Create checkpoint
        await self.state_manager.save_session_state(session, create_checkpoint=True)
        
        logger.info(f"Paused session {session_id} - Reason: {reason}")
        
    async def resume_session(self, session_id: str) -> None:
        """Resume a paused session."""
        session = self._get_session(session_id)
        
        # Validate transition
        self._validate_transition(session, SessionStatus.ACTIVE)
        
        # Perform transition
        await self._transition_session(session, SessionStatus.ACTIVE, "manual_resume")
        
        # Re-enable trading
        if session.trading_state:
            session.trading_state.trading_enabled = True
            
        # Resume agents
        await self._resume_agents(session)
        
        # Call lifecycle hooks
        await self._call_hooks('on_resume', session)
        
        # Save state
        await self.state_manager.save_session_state(session)
        
        logger.info(f"Resumed session {session_id}")
        
    async def stop_session(self, session_id: str, reason: str = "manual") -> None:
        """Stop a session and begin closure."""
        session = self._get_session(session_id)
        
        # Validate transition
        self._validate_transition(session, SessionStatus.CLOSING)
        
        # Perform transition
        await self._transition_session(session, SessionStatus.CLOSING, f"stop_{reason}")
        
        # Disable trading immediately
        if session.trading_state:
            session.trading_state.trading_enabled = False
            
        # Close open positions if configured
        if session.config.get('close_positions_on_stop', True):
            await self._close_open_positions(session)
            
        # Stop agents
        await self._stop_agents(session)
        
        # Cancel session task
        if session_id in self.session_tasks:
            self.session_tasks[session_id].cancel()
            await asyncio.gather(self.session_tasks[session_id], return_exceptions=True)
            del self.session_tasks[session_id]
            
        # Finalize metrics
        await self._finalize_session_metrics(session)
        
        # Transition to closed
        await self._transition_session(session, SessionStatus.CLOSED, "finalization_complete")
        
        # Call lifecycle hooks
        await self._call_hooks('on_stop', session)
        
        # Final checkpoint
        await self.state_manager.save_session_state(session, create_checkpoint=True)
        
        # Remove from active sessions
        del self.active_sessions[session_id]
        
        logger.info(f"Stopped session {session_id} - Reason: {reason}")
        
    # Session Recovery
    
    async def recover_session(self, session_id: str,
                            checkpoint_id: Optional[str] = None) -> TradingSession:
        """
        Recover a session from storage or checkpoint.
        
        Args:
            session_id: Session to recover
            checkpoint_id: Optional specific checkpoint
            
        Returns:
            Recovered session
        """
        # Create recovery plan
        plan = await self.state_manager.create_recovery_plan(session_id)
        if not plan:
            raise RuntimeError(f"Cannot create recovery plan for session {session_id}")
            
        # Override checkpoint if specified
        if checkpoint_id:
            plan.checkpoint_id = checkpoint_id
            
        # Execute recovery
        success = await self.state_manager.execute_recovery_plan(plan)
        if not success:
            raise RuntimeError(f"Failed to recover session {session_id}")
            
        # Load recovered session
        session = await self.state_manager.load_session_state(session_id)
        if not session:
            raise RuntimeError(f"Session not found after recovery: {session_id}")
            
        # Re-initialize components
        await self._reinitialize_session(session)
        
        # Add to active sessions
        self.active_sessions[session_id] = session
        
        # Add recovery event
        event = SessionEvent(
            session_id=session_id,
            event_type="session_recovered",
            event_category="lifecycle",
            severity="info",
            description=f"Session recovered from checkpoint {plan.checkpoint_id}",
            data={"recovery_plan": plan.dict()}
        )
        session.events.append(event)
        
        logger.info(f"Recovered session {session_id}")
        
        return session
        
    # Session Queries
    
    async def get_session(self, session_id: str) -> Optional[TradingSession]:
        """Get a session by ID."""
        # Check active sessions
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
            
        # Try loading from storage
        return await self.state_manager.load_session_state(session_id)
        
    async def list_active_sessions(self) -> List[TradingSession]:
        """List all active sessions."""
        return list(self.active_sessions.values())
        
    async def get_session_metrics(self, session_id: str) -> Optional[SessionMetrics]:
        """Get metrics for a session."""
        session = await self.get_session(session_id)
        if session:
            if not session.metrics:
                await self._calculate_session_metrics(session)
            return session.metrics
        return None
        
    # Lifecycle Hooks
    
    def register_lifecycle_hook(self, event: str, callback: Callable) -> None:
        """Register a lifecycle hook."""
        if event in self.lifecycle_hooks:
            self.lifecycle_hooks[event].append(callback)
        else:
            raise ValueError(f"Unknown lifecycle event: {event}")
            
    async def _call_hooks(self, event: str, session: TradingSession) -> None:
        """Call all registered hooks for an event."""
        for callback in self.lifecycle_hooks[event]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(session)
                else:
                    callback(session)
            except Exception as e:
                logger.error(f"Lifecycle hook error for {event}: {e}")
                
    # State Transitions
    
    def _validate_transition(self, session: TradingSession, 
                           target_status: SessionStatus) -> None:
        """Validate if a transition is allowed."""
        valid_transitions = {
            SessionStatus.INITIALIZING: [SessionStatus.ACTIVE, SessionStatus.ERROR],
            SessionStatus.ACTIVE: [SessionStatus.PAUSED, SessionStatus.SUSPENDED, 
                                 SessionStatus.CLOSING, SessionStatus.ERROR],
            SessionStatus.PAUSED: [SessionStatus.ACTIVE, SessionStatus.CLOSING],
            SessionStatus.SUSPENDED: [SessionStatus.ACTIVE, SessionStatus.CLOSING],
            SessionStatus.CLOSING: [SessionStatus.CLOSED],
            SessionStatus.CLOSED: [],
            SessionStatus.ERROR: [SessionStatus.CLOSING]
        }
        
        allowed = valid_transitions.get(session.status, [])
        if target_status not in allowed:
            raise TransitionError(
                f"Invalid transition from {session.status.value} to {target_status.value}"
            )
            
    async def _transition_session(self, session: TradingSession,
                                target_status: SessionStatus,
                                trigger: str) -> None:
        """Perform a session state transition."""
        # Create transition record
        transition = SessionTransition(
            session_id=session.session_id,
            from_status=session.status,
            to_status=target_status,
            trigger=trigger,
            pre_conditions_met=True
        )
        
        # Perform transition
        previous_status = session.status
        session.status = target_status
        
        # Add transition event
        event = SessionEvent(
            session_id=session.session_id,
            event_type="status_transition",
            event_category="lifecycle",
            severity="info",
            description=f"Status changed from {previous_status.value} to {target_status.value}",
            data={
                "from_status": previous_status.value,
                "to_status": target_status.value,
                "trigger": trigger
            }
        )
        session.events.append(event)
        
        # Notify agents
        await self._notify_status_change(session, previous_status, target_status)
        
        # Check post-conditions
        transition.post_conditions_met = True
        transition.state_preserved = True
        
        # Store transition
        await self._store_transition(transition)
        
    # Background Tasks
    
    async def _run_session(self, session: TradingSession) -> None:
        """Main session execution loop."""
        logger.info(f"Starting session loop for {session.session_id}")
        
        try:
            while session.status in [SessionStatus.ACTIVE, SessionStatus.PAUSED]:
                if session.status == SessionStatus.ACTIVE:
                    # Update market state
                    session.market_state = await self._get_current_market_state()
                    
                    # Check auto-stop conditions
                    if await self._check_auto_stop_conditions(session):
                        await self.stop_session(session.session_id, "auto_stop_condition")
                        break
                        
                    # Update session metrics
                    await self._update_session_metrics(session)
                    
                    # Save state periodically
                    await self.state_manager.save_session_state(session)
                    
                # Sleep based on status
                if session.status == SessionStatus.ACTIVE:
                    await asyncio.sleep(5)  # Active polling
                else:
                    await asyncio.sleep(30)  # Paused polling
                    
        except asyncio.CancelledError:
            logger.info(f"Session loop cancelled for {session.session_id}")
        except Exception as e:
            logger.error(f"Session loop error for {session.session_id}: {e}")
            await self._handle_session_error(session, e)
            
    async def _monitor_sessions(self) -> None:
        """Monitor all active sessions."""
        while True:
            try:
                for session_id, session in list(self.active_sessions.items()):
                    # Check session health
                    if not await self._check_session_health(session):
                        await self._handle_unhealthy_session(session)
                        
                    # Check timeout
                    if session.started_at:
                        runtime = datetime.utcnow() - session.started_at
                        if runtime > self.session_timeout:
                            logger.warning(f"Session {session_id} exceeded timeout")
                            await self.stop_session(session_id, "timeout")
                            
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Session monitoring error: {e}")
                await asyncio.sleep(60)
                
    async def _checkpoint_sessions(self) -> None:
        """Create periodic checkpoints for active sessions."""
        while True:
            try:
                for session in self.active_sessions.values():
                    if session.status == SessionStatus.ACTIVE:
                        # Check if checkpoint is due
                        last_checkpoint_time = datetime.utcnow()
                        if session.checkpoints:
                            # Get last checkpoint time
                            checkpoint = await self.state_manager.load_checkpoint(
                                session.checkpoints[-1]
                            )
                            if checkpoint:
                                last_checkpoint_time = checkpoint.timestamp
                                
                        time_since_checkpoint = datetime.utcnow() - last_checkpoint_time
                        if time_since_checkpoint >= self.checkpoint_interval:
                            await self.state_manager.save_session_state(
                                session,
                                create_checkpoint=True
                            )
                            
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Checkpoint creation error: {e}")
                await asyncio.sleep(300)
                
    # Helper Methods
    
    def _get_session(self, session_id: str) -> TradingSession:
        """Get session or raise error."""
        session = self.active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        return session
        
    def _create_from_template(self, template: SessionTemplate,
                            session_type: SessionType) -> TradingSession:
        """Create session from template."""
        session = TradingSession(
            session_type=session_type,
            config=template.default_config.copy(),
            risk_parameters=template.default_risk_parameters.copy(),
            enabled_strategies=template.enabled_strategies.copy()
        )
        
        # Apply agent configurations
        for agent_id, agent_config in template.agent_configurations.items():
            if agent_id not in session.agent_states:
                session.agent_states[agent_id] = AgentState(
                    agent_id=agent_id,
                    status="initializing",
                    internal_state=agent_config
                )
                
        return session
        
    def _load_default_templates(self) -> None:
        """Load default session templates."""
        # Regular trading template
        regular_template = SessionTemplate(
            template_name="Regular Trading",
            description="Standard SPY options trading session",
            session_type=SessionType.REGULAR,
            default_config={
                "close_positions_on_stop": True,
                "allow_overnight_positions": False,
                "max_position_hold_time": 240  # 4 hours
            },
            default_risk_parameters={
                "max_daily_risk": 0.02,
                "position_limit": 3,
                "stop_loss_multiplier": 3.0,
                "take_profit_multiplier": 0.5
            },
            required_agents=[
                "StrategicPlannerAgent",
                "TacticalExecutorAgent",
                "EnvironmentWatcherAgent",
                "RiskManagerAgent"
            ],
            enabled_strategies=["SPY_PUT_SELL", "SPY_CALL_SELL"],
            auto_start_conditions=[
                {"condition": "market_open", "value": True},
                {"condition": "vix_below", "value": 30}
            ],
            auto_stop_conditions=[
                {"condition": "daily_loss_exceeded", "value": True},
                {"condition": "market_close", "value": True}
            ]
        )
        self.templates[regular_template.template_id] = regular_template
        
        # Paper trading template
        paper_template = SessionTemplate(
            template_name="Paper Trading",
            description="Simulated trading for testing",
            session_type=SessionType.PAPER_TRADING,
            default_config={
                "use_real_data": True,
                "simulate_fills": True,
                "starting_capital": 100000
            },
            default_risk_parameters={
                "max_daily_risk": 0.05,  # Higher for testing
                "position_limit": 5,
                "stop_loss_multiplier": 2.0,
                "take_profit_multiplier": 0.3
            },
            required_agents=[
                "StrategicPlannerAgent",
                "TacticalExecutorAgent"
            ],
            enabled_strategies=["SPY_PUT_SELL", "SPY_CALL_SELL", "IRON_CONDOR"],
            auto_start_conditions=[],
            auto_stop_conditions=[]
        )
        self.templates[paper_template.template_id] = paper_template
        
    async def _initialize_agents(self, session: TradingSession) -> None:
        """Initialize agents for a session."""
        # Define required agents based on session type
        required_agents = {
            SessionType.REGULAR: [
                "StrategicPlannerAgent",
                "TacticalExecutorAgent",
                "EnvironmentWatcherAgent",
                "RiskManagerAgent",
                "EvaluatorAgent"
            ],
            SessionType.EXTENDED_HOURS: [
                "StrategicPlannerAgent",
                "TacticalExecutorAgent",
                "EnvironmentWatcherAgent",
                "RiskManagerAgent"
            ],
            SessionType.PAPER_TRADING: [
                "StrategicPlannerAgent",
                "TacticalExecutorAgent"
            ],
            SessionType.BACKTEST: [
                "StrategicPlannerAgent",
                "EvaluatorAgent"
            ],
            SessionType.MANUAL_OVERRIDE: [
                "RiskManagerAgent"
            ]
        }
        
        agents = required_agents.get(session.session_type, [])
        
        for agent_id in agents:
            session.agent_states[agent_id] = AgentState(
                agent_id=agent_id,
                status="active"
            )
            
    async def _get_current_market_state(self) -> MarketState:
        """Get current market state from environment."""
        # This would integrate with market data sources
        # For now, return a default state
        return MarketState(
            spy_price=445.0,
            vix_level=12.5,
            market_regime="low_volatility",
            market_open=True,
            liquidity_status="normal"
        )
        
    async def _pause_agents(self, session: TradingSession) -> None:
        """Pause all agents in a session."""
        for agent_id, agent_state in session.agent_states.items():
            if agent_state.status == "active":
                agent_state.status = "paused"
                
        await self.mcp.share_context(
            "SessionLifecycleManager",
            list(session.agent_states.keys()),
            {"session_command": "pause", "session_id": session.session_id}
        )
        
    async def _resume_agents(self, session: TradingSession) -> None:
        """Resume all agents in a session."""
        for agent_id, agent_state in session.agent_states.items():
            if agent_state.status == "paused":
                agent_state.status = "active"
                
        await self.mcp.share_context(
            "SessionLifecycleManager",
            list(session.agent_states.keys()),
            {"session_command": "resume", "session_id": session.session_id}
        )
        
    async def _stop_agents(self, session: TradingSession) -> None:
        """Stop all agents in a session."""
        for agent_state in session.agent_states.values():
            agent_state.status = "stopped"
            
        await self.mcp.share_context(
            "SessionLifecycleManager",
            list(session.agent_states.keys()),
            {"session_command": "stop", "session_id": session.session_id}
        )
        
    async def _close_open_positions(self, session: TradingSession) -> None:
        """Close any open positions in the session."""
        if not session.trading_state or not session.trading_state.open_positions:
            return
            
        logger.info(f"Closing {len(session.trading_state.open_positions)} open positions")
        
        # This would integrate with the execution system
        # For now, just clear the positions
        session.trading_state.open_positions.clear()
        
    async def _check_auto_stop_conditions(self, session: TradingSession) -> bool:
        """Check if auto-stop conditions are met."""
        # Check daily loss limit
        if session.trading_state:
            if session.trading_state.daily_pnl < -10000:  # -$10k
                logger.warning(f"Session {session.session_id} hit daily loss limit")
                return True
                
            if session.trading_state.max_daily_loss_remaining <= 0:
                logger.warning(f"Session {session.session_id} exhausted loss allowance")
                return True
                
        # Check market close
        if session.market_state and not session.market_state.market_open:
            if not session.config.get('allow_extended_hours', False):
                logger.info(f"Market closed, stopping session {session.session_id}")
                return True
                
        return False
        
    async def _check_session_health(self, session: TradingSession) -> bool:
        """Check if session is healthy."""
        # Check agent health
        error_agents = [
            agent_id for agent_id, state in session.agent_states.items()
            if state.status == "error"
        ]
        
        if len(error_agents) > len(session.agent_states) * 0.5:
            logger.error(f"Too many agents in error state: {error_agents}")
            return False
            
        # Validate session state
        validation = await self.state_manager.validate_session_state(session)
        if not validation["valid"]:
            logger.error(f"Session validation failed: {validation['errors']}")
            return False
            
        return True
        
    async def _handle_unhealthy_session(self, session: TradingSession) -> None:
        """Handle an unhealthy session."""
        logger.warning(f"Session {session.session_id} is unhealthy")
        
        # Try to recover
        try:
            if session.last_checkpoint_id:
                await self.state_manager.restore_from_checkpoint(
                    session,
                    session.last_checkpoint_id
                )
                logger.info(f"Restored session {session.session_id} from checkpoint")
            else:
                # Suspend the session
                await self._transition_session(
                    session,
                    SessionStatus.SUSPENDED,
                    "health_check_failed"
                )
        except Exception as e:
            logger.error(f"Failed to recover unhealthy session: {e}")
            await self._handle_session_error(session, e)
            
    async def _handle_session_error(self, session: TradingSession, error: Exception) -> None:
        """Handle a session error."""
        logger.error(f"Session {session.session_id} error: {error}")
        
        # Transition to error state
        try:
            await self._transition_session(session, SessionStatus.ERROR, f"error_{type(error).__name__}")
        except:
            session.status = SessionStatus.ERROR
            
        # Add error event
        event = SessionEvent(
            session_id=session.session_id,
            event_type="session_error",
            event_category="error",
            severity="critical",
            description=str(error),
            data={"error_type": type(error).__name__, "error_details": str(error)}
        )
        session.events.append(event)
        
        # Call error hooks
        await self._call_hooks('on_error', session)
        
        # Save state
        await self.state_manager.save_session_state(session)
        
    async def _reinitialize_session(self, session: TradingSession) -> None:
        """Reinitialize a recovered session."""
        # Restart agents
        for agent_id, agent_state in session.agent_states.items():
            if agent_state.status in ["active", "paused"]:
                await self.mcp.share_context(
                    "SessionLifecycleManager",
                    [agent_id],
                    {
                        "session_command": "reinitialize",
                        "session_id": session.session_id,
                        "agent_state": agent_state.dict()
                    }
                )
                
        # Restart session task if active
        if session.status == SessionStatus.ACTIVE:
            task = asyncio.create_task(self._run_session(session))
            self.session_tasks[session.session_id] = task
            
    async def _calculate_session_metrics(self, session: TradingSession) -> None:
        """Calculate metrics for a session."""
        if not session.metrics:
            session.metrics = SessionMetrics(
                session_id=session.session_id,
                start_time=session.created_at
            )
            
        metrics = session.metrics
        
        # Update end time
        if session.status == SessionStatus.CLOSED:
            metrics.end_time = session.ended_at or datetime.utcnow()
            
        # Calculate durations
        if session.started_at:
            if session.status == SessionStatus.ACTIVE:
                metrics.active_duration = datetime.utcnow() - session.started_at
            elif metrics.end_time:
                metrics.active_duration = metrics.end_time - session.started_at
                
        # Trading metrics from events
        trade_events = [e for e in session.events if e.event_type == "trade_executed"]
        metrics.total_trades = len(trade_events)
        
        # Resource metrics
        total_memory = sum(s.memory_usage_mb for s in session.agent_states.values())
        metrics.peak_memory_mb = max(metrics.peak_memory_mb, total_memory)
        
        # Checkpoint metrics
        metrics.checkpoint_count = len(session.checkpoints)
        
    async def _update_session_metrics(self, session: TradingSession) -> None:
        """Update live session metrics."""
        if not session.metrics:
            await self._calculate_session_metrics(session)
            return
            
        # Update trading metrics
        if session.trading_state:
            session.metrics.gross_pnl = session.trading_state.daily_pnl
            session.metrics.net_pnl = session.trading_state.daily_pnl  # Adjust for costs
            
        # Update resource usage
        total_memory = sum(s.memory_usage_mb for s in session.agent_states.values())
        session.metrics.peak_memory_mb = max(session.metrics.peak_memory_mb, total_memory)
        
    async def _finalize_session_metrics(self, session: TradingSession) -> None:
        """Finalize metrics when session closes."""
        await self._calculate_session_metrics(session)
        
        if session.metrics:
            session.metrics.end_time = datetime.utcnow()
            session.ended_at = session.metrics.end_time
            
            # Calculate final metrics
            if session.metrics.total_trades > 0:
                win_rate = session.metrics.winning_trades / session.metrics.total_trades
                session.metrics.error_rate = (
                    sum(1 for e in session.events if e.severity == "error") / 
                    len(session.events) * 100
                )
                
    async def _recover_sessions(self) -> None:
        """Recover sessions from previous run."""
        # This would query the database for sessions that were active
        # when the system shut down and attempt to recover them
        pass
        
    async def _notify_session_creation(self, session: TradingSession) -> None:
        """Notify agents of session creation."""
        await self.mcp.share_context(
            "SessionLifecycleManager",
            list(session.agent_states.keys()),
            {
                "session_event": "created",
                "session_id": session.session_id,
                "session_type": session.session_type.value,
                "config": session.config
            }
        )
        
    async def _notify_status_change(self, session: TradingSession,
                                  from_status: SessionStatus,
                                  to_status: SessionStatus) -> None:
        """Notify agents of status change."""
        await self.mcp.share_context(
            "SessionLifecycleManager",
            list(session.agent_states.keys()),
            {
                "session_event": "status_changed",
                "session_id": session.session_id,
                "from_status": from_status.value,
                "to_status": to_status.value
            }
        )
        
    async def _store_transition(self, transition: SessionTransition) -> None:
        """Store transition in MCP."""
        await self.mcp.store_memory(
            "SessionLifecycleManager",
            MemorySlice(
                memory_type=MemoryType.EXECUTION,
                content={
                    'session_transition': transition.dict(),
                    'timestamp': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.MEDIUM
            )
        )