import React from 'react';
import { Button } from '@/components/ui/button';

interface LandingPageProps {
  onSignIn: () => void;
  onSignUp: () => void;
  onDemoSignIn?: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onSignIn, onSignUp, onDemoSignIn }) => {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Top-right auth buttons */}
      <div className="absolute top-6 right-6 flex items-center space-x-3">
        <Button
          onClick={onSignIn}
          variant="default"
          className="bg-black text-white hover:bg-gray-800 px-6 py-2 rounded-lg"
        >
          Sign in
        </Button>
        <Button
          onClick={onSignUp}
          variant="outline"
          className="border-gray-300 text-gray-700 hover:bg-gray-50 px-6 py-2 rounded-lg"
        >
          Sign up
        </Button>
      </div>

      {/* Main content - centered */}
      <div className="flex-1 flex flex-col items-center justify-center px-8">
        <div className="max-w-md w-full text-left space-y-8">
          {/* FNTX Logo */}
          <div className="space-y-2">
            <div className="text-4xl font-bold text-gray-900">
              FNTX
            </div>
          </div>

          {/* Greeting */}
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold text-gray-900">Hello</h1>
            <p className="text-lg text-gray-600">What can I do for you?</p>
          </div>

          {/* Options */}
          <div className="space-y-3">
            <Button
              variant="outline"
              className="w-full justify-start text-left bg-gray-50 hover:bg-gray-100 border-gray-200 py-3"
            >
              <span className="flex-1">Option 1</span>
              <span className="text-gray-400">↗</span>
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start text-left bg-gray-50 hover:bg-gray-100 border-gray-200 py-3"
            >
              <span className="flex-1">Option 2</span>
              <span className="text-gray-400">↗</span>
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start text-left bg-gray-50 hover:bg-gray-100 border-gray-200 py-3"
            >
              <span className="flex-1">Option 3</span>
              <span className="text-gray-400">↗</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Bottom input area */}
      <div className="flex justify-center pb-8">
        <div className="w-full max-w-2xl px-8">
          <div className="relative">
            <input
              type="text"
              placeholder="Message..."
              disabled
              className="w-full px-4 py-3 pr-12 border border-gray-200 rounded-lg bg-gray-50 text-gray-500 cursor-not-allowed"
            />
            <button
              disabled
              className="absolute right-3 top-1/2 transform -translate-y-1/2 w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center cursor-not-allowed"
            >
              🎤
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};