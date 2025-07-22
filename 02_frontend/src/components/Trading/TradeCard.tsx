
import React from 'react';
import { TradeOption } from '../../types/trading';

interface TradeCardProps {
  tradeOption: TradeOption;
  onSelect: (option: TradeOption) => void;
  onViewDetails: (option: TradeOption) => void;
  onModify: (option: TradeOption) => void;
}

export const TradeCard = ({ tradeOption, onSelect, onViewDetails, onModify }: TradeCardProps) => {
  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'conservative':
        return 'bg-blue-600';
      case 'moderate':
        return 'bg-amber-600';
      case 'aggressive':
        return 'bg-red-600';
      default:
        return 'bg-gray-600';
    }
  };

  const getRiskLevelText = (level: string) => {
    return level.charAt(0).toUpperCase() + level.slice(1);
  };

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
      <div className={`${getRiskLevelColor(tradeOption.riskLevel)} text-white text-center py-2 rounded-t-lg -mx-6 -mt-6 mb-4`}>
        <span className="font-semibold text-sm uppercase tracking-wide">
          {getRiskLevelText(tradeOption.riskLevel)}
        </span>
      </div>

      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-800">
          {tradeOption.symbol} ${tradeOption.strike} {tradeOption.type.toUpperCase()}
        </h3>
        <p className="text-sm text-gray-600">
          Expiring {tradeOption.expiration.toLocaleDateString()}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-gray-50 p-3 rounded">
          <div className="text-xs font-semibold text-gray-600 uppercase mb-1">Premium</div>
          <div className="text-lg font-semibold text-gray-800">${tradeOption.premium}</div>
        </div>
        <div className="bg-gray-50 p-3 rounded">
          <div className="text-xs font-semibold text-gray-600 uppercase mb-1">Contracts</div>
          <div className="text-lg font-semibold text-gray-800">{tradeOption.contracts}</div>
        </div>
        <div className="bg-gray-50 p-3 rounded">
          <div className="text-xs font-semibold text-gray-600 uppercase mb-1">Probability</div>
          <div className="text-lg font-semibold text-gray-800">{tradeOption.probability}% OTM</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-gray-50 p-3 rounded">
          <div className="text-xs font-semibold text-gray-600 uppercase mb-1">Total Premium</div>
          <div className="text-lg font-semibold text-gray-800">${tradeOption.totalPremium}</div>
        </div>
        <div className="bg-gray-50 p-3 rounded">
          <div className="text-xs font-semibold text-gray-600 uppercase mb-1">Risk/Reward</div>
          <div className="text-lg font-semibold text-gray-800">{tradeOption.riskReward}</div>
        </div>
      </div>

      <div className="bg-gray-50 p-3 rounded mb-4">
        <div className="text-xs font-semibold text-gray-600 uppercase mb-2">Strategy Details</div>
        <p className="text-sm text-gray-800 mb-2">{tradeOption.strategy}</p>
        <p className="text-xs text-gray-600">
          Stop-loss at ${tradeOption.stopLoss} • Take-profit at ${tradeOption.takeProfit}
        </p>
      </div>

      <div className="flex space-x-2">
        <button
          onClick={() => onSelect(tradeOption)}
          className="flex-1 bg-blue-600 text-white py-2 px-4 rounded font-medium hover:bg-blue-700 transition-colors"
        >
          Select
        </button>
        <button
          onClick={() => onViewDetails(tradeOption)}
          className="flex-1 border border-gray-300 text-gray-700 py-2 px-4 rounded font-medium hover:bg-gray-50 transition-colors"
        >
          View Details
        </button>
        <button
          onClick={() => onModify(tradeOption)}
          className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
        >
          Modify
        </button>
      </div>
    </div>
  );
};
