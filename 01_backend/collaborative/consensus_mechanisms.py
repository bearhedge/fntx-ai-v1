"""
Consensus Mechanisms for Multi-Agent Decision Making
Implements various consensus algorithms for collaborative planning.
"""

import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime
from collections import defaultdict
import numpy as np

from .schemas import (
    AgentVote, VoteType, ConsensusType, CollaborativePlan,
    PlanProposal, AgentRole
)

logger = logging.getLogger(__name__)


class ConsensusEngine:
    """
    Engine for determining consensus among multiple agents.
    """
    
    def __init__(self):
        self.voting_history: Dict[str, List[AgentVote]] = defaultdict(list)
        self.agent_weights: Dict[str, float] = {}
        self.domain_expertise: Dict[str, Dict[str, float]] = defaultdict(dict)
        
    def calculate_consensus(self, plan: CollaborativePlan) -> Tuple[bool, Dict[str, Any]]:
        """
        Calculate if consensus has been reached for a plan.
        
        Args:
            plan: The collaborative plan
            
        Returns:
            Tuple of (consensus_reached, details)
        """
        if not plan.votes:
            return False, {"reason": "no_votes_cast"}
            
        consensus_type = plan.consensus_type
        
        if consensus_type == ConsensusType.UNANIMOUS:
            return self._unanimous_consensus(plan)
        elif consensus_type == ConsensusType.MAJORITY:
            return self._majority_consensus(plan)
        elif consensus_type == ConsensusType.WEIGHTED:
            return self._weighted_consensus(plan)
        elif consensus_type == ConsensusType.QUORUM:
            return self._quorum_consensus(plan)
        elif consensus_type == ConsensusType.VETO_POWER:
            return self._veto_consensus(plan)
        else:
            return False, {"reason": "unknown_consensus_type"}
            
    def _unanimous_consensus(self, plan: CollaborativePlan) -> Tuple[bool, Dict[str, Any]]:
        """Check for unanimous consensus."""
        all_approve = all(v.vote == VoteType.APPROVE for v in plan.votes.values())
        
        details = {
            "type": "unanimous",
            "total_votes": len(plan.votes),
            "approve_votes": sum(1 for v in plan.votes.values() if v.vote == VoteType.APPROVE),
            "consensus_reached": all_approve
        }
        
        return all_approve, details
        
    def _majority_consensus(self, plan: CollaborativePlan) -> Tuple[bool, Dict[str, Any]]:
        """Check for majority consensus."""
        total_votes = len(plan.votes)
        approve_votes = sum(1 for v in plan.votes.values() if v.vote == VoteType.APPROVE)
        
        approval_ratio = approve_votes / total_votes if total_votes > 0 else 0
        consensus_reached = approval_ratio >= plan.consensus_threshold
        
        details = {
            "type": "majority",
            "total_votes": total_votes,
            "approve_votes": approve_votes,
            "approval_ratio": approval_ratio,
            "required_threshold": plan.consensus_threshold,
            "consensus_reached": consensus_reached
        }
        
        return consensus_reached, details
        
    def _weighted_consensus(self, plan: CollaborativePlan) -> Tuple[bool, Dict[str, Any]]:
        """Check for weighted consensus based on agent expertise."""
        total_weight = sum(v.weight for v in plan.votes.values())
        approve_weight = sum(v.weight for v in plan.votes.values() 
                           if v.vote == VoteType.APPROVE)
        
        if total_weight == 0:
            return False, {"reason": "zero_total_weight"}
            
        approval_ratio = approve_weight / total_weight
        consensus_reached = approval_ratio >= plan.consensus_threshold
        
        # Calculate per-agent contributions
        agent_contributions = {
            v.agent_id: {
                "vote": v.vote.value,
                "weight": v.weight,
                "contribution": v.weight / total_weight
            }
            for v in plan.votes.values()
        }
        
        details = {
            "type": "weighted",
            "total_weight": total_weight,
            "approve_weight": approve_weight,
            "approval_ratio": approval_ratio,
            "required_threshold": plan.consensus_threshold,
            "consensus_reached": consensus_reached,
            "agent_contributions": agent_contributions
        }
        
        return consensus_reached, details
        
    def _quorum_consensus(self, plan: CollaborativePlan) -> Tuple[bool, Dict[str, Any]]:
        """Check for quorum-based consensus."""
        # Quorum requires minimum participation
        required_voters = len(plan.required_approvals)
        actual_voters = len(plan.votes)
        
        quorum_met = actual_voters >= required_voters * 0.8  # 80% participation
        
        if not quorum_met:
            return False, {
                "reason": "quorum_not_met",
                "required_voters": required_voters,
                "actual_voters": actual_voters
            }
            
        # If quorum met, check approval ratio
        approve_votes = sum(1 for v in plan.votes.values() if v.vote == VoteType.APPROVE)
        approval_ratio = approve_votes / actual_voters
        consensus_reached = approval_ratio >= plan.consensus_threshold
        
        details = {
            "type": "quorum",
            "quorum_met": quorum_met,
            "required_voters": required_voters,
            "actual_voters": actual_voters,
            "approve_votes": approve_votes,
            "approval_ratio": approval_ratio,
            "consensus_reached": consensus_reached
        }
        
        return consensus_reached, details
        
    def _veto_consensus(self, plan: CollaborativePlan) -> Tuple[bool, Dict[str, Any]]:
        """Check for veto-based consensus."""
        # Any rejection is a veto
        vetoes = [v for v in plan.votes.values() if v.vote == VoteType.REJECT]
        
        if vetoes:
            return False, {
                "type": "veto",
                "vetoed": True,
                "veto_agents": [v.agent_id for v in vetoes],
                "veto_reasons": [v.reasoning for v in vetoes]
            }
            
        # No vetoes, check if enough approvals
        approve_votes = sum(1 for v in plan.votes.values() if v.vote == VoteType.APPROVE)
        total_votes = len(plan.votes)
        
        if total_votes == 0:
            return False, {"reason": "no_votes"}
            
        approval_ratio = approve_votes / total_votes
        consensus_reached = approval_ratio >= plan.consensus_threshold
        
        details = {
            "type": "veto",
            "vetoed": False,
            "approve_votes": approve_votes,
            "total_votes": total_votes,
            "approval_ratio": approval_ratio,
            "consensus_reached": consensus_reached
        }
        
        return consensus_reached, details
        
    def calculate_agent_weights(self, agent_id: str, domain: str) -> float:
        """
        Calculate voting weight for an agent in a specific domain.
        
        Args:
            agent_id: Agent identifier
            domain: Domain of expertise (e.g., "risk_management", "strategy_selection")
            
        Returns:
            Voting weight
        """
        # Base weight
        base_weight = 1.0
        
        # Expertise modifier
        expertise = self.domain_expertise.get(agent_id, {}).get(domain, 0.5)
        
        # Historical performance modifier
        history_weight = self._calculate_historical_weight(agent_id)
        
        # Combine weights
        total_weight = base_weight * (0.5 + expertise) * (0.5 + history_weight)
        
        return min(max(total_weight, 0.1), 3.0)  # Clamp between 0.1 and 3.0
        
    def _calculate_historical_weight(self, agent_id: str) -> float:
        """Calculate weight based on voting history."""
        agent_votes = self.voting_history.get(agent_id, [])
        
        if not agent_votes:
            return 0.5  # Neutral weight for new agents
            
        # Calculate success rate based on past votes
        successful_votes = 0
        for vote in agent_votes[-20:]:  # Last 20 votes
            # A vote is successful if it aligned with final consensus
            # This is simplified - in practice would check actual outcomes
            if vote.vote == VoteType.APPROVE:
                successful_votes += 1
                
        success_rate = successful_votes / min(len(agent_votes), 20)
        
        return success_rate
        
    def update_agent_expertise(self, agent_id: str, domain: str, 
                             performance_score: float) -> None:
        """
        Update agent's domain expertise based on performance.
        
        Args:
            agent_id: Agent identifier
            domain: Domain of expertise
            performance_score: Score between 0 and 1
        """
        current_expertise = self.domain_expertise[agent_id].get(domain, 0.5)
        
        # Exponential moving average update
        alpha = 0.1  # Learning rate
        new_expertise = (1 - alpha) * current_expertise + alpha * performance_score
        
        self.domain_expertise[agent_id][domain] = new_expertise
        
        logger.info(f"Updated {agent_id} expertise in {domain}: {new_expertise:.3f}")
        
    def find_compromise(self, proposals: List[PlanProposal], 
                       votes: Dict[str, AgentVote]) -> Optional[Dict[str, Any]]:
        """
        Find compromise between different proposals.
        
        Args:
            proposals: List of proposals
            votes: Agent votes with concerns/suggestions
            
        Returns:
            Compromise proposal if found
        """
        if not proposals:
            return None
            
        # Collect all suggestions from votes
        all_suggestions = []
        for vote in votes.values():
            all_suggestions.extend(vote.suggestions)
            
        # Find common elements across proposals
        common_elements = self._find_common_elements(proposals)
        
        # Address main concerns
        addressed_concerns = self._address_concerns(proposals, votes)
        
        # Create compromise
        compromise = {
            "base_elements": common_elements,
            "modifications": addressed_concerns,
            "incorporated_suggestions": all_suggestions[:5],  # Top 5 suggestions
            "compromise_type": "automated_synthesis"
        }
        
        return compromise
        
    def _find_common_elements(self, proposals: List[PlanProposal]) -> Dict[str, Any]:
        """Find elements common to all proposals."""
        if not proposals:
            return {}
            
        common = {
            "objectives": [],
            "strategies": [],
            "risk_levels": []
        }
        
        # Find common objectives
        all_objectives = [set(p.objectives) for p in proposals]
        if all_objectives:
            common_objectives = set.intersection(*all_objectives)
            common["objectives"] = list(common_objectives)
            
        # Find similar strategies
        strategies = [p.strategy_details for p in proposals]
        common["strategies"] = self._find_similar_strategies(strategies)
        
        return common
        
    def _find_similar_strategies(self, strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find strategies that are similar across proposals."""
        # Simplified - in practice would use more sophisticated comparison
        similar = []
        
        for i, strategy1 in enumerate(strategies):
            similarity_count = 0
            for j, strategy2 in enumerate(strategies):
                if i != j and self._strategies_similar(strategy1, strategy2):
                    similarity_count += 1
                    
            if similarity_count >= len(strategies) / 2:
                similar.append(strategy1)
                
        return similar[:3]  # Return top 3 similar strategies
        
    def _strategies_similar(self, s1: Dict, s2: Dict) -> bool:
        """Check if two strategies are similar."""
        # Compare key fields
        key_fields = ["instrument", "direction", "strategy_type"]
        
        matches = 0
        for field in key_fields:
            if s1.get(field) == s2.get(field):
                matches += 1
                
        return matches >= 2  # At least 2 fields match
        
    def _address_concerns(self, proposals: List[PlanProposal], 
                         votes: Dict[str, AgentVote]) -> List[Dict[str, Any]]:
        """Address concerns raised in votes."""
        modifications = []
        
        # Collect all concerns
        all_concerns = []
        for vote in votes.values():
            all_concerns.extend(vote.concerns)
            
        # Group similar concerns
        concern_groups = self._group_similar_concerns(all_concerns)
        
        # Address top concern groups
        for concern_group in concern_groups[:3]:  # Top 3 concern groups
            modification = {
                "concern": concern_group["representative"],
                "frequency": concern_group["count"],
                "proposed_solution": self._propose_solution(concern_group["representative"])
            }
            modifications.append(modification)
            
        return modifications
        
    def _group_similar_concerns(self, concerns: List[str]) -> List[Dict[str, Any]]:
        """Group similar concerns together."""
        # Simplified grouping - in practice would use NLP
        groups = defaultdict(int)
        
        for concern in concerns:
            # Simple keyword-based grouping
            if "risk" in concern.lower():
                groups["risk_concerns"] += 1
            elif "timing" in concern.lower():
                groups["timing_concerns"] += 1
            elif "capital" in concern.lower() or "size" in concern.lower():
                groups["sizing_concerns"] += 1
            else:
                groups["other_concerns"] += 1
                
        return [
            {"representative": key, "count": count}
            for key, count in sorted(groups.items(), key=lambda x: x[1], reverse=True)
        ]
        
    def _propose_solution(self, concern_type: str) -> str:
        """Propose solution for a concern type."""
        solutions = {
            "risk_concerns": "Implement stricter risk limits and add hedging",
            "timing_concerns": "Add flexible timing windows with market condition triggers",
            "sizing_concerns": "Use dynamic position sizing based on volatility",
            "other_concerns": "Review and address on case-by-case basis"
        }
        
        return solutions.get(concern_type, "Requires further analysis")
        
    def rank_proposals(self, proposals: List[PlanProposal], 
                      context: Dict[str, Any]) -> List[Tuple[PlanProposal, float]]:
        """
        Rank proposals based on various criteria.
        
        Args:
            proposals: List of proposals to rank
            context: Current market/trading context
            
        Returns:
            List of (proposal, score) tuples sorted by score
        """
        scored_proposals = []
        
        for proposal in proposals:
            score = self._score_proposal(proposal, context)
            scored_proposals.append((proposal, score))
            
        # Sort by score descending
        scored_proposals.sort(key=lambda x: x[1], reverse=True)
        
        return scored_proposals
        
    def _score_proposal(self, proposal: PlanProposal, context: Dict[str, Any]) -> float:
        """Score a single proposal."""
        score = 0.0
        
        # Priority score (0.2 weight)
        priority_scores = {
            1: 1.0,  # CRITICAL
            2: 0.75,  # HIGH
            3: 0.5,   # MEDIUM
            4: 0.25   # LOW
        }
        score += 0.2 * priority_scores.get(proposal.priority.value, 0.5)
        
        # Objective alignment (0.3 weight)
        objective_score = len(proposal.objectives) / 10.0  # Normalize to 0-1
        score += 0.3 * min(objective_score, 1.0)
        
        # Risk assessment (0.2 weight)
        risk_level = proposal.risk_assessment.get("overall_risk", 0.5)
        risk_score = 1.0 - risk_level  # Lower risk = higher score
        score += 0.2 * risk_score
        
        # Expected outcome (0.2 weight)
        expected_return = proposal.expected_outcomes.get("expected_return", 0.0)
        return_score = min(expected_return / 0.1, 1.0)  # Normalize to 0-1 (10% = 1.0)
        score += 0.2 * return_score
        
        # Timing feasibility (0.1 weight)
        if proposal.proposed_start <= datetime.utcnow() + timedelta(hours=1):
            score += 0.1  # Executable soon
            
        return score
        
    def detect_voting_patterns(self, agent_id: str) -> Dict[str, Any]:
        """
        Detect patterns in an agent's voting behavior.
        
        Args:
            agent_id: Agent to analyze
            
        Returns:
            Dictionary of detected patterns
        """
        agent_votes = self.voting_history.get(agent_id, [])
        
        if not agent_votes:
            return {"pattern": "no_history"}
            
        patterns = {
            "total_votes": len(agent_votes),
            "approval_rate": sum(1 for v in agent_votes if v.vote == VoteType.APPROVE) / len(agent_votes),
            "rejection_rate": sum(1 for v in agent_votes if v.vote == VoteType.REJECT) / len(agent_votes),
            "abstention_rate": sum(1 for v in agent_votes if v.vote == VoteType.ABSTAIN) / len(agent_votes),
            "conditional_approval_rate": sum(1 for v in agent_votes if v.conditional_approval) / len(agent_votes)
        }
        
        # Detect behavioral patterns
        if patterns["approval_rate"] > 0.8:
            patterns["behavior"] = "generally_supportive"
        elif patterns["rejection_rate"] > 0.5:
            patterns["behavior"] = "generally_critical"
        elif patterns["conditional_approval_rate"] > 0.3:
            patterns["behavior"] = "detail_oriented"
        else:
            patterns["behavior"] = "balanced"
            
        return patterns
        
    def simulate_consensus(self, plan: CollaborativePlan, 
                          potential_votes: Dict[str, VoteType]) -> Tuple[bool, Dict[str, Any]]:
        """
        Simulate consensus outcome with potential votes.
        
        Args:
            plan: The plan
            potential_votes: Dict of agent_id -> vote_type
            
        Returns:
            Tuple of (would_reach_consensus, details)
        """
        # Create temporary plan copy
        temp_plan = CollaborativePlan(**plan.dict())
        
        # Add simulated votes
        for agent_id, vote_type in potential_votes.items():
            simulated_vote = AgentVote(
                plan_id=plan.plan_id,
                agent_id=agent_id,
                vote=vote_type,
                reasoning="Simulated vote",
                weight=self.calculate_agent_weights(agent_id, "general")
            )
            temp_plan.cast_vote(simulated_vote)
            
        # Calculate consensus
        return self.calculate_consensus(temp_plan)