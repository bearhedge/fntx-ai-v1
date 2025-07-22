
import React, { useState, useRef, useEffect } from 'react';
import { EnhancedMessage } from './EnhancedMessage';
import { EnhancedMessageInput } from './EnhancedMessageInput';
import { Message } from '../../types/trading';
import { Monitor, Maximize2, ChevronDown } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { OrchestratorClient } from '@/lib/orchestrator-client';
import { useTradeUpdates } from '@/hooks/useWebSocket';

interface EnhancedChatBotProps {
  chatId?: number;
  onShowContextPanel?: (show: boolean) => void;
  onToggleContextPanel?: () => void;
  showContextPanel?: boolean;
  isContextPanelExpanded?: boolean;
  onActivateChange?: (isActive: boolean) => void;
  onTradeIdChange?: (tradeId: string | null) => void;
}

// Store messages for each chat using React state management
const initialMessage = {
  id: '1',
  content: 'Hello Jimmy Hou\nWhat can I do for you?',
  sender: 'ai' as const,
  timestamp: new Date(),
  type: 'text' as const
};

function formatOptionsTable(table: any[]) {
  if (!table || table.length === 0) {
    return "No options data available for the nearest expiry.";
  }
  const headers = ["strike", "right", "bid", "ask", "last", "volume", "openInterest"];
  let html = "<table border='1' style='font-size:12px;'><tr>";
  headers.forEach((h) => (html += `<th>${h}</th>`));
  html += "</tr>";
  table.forEach((row) => {
    html += "<tr>";
    headers.forEach((h) => (html += `<td>${row[h] ?? ""}</td>`));
    html += "</tr>";
  });
  html += "</table>";
  return html;
}

export const EnhancedChatBot = ({
  chatId = 1,
  onShowContextPanel,
  onToggleContextPanel,
  showContextPanel = false,
  isContextPanelExpanded = false,
  onActivateChange,
  onTradeIdChange
}: EnhancedChatBotProps) => {
  // Store messages per chat ID in localStorage to persist across component unmounts
  const getStoredMessages = (id: number): Message[] => {
    try {
      const stored = localStorage.getItem(`chat_messages_${id}`);
      if (stored) {
        const parsedMessages = JSON.parse(stored);
        // Convert timestamp strings back to Date objects
        return parsedMessages.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }));
      }
      return [{ ...initialMessage, timestamp: new Date(initialMessage.timestamp) }];
    } catch {
      return [initialMessage];
    }
  };

  const [messages, setMessages] = useState<Message[]>(() => getStoredMessages(chatId));
  const [isProcessing, setIsProcessing] = useState(false);
  const [isActive, setIsActive] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [activeTradeId, setActiveTradeId] = useState<string | null>(null);
  const orchestratorClient = new OrchestratorClient();
  const { lastMessage } = useTradeUpdates(activeTradeId);

  // Update messages when chatId changes
  useEffect(() => {
    const chatMessages = getStoredMessages(chatId);
    setMessages(chatMessages);
  }, [chatId]);

  // Store messages in localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(`chat_messages_${chatId}`, JSON.stringify(messages));
  }, [messages, chatId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth'
    });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    onActivateChange?.(isActive);
  }, [isActive, onActivateChange]);

  useEffect(() => {
    onTradeIdChange?.(activeTradeId);
  }, [activeTradeId, onTradeIdChange]);

  // Handle WebSocket messages for real-time updates
  useEffect(() => {
    if (lastMessage && activeTradeId) {
      const updateMessage = (msg: string) => {
        const updateMsg: Message = {
          id: Date.now().toString(),
          content: msg,
          sender: 'ai',
          timestamp: new Date(),
          type: 'text'
        };
        setMessages(prev => [...prev, updateMsg]);
      };

      switch (lastMessage.type) {
        case 'orchestration_start':
          updateMessage(`🚀 ${lastMessage.message}`);
          break;
        case 'computation_step':
          updateMessage(`${lastMessage.message}`);
          break;
        case 'orchestration_complete':
          updateMessage(`✅ ${lastMessage.message}`);
          setIsActive(false);
          break;
        case 'orchestration_failed':
        case 'orchestration_error':
          updateMessage(`❌ ${lastMessage.message}`);
          setIsActive(false);
          break;
      }
    }
  }, [lastMessage, activeTradeId]);

  async function sendMessageToBackend(message: string) {
  const res = await fetch(`/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, messages: [] }),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  }
  const data = await res.json();
  return data.response; // Changed from data.reply to data.response
}

const handleSendMessage = async (content: string) => {
  const userMessage: Message = {
    id: Date.now().toString(),
    content,
    sender: 'user',
    timestamp: new Date(),
    type: 'text'
  };

  const newMessages = [...messages, userMessage];
  setMessages(newMessages);

  // Show context panel for ALL messages
  onShowContextPanel?.(true);
  setIsProcessing(true);

  // --- INTENT DETECTION: Check for trading orchestration request ---
  const lowerContent = content.toLowerCase().trim();
  
  // Check if this should trigger trade orchestration
  if (orchestratorClient.isTradeRequest(content)) {
    setIsActive(true);
    
    // Add initial orchestration message
    const orchestrationMsg: Message = {
      id: (Date.now() + 1).toString(),
      content: `🚀 Starting trade orchestration for: "${content}"`,
      sender: 'ai',
      timestamp: new Date(),
      type: 'text'
    };
    setMessages(prev => [...prev, orchestrationMsg]);
    
    try {
      // Start orchestration
      const result = await orchestratorClient.startTradeOrchestration(content);
      setActiveTradeId(result.trade_id);
      
      // Update initial message with trade ID
      const tradeStartMsg: Message = {
        id: (Date.now() + 2).toString(),
        content: `🚀 **Trade Orchestration Started**\n\nTrade ID: ${result.trade_id}\nStatus: ${result.status}\n\nThe AI agents are now analyzing your request...`,
        sender: 'ai',
        timestamp: new Date(),
        type: 'text'
      };
      setMessages(prev => [...prev, tradeStartMsg]);
      
    } catch (error) {
      const errorMsg: Message = {
        id: (Date.now() + 2).toString(),
        content: `❌ **Orchestration Error**: ${error instanceof Error ? error.message : 'Unknown error'}`,
        sender: 'ai',
        timestamp: new Date(),
        type: 'text'
      };
      setMessages(prev => [...prev, errorMsg]);
      setIsActive(false);
    }
    
    setIsProcessing(false);
    return;
  }
  
  // Check for SPY options chain request
  if (
    (lowerContent.includes("option chain") || lowerContent.includes("options chain")) &&
    lowerContent.includes("spy")
  ) {
    // Add loading message
    const loadingMsg: Message = {
      id: (Date.now() + 1).toString(),
      content: "Fetching SPY options chain...",
      sender: 'ai',
      timestamp: new Date(),
      type: 'text'
    };
    setMessages(prev => [...prev, loadingMsg]);

    // Call backend via chat API for clean Markdown table
    try {
      const aiReply = await sendMessageToBackend(content);
      const aiResponse: Message = {
        id: (Date.now() + 2).toString(),
        content: aiReply,
        sender: 'ai',
        timestamp: new Date(),
        type: 'text'
      };
      setMessages(prev => [...prev, aiResponse]);
    } catch (error) {
      const aiResponse: Message = {
        id: (Date.now() + 2).toString(),
        content: "Error fetching SPY options chain.",
        sender: 'ai',
        timestamp: new Date(),
        type: 'text'
      };
      setMessages(prev => [...prev, aiResponse]);
    }
    setIsProcessing(false);
    return;
  }

  // --- If not an options chain request, continue as normal ---
  // Check for activate/inactivate commands
  if (lowerContent === 'activate') {
    setIsActive(true);
    setTimeout(() => {
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: 'FNTX Computer is now active. Beginning task processing...',
        sender: 'ai',
        timestamp: new Date(),
        type: 'text'
      };
      setMessages(prev => [...prev, aiResponse]);
      setIsProcessing(false);
    }, 2000);
    return;
  }

  if (lowerContent === 'inactivate') {
    setIsActive(false);
    setTimeout(() => {
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: 'FNTX Computer is now inactive. Waiting for instructions.',
        sender: 'ai',
        timestamp: new Date(),
        type: 'text'
      };
      setMessages(prev => [...prev, aiResponse]);
      setIsProcessing(false);
    }, 1000);
    return;
  }

  // Route to Gemini API via backend for all other messages
  try {
    const aiReply = await sendMessageToBackend(content);
    const aiResponse: Message = {
      id: (Date.now() + 1).toString(),
      content: aiReply,
      sender: 'ai',
      timestamp: new Date(),
      type: 'text'
    };
    setMessages(prev => [...prev, aiResponse]);
  } catch (error) {
    const aiResponse: Message = {
      id: (Date.now() + 1).toString(),
      content: "Sorry, I couldn't reach the AI service.",
      sender: 'ai',
      timestamp: new Date(),
      type: 'text'
    };
    setMessages(prev => [...prev, aiResponse]);
  }
  setIsProcessing(false);
};

  return (
    <div className="h-screen flex flex-col bg-white relative">
      {/* Main chat area with fixed height and scroll */}
      <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full min-h-0">
        <div className="flex-1 overflow-y-auto p-4 pb-4">
          {messages.length === 1 ? (
            // Welcome state - with FNTX logo positioned to the left
            <div className="h-full flex flex-col justify-center">
              {/* FNTX logo positioned to the left */}
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
              
              {/* Welcome text aligned to the left */}
              <div className="text-left">
                <h1 className="text-4xl font-medium text-gray-800 mb-4">Hello Jimmy Hou</h1>
                <p className="text-xl text-gray-500 mb-8">
                  What can I do for you?
                </p>
                
                {/* Suggestion buttons */}
                <div className="flex flex-wrap gap-3 max-w-2xl">
                  <button className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm text-gray-700 transition-colors">Option 1 ↗</button>
                  <button className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm text-gray-700 transition-colors">Option 2 ↗</button>
                  <button className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm text-gray-700 transition-colors">Option 3 ↗</button>
                </div>
              </div>
            </div>
          ) : (
            // Messages view - all messages and logos aligned to the far left
            <div className="space-y-6">
              {messages.map((message, index) => {
                // Show FNTX logo above every AI message, aligned to the far left
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

      {/* Context Panel Collapsed State */}
      {showContextPanel && !isContextPanelExpanded && (
        <div className="absolute bottom-24 right-8 z-10">
          <div 
            onClick={onToggleContextPanel} 
            className="text-black rounded-lg flex items-center space-x-3 cursor-pointer transition-colors shadow-lg bg-gray-200 py-[12px] px-[20px] mx-0 my-0 hover:bg-gray-300"
          >
            <Monitor className="w-4 h-4" />
            <span className="text-sm font-light">FNTX's Computer</span>
            <Maximize2 className="w-4 h-4" />
          </div>
          {isProcessing && (
            <div className="mt-2 text-xs text-gray-500 text-center">
              Processing...
            </div>
          )}
        </div>
      )}
    </div>
  );
};
