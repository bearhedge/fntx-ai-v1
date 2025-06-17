"""
Collaborative Planning Framework Schemas
Defines data models for multi-agent planning and coordination.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from pydantic import BaseModel, Field, validator
from uuid import uuid4


class PlanStatus(str, Enum):
    """Status of a collaborative plan."""
    DRAFT = "draft"
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    CONSENSUS_REACHED = "consensus_reached"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class VoteType(str, Enum):
    """Types of votes agents can cast."""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"
    REQUEST_CHANGES = "request_changes"


class PlanPriority(int, Enum):
    """Priority levels for plans."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class ConsensusType(str, Enum):
    """Types of consensus mechanisms."""
    UNANIMOUS = "unanimous"
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    QUORUM = "quorum"
    VETO_POWER = "veto_power"


class AgentRole(str, Enum):
    """Roles agents can play in planning."""
    INITIATOR = "initiator"
    REVIEWER = "reviewer"
    APPROVER = "approver"
    EXECUTOR = "executor"
    OBSERVER = "observer"


class PlanTemplate(BaseModel):
    """Template for common planning patterns."""
    template_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="What this template is for")
    
    # Structure
    required_sections: List[str] = Field(..., description="Required plan sections")
    optional_sections: List[str] = Field(default_factory=list)
    validation_rules: Dict[str, Any] = Field(default_factory=dict)
    
    # Participants
    required_agents: List[str] = Field(..., description="Agents that must participate")
    optional_agents: List[str] = Field(default_factory=list)
    consensus_type: ConsensusType = Field(default=ConsensusType.MAJORITY)
    
    # Constraints
    max_duration_hours: Optional[int] = Field(None, description="Max planning duration")
    requires_human_approval: bool = Field(default=False)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    usage_count: int = Field(default=0)
    success_rate: float = Field(default=0.0)


class PlanProposal(BaseModel):
    """A proposed plan from an agent."""
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    plan_id: str = Field(..., description="ID of the plan this proposal is for")
    agent_id: str = Field(..., description="Proposing agent")
    
    # Content
    title: str = Field(..., description="Proposal title")
    description: str = Field(..., description="Detailed description")
    objectives: List[str] = Field(..., description="What this plan aims to achieve")
    
    # Details
    strategy_details: Dict[str, Any] = Field(..., description="Strategy specifics")
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)
    risk_assessment: Dict[str, Any] = Field(default_factory=dict)
    expected_outcomes: Dict[str, Any] = Field(default_factory=dict)
    
    # Timing
    proposed_start: datetime = Field(..., description="When to start")
    estimated_duration: int = Field(..., description="Duration in minutes")
    
    # Priority
    priority: PlanPriority = Field(default=PlanPriority.MEDIUM)
    urgency_reason: Optional[str] = Field(None)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    template_used: Optional[str] = Field(None, description="Template ID if used")


class AgentVote(BaseModel):
    """Vote cast by an agent on a plan."""
    vote_id: str = Field(default_factory=lambda: str(uuid4()))
    plan_id: str = Field(..., description="Plan being voted on")
    agent_id: str = Field(..., description="Voting agent")
    
    # Vote
    vote: VoteType = Field(..., description="The vote")
    weight: float = Field(default=1.0, description="Vote weight based on expertise")
    
    # Reasoning
    reasoning: str = Field(..., description="Why this vote was cast")
    concerns: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    
    # Conditions
    conditional_approval: bool = Field(default=False)
    conditions: List[str] = Field(default_factory=list)
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class CollaborativePlan(BaseModel):
    """A plan developed collaboratively by multiple agents."""
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: Optional[str] = Field(None, description="Trading session ID")
    
    # Basic Info
    title: str = Field(..., description="Plan title")
    description: str = Field(..., description="Plan description")
    initiator_agent: str = Field(..., description="Agent who initiated the plan")
    
    # Status
    status: PlanStatus = Field(default=PlanStatus.DRAFT)
    priority: PlanPriority = Field(default=PlanPriority.MEDIUM)
    
    # Participants
    participating_agents: Set[str] = Field(default_factory=set)
    agent_roles: Dict[str, AgentRole] = Field(default_factory=dict)
    required_approvals: Set[str] = Field(default_factory=set)
    
    # Proposals
    proposals: List[PlanProposal] = Field(default_factory=list)
    selected_proposal_id: Optional[str] = Field(None)
    
    # Voting
    votes: Dict[str, AgentVote] = Field(default_factory=dict)
    consensus_type: ConsensusType = Field(default=ConsensusType.MAJORITY)
    consensus_threshold: float = Field(default=0.66)
    
    # Execution
    execution_plan: Optional[Dict[str, Any]] = Field(None)
    assigned_executors: List[str] = Field(default_factory=list)
    execution_timeline: Optional[Dict[str, Any]] = Field(None)
    
    # Results
    execution_results: Optional[Dict[str, Any]] = Field(None)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
    
    # Timeline
    created_at: datetime = Field(default_factory=datetime.utcnow)
    proposal_deadline: Optional[datetime] = Field(None)
    voting_deadline: Optional[datetime] = Field(None)
    execution_deadline: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    parent_plan_id: Optional[str] = Field(None)
    child_plan_ids: List[str] = Field(default_factory=list)
    
    @validator('consensus_threshold')
    def validate_threshold(cls, v, values):
        """Ensure threshold is appropriate for consensus type."""
        consensus_type = values.get('consensus_type', ConsensusType.MAJORITY)
        if consensus_type == ConsensusType.UNANIMOUS:
            return 1.0
        elif consensus_type == ConsensusType.MAJORITY:
            return max(0.5, min(v, 1.0))
        return v
    
    def add_proposal(self, proposal: PlanProposal) -> None:
        """Add a proposal to the plan."""
        self.proposals.append(proposal)
        self.participating_agents.add(proposal.agent_id)
        
    def cast_vote(self, vote: AgentVote) -> None:
        """Cast a vote on the plan."""
        self.votes[vote.agent_id] = vote
        
    def check_consensus(self) -> bool:
        """Check if consensus has been reached."""
        if not self.votes:
            return False
            
        total_weight = sum(v.weight for v in self.votes.values())
        approve_weight = sum(
            v.weight for v in self.votes.values() 
            if v.vote == VoteType.APPROVE
        )
        
        if self.consensus_type == ConsensusType.UNANIMOUS:
            return all(v.vote == VoteType.APPROVE for v in self.votes.values())
        elif self.consensus_type == ConsensusType.MAJORITY:
            return approve_weight / total_weight >= self.consensus_threshold
        elif self.consensus_type == ConsensusType.VETO_POWER:
            # Any rejection vetoes the plan
            return not any(v.vote == VoteType.REJECT for v in self.votes.values())
        else:
            return approve_weight / total_weight >= self.consensus_threshold


class WorkflowStep(BaseModel):
    """A step in a collaborative workflow."""
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    workflow_id: str = Field(..., description="Parent workflow ID")
    
    # Definition
    name: str = Field(..., description="Step name")
    description: str = Field(..., description="What this step does")
    responsible_agent: str = Field(..., description="Agent responsible for this step")
    
    # Dependencies
    depends_on: List[str] = Field(default_factory=list, description="Previous step IDs")
    blocks: List[str] = Field(default_factory=list, description="Steps blocked by this")
    
    # Execution
    status: str = Field(default="pending")
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    
    # Data
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Validation
    success_criteria: Dict[str, Any] = Field(default_factory=dict)
    rollback_plan: Optional[Dict[str, Any]] = Field(None)


class CollaborativeWorkflow(BaseModel):
    """A multi-agent workflow."""
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    plan_id: str = Field(..., description="Associated plan ID")
    
    # Definition
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    
    # Steps
    steps: Dict[str, WorkflowStep] = Field(default_factory=dict)
    execution_order: List[str] = Field(default_factory=list)
    
    # Participants
    participating_agents: Set[str] = Field(default_factory=set)
    agent_assignments: Dict[str, List[str]] = Field(default_factory=dict)
    
    # Status
    status: str = Field(default="created")
    current_step_id: Optional[str] = Field(None)
    
    # Results
    completed_steps: Set[str] = Field(default_factory=set)
    failed_steps: Set[str] = Field(default_factory=set)
    workflow_output: Dict[str, Any] = Field(default_factory=dict)
    
    # Timeline
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    
    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow."""
        self.steps[step.step_id] = step
        self.participating_agents.add(step.responsible_agent)
        
    def get_next_steps(self) -> List[WorkflowStep]:
        """Get steps that are ready to execute."""
        ready_steps = []
        for step in self.steps.values():
            if step.status == "pending":
                # Check if all dependencies are completed
                if all(dep_id in self.completed_steps for dep_id in step.depends_on):
                    ready_steps.append(step)
        return ready_steps


class PlanningContext(BaseModel):
    """Context shared during collaborative planning."""
    context_id: str = Field(default_factory=lambda: str(uuid4()))
    plan_id: str = Field(..., description="Associated plan")
    
    # Market Context
    market_conditions: Dict[str, Any] = Field(..., description="Current market state")
    recent_performance: Dict[str, Any] = Field(default_factory=dict)
    risk_metrics: Dict[str, Any] = Field(default_factory=dict)
    
    # Constraints
    risk_limits: Dict[str, float] = Field(default_factory=dict)
    position_limits: Dict[str, int] = Field(default_factory=dict)
    capital_available: float = Field(default=0.0)
    
    # Historical Context
    similar_situations: List[Dict[str, Any]] = Field(default_factory=list)
    past_successes: List[Dict[str, Any]] = Field(default_factory=list)
    past_failures: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Agent Insights
    agent_observations: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    agent_recommendations: Dict[str, List[str]] = Field(default_factory=dict)
    
    # External Factors
    news_events: List[Dict[str, Any]] = Field(default_factory=list)
    economic_indicators: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def add_agent_insight(self, agent_id: str, insight_type: str, 
                         insight_data: Dict[str, Any]) -> None:
        """Add an insight from an agent."""
        if agent_id not in self.agent_observations:
            self.agent_observations[agent_id] = {}
        self.agent_observations[agent_id][insight_type] = insight_data
        self.updated_at = datetime.utcnow()


class ConflictResolution(BaseModel):
    """Resolution for conflicts between agents."""
    resolution_id: str = Field(default_factory=lambda: str(uuid4()))
    plan_id: str = Field(..., description="Plan with conflict")
    
    # Conflict
    conflicting_agents: List[str] = Field(..., description="Agents in conflict")
    conflict_type: str = Field(..., description="Type of conflict")
    conflict_description: str = Field(..., description="Detailed description")
    
    # Proposals
    agent_positions: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    compromise_proposals: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Resolution
    resolution_method: str = Field(..., description="How conflict was resolved")
    final_decision: Dict[str, Any] = Field(..., description="Final resolution")
    decided_by: str = Field(..., description="Who made final decision")
    
    # Outcome
    all_agents_agreed: bool = Field(default=False)
    dissenting_agents: List[str] = Field(default_factory=list)
    
    # Timeline
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = Field(None)