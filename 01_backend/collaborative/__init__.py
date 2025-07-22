"""
Collaborative Planning Framework
Enables multi-agent coordination and decision making.
"""

from .schemas import (
    # Core schemas
    CollaborativePlan,
    PlanProposal,
    AgentVote,
    CollaborativeWorkflow,
    WorkflowStep,
    PlanningContext,
    ConflictResolution,
    
    # Enums
    PlanStatus,
    VoteType,
    PlanPriority,
    ConsensusType,
    AgentRole
)

from .planning_templates import PlanningTemplateLibrary
from .workflow_orchestrator import WorkflowOrchestrator
from .consensus_mechanisms import ConsensusEngine
from .planning_manager import CollaborativePlanningManager

__all__ = [
    # Schemas
    'CollaborativePlan',
    'PlanProposal',
    'AgentVote',
    'CollaborativeWorkflow',
    'WorkflowStep',
    'PlanningContext',
    'ConflictResolution',
    
    # Enums
    'PlanStatus',
    'VoteType',
    'PlanPriority',
    'ConsensusType',
    'AgentRole',
    
    # Core components
    'PlanningTemplateLibrary',
    'WorkflowOrchestrator',
    'ConsensusEngine',
    'CollaborativePlanningManager'
]