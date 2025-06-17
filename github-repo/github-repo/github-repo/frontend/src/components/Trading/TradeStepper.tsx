import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { 
  CheckCircle, 
  Clock, 
  AlertTriangle, 
  XCircle, 
  Play,
  TrendingUp,
  Brain,
  Target,
  Zap,
  BarChart3,
  RefreshCw
} from 'lucide-react';

interface TradeStep {
  timestamp: string;
  agent: string;
  action: string;
  rationale: string;
  status: 'pending' | 'running' | 'completed' | 'error' | 'skipped';
  confidence_level: number;
  risk_assessment: Record<string, any>;
  execution_time: number;
  error_message?: string;
}

interface TradeJourney {
  trade_id: string;
  user_request: string;
  initiated_at: string;
  current_phase: string;
  steps: TradeStep[];
  risk_assessment: {
    overall_risk: string;
    confidence_level: number;
    max_exposure: number;
    stop_loss_level: number;
  };
  final_outcome?: {
    success: boolean;
    message: string;
    completed_at: string;
    total_steps: number;
    agent_statuses: Record<string, string>;
  };
  execution_time: number;
  errors: string[];
}

interface TradeStepperProps {
  journeyData?: TradeJourney;
  onRefresh?: () => void;
  className?: string;
}

const AGENT_ICONS = {
  'EnvironmentWatcherAgent': TrendingUp,
  'StrategicPlannerAgent': Brain,
  'RewardModelAgent': Target,
  'ExecutorAgent': Zap,
  'EvaluatorAgent': BarChart3
};

const AGENT_COLORS = {
  'EnvironmentWatcherAgent': 'bg-blue-500',
  'StrategicPlannerAgent': 'bg-purple-500',
  'RewardModelAgent': 'bg-green-500',
  'ExecutorAgent': 'bg-orange-500',
  'EvaluatorAgent': 'bg-indigo-500'
};

const STATUS_VARIANTS = {
  pending: 'outline',
  running: 'default',
  completed: 'success',
  error: 'destructive',
  skipped: 'secondary'
} as const;

const STATUS_ICONS = {
  pending: Clock,
  running: RefreshCw,
  completed: CheckCircle,
  error: XCircle,
  skipped: AlertTriangle
};

export const TradeStepper: React.FC<TradeStepperProps> = ({ 
  journeyData, 
  onRefresh,
  className = ""
}) => {
  const [isPolling, setIsPolling] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Auto-refresh when trade is in progress
  useEffect(() => {
    if (!journeyData?.final_outcome && journeyData?.current_phase !== 'completed') {
      const interval = setInterval(() => {
        onRefresh?.();
        setLastUpdate(new Date());
      }, 2000); // Poll every 2 seconds

      setIsPolling(true);
      return () => {
        clearInterval(interval);
        setIsPolling(false);
      };
    } else {
      setIsPolling(false);
    }
  }, [journeyData?.final_outcome, journeyData?.current_phase, onRefresh]);

  const getProgressPercentage = () => {
    if (!journeyData) return 0;
    
    const totalAgents = 5;
    const completedSteps = journeyData.steps.filter(step => step.status === 'completed').length;
    
    if (journeyData.final_outcome?.success) return 100;
    if (journeyData.final_outcome?.success === false) return Math.max(20, (completedSteps / totalAgents) * 100);
    
    return (completedSteps / totalAgents) * 100;
  };

  const getCurrentPhaseDescription = () => {
    const phase = journeyData?.current_phase;
    const phaseDescriptions = {
      'initiated': 'Trade request received and processing initiated',
      'environment_analysis': 'Analyzing market conditions and volatility',
      'strategic_planning': 'Formulating optimal trading strategy',
      'reward_optimization': 'Optimizing for user preferences and risk tolerance',
      'tactical_execution': 'Executing trade with risk management controls',
      'evaluation': 'Evaluating trade outcome and performance',
      'completed': 'Trade lifecycle completed successfully',
      'failed': 'Trade execution encountered errors'
    };
    
    return phaseDescriptions[phase as keyof typeof phaseDescriptions] || 'Processing...';
  };

  const formatRiskLevel = (risk: string) => {
    const riskColors = {
      'low': 'text-green-600 bg-green-50',
      'medium': 'text-yellow-600 bg-yellow-50', 
      'high': 'text-red-600 bg-red-50',
      'unknown': 'text-gray-600 bg-gray-50'
    };
    
    return riskColors[risk as keyof typeof riskColors] || riskColors.unknown;
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const formatExecutionTime = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`;
  };

  if (!journeyData) {
    return (
      <Card className={`w-full ${className}`}>
        <CardContent className="flex items-center justify-center h-64">
          <div className="text-center">
            <Brain className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">No active trade journey</p>
            <p className="text-sm text-muted-foreground mt-2">
              Start a new trade to see the step-by-step process
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={`w-full ${className}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Play className="w-5 h-5" />
              Trade Journey: {journeyData.trade_id}
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {journeyData.user_request}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {isPolling && (
              <RefreshCw className="w-4 h-4 animate-spin text-blue-500" />
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={isPolling}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              {getCurrentPhaseDescription()}
            </span>
            <span className="font-medium">
              {getProgressPercentage().toFixed(0)}%
            </span>
          </div>
          <Progress value={getProgressPercentage()} className="h-2" />
        </div>

        {/* Risk Assessment Summary */}
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Risk Level:</span>
            <Badge 
              variant="outline" 
              className={formatRiskLevel(journeyData.risk_assessment.overall_risk)}
            >
              {journeyData.risk_assessment.overall_risk.toUpperCase()}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Confidence:</span>
            <span className="font-medium">
              {(journeyData.risk_assessment.confidence_level * 100).toFixed(0)}%
            </span>
          </div>
          {journeyData.execution_time > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Duration:</span>
              <span className="font-medium">
                {formatExecutionTime(journeyData.execution_time)}
              </span>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-6">
          {/* Agent Steps */}
          {journeyData.steps.map((step, index) => {
            const AgentIcon = AGENT_ICONS[step.agent as keyof typeof AGENT_ICONS] || Brain;
            const StatusIcon = STATUS_ICONS[step.status];
            const agentColor = AGENT_COLORS[step.agent as keyof typeof AGENT_COLORS] || 'bg-gray-500';

            return (
              <div key={index} className="relative">
                {/* Timeline line */}
                {index < journeyData.steps.length - 1 && (
                  <div className="absolute left-6 top-12 w-px h-8 bg-border" />
                )}
                
                <div className="flex gap-4">
                  {/* Agent Icon */}
                  <div className={`flex-shrink-0 w-12 h-12 rounded-full ${agentColor} flex items-center justify-center`}>
                    <AgentIcon className="w-6 h-6 text-white" />
                  </div>
                  
                  {/* Step Content */}
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium">{step.agent.replace('Agent', '')}</h4>
                        <Badge variant={STATUS_VARIANTS[step.status]}>
                          <StatusIcon className="w-3 h-3 mr-1" />
                          {step.status.charAt(0).toUpperCase() + step.status.slice(1)}
                        </Badge>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {formatTimestamp(step.timestamp)}
                      </span>
                    </div>
                    
                    <div className="space-y-2">
                      <p className="font-medium text-sm">{step.action}</p>
                      <p className="text-sm text-muted-foreground">{step.rationale}</p>
                      
                      {/* Step Details */}
                      <div className="flex flex-wrap gap-3 text-xs">
                        {step.confidence_level > 0 && (
                          <div className="flex items-center gap-1">
                            <Target className="w-3 h-3" />
                            <span>Confidence: {(step.confidence_level * 100).toFixed(0)}%</span>
                          </div>
                        )}
                        
                        {step.execution_time > 0 && (
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            <span>Duration: {formatExecutionTime(step.execution_time)}</span>
                          </div>
                        )}
                        
                        {/* Risk Info */}
                        {Object.keys(step.risk_assessment).length > 0 && (
                          <div className="flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" />
                            <span>
                              {Object.entries(step.risk_assessment).slice(0, 2).map(([key, value]) => 
                                `${key}: ${value}`
                              ).join(', ')}
                            </span>
                          </div>
                        )}
                      </div>
                      
                      {/* Error Message */}
                      {step.error_message && (
                        <div className="bg-red-50 border border-red-200 rounded-md p-2">
                          <p className="text-sm text-red-700">{step.error_message}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}

          {/* Final Outcome */}
          {journeyData.final_outcome && (
            <>
              <Separator />
              <div className={`p-4 rounded-lg border ${
                journeyData.final_outcome.success 
                  ? 'bg-green-50 border-green-200' 
                  : 'bg-red-50 border-red-200'
              }`}>
                <div className="flex items-center gap-2 mb-2">
                  {journeyData.final_outcome.success ? (
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-600" />
                  )}
                  <h4 className={`font-medium ${
                    journeyData.final_outcome.success ? 'text-green-800' : 'text-red-800'
                  }`}>
                    {journeyData.final_outcome.success ? 'Trade Completed Successfully' : 'Trade Failed'}
                  </h4>
                </div>
                <p className={`text-sm ${
                  journeyData.final_outcome.success ? 'text-green-700' : 'text-red-700'
                }`}>
                  {journeyData.final_outcome.message}
                </p>
                <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                  <span>Completed: {formatTimestamp(journeyData.final_outcome.completed_at)}</span>
                  <span>Total Steps: {journeyData.final_outcome.total_steps}</span>
                  <span>Duration: {formatExecutionTime(journeyData.execution_time)}</span>
                </div>
              </div>
            </>
          )}

          {/* Real-time Status for Active Trades */}
          {!journeyData.final_outcome && journeyData.current_phase !== 'completed' && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center gap-2">
                <RefreshCw className="w-5 h-5 text-blue-600 animate-spin" />
                <span className="font-medium text-blue-800">Trade in Progress</span>
              </div>
              <p className="text-sm text-blue-700 mt-1">
                {getCurrentPhaseDescription()}
              </p>
              <div className="text-xs text-blue-600 mt-2">
                Last updated: {lastUpdate.toLocaleTimeString()}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};