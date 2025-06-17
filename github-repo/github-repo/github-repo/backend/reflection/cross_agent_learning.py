"""
Cross-Agent Learning
Facilitates knowledge sharing and collaborative learning between agents.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
import json

from ..mcp.context_manager import MCPContextManager
from ..mcp.schemas import MemorySlice, MemoryType, MemoryImportance
from .schemas import (
    CrossAgentLearning, LearningInsight, StrategyAdjustment,
    LearningType, InsightCategory
)

logger = logging.getLogger(__name__)


class CrossAgentLearningHub:
    """
    Central hub for cross-agent learning and knowledge sharing.
    """
    
    def __init__(self, mcp_manager: MCPContextManager):
        self.mcp = mcp_manager
        
        # Agent registry
        self.registered_agents: Set[str] = set()
        self.agent_capabilities: Dict[str, List[str]] = {}
        
        # Learning storage
        self.shared_learnings: List[CrossAgentLearning] = []
        self.learning_index: Dict[str, CrossAgentLearning] = {}
        
        # Adoption tracking
        self.adoption_rates: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.feedback_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Learning effectiveness
        self.learning_impact: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        
        # Configuration
        self.min_confidence_to_share = 0.75
        self.adoption_threshold = 0.6
        
        # Background tasks
        self._sharing_task: Optional[asyncio.Task] = None
        self._evaluation_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the cross-agent learning hub."""
        # Register with MCP
        await self.mcp.register_agent(
            "CrossAgentLearningHub",
            ["knowledge_sharing", "collaborative_learning", "performance_aggregation"]
        )
        
        # Load historical learnings
        await self._load_historical_learnings()
        
        # Start background tasks
        self._sharing_task = asyncio.create_task(self._process_learning_queue())
        self._evaluation_task = asyncio.create_task(self._evaluate_shared_learnings())
        
        logger.info("Cross-Agent Learning Hub initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the learning hub."""
        if self._sharing_task:
            self._sharing_task.cancel()
        if self._evaluation_task:
            self._evaluation_task.cancel()
            
        await asyncio.gather(
            self._sharing_task,
            self._evaluation_task,
            return_exceptions=True
        )
        
        # Save current state
        await self._save_learning_state()
        
        logger.info("Cross-Agent Learning Hub shut down")
        
    # Agent Registration
    
    async def register_agent(self, agent_id: str, capabilities: List[str]) -> None:
        """
        Register an agent with the learning hub.
        
        Args:
            agent_id: Agent identifier
            capabilities: List of agent capabilities
        """
        self.registered_agents.add(agent_id)
        self.agent_capabilities[agent_id] = capabilities
        
        logger.info(f"Registered agent {agent_id} with capabilities: {capabilities}")
        
    # Learning Submission
    
    async def submit_learning(self, source_agent: str, learning_type: str,
                            content: Dict[str, Any], evidence: Dict[str, Any]) -> str:
        """
        Submit a learning for potential sharing.
        
        Args:
            source_agent: Agent submitting the learning
            learning_type: Type of learning
            content: Learning content
            evidence: Supporting evidence
            
        Returns:
            Learning ID
        """
        # Determine target agents based on learning type
        target_agents = await self._determine_target_agents(source_agent, learning_type, content)
        
        if not target_agents:
            logger.warning(f"No suitable target agents for learning from {source_agent}")
            return ""
            
        # Calculate applicability scores
        applicability = await self._calculate_applicability(learning_type, content, target_agents)
        
        # Estimate performance improvement
        performance_improvement = await self._estimate_performance_improvement(content, evidence)
        
        # Create learning record
        learning = CrossAgentLearning(
            learning_id=f"learning_{datetime.utcnow().timestamp()}",
            source_agent=source_agent,
            target_agents=target_agents,
            learning_type=learning_type,
            content=content,
            applicability=applicability,
            supporting_data=evidence,
            performance_improvement=performance_improvement
        )
        
        # Store learning
        self.shared_learnings.append(learning)
        self.learning_index[learning.learning_id] = learning
        
        # Queue for sharing
        await self._queue_for_sharing(learning)
        
        # Store in MCP
        await self._store_learning(learning)
        
        logger.info(f"Submitted learning {learning.learning_id} from {source_agent}")
        
        return learning.learning_id
        
    async def _determine_target_agents(self, source_agent: str, 
                                     learning_type: str,
                                     content: Dict[str, Any]) -> List[str]:
        """Determine which agents should receive this learning."""
        target_agents = []
        
        # Get all agents except source
        potential_agents = [a for a in self.registered_agents if a != source_agent]
        
        for agent in potential_agents:
            capabilities = self.agent_capabilities.get(agent, [])
            
            # Check if agent has relevant capabilities
            if learning_type == "strategy_optimization" and "trading" in ' '.join(capabilities):
                target_agents.append(agent)
            elif learning_type == "risk_management" and "risk" in ' '.join(capabilities):
                target_agents.append(agent)
            elif learning_type == "market_analysis" and "market" in ' '.join(capabilities):
                target_agents.append(agent)
            elif learning_type == "execution_improvement" and "execution" in ' '.join(capabilities):
                target_agents.append(agent)
                
        return target_agents
        
    async def _calculate_applicability(self, learning_type: str,
                                     content: Dict[str, Any],
                                     target_agents: List[str]) -> Dict[str, float]:
        """Calculate how applicable a learning is to each target agent."""
        applicability = {}
        
        for agent in target_agents:
            # Base applicability on agent type and learning type
            score = 0.5  # Default moderate applicability
            
            # Adjust based on agent capabilities
            capabilities = self.agent_capabilities.get(agent, [])
            
            # Strategic planner benefits from market insights
            if agent == "StrategicPlannerAgent":
                if learning_type in ["market_analysis", "strategy_optimization"]:
                    score = 0.9
                elif learning_type == "risk_management":
                    score = 0.7
                    
            # Tactical executor benefits from execution improvements
            elif agent == "TacticalExecutorAgent":
                if learning_type in ["execution_improvement", "timing_optimization"]:
                    score = 0.9
                elif learning_type == "risk_management":
                    score = 0.8
                    
            # Risk manager benefits from all risk insights
            elif agent == "RiskManagerAgent":
                if learning_type == "risk_management":
                    score = 0.95
                elif learning_type in ["strategy_optimization", "market_analysis"]:
                    score = 0.7
                    
            # Environment watcher benefits from market insights
            elif agent == "EnvironmentWatcherAgent":
                if learning_type == "market_analysis":
                    score = 0.9
                elif learning_type == "pattern_recognition":
                    score = 0.8
                    
            applicability[agent] = score
            
        return applicability
        
    async def _estimate_performance_improvement(self, content: Dict[str, Any],
                                              evidence: Dict[str, Any]) -> Dict[str, float]:
        """Estimate potential performance improvement from adopting this learning."""
        improvements = {}
        
        # Extract metrics from evidence
        if 'performance_metrics' in evidence:
            metrics = evidence['performance_metrics']
            
            # Win rate improvement
            if 'win_rate_change' in metrics:
                improvements['win_rate'] = metrics['win_rate_change']
                
            # Risk reduction
            if 'drawdown_reduction' in metrics:
                improvements['max_drawdown'] = -metrics['drawdown_reduction']
                
            # Return improvement
            if 'return_improvement' in metrics:
                improvements['average_return'] = metrics['return_improvement']
                
        # If no specific metrics, estimate based on content
        if not improvements:
            if content.get('type') == 'risk_reduction':
                improvements['max_drawdown'] = -0.05
                improvements['sharpe_ratio'] = 0.1
            elif content.get('type') == 'win_rate_improvement':
                improvements['win_rate'] = 0.05
                improvements['profit_factor'] = 0.1
            else:
                improvements['overall_performance'] = 0.03
                
        return improvements
        
    # Learning Sharing
    
    async def _queue_for_sharing(self, learning: CrossAgentLearning) -> None:
        """Queue a learning for sharing with target agents."""
        # Check if meets sharing criteria
        avg_applicability = np.mean(list(learning.applicability.values()))
        
        if avg_applicability >= self.min_confidence_to_share:
            # Share immediately if high priority
            if any(v > 0.9 for v in learning.applicability.values()):
                await self._share_learning_with_agents(learning)
            else:
                # Queue for batch sharing
                logger.info(f"Queued learning {learning.learning_id} for sharing")
                
    async def _share_learning_with_agents(self, learning: CrossAgentLearning) -> None:
        """Share a learning with target agents."""
        for agent in learning.target_agents:
            if learning.applicability.get(agent, 0) >= self.adoption_threshold:
                # Share via MCP context
                await self.mcp.share_context(
                    "CrossAgentLearningHub",
                    [agent],
                    {
                        'shared_learning': {
                            'learning_id': learning.learning_id,
                            'source_agent': learning.source_agent,
                            'type': learning.learning_type,
                            'content': learning.content,
                            'expected_improvement': learning.performance_improvement,
                            'confidence': learning.applicability[agent]
                        }
                    }
                )
                
                # Update adoption status
                learning.adoption_status[agent] = "shared"
                
                logger.info(f"Shared learning {learning.learning_id} with {agent}")
                
    # Feedback Processing
    
    async def process_feedback(self, learning_id: str, agent_id: str,
                             feedback: Dict[str, Any]) -> None:
        """
        Process feedback from an agent about a shared learning.
        
        Args:
            learning_id: ID of the learning
            agent_id: Agent providing feedback
            feedback: Feedback content
        """
        if learning_id not in self.learning_index:
            logger.warning(f"Unknown learning ID: {learning_id}")
            return
            
        learning = self.learning_index[learning_id]
        
        # Store feedback
        learning.feedback[agent_id] = feedback
        self.feedback_history[learning_id].append({
            'agent': agent_id,
            'feedback': feedback,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Update adoption status
        if feedback.get('adopted', False):
            learning.adoption_status[agent_id] = "adopted"
            self.adoption_rates[learning.source_agent][agent_id] += 1
            
            # Track impact
            if 'performance_impact' in feedback:
                for metric, impact in feedback['performance_impact'].items():
                    self.learning_impact[learning_id][metric] = impact
                    
        elif feedback.get('rejected', False):
            learning.adoption_status[agent_id] = "rejected"
            
        # Update MCP
        await self._store_learning(learning)
        
        logger.info(f"Processed feedback for learning {learning_id} from {agent_id}")
        
    # Performance Aggregation
    
    async def aggregate_cross_agent_performance(self) -> Dict[str, Any]:
        """
        Aggregate performance improvements from cross-agent learning.
        
        Returns:
            Aggregated performance metrics
        """
        aggregated = {
            'total_learnings_shared': len(self.shared_learnings),
            'adoption_rate': 0.0,
            'performance_improvements': defaultdict(float),
            'most_valuable_learnings': [],
            'agent_collaboration_matrix': {}
        }
        
        # Calculate overall adoption rate
        total_shares = 0
        total_adoptions = 0
        
        for learning in self.shared_learnings:
            for agent, status in learning.adoption_status.items():
                total_shares += 1
                if status == "adopted":
                    total_adoptions += 1
                    
        if total_shares > 0:
            aggregated['adoption_rate'] = total_adoptions / total_shares
            
        # Aggregate performance improvements
        for learning_id, impacts in self.learning_impact.items():
            for metric, impact in impacts.items():
                aggregated['performance_improvements'][metric] += impact
                
        # Find most valuable learnings
        learning_values = []
        for learning in self.shared_learnings:
            total_impact = sum(abs(v) for v in self.learning_impact.get(learning.learning_id, {}).values())
            adoption_count = sum(1 for s in learning.adoption_status.values() if s == "adopted")
            value_score = total_impact * adoption_count
            
            if value_score > 0:
                learning_values.append({
                    'learning_id': learning.learning_id,
                    'source_agent': learning.source_agent,
                    'value_score': value_score,
                    'adoption_count': adoption_count,
                    'total_impact': total_impact
                })
                
        # Sort by value and take top 5
        learning_values.sort(key=lambda x: x['value_score'], reverse=True)
        aggregated['most_valuable_learnings'] = learning_values[:5]
        
        # Build collaboration matrix
        collab_matrix = defaultdict(lambda: defaultdict(int))
        for learning in self.shared_learnings:
            for target_agent in learning.target_agents:
                if learning.adoption_status.get(target_agent) == "adopted":
                    collab_matrix[learning.source_agent][target_agent] += 1
                    
        aggregated['agent_collaboration_matrix'] = dict(collab_matrix)
        
        return aggregated
        
    # Learning Synthesis
    
    async def synthesize_learnings(self, time_period: timedelta) -> List[LearningInsight]:
        """
        Synthesize multiple learnings into higher-level insights.
        
        Args:
            time_period: Period to analyze
            
        Returns:
            Synthesized insights
        """
        cutoff_time = datetime.utcnow() - time_period
        recent_learnings = [l for l in self.shared_learnings if l.shared_at > cutoff_time]
        
        if len(recent_learnings) < 3:
            return []
            
        insights = []
        
        # Group learnings by type
        learnings_by_type = defaultdict(list)
        for learning in recent_learnings:
            learnings_by_type[learning.learning_type].append(learning)
            
        # Synthesize each type
        for learning_type, type_learnings in learnings_by_type.items():
            if len(type_learnings) >= 2:
                # Find common patterns
                common_content = self._find_common_patterns(type_learnings)
                
                if common_content:
                    # Calculate aggregate performance
                    total_improvement = defaultdict(float)
                    for learning in type_learnings:
                        for metric, value in learning.performance_improvement.items():
                            total_improvement[metric] += value
                            
                    # Create synthesized insight
                    insight = LearningInsight(
                        insight_id=f"synth_{learning_type}_{datetime.utcnow().timestamp()}",
                        category=self._map_learning_type_to_category(learning_type),
                        confidence=0.85,
                        observation=f"Multiple agents discovered similar {learning_type} improvements",
                        conclusion=f"Cross-agent validation confirms {learning_type} effectiveness",
                        evidence=[{
                            'learning_count': len(type_learnings),
                            'common_patterns': common_content,
                            'aggregate_improvement': dict(total_improvement),
                            'source_agents': list(set(l.source_agent for l in type_learnings))
                        }],
                        recommendations=[
                            f"Standardize {learning_type} across all agents",
                            "Create shared protocol for this approach",
                            "Monitor aggregate performance improvement"
                        ],
                        expected_impact=dict(total_improvement),
                        based_on_trades=[],  # Not directly trade-based
                        learning_method=LearningType.COLLABORATIVE
                    )
                    
                    insights.append(insight)
                    
        return insights
        
    def _find_common_patterns(self, learnings: List[CrossAgentLearning]) -> Dict[str, Any]:
        """Find common patterns across multiple learnings."""
        common_patterns = {}
        
        # Extract all content keys
        all_keys = set()
        for learning in learnings:
            all_keys.update(learning.content.keys())
            
        # Find common values
        for key in all_keys:
            values = []
            for learning in learnings:
                if key in learning.content:
                    values.append(learning.content[key])
                    
            if len(values) >= len(learnings) * 0.6:  # Present in 60% of learnings
                # Check if values are similar
                if all(isinstance(v, (int, float)) for v in values):
                    avg_value = np.mean(values)
                    if all(abs(v - avg_value) / (abs(avg_value) + 0.001) < 0.2 for v in values):
                        common_patterns[key] = avg_value
                elif all(isinstance(v, str) for v in values):
                    # Check string similarity
                    if len(set(values)) <= 2:  # At most 2 unique values
                        common_patterns[key] = max(set(values), key=values.count)
                        
        return common_patterns
        
    def _map_learning_type_to_category(self, learning_type: str) -> InsightCategory:
        """Map learning type to insight category."""
        mapping = {
            'strategy_optimization': InsightCategory.STRATEGY_OPTIMIZATION,
            'risk_management': InsightCategory.RISK_MANAGEMENT,
            'execution_improvement': InsightCategory.EXECUTION_EFFICIENCY,
            'timing_optimization': InsightCategory.TIMING_IMPROVEMENT,
            'market_analysis': InsightCategory.MARKET_ADAPTATION,
            'pattern_recognition': InsightCategory.PATTERN_RECOGNITION
        }
        
        return mapping.get(learning_type, InsightCategory.STRATEGY_OPTIMIZATION)
        
    # Background Tasks
    
    async def _process_learning_queue(self) -> None:
        """Process queued learnings for sharing."""
        while True:
            try:
                # Process recent unshared learnings
                for learning in self.shared_learnings:
                    unshared_agents = [
                        agent for agent in learning.target_agents
                        if learning.adoption_status.get(agent, "pending") == "pending"
                    ]
                    
                    if unshared_agents:
                        # Re-evaluate and share if appropriate
                        await self._share_learning_with_agents(learning)
                        
                # Wait before next processing
                await asyncio.sleep(300)  # Process every 5 minutes
                
            except Exception as e:
                logger.error(f"Learning queue processing error: {e}")
                await asyncio.sleep(600)
                
    async def _evaluate_shared_learnings(self) -> None:
        """Evaluate effectiveness of shared learnings."""
        while True:
            try:
                # Evaluate recent learnings
                evaluation_cutoff = datetime.utcnow() - timedelta(hours=24)
                
                for learning in self.shared_learnings:
                    if learning.shared_at > evaluation_cutoff:
                        continue  # Too recent to evaluate
                        
                    # Check adoption and impact
                    adoption_count = sum(1 for s in learning.adoption_status.values() if s == "adopted")
                    
                    if adoption_count > 0:
                        # Request performance updates from adopting agents
                        for agent, status in learning.adoption_status.items():
                            if status == "adopted" and agent not in learning.feedback:
                                await self.mcp.share_context(
                                    "CrossAgentLearningHub",
                                    [agent],
                                    {
                                        'performance_update_request': {
                                            'learning_id': learning.learning_id,
                                            'metrics_requested': list(learning.performance_improvement.keys())
                                        }
                                    }
                                )
                                
                # Synthesize learnings periodically
                if datetime.utcnow().hour == 0:  # At midnight
                    synthesized = await self.synthesize_learnings(timedelta(days=7))
                    
                    if synthesized:
                        logger.info(f"Synthesized {len(synthesized)} cross-agent insights")
                        
                        # Share synthesized insights
                        for insight in synthesized:
                            await self.mcp.share_context(
                                "CrossAgentLearningHub",
                                ["StrategicPlannerAgent", "LearningEngine"],
                                {
                                    'synthesized_insight': insight.dict()
                                }
                            )
                            
                # Wait before next evaluation
                await asyncio.sleep(3600)  # Evaluate every hour
                
            except Exception as e:
                logger.error(f"Learning evaluation error: {e}")
                await asyncio.sleep(1800)
                
    # Data Persistence
    
    async def _store_learning(self, learning: CrossAgentLearning) -> None:
        """Store learning in MCP."""
        await self.mcp.store_memory(
            "CrossAgentLearningHub",
            MemorySlice(
                memory_type=MemoryType.EVALUATION,
                content={
                    'cross_agent_learning': learning.dict(),
                    'timestamp': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.HIGH
            )
        )
        
    async def _load_historical_learnings(self) -> None:
        """Load historical learnings from MCP."""
        memories = await self.mcp.semantic_search(
            "CrossAgentLearningHub",
            "cross agent learning shared knowledge",
            scope="own"
        )
        
        for memory in memories:
            if 'cross_agent_learning' in memory.content:
                learning_data = memory.content['cross_agent_learning']
                learning = CrossAgentLearning(**learning_data)
                self.shared_learnings.append(learning)
                self.learning_index[learning.learning_id] = learning
                
        logger.info(f"Loaded {len(self.shared_learnings)} historical learnings")
        
    async def _save_learning_state(self) -> None:
        """Save current learning state."""
        state = {
            'total_learnings': len(self.shared_learnings),
            'adoption_rates': dict(self.adoption_rates),
            'learning_impact': dict(self.learning_impact),
            'performance_summary': await self.aggregate_cross_agent_performance()
        }
        
        await self.mcp.store_memory(
            "CrossAgentLearningHub",
            MemorySlice(
                memory_type=MemoryType.EVALUATION,
                content={
                    'learning_hub_state': state,
                    'timestamp': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.HIGH
            )
        )