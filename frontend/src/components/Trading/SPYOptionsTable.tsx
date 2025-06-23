import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TrendingUp, TrendingDown, Activity, Target, AlertTriangle } from 'lucide-react';

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

interface OptionsChainData {
  spy_price: number;
  expiration_date: string;
  contracts: OptionsContract[];
  ai_insights: {
    market_regime: string;
    vix_level: number;
    trading_signal: string;
    strategy_preference: string;
    position_sizing: string;
    specific_actions: string[];
    confidence_level: number;
    recommended_strikes: number[];
    risk_warnings: string[];
  };
  market_regime: string;
  timestamp: string;
}

interface SPYOptionsTableProps {
  onContractSelect: (contract: OptionsContract) => void;
  optionType?: 'both' | 'put' | 'call';
  className?: string;
}

export const SPYOptionsTable: React.FC<SPYOptionsTableProps> = ({
  onContractSelect,
  optionType = 'both',
  className = ''
}) => {
  const [optionsData, setOptionsData] = useState<OptionsChainData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedContract, setSelectedContract] = useState<OptionsContract | null>(null);

  const fetchOptionsChain = async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log('🔄 Fetching SPY options chain...', { optionType });
      
      // Add timeout to the fetch request
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
      
      const response = await fetch(`/api/spy-options/chain?option_type=${optionType}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      console.log('📡 API Response status:', response.status, response.statusText);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ API Error response:', errorText);
        throw new Error(`Failed to fetch options chain: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('✅ Options data received:', {
        spy_price: data.spy_price,
        contracts_count: data.contracts?.length,
        market_regime: data.market_regime
      });
      
      setOptionsData(data);
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Request timed out - please try again');
        console.error('⏰ Request timed out');
      } else {
        setError(err instanceof Error ? err.message : 'Failed to fetch options data');
        console.error('❌ Options chain fetch error:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOptionsChain();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchOptionsChain, 30000);
    return () => clearInterval(interval);
  }, [optionType]);

  const handleContractClick = (contract: OptionsContract) => {
    setSelectedContract(contract);
    onContractSelect(contract);
  };

  const formatPrice = (price: number) => {
    return price > 0 ? `$${price.toFixed(2)}` : '-';
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const getAIScoreBadge = (score?: number) => {
    if (!score) return <Badge variant="secondary">-</Badge>;
    
    if (score >= 8) return <Badge className="bg-green-500">★ {score.toFixed(1)}</Badge>;
    if (score >= 6) return <Badge className="bg-yellow-500">◆ {score.toFixed(1)}</Badge>;
    return <Badge variant="secondary">◇ {score.toFixed(1)}</Badge>;
  };

  const getMarketRegimeBadge = (regime: string) => {
    const regimeColors = {
      'favorable_for_selling': 'bg-green-500',
      'neutral': 'bg-blue-500',
      'unfavorable_high_vol': 'bg-red-500',
      'risk_off': 'bg-red-600',
      'unknown': 'bg-gray-500'
    };
    
    return (
      <Badge className={regimeColors[regime as keyof typeof regimeColors] || 'bg-gray-500'}>
        {regime.replace('_', ' ').toUpperCase()}
      </Badge>
    );
  };

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5 animate-spin" />
            Loading SPY Options Chain...
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-32">
            <div className="text-sm text-gray-500">Fetching live data from IBKR...</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="w-5 h-5" />
            Error Loading Options
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-red-600 mb-4">{error}</div>
          <Button onClick={fetchOptionsChain} variant="outline">
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!optionsData) {
    return null;
  }

  const { contracts, ai_insights, spy_price, expiration_date, market_regime } = optionsData;

  // Filter contracts by type
  const filteredContracts = contracts.filter(contract => {
    if (optionType === 'put') return contract.option_type === 'P';
    if (optionType === 'call') return contract.option_type === 'C';
    return true;
  });

  // Sort by AI score (highest first) and then by strike
  const sortedContracts = filteredContracts.sort((a, b) => {
    const scoreA = a.ai_score || 0;
    const scoreB = b.ai_score || 0;
    if (scoreA !== scoreB) return scoreB - scoreA;
    return a.strike - b.strike;
  });

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5" />
            SPY Options Chain - {expiration_date}
          </div>
          <Button onClick={fetchOptionsChain} variant="outline" size="sm">
            Refresh
          </Button>
        </CardTitle>
        
        {/* Market Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">${spy_price.toFixed(2)}</div>
            <div className="text-sm text-gray-600">SPY Price</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">{ai_insights.vix_level.toFixed(1)}</div>
            <div className="text-sm text-gray-600">VIX Level</div>
          </div>
          <div className="text-center">
            {getMarketRegimeBadge(market_regime)}
            <div className="text-sm text-gray-600 mt-1">Market Regime</div>
          </div>
          <div className="text-center">
            <Badge variant={ai_insights.trading_signal === 'bullish' ? 'default' : 'secondary'}>
              {ai_insights.trading_signal.toUpperCase()}
            </Badge>
            <div className="text-sm text-gray-600 mt-1">AI Signal</div>
          </div>
        </div>

        {/* AI Insights */}
        {ai_insights.specific_actions.length > 0 && (
          <div className="p-3 bg-blue-50 rounded-lg">
            <div className="text-sm font-medium text-blue-800 mb-2">AI Recommendations:</div>
            <ul className="text-sm text-blue-700 space-y-1">
              {ai_insights.specific_actions.map((action, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="text-blue-500">•</span>
                  {action}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Risk Warnings */}
        {ai_insights.risk_warnings.length > 0 && (
          <div className="p-3 bg-yellow-50 rounded-lg">
            <div className="text-sm font-medium text-yellow-800 mb-2">Risk Warnings:</div>
            <ul className="text-sm text-yellow-700 space-y-1">
              {ai_insights.risk_warnings.map((warning, index) => (
                <li key={index} className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 text-yellow-600" />
                  {warning}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardHeader>

      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>Strike</TableHead>
                <TableHead>Premium</TableHead>
                <TableHead>Bid/Ask</TableHead>
                <TableHead>Volume</TableHead>
                <TableHead>AI Score</TableHead>
                <TableHead>Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedContracts.map((contract) => (
                <TableRow 
                  key={contract.symbol}
                  className={selectedContract?.symbol === contract.symbol ? 'bg-blue-50' : 'hover:bg-gray-50 cursor-pointer'}
                  onClick={() => handleContractClick(contract)}
                >
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {contract.option_type === 'P' ? (
                        <TrendingDown className="w-4 h-4 text-red-500" />
                      ) : (
                        <TrendingUp className="w-4 h-4 text-green-500" />
                      )}
                      <span className="font-medium">
                        {contract.option_type === 'P' ? 'PUT' : 'CALL'}
                      </span>
                    </div>
                  </TableCell>
                  
                  <TableCell>
                    <div className="font-mono text-sm">
                      ${contract.strike.toFixed(0)}
                    </div>
                    <div className="text-xs text-gray-500">
                      {contract.option_type === 'P' 
                        ? `${((spy_price - contract.strike) / spy_price * 100).toFixed(1)}% OTM`
                        : `${((contract.strike - spy_price) / spy_price * 100).toFixed(1)}% OTM`
                      }
                    </div>
                  </TableCell>
                  
                  <TableCell>
                    <div className="font-medium">
                      {formatPrice(contract.last)}
                    </div>
                    {contract.implied_volatility > 0 && (
                      <div className="text-xs text-gray-500">
                        IV: {formatPercentage(contract.implied_volatility)}
                      </div>
                    )}
                  </TableCell>
                  
                  <TableCell>
                    <div className="text-sm">
                      {formatPrice(contract.bid)} / {formatPrice(contract.ask)}
                    </div>
                    <div className="text-xs text-gray-500">
                      Spread: {formatPrice(contract.ask - contract.bid)}
                    </div>
                  </TableCell>
                  
                  <TableCell>
                    <div className="text-sm">
                      {contract.volume.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">
                      OI: {contract.open_interest.toLocaleString()}
                    </div>
                  </TableCell>
                  
                  <TableCell>
                    {getAIScoreBadge(contract.ai_score)}
                  </TableCell>
                  
                  <TableCell>
                    <Button 
                      onClick={(e) => {
                        e.stopPropagation();
                        handleContractClick(contract);
                      }}
                      size="sm"
                      variant={selectedContract?.symbol === contract.symbol ? "default" : "outline"}
                    >
                      {selectedContract?.symbol === contract.symbol ? "Selected" : "Select"}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {sortedContracts.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No options contracts found for the selected criteria.
          </div>
        )}
      </CardContent>
    </Card>
  );
};