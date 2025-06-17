"""
Planning Templates for Common Trading Scenarios
Provides pre-defined templates for collaborative planning patterns.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from .schemas import (
    PlanTemplate, ConsensusType, PlanPriority, 
    CollaborativePlan, PlanProposal, WorkflowStep
)

logger = logging.getLogger(__name__)


class PlanningTemplateLibrary:
    """Library of pre-defined planning templates."""
    
    def __init__(self):
        self.templates: Dict[str, PlanTemplate] = {}
        self._initialize_default_templates()
        
    def _initialize_default_templates(self):
        """Initialize built-in planning templates."""
        
        # Daily Trading Strategy Template
        self.templates['daily_trading_strategy'] = PlanTemplate(
            name="Daily Trading Strategy",
            description="Plan daily SPY options trading strategy",
            required_sections=[
                "market_analysis",
                "strategy_selection",
                "risk_parameters",
                "execution_timing",
                "success_criteria"
            ],
            optional_sections=[
                "alternative_strategies",
                "hedging_plan",
                "news_considerations"
            ],
            required_agents=[
                "EnvironmentWatcherAgent",
                "StrategicPlannerAgent",
                "ExecutorAgent"
            ],
            optional_agents=[
                "RiskManagerAgent",
                "RewardModelAgent"
            ],
            consensus_type=ConsensusType.MAJORITY,
            max_duration_hours=1,
            validation_rules={
                "min_confidence": 0.7,
                "max_risk_per_trade": 0.02,
                "required_approvals": 2
            }
        )
        
        # Risk Mitigation Template
        self.templates['risk_mitigation'] = PlanTemplate(
            name="Risk Mitigation Plan",
            description="Emergency response to high-risk market conditions",
            required_sections=[
                "risk_assessment",
                "mitigation_actions",
                "position_adjustments",
                "monitoring_plan"
            ],
            required_agents=[
                "RiskManagerAgent",
                "ExecutorAgent",
                "EnvironmentWatcherAgent"
            ],
            consensus_type=ConsensusType.UNANIMOUS,
            max_duration_hours=0.5,  # 30 minutes
            requires_human_approval=True,
            validation_rules={
                "immediate_action": True,
                "max_loss_tolerance": 0.05
            }
        )
        
        # Position Exit Strategy Template
        self.templates['position_exit'] = PlanTemplate(
            name="Position Exit Strategy",
            description="Collaborative decision on when and how to exit positions",
            required_sections=[
                "current_position_analysis",
                "exit_criteria",
                "exit_timing",
                "execution_method"
            ],
            optional_sections=[
                "partial_exit_plan",
                "re-entry_conditions"
            ],
            required_agents=[
                "StrategicPlannerAgent",
                "ExecutorAgent",
                "EvaluatorAgent"
            ],
            consensus_type=ConsensusType.WEIGHTED,
            validation_rules={
                "min_profit_threshold": 0.5,  # 50% of max profit
                "max_loss_threshold": 3.0    # 3x premium
            }
        )
        
        # Market Regime Change Template
        self.templates['regime_change_response'] = PlanTemplate(
            name="Market Regime Change Response",
            description="Adapt strategy to significant market regime changes",
            required_sections=[
                "regime_analysis",
                "strategy_adjustments",
                "position_modifications",
                "new_risk_parameters"
            ],
            required_agents=[
                "EnvironmentWatcherAgent",
                "StrategicPlannerAgent",
                "RiskManagerAgent",
                "ExecutorAgent"
            ],
            consensus_type=ConsensusType.VETO_POWER,
            max_duration_hours=2,
            validation_rules={
                "regime_confidence": 0.8,
                "adjustment_magnitude": "significant"
            }
        )
        
        # Performance Review Template
        self.templates['performance_review'] = PlanTemplate(
            name="Trading Performance Review",
            description="Collaborative review of trading performance and improvements",
            required_sections=[
                "performance_metrics",
                "success_analysis",
                "failure_analysis",
                "improvement_recommendations",
                "implementation_plan"
            ],
            required_agents=[
                "EvaluatorAgent",
                "RewardModelAgent",
                "StrategicPlannerAgent"
            ],
            optional_agents=[
                "All"  # All agents can participate
            ],
            consensus_type=ConsensusType.MAJORITY,
            max_duration_hours=4,
            validation_rules={
                "min_trades_analyzed": 10,
                "time_period_days": 7
            }
        )
        
    def get_template(self, template_name: str) -> Optional[PlanTemplate]:
        """Get a planning template by name."""
        return self.templates.get(template_name)
        
    def create_plan_from_template(self, template_name: str, 
                                 initiator_agent: str,
                                 customizations: Dict = None) -> Optional[CollaborativePlan]:
        """Create a new plan from a template."""
        template = self.get_template(template_name)
        if not template:
            logger.error(f"Template {template_name} not found")
            return None
            
        # Create base plan
        plan = CollaborativePlan(
            title=f"{template.name} - {datetime.utcnow().strftime('%Y-%m-%d')}",
            description=template.description,
            initiator_agent=initiator_agent,
            consensus_type=template.consensus_type,
            required_approvals=set(template.required_agents)
        )
        
        # Set deadlines based on template
        if template.max_duration_hours:
            deadline = datetime.utcnow() + timedelta(hours=template.max_duration_hours)
            plan.proposal_deadline = deadline - timedelta(minutes=30)
            plan.voting_deadline = deadline - timedelta(minutes=15)
            plan.execution_deadline = deadline
            
        # Apply customizations
        if customizations:
            if 'priority' in customizations:
                plan.priority = customizations['priority']
            if 'additional_agents' in customizations:
                plan.participating_agents.update(customizations['additional_agents'])
                
        # Add template reference
        plan.tags.append(f"template:{template_name}")
        
        # Increment template usage
        template.usage_count += 1
        
        logger.info(f"Created plan from template {template_name}: {plan.plan_id}")
        
        return plan
        
    def get_workflow_for_template(self, template_name: str) -> List[WorkflowStep]:
        """Get suggested workflow steps for a template."""
        workflows = {
            'daily_trading_strategy': [
                WorkflowStep(
                    workflow_id="",  # Will be set when added to workflow
                    name="Market Analysis",
                    description="Analyze current market conditions",
                    responsible_agent="EnvironmentWatcherAgent",
                    depends_on=[],
                    success_criteria={"market_data_collected": True}
                ),
                WorkflowStep(
                    workflow_id="",
                    name="Strategy Selection",
                    description="Select optimal trading strategy",
                    responsible_agent="StrategicPlannerAgent",
                    depends_on=["Market Analysis"],
                    success_criteria={"strategy_confidence": 0.7}
                ),
                WorkflowStep(
                    workflow_id="",
                    name="Risk Validation",
                    description="Validate risk parameters",
                    responsible_agent="RiskManagerAgent",
                    depends_on=["Strategy Selection"],
                    success_criteria={"risk_approved": True}
                ),
                WorkflowStep(
                    workflow_id="",
                    name="Trade Execution",
                    description="Execute the selected trades",
                    responsible_agent="ExecutorAgent",
                    depends_on=["Risk Validation"],
                    success_criteria={"trades_executed": True}
                ),
                WorkflowStep(
                    workflow_id="",
                    name="Performance Monitoring",
                    description="Monitor trade performance",
                    responsible_agent="EvaluatorAgent",
                    depends_on=["Trade Execution"],
                    success_criteria={"monitoring_active": True}
                )
            ],
            
            'risk_mitigation': [
                WorkflowStep(
                    workflow_id="",
                    name="Risk Assessment",
                    description="Assess current risk exposure",
                    responsible_agent="RiskManagerAgent",
                    depends_on=[],
                    success_criteria={"risk_level_determined": True}
                ),
                WorkflowStep(
                    workflow_id="",
                    name="Position Analysis",
                    description="Analyze all open positions",
                    responsible_agent="ExecutorAgent",
                    depends_on=["Risk Assessment"],
                    success_criteria={"positions_analyzed": True}
                ),
                WorkflowStep(
                    workflow_id="",
                    name="Mitigation Execution",
                    description="Execute risk mitigation actions",
                    responsible_agent="ExecutorAgent",
                    depends_on=["Position Analysis"],
                    success_criteria={"risk_reduced": True}
                ),
                WorkflowStep(
                    workflow_id="",
                    name="Verify Mitigation",
                    description="Verify risk has been mitigated",
                    responsible_agent="RiskManagerAgent",
                    depends_on=["Mitigation Execution"],
                    success_criteria={"risk_acceptable": True}
                )
            ],
            
            'position_exit': [
                WorkflowStep(
                    workflow_id="",
                    name="Position Evaluation",
                    description="Evaluate current position P&L and market conditions",
                    responsible_agent="EvaluatorAgent",
                    depends_on=[],
                    success_criteria={"evaluation_complete": True}
                ),
                WorkflowStep(
                    workflow_id="",
                    name="Exit Strategy Planning",
                    description="Plan optimal exit strategy",
                    responsible_agent="StrategicPlannerAgent",
                    depends_on=["Position Evaluation"],
                    success_criteria={"exit_plan_defined": True}
                ),
                WorkflowStep(
                    workflow_id="",
                    name="Execute Exit",
                    description="Execute position exit",
                    responsible_agent="ExecutorAgent",
                    depends_on=["Exit Strategy Planning"],
                    success_criteria={"position_closed": True}
                ),
                WorkflowStep(
                    workflow_id="",
                    name="Exit Analysis",
                    description="Analyze exit performance",
                    responsible_agent="EvaluatorAgent",
                    depends_on=["Execute Exit"],
                    success_criteria={"analysis_complete": True}
                )
            ]
        }
        
        return workflows.get(template_name, [])
        
    def suggest_template(self, context: Dict[str, Any]) -> Optional[str]:
        """Suggest appropriate template based on context."""
        # Analyze context to suggest template
        if context.get('emergency', False) or context.get('high_risk', False):
            return 'risk_mitigation'
        elif context.get('regime_change', False):
            return 'regime_change_response'
        elif context.get('position_exit_needed', False):
            return 'position_exit'
        elif context.get('performance_review_due', False):
            return 'performance_review'
        else:
            # Default to daily strategy
            return 'daily_trading_strategy'
            
    def get_template_analytics(self) -> Dict[str, Dict[str, Any]]:
        """Get usage analytics for all templates."""
        analytics = {}
        
        for name, template in self.templates.items():
            analytics[name] = {
                'usage_count': template.usage_count,
                'success_rate': template.success_rate,
                'avg_duration': template.max_duration_hours,
                'required_agents': len(template.required_agents),
                'consensus_type': template.consensus_type.value
            }
            
        return analytics
        
    def update_template_success_rate(self, template_name: str, 
                                   success: bool) -> None:
        """Update success rate for a template based on plan outcome."""
        template = self.get_template(template_name)
        if template:
            # Simple moving average
            current_rate = template.success_rate
            usage_count = template.usage_count
            
            if usage_count > 0:
                new_rate = ((current_rate * (usage_count - 1)) + 
                           (1.0 if success else 0.0)) / usage_count
                template.success_rate = new_rate
                
    def export_template(self, template_name: str) -> Optional[Dict]:
        """Export template as dictionary for storage."""
        template = self.get_template(template_name)
        if template:
            return template.dict()
        return None
        
    def import_template(self, template_data: Dict) -> bool:
        """Import template from dictionary."""
        try:
            template = PlanTemplate(**template_data)
            self.templates[template.name] = template
            logger.info(f"Imported template: {template.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to import template: {e}")
            return False