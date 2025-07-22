import { TradesList } from "../components/TradesList";
import React from 'react';
import { AppLayout } from '../components/Layout/AppLayout';

const Index = () => {
  return (
    <AppLayout>
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center max-w-2xl">
          <h1 className="text-3xl font-bold text-gray-800 mb-4">Welcome to Trading Assistant</h1>
          <p className="text-lg text-gray-600 mb-8">
            Your AI-powered trading companion is ready to help optimize your strategies. 
            Start a conversation to get personalized recommendations and market insights.
          </p>
          <div className="bg-white rounded-lg p-6 shadow-lg border border-gray-200">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">Getting Started</h2>
            <div className="space-y-3 text-left">
              <TradesList />
              <div className="flex items-center space-x-3">
                <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                <span className="text-gray-700">Ask about current market conditions</span>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                <span className="text-gray-700">Request trade recommendations</span>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                <span className="text-gray-700">View your portfolio status</span>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                <span className="text-gray-700">Type "show status" to toggle the context panel</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

export default Index;
