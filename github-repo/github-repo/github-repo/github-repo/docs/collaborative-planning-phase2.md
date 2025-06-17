# Collaborative Planning Framework - Phase 2 Implementation

## Overview

Phase 2 implements a comprehensive collaborative planning framework that enables multiple trading agents to coordinate, propose strategies, vote on decisions, and execute complex workflows together. This framework transforms independent agents into a cohesive team capable of sophisticated multi-agent decision making.

## Architecture

### Core Components

1. **Planning Manager** (`planning_manager.py`)
   - High-level interface for collaborative planning
   - Manages plan lifecycle from creation to completion
   - Integrates templates, orchestration, and consensus

2. **Workflow Orchestrator** (`workflow_orchestrator.py`)
   - Executes multi-step workflows across agents
   - Manages dependencies and parallel execution
   - Handles failures and conflict resolution

3. **Consensus Engine** (`consensus_mechanisms.py`)
   - Implements various consensus algorithms
   - Weighted voting based on expertise
   - Compromise finding and conflict resolution

4. **Planning Templates** (`planning_templates.py`)
   - Pre-defined templates for common scenarios
   - Reduces planning overhead
   - Ensures consistency

5. **Schemas** (`schemas.py`)
   - Comprehensive data models
   - Type-safe planning structures
   - Clear contracts between components

## Key Features

### 1. Multi-Agent Coordination

Agents can now work together on complex decisions:

```python
# Create a collaborative plan
plan_id = await planning_manager.create_plan_from_template(
    template_name="daily_trading_strategy",
    initiator_agent="StrategicPlannerAgent",
    session_id=session.session_id
)

# Each agent submits proposals
await planning_manager.submit_proposal(
    agent_id="StrategicPlannerAgent",
    plan_id=plan_id,
    proposal_data={
        "title": "Conservative SPY Put Selling",
        "objectives": ["Generate 2% daily return", "Minimize risk"],
        "strategy_details": {"instrument": "SPY", "strategy": "put_selling"}
    }
)

# Agents vote on proposals
await planning_manager.cast_vote(
    agent_id="RiskManagerAgent",
    plan_id=plan_id,
    vote=VoteType.APPROVE,
    reasoning="Risk parameters are within acceptable limits"
)
```

### 2. Flexible Consensus Mechanisms

Different types of consensus for different situations:

- **Unanimous**: All agents must agree (critical decisions)
- **Majority**: Simple or super-majority voting
- **Weighted**: Expertise-based voting weights
- **Quorum**: Minimum participation required
- **Veto Power**: Any agent can block (safety-critical)

### 3. Workflow Orchestration

Complex multi-step workflows with dependencies:

```python
workflow = CollaborativeWorkflow(
    plan_id=plan_id,
    name="Daily Trading Workflow"
)

# Add interconnected steps
workflow.add_step(WorkflowStep(
    name="Market Analysis",
    responsible_agent="EnvironmentWatcherAgent"
))

workflow.add_step(WorkflowStep(
    name="Strategy Selection",
    responsible_agent="StrategicPlannerAgent",
    depends_on=["Market Analysis"]
))

workflow.add_step(WorkflowStep(
    name="Risk Validation",
    responsible_agent="RiskManagerAgent",
    depends_on=["Strategy Selection"]
))
```

### 4. Conflict Resolution

Automated mechanisms for resolving disagreements:

```python
resolution = await orchestrator.resolve_conflict(
    plan_id=plan_id,
    conflicting_agents=["StrategicPlannerAgent", "RiskManagerAgent"],
    conflict_type="risk_assessment",
    conflict_description="Disagreement on position sizing"
)
```

### 5. Planning Templates

Pre-built templates for common scenarios:

- **Daily Trading Strategy**: Regular strategy planning
- **Risk Mitigation**: Emergency risk response
- **Position Exit**: Collaborative exit decisions
- **Regime Change Response**: Market adaptation
- **Performance Review**: Learning and improvement

## Integration with MCP

The collaborative framework deeply integrates with the MCP memory system:

### Memory Persistence
- All plans, proposals, and votes stored in MCP
- Searchable planning history
- Learning from past decisions

### Context Sharing
- Real-time context updates between agents
- Shared planning context with market data
- Cross-agent insights

### Learning Integration
- Success/failure patterns analyzed
- Agent expertise updated based on outcomes
- Continuous improvement

## Usage Examples

### Example 1: Daily Strategy Planning

```python
# Morning strategy planning
async def plan_daily_strategy(session_id: str):
    # Create plan from template
    plan_id = await planning_manager.create_plan_from_template(
        "daily_trading_strategy",
        "StrategicPlannerAgent",
        session_id=session_id,
        customizations={"priority": PlanPriority.HIGH}
    )
    
    # Wait for proposals and votes
    await asyncio.sleep(30)
    
    # Check status
    status = await planning_manager.get_plan_status(plan_id)
    
    if status['consensus_reached']:
        # Plan will execute automatically
        print(f"Daily strategy approved and executing")
    else:
        print(f"No consensus reached: {status['consensus_details']}")
```

### Example 2: Emergency Risk Response

```python
# Triggered by high-risk detection
async def handle_risk_emergency(risk_level: float):
    if risk_level > 0.08:  # 8% portfolio risk
        plan_id = await planning_manager.create_plan_from_template(
            "risk_mitigation",
            "RiskManagerAgent",
            customizations={
                "priority": PlanPriority.CRITICAL,
                "additional_agents": ["ExecutorAgent", "EvaluatorAgent"]
            }
        )
        
        # Fast-track voting with shorter deadlines
        # Unanimous consent required for risk actions
```

### Example 3: Collaborative Position Exit

```python
# When considering position exit
async def plan_position_exit(position_id: str):
    plan_id = await planning_manager.create_custom_plan(
        title=f"Exit Strategy for {position_id}",
        description="Collaborative decision on position exit",
        initiator_agent="EvaluatorAgent",
        participating_agents=[
            "StrategicPlannerAgent",
            "ExecutorAgent",
            "RiskManagerAgent"
        ],
        consensus_type=ConsensusType.WEIGHTED
    )
    
    # Agents analyze position and market
    # Submit exit proposals with timing
    # Weighted voting based on expertise
```

## Workflow Patterns

### Sequential Workflow
Steps execute in order with dependencies:
```
Market Analysis → Strategy Selection → Risk Check → Execution
```

### Parallel Workflow
Independent steps run simultaneously:
```
┌─ Position Analysis ─┐
├─ Market Analysis   ─┼→ Strategy Decision → Execution
└─ Risk Assessment  ─┘
```

### Conditional Workflow
Branches based on outcomes:
```
Analysis → Decision → [If Approved] → Execute
                   └→ [If Rejected] → Revise → Re-vote
```

## Agent Integration Guide

### Making an Agent Collaborative

1. **Inherit from base class**:
```python
class CollaborativeAgent(MCPEnabledAgent):
    def __init__(self, agent_id: str, mcp: MCPContextManager,
                 planning_manager: CollaborativePlanningManager):
        super().__init__(agent_id, mcp)
        self.planning = planning_manager
```

2. **Implement proposal generation**:
```python
async def generate_proposal(self, plan_id: str) -> Dict[str, Any]:
    # Analyze planning context
    context = await self.get_planning_context(plan_id)
    
    # Generate proposal based on expertise
    proposal = {
        "title": "My Strategy Proposal",
        "objectives": ["objective1", "objective2"],
        "strategy_details": {...}
    }
    
    return proposal
```

3. **Implement voting logic**:
```python
async def evaluate_proposals(self, plan_id: str, proposals: List[PlanProposal]):
    for proposal in proposals:
        # Evaluate based on agent's criteria
        vote = VoteType.APPROVE if self.meets_criteria(proposal) else VoteType.REJECT
        
        await self.planning.cast_vote(
            self.agent_id,
            plan_id,
            vote,
            reasoning="My evaluation reasoning"
        )
```

4. **Implement workflow steps**:
```python
async def execute_workflow_step(self, step: WorkflowStep) -> Dict[str, Any]:
    # Perform assigned work
    result = await self.do_work(step.input_data)
    
    # Return results
    return {
        "status": "completed",
        "output": result
    }
```

## Performance Considerations

### Scalability
- Plans and workflows stored efficiently in MCP tiers
- Parallel execution of independent steps
- Async operations throughout

### Reliability
- Automatic timeout handling
- Failure recovery mechanisms
- Persistent state across restarts

### Monitoring
- Real-time plan status tracking
- Workflow execution monitoring
- Performance metrics collection

## Configuration

### Consensus Thresholds
```python
# Adjust consensus requirements
plan.consensus_threshold = 0.75  # 75% approval needed
plan.consensus_type = ConsensusType.WEIGHTED
```

### Timing Configuration
```python
# Set custom deadlines
plan.proposal_deadline = datetime.utcnow() + timedelta(minutes=15)
plan.voting_deadline = datetime.utcnow() + timedelta(minutes=25)
plan.execution_deadline = datetime.utcnow() + timedelta(minutes=30)
```

### Agent Weights
```python
# Configure expertise weights
consensus_engine.update_agent_expertise(
    "RiskManagerAgent",
    domain="risk_assessment",
    performance_score=0.95
)
```

## Best Practices

1. **Use Templates**: Leverage pre-built templates for common scenarios
2. **Set Appropriate Consensus**: Match consensus type to decision criticality
3. **Include Context**: Provide rich context in proposals
4. **Handle Timeouts**: Plan for agents that don't respond
5. **Learn from History**: Use past planning outcomes to improve

## Troubleshooting

### No Consensus Reached
- Check if all required agents voted
- Review vote reasoning for concerns
- Consider compromise mechanisms

### Workflow Stalled
- Check step dependencies
- Verify responsible agents are active
- Review timeout settings

### Conflicting Proposals
- Use conflict resolution mechanisms
- Consider weighted voting
- Escalate to human if needed

## Future Enhancements

1. **Visual Planning Tools**: UI for plan visualization
2. **ML-Based Consensus**: Learn optimal consensus strategies
3. **Advanced Workflows**: More complex workflow patterns
4. **Cross-Session Planning**: Plans spanning multiple sessions
5. **Hierarchical Planning**: Nested plans and sub-plans

## Conclusion

Phase 2 successfully implements a sophisticated collaborative planning framework that enables:

- **Team Decision Making**: Agents work together effectively
- **Flexible Consensus**: Various methods for different scenarios  
- **Complex Workflows**: Multi-step coordinated execution
- **Conflict Resolution**: Automated disagreement handling
- **Continuous Learning**: Improvement through experience

This framework transforms individual agents into a cohesive team capable of making complex trading decisions collaboratively, with built-in safety mechanisms and continuous improvement capabilities.