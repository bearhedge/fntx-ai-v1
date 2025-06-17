import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { WithdrawalHistory } from './WithdrawalHistory';
import { WithdrawalRecord, WithdrawalDestination, AvailabilityBreakdown } from '@/types/trading';
interface WithdrawalTabProps {
  availableBalance: number;
  withdrawalHistory: WithdrawalRecord[];
  availabilityBreakdown: AvailabilityBreakdown;
}
export const WithdrawalTab: React.FC<WithdrawalTabProps> = ({
  availableBalance,
  withdrawalHistory,
  availabilityBreakdown
}) => {
  const [activeView, setActiveView] = useState<'dashboard' | 'history'>('dashboard');
  const [withdrawalAmount, setWithdrawalAmount] = useState<string>('');
  const [amountType, setAmountType] = useState<'recommended' | 'custom'>('recommended');
  const [selectedDestination, setSelectedDestination] = useState<string>('1');
  const sampleDestinations: WithdrawalDestination[] = [{
    id: '1',
    type: 'bank',
    name: 'Bank Account',
    details: '****1234',
    lastUsed: '2025-05-28'
  }, {
    id: '2',
    type: 'crypto',
    name: 'Crypto Wallet',
    details: '0x1234...abcd',
    lastUsed: '2025-05-15'
  }];

  // Calculate metrics
  const totalPortfolioValue = 18820;
  const lockedFunds = 14000;
  const pendingRelease = 2320;
  const totalWithdrawnYTD = withdrawalHistory.filter(w => w.status === 'Completed' && new Date(w.date).getFullYear() === 2025).reduce((sum, w) => sum + w.amount, 0);
  const weeklyProfit = 2000;
  const weeklyReturn = 0.2;
  const recommendedAmount = 1200;
  const handleWithdrawal = () => {
    const amount = amountType === 'recommended' ? recommendedAmount : parseFloat(withdrawalAmount);
    console.log('Processing withdrawal:', {
      amount,
      destinationId: selectedDestination
    });
    setActiveView('history');
  };
  if (activeView === 'history') {
    return <div className="px-1">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-medium text-gray-900">Withdrawals</h3>
          <Button variant="outline" onClick={() => setActiveView('dashboard')} className="bg-white border-gray-200 text-gray-700 hover:bg-gray-50">
            Back to Dashboard
          </Button>
        </div>
        <WithdrawalHistory withdrawals={withdrawalHistory} />
      </div>;
  }
  return <div className="px-1 space-y-4">
      {/* Portfolio Summary */}
      <div className="border border-gray-200 rounded-lg p-6 bg-gray-200">
        <h3 className="text-sm font-medium text-gray-700 uppercase tracking-wide mb-6">PORTFOLIO SUMMARY</h3>
        
        <div className="grid grid-cols-3 gap-8 mb-6">
          <div>
            <div className="text-2xl font-bold text-gray-900 mb-1">${totalPortfolioValue.toLocaleString()}</div>
            <div className="text-sm text-gray-600 mb-2">Total Value</div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-gray-900 h-2 rounded-full" style={{
              width: '100%'
            }}></div>
            </div>
          </div>
          
          <div>
            <div className="text-2xl font-bold text-gray-900 mb-1">${availableBalance.toLocaleString()}</div>
            <div className="text-sm text-gray-600 mb-2">Available</div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-gray-600 h-2 rounded-full" style={{
              width: `${availableBalance / totalPortfolioValue * 100}%`
            }}></div>
            </div>
          </div>
          
          <div>
            <div className="text-2xl font-bold text-gray-900 mb-1">${lockedFunds.toLocaleString()}</div>
            <div className="text-sm text-gray-600 mb-2">Locked</div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-gray-400 h-2 rounded-full" style={{
              width: `${lockedFunds / totalPortfolioValue * 100}%`
            }}></div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-8">
          <div>
            <div className="text-lg font-medium text-gray-900 mb-1">${pendingRelease.toLocaleString()}</div>
            <div className="text-sm text-gray-600">Pending Release (on 6/15/2025)</div>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
              <div className="bg-gray-500 h-2 rounded-full" style={{
              width: `${pendingRelease / totalPortfolioValue * 100}%`
            }}></div>
            </div>
          </div>
          
          <div>
            <div className="text-lg font-medium text-gray-900 mb-1">${totalWithdrawnYTD.toLocaleString()}</div>
            <div className="text-sm text-gray-600">Total Withdrawn YTD</div>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
              <div className="bg-gray-700 h-2 rounded-full" style={{
              width: `${totalWithdrawnYTD / totalPortfolioValue * 100}%`
            }}></div>
            </div>
          </div>
        </div>
      </div>

      {/* Withdrawal Recommendation */}
      <div className="border border-gray-200 rounded-lg p-6 bg-gray-200">
        <h3 className="text-sm font-medium text-gray-700 uppercase tracking-wide mb-6">WITHDRAWAL RECOMMENDATION</h3>
        
        <div className="grid grid-cols-2 gap-6 mb-4">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-700 uppercase tracking-wide mb-3">WEEKLY PERFORMANCE</h4>
            <div className="text-xl font-bold text-gray-900 mb-1">${weeklyProfit.toLocaleString()}</div>
            <div className="text-sm text-gray-600">Profit</div>
            <div className="text-sm text-gray-600 mt-1">{weeklyReturn}% of principal</div>
          </div>
          
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-700 uppercase tracking-wide mb-3">RECOMMENDED WITHDRAWAL</h4>
            <div className="text-xl font-bold text-gray-900 mb-1">${recommendedAmount.toLocaleString()}</div>
            <div className="text-sm text-gray-600">Amount</div>
            <div className="text-sm text-gray-600 mt-1">(60% of weekly profit)</div>
          </div>
        </div>

        <p className="text-sm text-gray-700 leading-relaxed">
          Based on your trading performance this week, we recommend withdrawing ${recommendedAmount.toLocaleString()} while maintaining adequate margin for your open positions.
        </p>
      </div>

      {/* Withdrawal Action */}
      <div className="border border-gray-200 rounded-lg p-6 bg-gray-200">
        <h3 className="text-sm font-medium text-gray-700 uppercase tracking-wide mb-6">WITHDRAWAL ACTION</h3>
        
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700 mb-3 block">Amount</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" name="amountType" value="recommended" checked={amountType === 'recommended'} onChange={e => setAmountType(e.target.value as 'recommended' | 'custom')} className="w-4 h-4 text-gray-900 border-gray-300 focus:ring-gray-900" />
                <span className="text-sm text-gray-700">Recommended (${recommendedAmount.toLocaleString()})</span>
              </label>
              
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" name="amountType" value="custom" checked={amountType === 'custom'} onChange={e => setAmountType(e.target.value as 'recommended' | 'custom')} className="w-4 h-4 text-gray-900 border-gray-300 focus:ring-gray-900" />
                <span className="text-sm text-gray-700">Custom:</span>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
                  <Input type="number" value={withdrawalAmount} onChange={e => setWithdrawalAmount(e.target.value)} placeholder="0" className="pl-8 w-32 h-8 text-sm" disabled={amountType === 'recommended'} />
                </div>
              </label>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">Destination</label>
            <Select value={selectedDestination} onValueChange={setSelectedDestination}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {sampleDestinations.map(dest => <SelectItem key={dest.id} value={dest.id}>
                    {dest.name} ({dest.details})
                  </SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div className="pt-4">
            <Button onClick={handleWithdrawal} className="w-full h-12 bg-gray-900 hover:bg-gray-800 text-white font-medium">
              WITHDRAW FUNDS
            </Button>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="border border-gray-200 rounded-lg p-6 bg-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-gray-700 uppercase tracking-wide">RECENT ACTIVITY</h3>
          <Button variant="ghost" onClick={() => setActiveView('history')} className="text-sm text-gray-600 hover:text-gray-900 p-0 h-auto font-normal">
            View Complete History →
          </Button>
        </div>
        
        <div className="space-y-3">
          {withdrawalHistory.slice(0, 2).map(withdrawal => <div key={withdrawal.id} className="border border-gray-200 rounded-lg p-4">
              <div className="flex justify-between items-center">
                <div className="flex gap-4">
                  <div className="text-sm font-medium text-gray-900">{withdrawal.date}</div>
                  <div className="text-sm font-medium text-gray-900">${withdrawal.amount.toLocaleString()}</div>
                  <div className="text-sm text-gray-600">{withdrawal.destination}</div>
                </div>
                <div className="text-sm font-medium text-gray-900">{withdrawal.status}</div>
              </div>
            </div>)}
        </div>
      </div>
    </div>;
};