"""
Workflow Orchestration Engine
Manages execution of multi-agent collaborative workflows.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import json

from ..mcp.context_manager import MCPContextManager
from ..mcp.schemas import MemorySlice, MemoryType, MemoryImportance
from .schemas import (
    CollaborativePlan, CollaborativeWorkflow, WorkflowStep,
    PlanStatus, PlanProposal, AgentVote, VoteType,
    PlanningContext, ConflictResolution
)

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Orchestrates collaborative workflows between multiple agents.
    """
    
    def __init__(self, mcp_manager: MCPContextManager):
        self.mcp = mcp_manager
        self.active_workflows: Dict[str, CollaborativeWorkflow] = {}
        self.active_plans: Dict[str, CollaborativePlan] = {}
        self.step_handlers: Dict[str, Callable] = {}
        self.agent_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._background_tasks: Set[asyncio.Task] = set()
        
    async def initialize(self) -> None:
        """Initialize the orchestrator."""
        # Register as a system agent
        await self.mcp.register_agent(
            "WorkflowOrchestrator",
            ["workflow_management", "plan_coordination", "conflict_resolution"]
        )
        
        # Start background monitoring
        task = asyncio.create_task(self._monitor_workflows())
        self._background_tasks.add(task)
        
        logger.info("Workflow Orchestrator initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the orchestrator."""
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
            
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        logger.info("Workflow Orchestrator shut down")
        
    # Plan Management
    
    async def create_plan(self, plan: CollaborativePlan) -> str:
        """
        Create a new collaborative plan.
        
        Args:
            plan: The plan to create
            
        Returns:
            Plan ID
        """
        try:
            # Store plan
            self.active_plans[plan.plan_id] = plan
            
            # Store in MCP for persistence
            await self.mcp.store_memory(
                "WorkflowOrchestrator",
                MemorySlice(
                    memory_type=MemoryType.STRATEGIC_PLANNING,
                    content={
                        'plan_id': plan.plan_id,
                        'plan_data': plan.dict(),
                        'event': 'plan_created'
                    },
                    importance=MemoryImportance.HIGH
                )
            )
            
            # Notify participating agents
            await self._notify_agents(
                plan.participating_agents,
                {
                    'event': 'plan_created',
                    'plan_id': plan.plan_id,
                    'title': plan.title,
                    'initiator': plan.initiator_agent,
                    'deadline': plan.proposal_deadline.isoformat() if plan.proposal_deadline else None
                }
            )
            
            # Create planning context
            context = PlanningContext(
                plan_id=plan.plan_id,
                market_conditions=await self._get_current_market_conditions()
            )
            
            # Share context with agents
            await self.mcp.share_context(
                "WorkflowOrchestrator",
                list(plan.participating_agents),
                {'planning_context': context.dict()}
            )
            
            logger.info(f"Created plan {plan.plan_id}: {plan.title}")
            
            return plan.plan_id
            
        except Exception as e:
            logger.error(f"Failed to create plan: {e}")
            raise
            
    async def submit_proposal(self, agent_id: str, proposal: PlanProposal) -> bool:
        """
        Submit a proposal for a plan.
        
        Args:
            agent_id: Submitting agent
            proposal: The proposal
            
        Returns:
            Success status
        """
        try:
            plan = self.active_plans.get(proposal.plan_id)
            if not plan:
                logger.error(f"Plan {proposal.plan_id} not found")
                return False
                
            # Check deadline
            if plan.proposal_deadline and datetime.utcnow() > plan.proposal_deadline:
                logger.warning(f"Proposal deadline passed for plan {plan.plan_id}")
                return False
                
            # Add proposal
            proposal.agent_id = agent_id
            plan.add_proposal(proposal)
            plan.status = PlanStatus.PROPOSED
            
            # Store in MCP
            await self.mcp.store_memory(
                agent_id,
                MemorySlice(
                    memory_type=MemoryType.STRATEGIC_PLANNING,
                    content={
                        'plan_id': plan.plan_id,
                        'proposal': proposal.dict(),
                        'event': 'proposal_submitted'
                    },
                    importance=MemoryImportance.HIGH
                )
            )
            
            # Notify other agents
            await self._notify_agents(
                plan.participating_agents - {agent_id},
                {
                    'event': 'proposal_submitted',
                    'plan_id': plan.plan_id,
                    'proposal_id': proposal.proposal_id,
                    'agent_id': agent_id,
                    'title': proposal.title
                }
            )
            
            # Check if all required agents have submitted
            submitters = {p.agent_id for p in plan.proposals}
            if plan.required_approvals.issubset(submitters):
                await self._initiate_voting(plan.plan_id)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit proposal: {e}")
            return False
            
    async def cast_vote(self, agent_id: str, vote: AgentVote) -> bool:
        """
        Cast a vote on a plan.
        
        Args:
            agent_id: Voting agent
            vote: The vote
            
        Returns:
            Success status
        """
        try:
            plan = self.active_plans.get(vote.plan_id)
            if not plan:
                logger.error(f"Plan {vote.plan_id} not found")
                return False
                
            # Check voting deadline
            if plan.voting_deadline and datetime.utcnow() > plan.voting_deadline:
                logger.warning(f"Voting deadline passed for plan {plan.plan_id}")
                return False
                
            # Cast vote
            vote.agent_id = agent_id
            plan.cast_vote(vote)
            
            # Store in MCP
            await self.mcp.store_memory(
                agent_id,
                MemorySlice(
                    memory_type=MemoryType.EVALUATION,
                    content={
                        'plan_id': plan.plan_id,
                        'vote': vote.dict(),
                        'event': 'vote_cast'
                    },
                    importance=MemoryImportance.MEDIUM
                )
            )
            
            # Check consensus
            if plan.check_consensus():
                await self._approve_plan(plan.plan_id)
            elif self._check_rejection(plan):
                await self._reject_plan(plan.plan_id)
            elif self._all_votes_cast(plan):
                await self._handle_no_consensus(plan.plan_id)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to cast vote: {e}")
            return False
            
    # Workflow Execution
    
    async def create_workflow(self, plan_id: str) -> Optional[str]:
        """
        Create a workflow from an approved plan.
        
        Args:
            plan_id: Plan to create workflow from
            
        Returns:
            Workflow ID if created
        """
        try:
            plan = self.active_plans.get(plan_id)
            if not plan or plan.status != PlanStatus.APPROVED:
                logger.error(f"Plan {plan_id} not approved or not found")
                return None
                
            # Create workflow
            workflow = CollaborativeWorkflow(
                plan_id=plan_id,
                name=f"Workflow for {plan.title}",
                description=plan.description
            )
            
            # Add steps based on selected proposal
            if plan.selected_proposal_id:
                proposal = next(
                    (p for p in plan.proposals if p.proposal_id == plan.selected_proposal_id),
                    None
                )
                if proposal:
                    # Generate steps from proposal
                    steps = await self._generate_workflow_steps(proposal)
                    for step in steps:
                        workflow.add_step(step)
                        
            # Store workflow
            self.active_workflows[workflow.workflow_id] = workflow
            
            # Update plan status
            plan.status = PlanStatus.EXECUTING
            
            # Start execution
            task = asyncio.create_task(self._execute_workflow(workflow.workflow_id))
            self._background_tasks.add(task)
            
            logger.info(f"Created workflow {workflow.workflow_id} for plan {plan_id}")
            
            return workflow.workflow_id
            
        except Exception as e:
            logger.error(f"Failed to create workflow: {e}")
            return None
            
    async def _execute_workflow(self, workflow_id: str) -> None:
        """Execute a workflow asynchronously."""
        try:
            workflow = self.active_workflows.get(workflow_id)
            if not workflow:
                return
                
            workflow.status = "executing"
            workflow.started_at = datetime.utcnow()
            
            # Execute steps
            while True:
                # Get next steps
                ready_steps = workflow.get_next_steps()
                if not ready_steps:
                    # Check if workflow is complete
                    if len(workflow.completed_steps) == len(workflow.steps):
                        workflow.status = "completed"
                        workflow.completed_at = datetime.utcnow()
                        await self._complete_workflow(workflow_id)
                        break
                    elif workflow.failed_steps:
                        workflow.status = "failed"
                        await self._fail_workflow(workflow_id)
                        break
                    else:
                        # Wait for dependencies
                        await asyncio.sleep(1)
                        continue
                        
                # Execute ready steps in parallel
                tasks = []
                for step in ready_steps:
                    task = asyncio.create_task(
                        self._execute_step(workflow_id, step.step_id)
                    )
                    tasks.append(task)
                    
                await asyncio.gather(*tasks)
                
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            workflow.status = "failed"
            
    async def _execute_step(self, workflow_id: str, step_id: str) -> None:
        """Execute a single workflow step."""
        try:
            workflow = self.active_workflows.get(workflow_id)
            if not workflow:
                return
                
            step = workflow.steps.get(step_id)
            if not step:
                return
                
            step.status = "executing"
            step.started_at = datetime.utcnow()
            
            # Notify responsible agent
            await self._send_to_agent(
                step.responsible_agent,
                {
                    'event': 'execute_step',
                    'workflow_id': workflow_id,
                    'step': step.dict()
                }
            )
            
            # Wait for completion (with timeout)
            timeout = 300  # 5 minutes default
            start_time = datetime.utcnow()
            
            while (datetime.utcnow() - start_time).seconds < timeout:
                # Check if agent has completed the step
                result = await self._check_step_completion(step.responsible_agent, step_id)
                if result:
                    step.output_data = result
                    step.status = "completed"
                    step.completed_at = datetime.utcnow()
                    workflow.completed_steps.add(step_id)
                    
                    # Store completion in MCP
                    await self.mcp.store_memory(
                        step.responsible_agent,
                        MemorySlice(
                            memory_type=MemoryType.EXECUTION_PLAN,
                            content={
                                'workflow_id': workflow_id,
                                'step_id': step_id,
                                'result': result,
                                'event': 'step_completed'
                            },
                            importance=MemoryImportance.MEDIUM
                        )
                    )
                    
                    break
                    
                await asyncio.sleep(1)
            else:
                # Timeout
                step.status = "failed"
                workflow.failed_steps.add(step_id)
                logger.error(f"Step {step_id} timed out")
                
        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            step.status = "failed"
            workflow.failed_steps.add(step_id)
            
    # Conflict Resolution
    
    async def resolve_conflict(self, plan_id: str, 
                             conflicting_agents: List[str],
                             conflict_type: str,
                             conflict_description: str) -> ConflictResolution:
        """
        Resolve conflicts between agents.
        
        Args:
            plan_id: Plan with conflict
            conflicting_agents: Agents in conflict
            conflict_type: Type of conflict
            conflict_description: Description
            
        Returns:
            Conflict resolution
        """
        try:
            resolution = ConflictResolution(
                plan_id=plan_id,
                conflicting_agents=conflicting_agents,
                conflict_type=conflict_type,
                conflict_description=conflict_description,
                resolution_method="",
                final_decision={},
                decided_by=""
            )
            
            # Get agent positions
            for agent_id in conflicting_agents:
                position = await self._get_agent_position(agent_id, plan_id)
                resolution.agent_positions[agent_id] = position
                
            # Try different resolution methods
            
            # 1. Compromise based on weighted expertise
            if conflict_type == "strategy_selection":
                resolution.resolution_method = "weighted_expertise"
                final_strategy = await self._weighted_strategy_selection(
                    resolution.agent_positions
                )
                resolution.final_decision = final_strategy
                resolution.decided_by = "consensus_algorithm"
                
            # 2. Risk-based resolution
            elif conflict_type == "risk_assessment":
                resolution.resolution_method = "conservative_approach"
                # Take most conservative risk assessment
                resolution.final_decision = self._most_conservative_position(
                    resolution.agent_positions
                )
                resolution.decided_by = "risk_priority"
                
            # 3. Performance-based resolution
            elif conflict_type == "execution_timing":
                resolution.resolution_method = "performance_history"
                best_performer = await self._get_best_performer(conflicting_agents)
                resolution.final_decision = resolution.agent_positions[best_performer]
                resolution.decided_by = best_performer
                
            # 4. Escalation to human
            else:
                resolution.resolution_method = "human_intervention"
                # Would trigger human review in production
                resolution.final_decision = {"requires_human_review": True}
                resolution.decided_by = "human_operator"
                
            resolution.resolved_at = datetime.utcnow()
            
            # Store resolution
            await self.mcp.store_memory(
                "WorkflowOrchestrator",
                MemorySlice(
                    memory_type=MemoryType.EVALUATION,
                    content=resolution.dict(),
                    importance=MemoryImportance.HIGH
                )
            )
            
            # Notify agents of resolution
            await self._notify_agents(
                set(conflicting_agents),
                {
                    'event': 'conflict_resolved',
                    'resolution': resolution.dict()
                }
            )
            
            return resolution
            
        except Exception as e:
            logger.error(f"Failed to resolve conflict: {e}")
            raise
            
    # Helper Methods
    
    async def _monitor_workflows(self) -> None:
        """Background task to monitor workflow progress."""
        while True:
            try:
                # Check for stalled workflows
                for workflow_id, workflow in self.active_workflows.items():
                    if workflow.status == "executing":
                        # Check if workflow is making progress
                        if workflow.started_at:
                            elapsed = (datetime.utcnow() - workflow.started_at).seconds
                            if elapsed > 3600:  # 1 hour timeout
                                logger.warning(f"Workflow {workflow_id} appears stalled")
                                await self._escalate_workflow(workflow_id)
                                
                # Check for plan deadlines
                for plan_id, plan in self.active_plans.items():
                    if plan.proposal_deadline and datetime.utcnow() > plan.proposal_deadline:
                        if plan.status == PlanStatus.DRAFT:
                            await self._handle_proposal_timeout(plan_id)
                            
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(30)
                
    async def _notify_agents(self, agents: Set[str], message: Dict[str, Any]) -> None:
        """Notify a set of agents."""
        await self.mcp.share_context(
            "WorkflowOrchestrator",
            list(agents),
            message
        )
        
    async def _send_to_agent(self, agent_id: str, message: Dict[str, Any]) -> None:
        """Send message to specific agent."""
        await self.agent_queues[agent_id].put(message)
        
    async def _get_current_market_conditions(self) -> Dict[str, Any]:
        """Get current market conditions from environment watcher."""
        # Query recent market observations
        memories = await self.mcp.semantic_search(
            "WorkflowOrchestrator",
            "current market conditions SPY VIX",
            scope="global"
        )
        
        if memories:
            return memories[0].content
        
        return {
            'spy_price': 0,
            'vix_level': 0,
            'market_regime': 'unknown'
        }
        
    async def _initiate_voting(self, plan_id: str) -> None:
        """Initiate voting phase for a plan."""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return
            
        plan.status = PlanStatus.UNDER_REVIEW
        
        await self._notify_agents(
            plan.participating_agents,
            {
                'event': 'voting_initiated',
                'plan_id': plan_id,
                'proposals': [p.dict() for p in plan.proposals],
                'deadline': plan.voting_deadline.isoformat() if plan.voting_deadline else None
            }
        )
        
    async def _approve_plan(self, plan_id: str) -> None:
        """Approve a plan and prepare for execution."""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return
            
        plan.status = PlanStatus.APPROVED
        
        # Select best proposal based on votes
        proposal_scores = defaultdict(float)
        for vote in plan.votes.values():
            if vote.vote == VoteType.APPROVE:
                # Accumulate weighted scores
                proposal_scores[vote.agent_id] += vote.weight * vote.confidence
                
        if proposal_scores:
            best_agent = max(proposal_scores.items(), key=lambda x: x[1])[0]
            best_proposal = next(
                (p for p in plan.proposals if p.agent_id == best_agent),
                None
            )
            if best_proposal:
                plan.selected_proposal_id = best_proposal.proposal_id
                
        # Create workflow
        await self.create_workflow(plan_id)
        
    async def _reject_plan(self, plan_id: str) -> None:
        """Reject a plan."""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return
            
        plan.status = PlanStatus.REJECTED
        
        await self._notify_agents(
            plan.participating_agents,
            {
                'event': 'plan_rejected',
                'plan_id': plan_id,
                'reason': 'consensus_not_reached'
            }
        )
        
    async def _handle_no_consensus(self, plan_id: str) -> None:
        """Handle case where no consensus is reached."""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return
            
        # Identify conflicts
        conflicting_agents = []
        for agent_id, vote in plan.votes.items():
            if vote.vote != VoteType.APPROVE:
                conflicting_agents.append(agent_id)
                
        if len(conflicting_agents) >= 2:
            await self.resolve_conflict(
                plan_id,
                conflicting_agents,
                "consensus_failure",
                "Agents could not reach consensus on plan"
            )
            
    def _check_rejection(self, plan: CollaborativePlan) -> bool:
        """Check if plan should be rejected."""
        reject_count = sum(1 for v in plan.votes.values() if v.vote == VoteType.REJECT)
        total_count = len(plan.votes)
        
        if total_count == 0:
            return False
            
        reject_ratio = reject_count / total_count
        return reject_ratio > (1 - plan.consensus_threshold)
        
    def _all_votes_cast(self, plan: CollaborativePlan) -> bool:
        """Check if all required votes are cast."""
        return plan.required_approvals.issubset(set(plan.votes.keys()))
        
    async def _generate_workflow_steps(self, proposal: PlanProposal) -> List[WorkflowStep]:
        """Generate workflow steps from a proposal."""
        # This would be customized based on proposal type
        # For now, return generic steps
        return [
            WorkflowStep(
                workflow_id="",
                name="Prepare Execution",
                description="Prepare for strategy execution",
                responsible_agent=proposal.agent_id
            ),
            WorkflowStep(
                workflow_id="",
                name="Execute Strategy",
                description="Execute the proposed strategy",
                responsible_agent="ExecutorAgent",
                depends_on=["Prepare Execution"]
            ),
            WorkflowStep(
                workflow_id="",
                name="Monitor Results",
                description="Monitor execution results",
                responsible_agent="EvaluatorAgent",
                depends_on=["Execute Strategy"]
            )
        ]
        
    async def _check_step_completion(self, agent_id: str, step_id: str) -> Optional[Dict]:
        """Check if an agent has completed a step."""
        # Check agent queue for completion message
        try:
            while not self.agent_queues[agent_id].empty():
                message = await self.agent_queues[agent_id].get()
                if (message.get('event') == 'step_completed' and 
                    message.get('step_id') == step_id):
                    return message.get('result', {})
        except:
            pass
        return None
        
    async def _complete_workflow(self, workflow_id: str) -> None:
        """Handle workflow completion."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return
            
        plan = self.active_plans.get(workflow.plan_id)
        if plan:
            plan.status = PlanStatus.COMPLETED
            plan.completed_at = datetime.utcnow()
            plan.execution_results = workflow.workflow_output
            
        await self._notify_agents(
            workflow.participating_agents,
            {
                'event': 'workflow_completed',
                'workflow_id': workflow_id,
                'results': workflow.workflow_output
            }
        )
        
    async def _fail_workflow(self, workflow_id: str) -> None:
        """Handle workflow failure."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return
            
        await self._notify_agents(
            workflow.participating_agents,
            {
                'event': 'workflow_failed',
                'workflow_id': workflow_id,
                'failed_steps': list(workflow.failed_steps)
            }
        )
        
    async def _escalate_workflow(self, workflow_id: str) -> None:
        """Escalate a stalled workflow."""
        # In production, this would notify human operators
        logger.error(f"Workflow {workflow_id} requires escalation")
        
    async def _handle_proposal_timeout(self, plan_id: str) -> None:
        """Handle timeout in proposal phase."""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return
            
        if not plan.proposals:
            # No proposals received
            plan.status = PlanStatus.CANCELLED
            await self._notify_agents(
                plan.participating_agents,
                {
                    'event': 'plan_cancelled',
                    'plan_id': plan_id,
                    'reason': 'no_proposals_received'
                }
            )
        else:
            # Proceed with what we have
            await self._initiate_voting(plan_id)
            
    async def _weighted_strategy_selection(self, positions: Dict[str, Dict]) -> Dict:
        """Select strategy based on weighted agent expertise."""
        # Simplified implementation
        # In production, would consider agent track records
        strategies = {}
        for agent_id, position in positions.items():
            strategy = position.get('proposed_strategy', {})
            weight = position.get('confidence', 0.5)
            strategies[json.dumps(strategy)] = strategies.get(json.dumps(strategy), 0) + weight
            
        # Return most weighted strategy
        if strategies:
            best_strategy_json = max(strategies.items(), key=lambda x: x[1])[0]
            return json.loads(best_strategy_json)
        return {}
        
    def _most_conservative_position(self, positions: Dict[str, Dict]) -> Dict:
        """Select most conservative position."""
        min_risk = float('inf')
        conservative_position = {}
        
        for position in positions.values():
            risk_level = position.get('risk_level', float('inf'))
            if risk_level < min_risk:
                min_risk = risk_level
                conservative_position = position
                
        return conservative_position
        
    async def _get_best_performer(self, agents: List[str]) -> str:
        """Get best performing agent based on history."""
        # Query performance metrics from MCP
        best_agent = agents[0]  # Default to first
        best_score = 0
        
        for agent_id in agents:
            # Get recent performance
            memories = await self.mcp.semantic_search(
                "WorkflowOrchestrator",
                f"{agent_id} performance success rate",
                scope="global"
            )
            
            if memories:
                # Extract performance score
                score = memories[0].content.get('success_rate', 0)
                if score > best_score:
                    best_score = score
                    best_agent = agent_id
                    
        return best_agent
        
    async def _get_agent_position(self, agent_id: str, plan_id: str) -> Dict:
        """Get agent's position on a plan."""
        # Find agent's proposal or vote
        plan = self.active_plans.get(plan_id)
        if not plan:
            return {}
            
        # Check proposals
        for proposal in plan.proposals:
            if proposal.agent_id == agent_id:
                return {
                    'proposed_strategy': proposal.strategy_details,
                    'confidence': proposal.priority.value / 4.0  # Normalize priority
                }
                
        # Check votes
        vote = plan.votes.get(agent_id)
        if vote:
            return {
                'vote': vote.vote.value,
                'reasoning': vote.reasoning,
                'suggestions': vote.suggestions
            }
            
        return {}