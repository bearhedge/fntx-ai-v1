
import React, { useState } from 'react';
import { Paperclip, Mic } from 'lucide-react';

interface EnhancedMessageInputProps {
  onSendMessage: (message: string) => void;
}

export const EnhancedMessageInput = ({
  onSendMessage
}: EnhancedMessageInputProps) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim()) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  return (
    <div className="bg-white">
      <div className="max-w-4xl mx-auto">
        <div className="p-6">
          <form onSubmit={handleSubmit}>
            <div className="flex items-center space-x-3 bg-gray-50 rounded-xl border border-gray-200 p-3">
              <button 
                type="button" 
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              
              <textarea 
                value={message} 
                onChange={e => setMessage(e.target.value)} 
                placeholder="Message..." 
                className="flex-1 bg-transparent resize-none border-0 focus:outline-none text-gray-800 placeholder-gray-400 min-h-[24px]" 
                rows={1} 
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }} 
              />
              
              <div className="flex items-center space-x-2 flex-shrink-0">
                <button 
                  type="button" 
                  className="p-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 transition-colors"
                >
                  <Mic className="w-4 h-4" />
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
