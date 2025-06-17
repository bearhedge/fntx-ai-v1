
export interface Message {
  id: string;
  content: string;
  sender: 'user' | 'ai' | 'system';
  timestamp: Date;
  type: 'text' | 'trade-options' | 'waiting-period' | 'html';
  tradeOptions?: TradeOption[];
  waitingPeriod?: WaitingPeriod;
  table?: string; // Optional HTML table for options chain, used by EnhancedMessage
}

export interface WaitingPeriod {
  totalMinutes: number;
  remainingMinutes: number;
  reason: string;
}

export interface TradeOption {
  id: string;
  symbol: string;
  strike: number;
  type: 'call' | 'put';
  expiration: Date;
  premium: number;
  contracts: number;
  riskLevel: 'conservative' | 'moderate' | 'aggressive';
  probability: number;
  totalPremium: number;
  riskReward: string;
  strategy: string;
  stopLoss: number;
  takeProfit: number;
}

export interface Position {
  id: string;
  symbol: string;
  strike: number;
  type: 'call' | 'put';
  contracts: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercentage: number;
  stopLoss: number;
  takeProfit: number;
  expiration: Date;
  status: 'open' | 'closed' | 'expired';
}

export interface AccountSummary {
  balance: number;
  available: number;
  marginUsed: number;
  dailyPnl: number;
  totalTrades: number;
  winRate: number;
}

export interface MarketData {
  spyPrice: number;
  vix: number;
  marketTrend: string;
  marketStatus: 'open' | 'closed' | 'pre-market' | 'after-hours';
}

export interface WithdrawalRecord {
  id: string;
  date: string;
  amount: number;
  status: 'Pending' | 'Completed' | 'Failed';
  destination: string;
  transactionId?: string;
  fees: number;
}

export interface AvailabilityBreakdown {
  total: number;
  available: number;
  locked: number;
  pendingRelease: {
    amount: number;
    releaseDate: string;
    reason: string;
  }[];
}

export interface WithdrawalDestination {
  id: string;
  type: 'bank' | 'crypto';
  name: string;
  details: string;
  lastUsed?: string;
}
