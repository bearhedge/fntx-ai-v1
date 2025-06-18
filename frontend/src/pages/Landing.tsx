import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { EnhancedMessage } from '@/components/Chat/EnhancedMessage';
import { EnhancedMessageInput } from '@/components/Chat/EnhancedMessageInput';
import { Button } from '@/components/ui/button';
import { Message } from '@/types/trading';
import { Target, Settings, Monitor, Bot } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

const Landing = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth'
    });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Redirect authenticated users to their personal page
  useEffect(() => {
    if (isAuthenticated && user?.email) {
      const username = user.email.split('@')[0].toLowerCase();
      navigate(`/${username}`);
    }
  }, [isAuthenticated, user, navigate]);

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      sender: 'user',
      timestamp: new Date(),
      type: 'text'
    };

    setMessages(prev => [...prev, userMessage]);
    setIsProcessing(true);

    // Send to guest chat endpoint
    try {
      const response = await fetch('/api/orchestrator/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content }),
      });
      
      const data = await response.json();
      
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: data.response || "I'm here to help! Please sign in to access full trading capabilities.",
        sender: 'ai',
        timestamp: new Date(),
        type: 'text'
      };
      
      setMessages(prev => [...prev, aiResponse]);
    } catch (error) {
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: "Please sign in to access trading features and personalized assistance.",
        sender: 'ai',
        timestamp: new Date(),
        type: 'text'
      };
      setMessages(prev => [...prev, aiResponse]);
    }
    
    setIsProcessing(false);
  };

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Top-right auth buttons */}
      <div className="absolute top-6 right-6 flex items-center space-x-3 z-10">
        <Button
          onClick={() => navigate('/signin')}
          variant="default"
          className="bg-black text-white hover:bg-gray-800 px-6 py-2 rounded-lg"
        >
          Sign-in
        </Button>
        <Button
          onClick={() => navigate('/signup')}
          variant="outline"
          className="border-gray-300 text-gray-700 hover:bg-gray-50 px-6 py-2 rounded-lg"
        >
          Sign-up
        </Button>
      </div>

      {/* Main chat area - exactly like OrchestratedChatBot */}
      <div className="h-screen flex flex-col bg-white">
        <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full min-h-0">
          <div className="flex-1 overflow-y-auto p-4 pb-4">
            {messages.length === 0 ? (
              // Welcome state - same as OrchestratedChatBot
              <div className="h-full flex flex-col justify-center">
                <div className="flex justify-start mb-4">
                  <svg width="100" height="54" viewBox="0 0 640 347" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M205.848 115.154H282.121V141.048H256.978V253.159H230.334V141.048H205.848V115.154Z" fill="#374151" />
                    <path d="M85.0049 115.154H110.148L169.346 205.969V115.154H195.615V253.159H170.378L111.274 162.626V253.159H85.0049V115.154Z" fill="#374151" />
                    <path d="M0.656494 115.154H69.1427V140.766H26.6437V165.815H69.1427V191.052H26.6437V253.159H0.656494V115.154Z" fill="#374151" />
                    <path d="M232.712 141.035V115.175H314.998L356.238 167.605C356.238 167.605 441.088 55.0648 639.478 0.53479C639.478 0.53479 477.868 51.5648 352.048 212.345C338.068 194.175 292.628 141.045 292.628 141.045H270.057H259.972H232.712V141.035Z" fill="#374151" />
                    <path d="M319.538 189.975L341.558 216.885L212.938 346.555L319.538 189.975Z" fill="#9CA3AF" />
                    <path d="M361.838 215.715L403.078 263.365H445.718L384.198 186.475L361.838 215.715Z" fill="#9CA3AF" />
                  </svg>
                </div>
                
                <div className="text-left">
                  <h1 className="text-4xl font-medium text-gray-800 mb-4">Hello Guest</h1>
                  <p className="text-xl text-gray-500 mb-8">
                    What can I do for you?
                  </p>
                  
                  {/* Suggestion buttons */}
                  <div className="flex flex-wrap gap-3 max-w-2xl">
                    <button 
                      onClick={() => handleSendMessage("show spy put options")}
                      className="px-4 py-2 bg-green-100 hover:bg-green-200 rounded-lg text-sm text-green-700 transition-colors flex items-center gap-2"
                    >
                      <Target className="w-4 h-4" />
                      SPY PUT Options ↗
                    </button>
                    <button 
                      onClick={() => handleSendMessage("show spy options")}
                      className="px-4 py-2 bg-blue-100 hover:bg-blue-200 rounded-lg text-sm text-blue-700 transition-colors flex items-center gap-2"
                    >
                      <Settings className="w-4 h-4" />
                      Manual Trading ↗
                    </button>
                    <button 
                      onClick={() => handleSendMessage("analyze market conditions")}
                      className="px-4 py-2 bg-purple-100 hover:bg-purple-200 rounded-lg text-sm text-purple-700 transition-colors flex items-center gap-2"
                    >
                      <Monitor className="w-4 h-4" />
                      Market Analysis ↗
                    </button>
                    <button 
                      onClick={() => handleSendMessage("what's the best trading strategy today")}
                      className="px-4 py-2 bg-orange-100 hover:bg-orange-200 rounded-lg text-sm text-orange-700 transition-colors flex items-center gap-2"
                    >
                      <Bot className="w-4 h-4" />
                      AI Strategy ↗
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              // Messages view
              <div className="space-y-6">
                {messages.map((message) => {
                  const showLogo = message.sender === 'ai';
                  return (
                    <div key={message.id}>
                      {showLogo && (
                        <div className="flex justify-start mb-4">
                          <svg width="100" height="54" viewBox="0 0 640 347" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M205.848 115.154H282.121V141.048H256.978V253.159H230.334V141.048H205.848V115.154Z" fill="#374151" />
                            <path d="M85.0049 115.154H110.148L169.346 205.969V115.154H195.615V253.159H170.378L111.274 162.626V253.159H85.0049V115.154Z" fill="#374151" />
                            <path d="M0.656494 115.154H69.1427V140.766H26.6437V165.815H69.1427V191.052H26.6437V253.159H0.656494V115.154Z" fill="#374151" />
                            <path d="M232.712 141.035V115.175H314.998L356.238 167.605C356.238 167.605 441.088 55.0648 639.478 0.53479C639.478 0.53479 477.868 51.5648 352.048 212.345C338.068 194.175 292.628 141.045 292.628 141.045H270.057H259.972H232.712V141.035Z" fill="#374151" />
                            <path d="M319.538 189.975L341.558 216.885L212.938 346.555L319.538 189.975Z" fill="#9CA3AF" />
                            <path d="M361.838 215.715L403.078 263.365H445.718L384.198 186.475L361.838 215.715Z" fill="#9CA3AF" />
                          </svg>
                        </div>
                      )}
                      <EnhancedMessage message={message} />
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
          
          {/* Message input fixed at the bottom */}
          <div className="flex-shrink-0">
            <EnhancedMessageInput onSendMessage={handleSendMessage} />
          </div>
        </div>
      </div>

    </div>
  );
};

export default Landing;