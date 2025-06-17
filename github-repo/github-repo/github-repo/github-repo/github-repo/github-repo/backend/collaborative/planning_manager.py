"""
Collaborative Planning Manager
High-level interface for multi-agent collaborative planning.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta

from ..mcp.context_manager import MCPContextManager
from ..mcp.schemas import MemorySlice, MemoryType, MemoryImportance
from .schemas import (
    CollaborativePlan, PlanProposal, AgentVote, VoteType,
    PlanStatus, PlanPriority, ConsensusType, PlanningContext,
    WorkflowStep, CollaborativeWorkflow
)
from .planning_templates import PlanningTemplateLibrary
from .workflow_orchestrator import WorkflowOrchestrator
from .consensus_mechanisms import ConsensusEngine

logger = logging.getLogger(__name__)


class CollaborativePlanningManager:
    """
    Manages the entire collaborative planning lifecycle.
    """
    
    def __init__(self, mcp_manager: MCPContextManager):
        self.mcp = mcp_manager
        self.template_library = PlanningTemplateLibrary()
        self.orchestrator = WorkflowOrchestrator(mcp_manager)
        self.consensus_engine = ConsensusEngine()
        
        # Planning state
        self.active_plans: Dict[str, CollaborativePlan] = {}
        self.completed_plans: Dict[str, CollaborativePlan] = {}
        self.planning_queue: asyncio.Queue = asyncio.Queue()
        
        # Agent capabilities cache
        self.agent_capabilities: Dict[str, List[str]] = {}
        
    async def initialize(self) -> None:
        """Initialize the planning manager."""
        await self.orchestrator.initialize()
        
        # Load agent capabilities
        await self._load_agent_capabilities()
        
        # Start planning processor
        asyncio.create_task(self._process_planning_queue())
        
        logger.info("Collaborative Planning Manager initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the planning manager."""
        await self.orchestrator.shutdown()
        
        # Save active plans
        for plan in self.active_plans.values():
            await self._persist_plan(plan)
            
        logger.info("Collaborative Planning Manager shut down")
        
    # Plan Creation
    
    async def create_plan_from_template(self, template_name: str,
                                      initiator_agent: str,
                                      session_id: Optional[str] = None,
                                      customizations: Optional[Dict] = None) -> str:
        """
        Create a new plan from a template.
        
        Args:
            template_name: Name of template to use
            initiator_agent: Agent initiating the plan
            session_id: Optional trading session ID
            customizations: Optional customizations
            
        Returns:
            Plan ID
        """
        try:
            # Create plan from template
            plan = self.template_library.create_plan_from_template(
                template_name,
                initiator_agent,
                customizations
            )
            
            if not plan:
                raise ValueError(f"Failed to create plan from template {template_name}")
                
            # Set session ID
            if session_id:
                plan.session_id = session_id
                
            # Get current market context
            context = await self._build_planning_context(plan)
            
            # Add to active plans
            self.active_plans[plan.plan_id] = plan
            
            # Create plan in orchestrator
            await self.orchestrator.create_plan(plan)
            
            # Queue for processing
            await self.planning_queue.put({
                'action': 'process_new_plan',
                'plan_id': plan.plan_id,
                'context': context
            })
            
            logger.info(f"Created plan {plan.plan_id} from template {template_name}")
            
            return plan.plan_id
            
        except Exception as e:
            logger.error(f"Failed to create plan from template: {e}")
            raise
            
    async def create_custom_plan(self, title: str, description: str,
                               initiator_agent: str,
                               participating_agents: List[str],
                               consensus_type: ConsensusType = ConsensusType.MAJORITY,
                               priority: PlanPriority = PlanPriority.MEDIUM,
                               session_id: Optional[str] = None) -> str:
        """
        Create a custom collaborative plan.
        
        Args:
            title: Plan title
            description: Plan description
            initiator_agent: Initiating agent
            participating_agents: List of participating agents
            consensus_type: Type of consensus required
            priority: Plan priority
            session_id: Optional session ID
            
        Returns:
            Plan ID
        """
        try:
            # Create plan
            plan = CollaborativePlan(
                title=title,
                description=description,
                initiator_agent=initiator_agent,
                consensus_type=consensus_type,
                priority=priority,
                session_id=session_id
            )
            
            # Add participants
            plan.participating_agents.update(participating_agents)
            plan.participating_agents.add(initiator_agent)
            
            # Set deadlines based on priority
            if priority == PlanPriority.CRITICAL:
                deadline_hours = 0.5
            elif priority == PlanPriority.HIGH:
                deadline_hours = 1
            elif priority == PlanPriority.MEDIUM:
                deadline_hours = 2
            else:
                deadline_hours = 4
                
            deadline = datetime.utcnow() + timedelta(hours=deadline_hours)
            plan.proposal_deadline = deadline - timedelta(minutes=30)
            plan.voting_deadline = deadline - timedelta(minutes=15)
            plan.execution_deadline = deadline
            
            # Add to active plans
            self.active_plans[plan.plan_id] = plan
            
            # Create in orchestrator
            await self.orchestrator.create_plan(plan)
            
            # Queue for processing
            await self.planning_queue.put({
                'action': 'process_new_plan',
                'plan_id': plan.plan_id
            })
            
            logger.info(f"Created custom plan {plan.plan_id}: {title}")
            
            return plan.plan_id
            
        except Exception as e:
            logger.error(f"Failed to create custom plan: {e}")
            raise
            
    # Proposal Management
    
    async def submit_proposal(self, agent_id: str, plan_id: str,
                            proposal_data: Dict[str, Any]) -> bool:
        """
        Submit a proposal for a plan.
        
        Args:
            agent_id: Submitting agent
            plan_id: Plan to propose for
            proposal_data: Proposal details
            
        Returns:
            Success status
        """
        try:
            plan = self.active_plans.get(plan_id)
            if not plan:
                logger.error(f"Plan {plan_id} not found")
                return False
                
            # Create proposal
            proposal = PlanProposal(
                plan_id=plan_id,
                agent_id=agent_id,
                title=proposal_data['title'],
                description=proposal_data['description'],
                objectives=proposal_data.get('objectives', []),
                strategy_details=proposal_data.get('strategy_details', {}),
                proposed_start=datetime.utcnow() + timedelta(minutes=proposal_data.get('delay_minutes', 0)),
                estimated_duration=proposal_data.get('duration_minutes', 60),
                priority=plan.priority
            )
            
            # Submit through orchestrator
            success = await self.orchestrator.submit_proposal(agent_id, proposal)
            
            if success:
                # Queue for evaluation
                await self.planning_queue.put({
                    'action': 'evaluate_proposals',
                    'plan_id': plan_id
                })
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to submit proposal: {e}")
            return False
            
    # Voting Management
    
    async def cast_vote(self, agent_id: str, plan_id: str,
                       vote: VoteType, reasoning: str,
                       suggestions: Optional[List[str]] = None,
                       concerns: Optional[List[str]] = None) -> bool:
        """
        Cast a vote on a plan.
        
        Args:
            agent_id: Voting agent
            plan_id: Plan to vote on
            vote: Vote type
            reasoning: Reasoning for vote
            suggestions: Optional suggestions
            concerns: Optional concerns
            
        Returns:
            Success status
        """
        try:
            plan = self.active_plans.get(plan_id)
            if not plan:
                logger.error(f"Plan {plan_id} not found")
                return False
                
            # Calculate agent weight
            domain = self._get_plan_domain(plan)
            weight = self.consensus_engine.calculate_agent_weights(agent_id, domain)
            
            # Create vote
            agent_vote = AgentVote(
                plan_id=plan_id,
                agent_id=agent_id,
                vote=vote,
                weight=weight,
                reasoning=reasoning,
                suggestions=suggestions or [],
                concerns=concerns or []
            )
            
            # Cast through orchestrator
            success = await self.orchestrator.cast_vote(agent_id, agent_vote)
            
            if success:
                # Update consensus engine history
                self.consensus_engine.voting_history[agent_id].append(agent_vote)
                
                # Check consensus
                await self._check_and_handle_consensus(plan_id)
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to cast vote: {e}")
            return False
            
    # Plan Execution
    
    async def execute_plan(self, plan_id: str) -> Optional[str]:
        """
        Execute an approved plan.
        
        Args:
            plan_id: Plan to execute
            
        Returns:
            Workflow ID if created
        """
        try:
            plan = self.active_plans.get(plan_id)
            if not plan or plan.status != PlanStatus.APPROVED:
                logger.error(f"Plan {plan_id} not approved or not found")
                return None
                
            # Create workflow
            workflow_id = await self.orchestrator.create_workflow(plan_id)
            
            if workflow_id:
                # Queue for monitoring
                await self.planning_queue.put({
                    'action': 'monitor_execution',
                    'plan_id': plan_id,
                    'workflow_id': workflow_id
                })
                
            return workflow_id
            
        except Exception as e:
            logger.error(f"Failed to execute plan: {e}")
            return None
            
    # Query Methods
    
    async def get_active_plans(self, agent_id: Optional[str] = None) -> List[CollaborativePlan]:
        """
        Get active plans, optionally filtered by agent.
        
        Args:
            agent_id: Optional agent filter
            
        Returns:
            List of active plans
        """
        plans = list(self.active_plans.values())
        
        if agent_id:
            plans = [p for p in plans if agent_id in p.participating_agents]
            
        return plans
        
    async def get_plan_status(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed status of a plan.
        
        Args:
            plan_id: Plan ID
            
        Returns:
            Status dictionary
        """
        plan = self.active_plans.get(plan_id) or self.completed_plans.get(plan_id)
        
        if not plan:
            return None
            
        # Calculate consensus status
        consensus_reached, consensus_details = self.consensus_engine.calculate_consensus(plan)
        
        status = {
            'plan_id': plan.plan_id,
            'title': plan.title,
            'status': plan.status.value,
            'priority': plan.priority.value,
            'proposals_count': len(plan.proposals),
            'votes_cast': len(plan.votes),
            'consensus_reached': consensus_reached,
            'consensus_details': consensus_details,
            'participating_agents': list(plan.participating_agents),
            'deadlines': {
                'proposal': plan.proposal_deadline.isoformat() if plan.proposal_deadline else None,
                'voting': plan.voting_deadline.isoformat() if plan.voting_deadline else None,
                'execution': plan.execution_deadline.isoformat() if plan.execution_deadline else None
            }
        }
        
        return status
        
    async def get_agent_planning_stats(self, agent_id: str) -> Dict[str, Any]:
        """
        Get planning statistics for an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'agent_id': agent_id,
            'active_plans': 0,
            'completed_plans': 0,
            'proposals_submitted': 0,
            'votes_cast': 0,
            'consensus_success_rate': 0.0,
            'voting_patterns': {},
            'domain_expertise': {}
        }
        
        # Count active plans
        for plan in self.active_plans.values():
            if agent_id in plan.participating_agents:
                stats['active_plans'] += 1
                
        # Count completed plans
        for plan in self.completed_plans.values():
            if agent_id in plan.participating_agents:
                stats['completed_plans'] += 1
                
        # Count proposals and votes
        all_plans = list(self.active_plans.values()) + list(self.completed_plans.values())
        for plan in all_plans:
            stats['proposals_submitted'] += sum(1 for p in plan.proposals if p.agent_id == agent_id)
            if agent_id in plan.votes:
                stats['votes_cast'] += 1
                
        # Get voting patterns
        stats['voting_patterns'] = self.consensus_engine.detect_voting_patterns(agent_id)
        
        # Get domain expertise
        stats['domain_expertise'] = self.consensus_engine.domain_expertise.get(agent_id, {})
        
        return stats
        
    # Background Processing
    
    async def _process_planning_queue(self) -> None:
        """Process planning queue in background."""
        while True:
            try:
                item = await self.planning_queue.get()
                action = item.get('action')
                
                if action == 'process_new_plan':
                    await self._process_new_plan(item['plan_id'], item.get('context'))
                elif action == 'evaluate_proposals':
                    await self._evaluate_proposals(item['plan_id'])
                elif action == 'monitor_execution':
                    await self._monitor_execution(item['plan_id'], item['workflow_id'])
                    
            except Exception as e:
                logger.error(f"Error processing planning queue: {e}")
                
            await asyncio.sleep(0.1)
            
    async def _process_new_plan(self, plan_id: str, context: Optional[Dict] = None) -> None:
        """Process a newly created plan."""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return
            
        # Share planning context with agents
        if context:
            await self.mcp.share_context(
                "CollaborativePlanningManager",
                list(plan.participating_agents),
                {
                    'planning_context': context,
                    'plan_id': plan_id
                }
            )
            
        # If using template, suggest workflow
        if any('template:' in tag for tag in plan.tags):
            template_name = next(
                (tag.split(':')[1] for tag in plan.tags if tag.startswith('template:')),
                None
            )
            if template_name:
                workflow_steps = self.template_library.get_workflow_for_template(template_name)
                
                # Share suggested workflow
                await self.mcp.share_context(
                    "CollaborativePlanningManager",
                    list(plan.participating_agents),
                    {
                        'suggested_workflow': [step.dict() for step in workflow_steps],
                        'plan_id': plan_id
                    }
                )
                
    async def _evaluate_proposals(self, plan_id: str) -> None:
        """Evaluate proposals for a plan."""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return
            
        # Check if all required agents have submitted
        submitters = {p.agent_id for p in plan.proposals}
        if not plan.required_approvals.issubset(submitters):
            # Still waiting for proposals
            return
            
        # Rank proposals
        context = await self._build_planning_context(plan)
        ranked_proposals = self.consensus_engine.rank_proposals(
            plan.proposals,
            context
        )
        
        # Share rankings
        await self.mcp.share_context(
            "CollaborativePlanningManager",
            list(plan.participating_agents),
            {
                'proposal_rankings': [
                    {
                        'proposal_id': p.proposal_id,
                        'agent_id': p.agent_id,
                        'score': score
                    }
                    for p, score in ranked_proposals
                ],
                'plan_id': plan_id
            }
        )
        
    async def _check_and_handle_consensus(self, plan_id: str) -> None:
        """Check and handle consensus for a plan."""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return
            
        # Calculate consensus
        consensus_reached, details = self.consensus_engine.calculate_consensus(plan)
        
        # Store consensus check
        await self.mcp.store_memory(
            "CollaborativePlanningManager",
            MemorySlice(
                memory_type=MemoryType.EVALUATION,
                content={
                    'plan_id': plan_id,
                    'consensus_check': details,
                    'consensus_reached': consensus_reached,
                    'timestamp': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.HIGH
            )
        )
        
        if consensus_reached:
            # Plan approved
            plan.status = PlanStatus.APPROVED
            plan.consensus_reached_at = datetime.utcnow()
            
            # Execute plan
            await self.execute_plan(plan_id)
            
        elif self._all_votes_cast(plan):
            # No consensus but all votes cast
            if details.get('type') == 'veto' and details.get('vetoed'):
                # Plan vetoed
                plan.status = PlanStatus.REJECTED
            else:
                # Try to find compromise
                compromise = self.consensus_engine.find_compromise(
                    plan.proposals,
                    plan.votes
                )
                
                if compromise:
                    # Share compromise
                    await self.mcp.share_context(
                        "CollaborativePlanningManager",
                        list(plan.participating_agents),
                        {
                            'compromise_proposal': compromise,
                            'plan_id': plan_id,
                            'action': 'review_compromise'
                        }
                    )
                else:
                    # No compromise possible
                    plan.status = PlanStatus.REJECTED
                    
    def _all_votes_cast(self, plan: CollaborativePlan) -> bool:
        """Check if all required votes are cast."""
        return len(plan.votes) >= len(plan.required_approvals)
        
    async def _monitor_execution(self, plan_id: str, workflow_id: str) -> None:
        """Monitor plan execution."""
        # Execution monitoring is handled by the orchestrator
        # This method could add additional monitoring logic
        pass
        
    async def _build_planning_context(self, plan: CollaborativePlan) -> PlanningContext:
        """Build planning context for a plan."""
        # Get current market conditions
        market_conditions = await self._get_current_market_conditions()
        
        # Get recent performance
        recent_performance = await self._get_recent_performance(plan.session_id)
        
        # Create context
        context = PlanningContext(
            plan_id=plan.plan_id,
            market_conditions=market_conditions,
            recent_performance=recent_performance
        )
        
        return context
        
    async def _get_current_market_conditions(self) -> Dict[str, Any]:
        """Get current market conditions."""
        # Query from MCP
        memories = await self.mcp.semantic_search(
            "CollaborativePlanningManager",
            "current SPY price VIX level market regime",
            scope="global"
        )
        
        if memories:
            return memories[0].content
            
        return {}
        
    async def _get_recent_performance(self, session_id: Optional[str]) -> Dict[str, Any]:
        """Get recent trading performance."""
        if not session_id:
            return {}
            
        # Query performance from MCP
        memories = await self.mcp.semantic_search(
            "CollaborativePlanningManager",
            f"session {session_id} performance metrics profit loss",
            scope="session"
        )
        
        if memories:
            return memories[0].content
            
        return {}
        
    def _get_plan_domain(self, plan: CollaborativePlan) -> str:
        """Determine domain of a plan."""
        # Simple heuristic based on plan type
        if 'risk' in plan.title.lower():
            return 'risk_management'
        elif 'strategy' in plan.title.lower():
            return 'strategy_selection'
        elif 'exit' in plan.title.lower():
            return 'position_management'
        else:
            return 'general'
            
    async def _persist_plan(self, plan: CollaborativePlan) -> None:
        """Persist plan to MCP."""
        await self.mcp.store_memory(
            "CollaborativePlanningManager",
            MemorySlice(
                memory_type=MemoryType.STRATEGIC_PLANNING,
                content={
                    'plan': plan.dict(),
                    'final_status': plan.status.value,
                    'completed': plan.completed_at.isoformat() if plan.completed_at else None
                },
                importance=MemoryImportance.HIGH
            )
        )
        
    async def _load_agent_capabilities(self) -> None:
        """Load agent capabilities from MCP."""
        # This would query MCP for registered agents and their capabilities
        # For now, use defaults
        self.agent_capabilities = {
            "EnvironmentWatcherAgent": ["market_monitoring", "regime_detection"],
            "StrategicPlannerAgent": ["strategy_planning", "risk_assessment"],
            "ExecutorAgent": ["trade_execution", "position_management"],
            "EvaluatorAgent": ["performance_evaluation", "analysis"],
            "RiskManagerAgent": ["risk_management", "compliance"],
            "RewardModelAgent": ["learning", "optimization"]
        }