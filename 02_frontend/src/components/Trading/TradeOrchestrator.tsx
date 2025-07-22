import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { TradeStepper } from './TradeStepper';
import { 
  Send, 
  Bot, 
  TrendingUp, 
  DollarSign,
  AlertTriangle,
  CheckCircle,
  Clock,
  Activity
} from 'lucide-react';

interface TradeJourney {
  trade_id: string;
  user_request: string;
  initiated_at: string;
  current_phase: string;
  steps: Array<{
    timestamp: string;
    agent: string;
    action: string;
    rationale: string;
    status: string;
    confidence_level: number;
    risk_assessment: Record<string, any>;
    execution_time: number;
    error_message?: string;
  }>;
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

interface OrchestratorStats {
  total_orchestrations: number;
  successful_trades: number;
  failed_trades: number;
  avg_execution_time: number;
  success_rate: number;
}

export const TradeOrchestrator: React.FC = () => {
  const [userRequest, setUserRequest] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentJourney, setCurrentJourney] = useState<TradeJourney | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<OrchestratorStats | null>(null);
  const [recentTrades, setRecentTrades] = useState<TradeJourney[]>([]);

  // Load initial data
  useEffect(() => {
    loadOrchestratorStats();
    loadRecentTrades();
  }, []);

  const loadOrchestratorStats = useCallback(async () => {
    try {
      // In a real implementation, this would call the backend API
      // For now, we'll simulate loading stats from the orchestrator memory
      const response = await fetch('/api/orchestrator/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Failed to load orchestrator stats:', err);
    }
  }, []);

  const loadRecentTrades = useCallback(async () => {
    try {
      const response = await fetch('/api/orchestrator/recent-trades');
      if (response.ok) {
        const data = await response.json();
        setRecentTrades(data);
      }
    } catch (err) {
      console.error('Failed to load recent trades:', err);
    }
  }, []);

  const loadTradeJourney = useCallback(async (tradeId?: string) => {
    try {
      const url = tradeId ? `/api/orchestrator/journey/${tradeId}` : '/api/orchestrator/current-journey';
      const response = await fetch(url);
      
      if (response.ok) {
        const journey = await response.json();
        setCurrentJourney(journey);
        return journey;
      }
    } catch (err) {
      console.error('Failed to load trade journey:', err);
    }
    return null;
  }, []);

  const executeTradeRequest = async () => {
    if (!userRequest.trim()) {
      setError('Please enter a trade request');
      return;
    }

    setIsExecuting(true);
    setError(null);
    setCurrentJourney(null);

    try {
      // Start the orchestration
      const response = await fetch('/api/orchestrator/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_request: userRequest,
          timestamp: new Date().toISOString()
        }),
      });

      if (response.ok) {
        const result = await response.json();
        
        if (result.trade_id) {
          // Start polling for updates
          pollTradeProgress(result.trade_id);
        } else {
          throw new Error('No trade ID returned');
        }
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to start trade orchestration');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
      setIsExecuting(false);
    }
  };

  const pollTradeProgress = (tradeId: string) => {
    const pollInterval = setInterval(async () => {
      const journey = await loadTradeJourney(tradeId);
      
      if (journey) {
        setCurrentJourney(journey);
        
        // Stop polling if trade is completed or failed
        if (journey.final_outcome || journey.current_phase === 'completed' || journey.current_phase === 'failed') {
          clearInterval(pollInterval);
          setIsExecuting(false);
          
          // Refresh stats and recent trades
          loadOrchestratorStats();
          loadRecentTrades();
        }
      }
    }, 2000); // Poll every 2 seconds

    // Stop polling after 10 minutes max
    setTimeout(() => {
      clearInterval(pollInterval);
      setIsExecuting(false);
    }, 600000);
  };

  const handleQuickAction = (action: string) => {
    const quickActions = {
      'best_spy_trade': "What's the best SPY PUT selling opportunity today?",
      'safe_premium': "Find a safe premium collection trade with low risk",
      'high_probability': "Show me high probability trades with 70%+ win rate",
      'market_analysis': "Analyze current market conditions for options trading"
    };
    
    setUserRequest(quickActions[action as keyof typeof quickActions] || action);
  };

  const formatSuccessRate = (rate: number) => {
    return `${(rate * 100).toFixed(1)}%`;
  };

  const formatExecutionTime = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`;
  };

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Trades</p>
                  <p className="text-2xl font-bold">{stats.total_orchestrations}</p>
                </div>
                <Activity className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Success Rate</p>
                  <p className="text-2xl font-bold text-green-600">
                    {formatSuccessRate(stats.success_rate)}
                  </p>
                </div>
                <CheckCircle className="w-8 h-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Avg. Time</p>
                  <p className="text-2xl font-bold">
                    {formatExecutionTime(stats.avg_execution_time)}
                  </p>
                </div>
                <Clock className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Failed Trades</p>
                  <p className="text-2xl font-bold text-red-600">{stats.failed_trades}</p>
                </div>
                <AlertTriangle className="w-8 h-8 text-red-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Trade Request Interface */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="w-5 h-5" />
            FNTX AI Trade Orchestrator
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Enter your trading request and watch the AI agents collaborate to execute your strategy
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Quick Actions */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Quick Actions:</p>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleQuickAction('best_spy_trade')}
                disabled={isExecuting}
              >
                <TrendingUp className="w-4 h-4 mr-2" />
                Best SPY Trade
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleQuickAction('safe_premium')}
                disabled={isExecuting}
              >
                <DollarSign className="w-4 h-4 mr-2" />
                Safe Premium
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleQuickAction('high_probability')}
                disabled={isExecuting}
              >
                <CheckCircle className="w-4 h-4 mr-2" />
                High Probability
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleQuickAction('market_analysis')}
                disabled={isExecuting}
              >
                <Activity className="w-4 h-4 mr-2" />
                Market Analysis
              </Button>
            </div>
          </div>

          <Separator />

          {/* Custom Request */}
          <div className="space-y-3">
            <label className="text-sm font-medium">Custom Trade Request:</label>
            <Textarea
              placeholder="Describe what you want to trade... (e.g., 'Find the best SPY PUT selling opportunity with low risk and high premium')"
              value={userRequest}
              onChange={(e) => setUserRequest(e.target.value)}
              disabled={isExecuting}
              rows={3}
            />
            <Button 
              onClick={executeTradeRequest}
              disabled={isExecuting || !userRequest.trim()}
              className="w-full"
            >
              {isExecuting ? (
                <>
                  <Activity className="w-4 h-4 mr-2 animate-spin" />
                  Orchestrating Trade...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Execute Trade Request
                </>
              )}
            </Button>
          </div>

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Trade Journey Stepper */}
      <TradeStepper 
        journeyData={currentJourney || undefined}
        onRefresh={() => loadTradeJourney()}
      />

      {/* Recent Trades */}
      {recentTrades.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Trade Orchestrations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentTrades.slice(0, 5).map((trade) => (
                <div key={trade.trade_id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{trade.trade_id}</span>
                      <Badge variant={trade.final_outcome?.success ? "success" : "destructive"}>
                        {trade.final_outcome?.success ? "Success" : "Failed"}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1 truncate">
                      {trade.user_request}
                    </p>
                  </div>
                  <div className="text-right text-sm text-muted-foreground">
                    <div>{formatExecutionTime(trade.execution_time)}</div>
                    <div>{new Date(trade.initiated_at).toLocaleDateString()}</div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setCurrentJourney(trade)}
                  >
                    View
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};