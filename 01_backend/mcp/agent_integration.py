"""
Example integration showing how agents can use the MCP system.
This demonstrates memory storage, retrieval, semantic search, and context sharing.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from .context_manager import MCPContextManager
from .config import get_environment_config
from .schemas import (
    MemorySlice, MemoryQuery, MemoryType, MemoryImportance,
    ExecutionPlan, TradeOutcome, MarketIntelligence
)

logger = logging.getLogger(__name__)


class MCPEnabledAgent:
    """
    Base class for MCP-enabled agents.
    Provides common memory operations and context management.
    """
    
    def __init__(self, agent_id: str, mcp_manager: MCPContextManager):
        self.agent_id = agent_id
        self.mcp = mcp_manager
        
    async def initialize(self, capabilities: List[str]) -> None:
        """Register agent with MCP system."""
        await self.mcp.register_agent(self.agent_id, capabilities)
        logger.info(f"{self.agent_id} registered with MCP")
        
    async def store_memory(self, content: Dict[str, Any], 
                          memory_type: MemoryType,
                          importance: MemoryImportance = MemoryImportance.MEDIUM) -> str:
        """Store a memory with automatic session tracking."""
        memory = MemorySlice(
            memory_type=memory_type,
            content=content,
            importance=importance
        )
        
        return await self.mcp.store_memory(self.agent_id, memory)
        
    async def recall_recent_memories(self, hours: int = 24, 
                                   memory_types: List[MemoryType] = None) -> List[MemorySlice]:
        """Recall recent memories of specific types."""
        query = MemoryQuery(
            agent_id=self.agent_id,
            memory_types=memory_types,
            start_time=datetime.utcnow() - timedelta(hours=hours),
            limit=50
        )
        
        return await self.mcp.retrieve_memories(self.agent_id, query)
        
    async def find_similar_memories(self, query_text: str) -> List[MemorySlice]:
        """Find semantically similar memories."""
        return await self.mcp.semantic_search(self.agent_id, query_text, scope="own")
        
    async def share_insight(self, target_agents: List[str], insight: Dict[str, Any]) -> None:
        """Share an insight with other agents."""
        await self.mcp.share_context(self.agent_id, target_agents, insight)
        

class StrategicPlannerAgentExample(MCPEnabledAgent):
    """
    Example Strategic Planner Agent with MCP integration.
    """
    
    async def plan_trading_strategy(self, market_data: Dict[str, Any]) -> ExecutionPlan:
        """Plan a trading strategy based on market data and historical memories."""
        
        # 1. Store market observation
        await self.store_memory(
            content={
                'market_data': market_data,
                'timestamp': datetime.utcnow().isoformat(),
                'analysis': 'Analyzing market conditions for strategy planning'
            },
            memory_type=MemoryType.MARKET_OBSERVATION,
            importance=MemoryImportance.MEDIUM
        )
        
        # 2. Search for similar market conditions in memory
        market_description = f"SPY at {market_data['spy_price']}, VIX at {market_data['vix_level']}"
        similar_conditions = await self.find_similar_memories(market_description)
        
        # 3. Recall recent successful trades
        recent_trades = await self.recall_recent_memories(
            hours=72,
            memory_types=[MemoryType.TRADE_OUTCOME]
        )
        
        # 4. Analyze and create strategy
        strategy = ExecutionPlan(
            strategy_type="SPY_PUT_SELLING",
            target_instrument="SPY",
            entry_conditions={
                'min_premium': 1.0,
                'max_strike_distance': 5.0,
                'required_win_probability': 0.7
            },
            risk_parameters={
                'max_loss': 500,
                'position_size': 1,
                'stop_loss_multiplier': 3.0
            },
            confidence_score=0.85
        )
        
        # 5. Store the strategic plan
        plan_memory_id = await self.store_memory(
            content=strategy.dict(),
            memory_type=MemoryType.STRATEGIC_PLANNING,
            importance=MemoryImportance.HIGH
        )
        
        # 6. Share with Executor Agent
        await self.share_insight(
            target_agents=['ExecutorAgent'],
            insight={
                'new_strategy': strategy.dict(),
                'memory_id': plan_memory_id,
                'based_on_similar_conditions': len(similar_conditions),
                'recent_success_rate': self._calculate_success_rate(recent_trades)
            }
        )
        
        logger.info(f"Created strategy plan with confidence {strategy.confidence_score}")
        
        return strategy
        
    def _calculate_success_rate(self, trades: List[MemorySlice]) -> float:
        """Calculate success rate from trade outcomes."""
        if not trades:
            return 0.0
            
        successful = sum(1 for t in trades 
                        if t.content.get('profit_loss', 0) > 0)
        return successful / len(trades)
        

class ExecutorAgentExample(MCPEnabledAgent):
    """
    Example Executor Agent with MCP integration.
    """
    
    async def execute_trade(self, plan: ExecutionPlan) -> TradeOutcome:
        """Execute a trade based on strategic plan."""
        
        # 1. Store execution attempt
        await self.store_memory(
            content={
                'plan': plan.dict(),
                'execution_start': datetime.utcnow().isoformat(),
                'status': 'initiating'
            },
            memory_type=MemoryType.EXECUTION_PLAN,
            importance=MemoryImportance.HIGH
        )
        
        # 2. Check for recent similar executions
        similar_executions = await self.find_similar_memories(
            f"Execute {plan.strategy_type} on {plan.target_instrument}"
        )
        
        # 3. Simulate trade execution
        # In real implementation, this would interface with IBKR
        outcome = TradeOutcome(
            trade_id=f"TRADE_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            strategy_type=plan.strategy_type,
            entry_price=445.0,
            exit_price=447.0,
            profit_loss=250.0,
            execution_time=datetime.utcnow(),
            success=True
        )
        
        # 4. Store trade outcome
        outcome_id = await self.store_memory(
            content=outcome.dict(),
            memory_type=MemoryType.TRADE_OUTCOME,
            importance=MemoryImportance.CRITICAL
        )
        
        # 5. Share outcome with Evaluator
        await self.share_insight(
            target_agents=['EvaluatorAgent', 'RewardModelAgent'],
            insight={
                'trade_outcome': outcome.dict(),
                'memory_id': outcome_id,
                'execution_quality': 'excellent' if outcome.success else 'poor'
            }
        )
        
        logger.info(f"Executed trade {outcome.trade_id} with P&L: ${outcome.profit_loss}")
        
        return outcome
        

class EvaluatorAgentExample(MCPEnabledAgent):
    """
    Example Evaluator Agent with MCP integration.
    """
    
    async def evaluate_performance(self, session_id: str) -> Dict[str, Any]:
        """Evaluate trading performance for a session."""
        
        # 1. Retrieve all trades for session
        trades = await self.recall_recent_memories(
            hours=24,
            memory_types=[MemoryType.TRADE_OUTCOME]
        )
        
        # 2. Calculate metrics
        total_trades = len(trades)
        successful_trades = sum(1 for t in trades 
                              if t.content.get('success', False))
        total_pnl = sum(t.content.get('profit_loss', 0) for t in trades)
        
        evaluation = {
            'session_id': session_id,
            'total_trades': total_trades,
            'success_rate': successful_trades / total_trades if total_trades > 0 else 0,
            'total_pnl': total_pnl,
            'average_pnl': total_pnl / total_trades if total_trades > 0 else 0,
            'evaluation_time': datetime.utcnow().isoformat()
        }
        
        # 3. Store evaluation
        await self.store_memory(
            content=evaluation,
            memory_type=MemoryType.EVALUATION,
            importance=MemoryImportance.HIGH
        )
        
        # 4. Submit reflection for learning
        reflection = {
            'patterns': self._identify_patterns(trades),
            'improvements': self._suggest_improvements(evaluation),
            'success_factors': self._identify_success_factors(trades)
        }
        
        await self.mcp.submit_reflection(self.agent_id, reflection)
        
        logger.info(f"Evaluated session {session_id}: {total_trades} trades, "
                   f"${total_pnl:.2f} P&L")
        
        return evaluation
        
    def _identify_patterns(self, trades: List[MemorySlice]) -> List[str]:
        """Identify patterns in trading outcomes."""
        patterns = []
        
        # Example pattern detection
        morning_trades = [t for t in trades 
                         if 9 <= datetime.fromisoformat(
                             t.content['execution_time']).hour < 11]
        if morning_trades:
            morning_success = sum(1 for t in morning_trades 
                                if t.content.get('success', False))
            if morning_success / len(morning_trades) > 0.8:
                patterns.append("High success rate in morning trades")
                
        return patterns
        
    def _suggest_improvements(self, evaluation: Dict[str, Any]) -> List[str]:
        """Suggest improvements based on evaluation."""
        improvements = []
        
        if evaluation['success_rate'] < 0.7:
            improvements.append("Consider tightening entry criteria")
            
        if evaluation['average_pnl'] < 100:
            improvements.append("Look for higher premium opportunities")
            
        return improvements
        
    def _identify_success_factors(self, trades: List[MemorySlice]) -> List[str]:
        """Identify factors contributing to success."""
        factors = []
        
        successful = [t for t in trades if t.content.get('success', False)]
        if successful:
            # Analyze successful trades for common factors
            factors.append("Trades during low volatility periods showed higher success")
            
        return factors


async def example_usage():
    """
    Example of how agents interact with MCP system.
    """
    # Initialize MCP
    config = get_environment_config()
    mcp = MCPContextManager(config)
    await mcp.initialize()
    
    # Create a trading session
    session = await mcp.create_session(user_id="example_user")
    
    # Initialize agents
    planner = StrategicPlannerAgentExample("StrategicPlannerAgent", mcp)
    executor = ExecutorAgentExample("ExecutorAgent", mcp)
    evaluator = EvaluatorAgentExample("EvaluatorAgent", mcp)
    
    await planner.initialize(['strategic_planning', 'market_analysis'])
    await executor.initialize(['trade_execution', 'risk_management'])
    await evaluator.initialize(['performance_evaluation', 'learning'])
    
    # Simulate trading workflow
    async with mcp.agent_context("StrategicPlannerAgent", session.session_id):
        
        # 1. Planner creates strategy
        market_data = {
            'spy_price': 445.0,
            'vix_level': 12.5,
            'market_regime': 'favorable'
        }
        
        plan = await planner.plan_trading_strategy(market_data)
        
    async with mcp.agent_context("ExecutorAgent", session.session_id):
        
        # 2. Executor executes trade
        outcome = await executor.execute_trade(plan)
        
    async with mcp.agent_context("EvaluatorAgent", session.session_id):
        
        # 3. Evaluator assesses performance
        evaluation = await evaluator.evaluate_performance(session.session_id)
        
    # 4. Get learning insights
    insights = await mcp.get_learning_insights(
        "StrategicPlannerAgent",
        timeframe=timedelta(days=7)
    )
    
    print(f"Session {session.session_id} completed")
    print(f"Evaluation: {evaluation}")
    print(f"Learning insights: {insights}")
    
    # End session
    await mcp.end_session(session.session_id)
    
    # Shutdown
    await mcp.shutdown()


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_usage())