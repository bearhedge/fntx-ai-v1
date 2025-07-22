import React from 'react';
import { Settings, User } from 'lucide-react';

export const Header = () => {
  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shadow-sm">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <svg width="120" height="65" viewBox="0 0 640 347" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-black-1500">
            <path d="M205.848 115.154H282.121V141.048H256.978V253.159H230.334V141.048H205.848V115.154Z" fill="#02001E"/>
            <path d="M85.0049 115.154H110.148L169.346 205.969V115.154H195.615V253.159H170.378L111.274 162.626V253.159H85.0049V115.154Z" fill="#02001E"/>
            <path d="M0.656494 115.154H69.1427V140.766H26.6437V165.815H69.1427V191.052H26.6437V253.159H0.656494V115.154Z" fill="#02001E"/>
            <path d="M232.712 141.035V115.175H314.998L356.238 167.605C356.238 167.605 441.088 55.0648 639.478 0.53479C639.478 0.53479 477.868 51.5648 352.048 212.345C338.068 194.175 292.628 141.045 292.628 141.045H270.057H259.972H232.712V141.035Z" fill="#02001E"/>
            <path d="M319.538 189.975L341.558 216.885L212.938 346.555L319.538 189.975Z" fill="#707070"/>
            <path d="M361.838 215.715L403.078 263.365H445.718L384.198 186.475L361.838 215.715Z" fill="#707070"/>
          </svg>
          <h1 className="text-xl font-semibold text-gray-800"></h1>
        </div>
      </div>

      <div className="flex items-center space-x-6">
        <div className="text-sm text-gray-600">
          <span className="font-medium">SPY:</span> $452.75 
          <span className="ml-4 font-medium">VIX:</span> 16.42
        </div>
        <button className="p-2 text-gray-600 hover:text-gray-800 transition-colors">
          <Settings className="w-5 h-5" />
        </button>
        <button className="p-2 text-gray-600 hover:text-gray-800 transition-colors">
          <User className="w-5 h-5" />
        </button>
      </div>
    </header>
  );
};
