import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Activity, AlertTriangle } from 'lucide-react';

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
  implied_volatility: number | null;
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
    vix_level: number | null;
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
  data_timestamp?: string | null;
  data_note?: string | null;
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
      
      const response = await fetch(`/api/options/spy-atm?num_strikes=5`, {
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

  const formatPercentage = (value: number | null | undefined) => {
    if (value === null || value === undefined) return 'N/A';
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

  if (loading || error || !optionsData) {
    return null; // Don't show any UI when loading, error, or no data
  }

  const { contracts, ai_insights, spy_price, expiration_date, market_regime, data_timestamp, data_note } = optionsData;

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
    <div className={`${className} p-4 bg-white rounded-lg border`}>
      <div className="flex items-center justify-between mb-2">
        <div className="font-mono text-sm font-bold">
          SPY Options Chain | {expiration_date} | SPY: ${spy_price.toFixed(2)} | {ai_insights.vix_level ? `VIX: ${ai_insights.vix_level.toFixed(1)}` : 'VIX: N/A'}
        </div>
        <Button onClick={fetchOptionsChain} variant="ghost" size="sm" className="h-6 px-2 text-xs">
          Refresh
        </Button>
      </div>

      <div className="overflow-x-auto">
        <Table className="font-mono text-sm">
            <TableHeader>
              <TableRow className="bg-gray-100">
                <TableHead className="text-center font-bold">Type</TableHead>
                <TableHead className="text-center font-bold">Strike</TableHead>
                <TableHead className="text-center font-bold">Bid</TableHead>
                <TableHead className="text-center font-bold">Ask</TableHead>
                <TableHead className="text-center font-bold">Last</TableHead>
                <TableHead className="text-center font-bold">Vol</TableHead>
                <TableHead className="text-center font-bold">OI</TableHead>
                <TableHead className="text-center font-bold">IV</TableHead>
                <TableHead className="text-center font-bold">Score</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedContracts.map((contract) => (
                <TableRow 
                  key={contract.symbol}
                  className={selectedContract?.symbol === contract.symbol ? 'bg-blue-50' : 'hover:bg-gray-50 cursor-pointer'}
                  onClick={() => handleContractClick(contract)}
                >
                  <TableCell className="text-center">
                    <span className={`font-bold ${contract.option_type === 'P' ? 'text-red-600' : 'text-green-600'}`}>
                      {contract.option_type === 'P' ? 'PUT' : 'CALL'}
                    </span>
                  </TableCell>
                  
                  <TableCell className="text-center font-bold">
                    {contract.strike.toFixed(0)}
                  </TableCell>
                  
                  <TableCell className="text-center">{contract.bid.toFixed(2)}</TableCell>
                  <TableCell className="text-center">{contract.ask.toFixed(2)}</TableCell>
                  <TableCell className="text-center">{contract.last.toFixed(2)}</TableCell>
                  <TableCell className="text-center">{contract.volume}</TableCell>
                  <TableCell className="text-center">{contract.open_interest}</TableCell>
                  <TableCell className="text-center">{formatPercentage(contract.implied_volatility)}</TableCell>
                  <TableCell className="text-center">
                    <span className={`font-bold ${contract.ai_score >= 8 ? 'text-green-600' : 'text-gray-600'}`}>
                      {contract.ai_score?.toFixed(1) || '-'}
                    </span>
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

        {data_note && (
          <div className="mt-2 text-xs text-gray-500 font-mono">
            {data_note} {data_timestamp && `(${data_timestamp})`}
          </div>
        )}
    </div>
  );
};