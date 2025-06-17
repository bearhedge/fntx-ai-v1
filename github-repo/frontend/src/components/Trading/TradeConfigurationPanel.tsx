import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Slider } from "@/components/ui/slider";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  Target, 
  Shield, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle, 
  DollarSign,
  Activity,
  Brain,
  Settings
} from 'lucide-react';

interface OptionsContract {
  symbol: string;
  strike: number;
  expiration: string;
  option_type: string;
  bid: number;
  ask: number;
  last: number;
  volume: number;
  open_interest: number;
  implied_volatility: number;
  delta?: number;
  gamma?: number;
  theta?: number;
  vega?: number;
  ai_score?: number;
}

interface TradeConfig {
  contract_symbol: string;
  strike: number;
  expiration: string;
  option_type: string;
  quantity: number;
  entry_price: number;
  stop_loss_multiplier: number;
  take_profit_percentage: number;
  max_loss_dollars?: number;
  notes?: string;
}

interface TradeAnalysis {
  trade_id: string;
  config: TradeConfig;
  ai_analysis: {
    environment_watcher: {
      market_regime: string;
      volatility_environment: string;
      recommendation: string;
    };
    strategic_planner: {
      strategy_alignment: string;
      optimal_timing: string;
      position_sizing: string;
    };
    reward_model: {
      user_preference_match: string;
      risk_tolerance_alignment: string;
      profit_goal_alignment: string;
    };
    executor: {
      execution_feasibility: string;
      liquidity_assessment: string;
      timing_optimization: string;
    };
    evaluator: {
      overall_score: number;
      confidence_level: number;
      risk_score: number;
      recommendation: string;
    };
  };
  risk_assessment: {
    max_loss_dollars: number;
    max_profit_dollars: number;
    break_even_price: number;
    risk_reward_ratio: number;
    probability_of_profit: number;
    time_to_expiration: string;
    assignment_risk: string;
  };
  estimated_profit_loss: {
    best_case: number;
    worst_case: number;
    expected_value: number;
    break_even_scenarios: string[];
  };
  execution_ready: boolean;
  warnings: string[];
}

interface TradeConfigurationPanelProps {
  contract: OptionsContract;
  spyPrice: number;
  onExecuteTrade: (analysis: TradeAnalysis) => void;
  onCancel: () => void;
  className?: string;
}

export const TradeConfigurationPanel: React.FC<TradeConfigurationPanelProps> = ({
  contract,
  spyPrice,
  onExecuteTrade,
  onCancel,
  className = ''
}) => {
  const [config, setConfig] = useState<TradeConfig>({
    contract_symbol: contract.symbol,
    strike: contract.strike,
    expiration: contract.expiration,
    option_type: contract.option_type,
    quantity: 1,
    entry_price: contract.last || (contract.bid + contract.ask) / 2,
    stop_loss_multiplier: 3.0,
    take_profit_percentage: 0.5,
    notes: ''
  });

  const [analysis, setAnalysis] = useState<TradeAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTradeAnalysis = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`http://localhost:8002/api/trade/manual-configure`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        throw new Error(`Failed to analyze trade: ${response.statusText}`);
      }

      const data = await response.json();
      setAnalysis(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze trade');
      console.error('Trade analysis error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTradeAnalysis();
  }, [config.quantity, config.entry_price, config.stop_loss_multiplier, config.take_profit_percentage]);

  const handleConfigChange = (field: keyof TradeConfig, value: any) => {
    setConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleExecute = () => {
    if (analysis && analysis.execution_ready) {
      onExecuteTrade(analysis);
    }
  };

  const formatPrice = (price: number) => {
    return `$${price.toFixed(2)}`;
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const getRecommendationBadge = (recommendation: string) => {
    const badgeStyles = {
      'FAVORABLE': 'bg-green-500',
      'GOOD': 'bg-green-400', 
      'PROCEED_WITH_CAUTION': 'bg-yellow-500',
      'CAUTION': 'bg-yellow-600',
      'HIGH': 'bg-green-500',
      'MEDIUM': 'bg-yellow-500',
      'LOW': 'bg-red-500',
      'READY': 'bg-green-500',
      'APPROPRIATE': 'bg-green-400',
      'WITHIN_LIMITS': 'bg-green-400',
      'ALIGNED': 'bg-green-400',
      'CURRENT_OPTIMAL': 'bg-green-500',
      'EXCELLENT': 'bg-green-600'
    };

    return (
      <Badge className={badgeStyles[recommendation as keyof typeof badgeStyles] || 'bg-gray-500'}>
        {recommendation.replace('_', ' ')}
      </Badge>
    );
  };

  const calculateBreakEven = () => {
    if (contract.option_type === 'P') {
      return contract.strike - config.entry_price;
    } else {
      return contract.strike + config.entry_price;
    }
  };

  const calculateMaxLoss = () => {
    return config.entry_price * config.stop_loss_multiplier * config.quantity * 100;
  };

  const calculateMaxProfit = () => {
    return (config.entry_price - (config.entry_price * config.take_profit_percentage)) * config.quantity * 100;
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Configure Trade: {contract.symbol}
          </div>
          <Button onClick={onCancel} variant="outline" size="sm">
            Cancel
          </Button>
        </CardTitle>

        {/* Contract Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
          <div className="text-center">
            <div className="text-lg font-bold text-blue-600">
              {contract.option_type === 'P' ? 'PUT' : 'CALL'}
            </div>
            <div className="text-sm text-gray-600">${contract.strike}</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-green-600">{formatPrice(contract.last)}</div>
            <div className="text-sm text-gray-600">Last Price</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-purple-600">{formatPrice(spyPrice)}</div>
            <div className="text-sm text-gray-600">SPY Price</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-orange-600">{formatPrice(calculateBreakEven())}</div>
            <div className="text-sm text-gray-600">Break Even</div>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <Tabs defaultValue="config" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="config">Configuration</TabsTrigger>
            <TabsTrigger value="greeks">Greeks & Risk</TabsTrigger>
            <TabsTrigger value="ai-insights">AI Insights</TabsTrigger>
            <TabsTrigger value="execution">Execute</TabsTrigger>
          </TabsList>

          <TabsContent value="config" className="space-y-4">
            {/* Position Configuration */}
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="quantity">Number of Contracts</Label>
                  <Input
                    id="quantity"
                    type="number"
                    min="1"
                    max="10"
                    value={config.quantity}
                    onChange={(e) => handleConfigChange('quantity', parseInt(e.target.value) || 1)}
                  />
                </div>

                <div>
                  <Label htmlFor="entry_price">Entry Price</Label>
                  <Input
                    id="entry_price"
                    type="number"
                    step="0.01"
                    value={config.entry_price}
                    onChange={(e) => handleConfigChange('entry_price', parseFloat(e.target.value) || 0)}
                  />
                </div>
              </div>

              {/* Risk Management */}
              <div className="space-y-4">
                <div>
                  <Label>Stop Loss Multiplier: {config.stop_loss_multiplier}x</Label>
                  <Slider
                    value={[config.stop_loss_multiplier]}
                    onValueChange={([value]) => handleConfigChange('stop_loss_multiplier', value)}
                    min={1}
                    max={10}
                    step={0.5}
                    className="mt-2"
                  />
                  <div className="flex justify-between text-sm text-gray-500 mt-1">
                    <span>1x (Conservative)</span>
                    <span>Stop Loss: {formatPrice(config.entry_price * config.stop_loss_multiplier)}</span>
                    <span>10x (Aggressive)</span>
                  </div>
                </div>

                <div>
                  <Label>Take Profit: {formatPercentage(config.take_profit_percentage)}</Label>
                  <Slider
                    value={[config.take_profit_percentage * 100]}
                    onValueChange={([value]) => handleConfigChange('take_profit_percentage', value / 100)}
                    min={10}
                    max={90}
                    step={5}
                    className="mt-2"
                  />
                  <div className="flex justify-between text-sm text-gray-500 mt-1">
                    <span>10% (Quick)</span>
                    <span>Target: {formatPrice(config.entry_price * config.take_profit_percentage)}</span>
                    <span>90% (Patient)</span>
                  </div>
                </div>
              </div>

              {/* Risk Summary */}
              <div className="grid grid-cols-3 gap-4 p-4 bg-blue-50 rounded-lg">
                <div className="text-center">
                  <div className="text-lg font-bold text-green-600">{formatPrice(calculateMaxProfit())}</div>
                  <div className="text-sm text-gray-600">Max Profit</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-red-600">{formatPrice(calculateMaxLoss())}</div>
                  <div className="text-sm text-gray-600">Max Loss</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-blue-600">
                    {calculateMaxLoss() > 0 ? (calculateMaxProfit() / calculateMaxLoss()).toFixed(2) : '∞'}:1
                  </div>
                  <div className="text-sm text-gray-600">Risk/Reward</div>
                </div>
              </div>

              <div>
                <Label htmlFor="notes">Notes (Optional)</Label>
                <Input
                  id="notes"
                  placeholder="Add any notes about this trade..."
                  value={config.notes || ''}
                  onChange={(e) => handleConfigChange('notes', e.target.value)}
                />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="greeks" className="space-y-4">
            {/* Greeks Display */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card className="p-4">
                <div className="text-center">
                  <div className="text-lg font-bold text-blue-600">
                    {contract.delta?.toFixed(3) || 'N/A'}
                  </div>
                  <div className="text-sm text-gray-600">Delta</div>
                  <div className="text-xs text-gray-500">Price sensitivity</div>
                </div>
              </Card>

              <Card className="p-4">
                <div className="text-center">
                  <div className="text-lg font-bold text-green-600">
                    {contract.gamma?.toFixed(4) || 'N/A'}
                  </div>
                  <div className="text-sm text-gray-600">Gamma</div>
                  <div className="text-xs text-gray-500">Delta acceleration</div>
                </div>
              </Card>

              <Card className="p-4">
                <div className="text-center">
                  <div className="text-lg font-bold text-red-600">
                    {contract.theta?.toFixed(3) || 'N/A'}
                  </div>
                  <div className="text-sm text-gray-600">Theta</div>
                  <div className="text-xs text-gray-500">Time decay</div>
                </div>
              </Card>

              <Card className="p-4">
                <div className="text-center">
                  <div className="text-lg font-bold text-purple-600">
                    {contract.vega?.toFixed(3) || 'N/A'}
                  </div>
                  <div className="text-sm text-gray-600">Vega</div>
                  <div className="text-xs text-gray-500">Volatility sensitivity</div>
                </div>
              </Card>
            </div>

            {/* Advanced Risk Metrics */}
            {analysis && (
              <div className="space-y-4">
                <Card className="p-4">
                  <h4 className="font-medium mb-3 flex items-center gap-2">
                    <Shield className="w-4 h-4" />
                    Risk Assessment
                  </h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Probability of Profit:</span>
                      <span className="ml-2 font-medium">{formatPercentage(analysis.risk_assessment.probability_of_profit)}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Assignment Risk:</span>
                      <span className="ml-2">
                        <Badge variant={analysis.risk_assessment.assignment_risk === 'LOW' ? 'default' : 'secondary'}>
                          {analysis.risk_assessment.assignment_risk}
                        </Badge>
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Time to Expiration:</span>
                      <span className="ml-2 font-medium">{analysis.risk_assessment.time_to_expiration}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Break Even:</span>
                      <span className="ml-2 font-medium">{formatPrice(analysis.risk_assessment.break_even_price)}</span>
                    </div>
                  </div>
                </Card>
              </div>
            )}
          </TabsContent>

          <TabsContent value="ai-insights" className="space-y-4">
            {loading && (
              <div className="flex items-center justify-center h-32">
                <Activity className="w-6 h-6 animate-spin" />
                <span className="ml-2">Analyzing trade with AI agents...</span>
              </div>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {analysis && (
              <div className="space-y-4">
                {/* Overall AI Score */}
                <Card className="p-4">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="font-medium flex items-center gap-2">
                      <Brain className="w-4 h-4" />
                      AI Analysis Summary
                    </h4>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-blue-600">
                        {analysis.ai_analysis.evaluator.overall_score.toFixed(1)}/10
                      </div>
                      <div className="text-sm text-gray-600">Overall Score</div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Confidence Level:</span>
                      <span className="ml-2 font-medium">{formatPercentage(analysis.ai_analysis.evaluator.confidence_level)}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Risk Score:</span>
                      <span className="ml-2 font-medium">{analysis.ai_analysis.evaluator.risk_score.toFixed(1)}/10</span>
                    </div>
                  </div>
                  
                  <div className="mt-3">
                    <span className="text-gray-600">Recommendation:</span>
                    <span className="ml-2">{getRecommendationBadge(analysis.ai_analysis.evaluator.recommendation)}</span>
                  </div>
                </Card>

                {/* Individual Agent Insights */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card className="p-4">
                    <h5 className="font-medium mb-3">Environment Watcher</h5>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>Market Regime:</span>
                        {getRecommendationBadge(analysis.ai_analysis.environment_watcher.market_regime)}
                      </div>
                      <div className="flex justify-between">
                        <span>Volatility:</span>
                        {getRecommendationBadge(analysis.ai_analysis.environment_watcher.volatility_environment)}
                      </div>
                      <div className="flex justify-between">
                        <span>Recommendation:</span>
                        {getRecommendationBadge(analysis.ai_analysis.environment_watcher.recommendation)}
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4">
                    <h5 className="font-medium mb-3">Strategic Planner</h5>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>Strategy Alignment:</span>
                        {getRecommendationBadge(analysis.ai_analysis.strategic_planner.strategy_alignment)}
                      </div>
                      <div className="flex justify-between">
                        <span>Timing:</span>
                        {getRecommendationBadge(analysis.ai_analysis.strategic_planner.optimal_timing)}
                      </div>
                      <div className="flex justify-between">
                        <span>Position Size:</span>
                        {getRecommendationBadge(analysis.ai_analysis.strategic_planner.position_sizing)}
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4">
                    <h5 className="font-medium mb-3">Reward Model</h5>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>User Preference:</span>
                        {getRecommendationBadge(analysis.ai_analysis.reward_model.user_preference_match)}
                      </div>
                      <div className="flex justify-between">
                        <span>Risk Tolerance:</span>
                        {getRecommendationBadge(analysis.ai_analysis.reward_model.risk_tolerance_alignment)}
                      </div>
                      <div className="flex justify-between">
                        <span>Profit Goals:</span>
                        {getRecommendationBadge(analysis.ai_analysis.reward_model.profit_goal_alignment)}
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4">
                    <h5 className="font-medium mb-3">Executor</h5>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span>Feasibility:</span>
                        {getRecommendationBadge(analysis.ai_analysis.executor.execution_feasibility)}
                      </div>
                      <div className="flex justify-between">
                        <span>Liquidity:</span>
                        {getRecommendationBadge(analysis.ai_analysis.executor.liquidity_assessment)}
                      </div>
                      <div className="flex justify-between">
                        <span>Timing:</span>
                        {getRecommendationBadge(analysis.ai_analysis.executor.timing_optimization)}
                      </div>
                    </div>
                  </Card>
                </div>

                {/* Warnings */}
                {analysis.warnings.length > 0 && (
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      <div className="font-medium mb-2">Warnings:</div>
                      <ul className="space-y-1">
                        {analysis.warnings.map((warning, index) => (
                          <li key={index} className="text-sm">• {warning}</li>
                        ))}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            )}
          </TabsContent>

          <TabsContent value="execution" className="space-y-4">
            {analysis && (
              <>
                {/* Final Trade Summary */}
                <Card className="p-4">
                  <h4 className="font-medium mb-4 flex items-center gap-2">
                    <Target className="w-4 h-4" />
                    Trade Execution Summary
                  </h4>
                  
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="space-y-2">
                      <div className="text-sm">
                        <span className="text-gray-600">Contract:</span>
                        <span className="ml-2 font-medium">{contract.symbol}</span>
                      </div>
                      <div className="text-sm">
                        <span className="text-gray-600">Quantity:</span>
                        <span className="ml-2 font-medium">{config.quantity} contract(s)</span>
                      </div>
                      <div className="text-sm">
                        <span className="text-gray-600">Entry Price:</span>
                        <span className="ml-2 font-medium">{formatPrice(config.entry_price)}</span>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm">
                        <span className="text-gray-600">Stop Loss:</span>
                        <span className="ml-2 font-medium">{formatPrice(config.entry_price * config.stop_loss_multiplier)}</span>
                      </div>
                      <div className="text-sm">
                        <span className="text-gray-600">Take Profit:</span>
                        <span className="ml-2 font-medium">{formatPrice(config.entry_price * config.take_profit_percentage)}</span>
                      </div>
                      <div className="text-sm">
                        <span className="text-gray-600">Max Risk:</span>
                        <span className="ml-2 font-medium text-red-600">{formatPrice(analysis.risk_assessment.max_loss_dollars)}</span>
                      </div>
                    </div>
                  </div>

                  {/* P&L Scenarios */}
                  <div className="grid grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
                    <div className="text-center">
                      <div className="text-lg font-bold text-green-600">
                        {formatPrice(analysis.estimated_profit_loss.best_case)}
                      </div>
                      <div className="text-sm text-gray-600">Best Case</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-blue-600">
                        {formatPrice(analysis.estimated_profit_loss.expected_value)}
                      </div>
                      <div className="text-sm text-gray-600">Expected</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-red-600">
                        {formatPrice(analysis.estimated_profit_loss.worst_case)}
                      </div>
                      <div className="text-sm text-gray-600">Worst Case</div>
                    </div>
                  </div>
                </Card>

                {/* Execution Button */}
                <div className="flex gap-4">
                  <Button
                    onClick={handleExecute}
                    disabled={!analysis.execution_ready || loading}
                    className="flex-1"
                    size="lg"
                  >
                    {analysis.execution_ready ? (
                      <>
                        <CheckCircle className="w-5 h-5 mr-2" />
                        Execute Trade
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="w-5 h-5 mr-2" />
                        Not Ready to Execute
                      </>
                    )}
                  </Button>
                  
                  <Button onClick={onCancel} variant="outline" size="lg">
                    Cancel
                  </Button>
                </div>

                {!analysis.execution_ready && (
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      Trade not ready for execution. Please review the warnings and AI recommendations.
                    </AlertDescription>
                  </Alert>
                )}
              </>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};