import React, { useState, useRef, useEffect } from 'react';
import { EnhancedMessage } from './EnhancedMessage';
import { EnhancedMessageInput } from './EnhancedMessageInput';
import { TradeStepper } from '../Trading/TradeStepper';
import { SPYOptionsTable } from '../Trading/SPYOptionsTable';
import { TradeConfigurationPanel } from '../Trading/TradeConfigurationPanel';
import { Message } from '../../types/trading';
import { Monitor, Maximize2, ChevronDown, Activity, Bot, Target, Settings } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { OrchestratorClient, TradeJourney } from '@/lib/orchestrator-client';

interface OrchestratedChatBotProps {
  chatId?: number;
  onShowContextPanel?: (show: boolean) => void;
  onToggleContextPanel?: () => void;
  showContextPanel?: boolean;
  isContextPanelExpanded?: boolean;
  onActivateChange?: (isActive: boolean) => void;
}

// Enhanced message type for orchestration and manual trading
interface OrchestrationMessage extends Message {
  tradeId?: string;
  isTradeOrchestration?: boolean;
  journeyData?: TradeJourney;
  isManualTrading?: boolean;
  showOptionsTable?: boolean;
  showTradeConfig?: boolean;
  selectedContract?: any;
  spyPrice?: number;
}

const initialMessage: OrchestrationMessage = {
  id: '1',
  content: 'Hello Jimmy Hou\nWhat can I do for you?',
  sender: 'ai' as const,
  timestamp: new Date(),
  type: 'text' as const
};

export const OrchestratedChatBot = ({
  chatId = 1,
  onShowContextPanel,
  onToggleContextPanel,
  showContextPanel = false,
  isContextPanelExpanded = false,
  onActivateChange
}: OrchestratedChatBotProps) => {
  const orchestratorClient = new OrchestratorClient();
  
  const getStoredMessages = (id: number): OrchestrationMessage[] => {
    try {
      const stored = localStorage.getItem(`chat_messages_${id}`);
      if (stored) {
        const parsedMessages = JSON.parse(stored);
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

  const [messages, setMessages] = useState<OrchestrationMessage[]>(() => getStoredMessages(chatId));
  const [isProcessing, setIsProcessing] = useState(false);
  const [isActive, setIsActive] = useState(false);
  const [activeTradeId, setActiveTradeId] = useState<string | null>(null);
  const [currentJourney, setCurrentJourney] = useState<TradeJourney | null>(null);
  const [selectedContract, setSelectedContract] = useState<any | null>(null);
  const [showTradeConfig, setShowTradeConfig] = useState(false);
  const [spyPrice, setSpyPrice] = useState<number>(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Check if message should trigger manual options discovery
  const isManualOptionsRequest = (message: string): boolean => {
    const messageLower = message.toLowerCase().trim();
    
    // Check for exact options-related phrases first
    const optionsKeywords = [
      'spy options', 'spy option', 'options chain', 'option chain', 'spy puts', 'spy calls', 
      'spy put options', 'spy call options', 'get spy options', 'show spy options', 
      'list spy options', 'spy contracts', 'options table', 'manual trade'
    ];
    
    // Return true if any options keyword is found
    return optionsKeywords.some(keyword => messageLower.includes(keyword));
  };

  // Check if message should trigger orchestration (now for strategy analysis only)
  const isTradeRequest = (message: string): boolean => {
    const messageLower = message.toLowerCase();
    
    // Exclude if it's already an options request
    if (isManualOptionsRequest(message)) {
      return false;
    }
    
    const tradeKeywords = [
      'strategy', 'market analysis', 'best strategy', 'trading strategy',
      'market conditions', 'what should i trade', 'find me a trade',
      'trading opportunity', 'analyze market', 'market insights'
    ];

    return tradeKeywords.some(keyword => messageLower.includes(keyword));
  };

  // Format journey for chat display
  const formatJourneyForChat = (journey: TradeJourney): string => {
    let message = `🚀 **Trade Journey: ${journey.trade_id}**\n\n`;
    message += `**Request:** ${journey.user_request}\n`;
    message += `**Phase:** ${journey.current_phase.replace('_', ' ').toUpperCase()}\n`;
    message += `**Risk Level:** ${journey.risk_assessment.overall_risk.toUpperCase()}\n`;
    message += `**Confidence:** ${(journey.risk_assessment.confidence_level * 100).toFixed(0)}%\n\n`;

    if (journey.steps.length > 0) {
      message += `**Agent Progress:**\n`;
      journey.steps.forEach((step, index) => {
        const statusEmoji = {
          pending: '⏳',
          running: '🔄',
          completed: '✅',
          error: '❌',
          skipped: '⏭️'
        }[step.status] || '📍';

        const agentName = step.agent.replace('Agent', '');
        message += `${statusEmoji} **${agentName}**: ${step.action}\n`;
        
        if (step.status === 'completed' && step.rationale) {
          message += `   💡 _${step.rationale.substring(0, 100)}${step.rationale.length > 100 ? '...' : ''}_\n`;
        }
        
        if (step.confidence_level > 0) {
          message += `   📊 Confidence: ${(step.confidence_level * 100).toFixed(0)}%\n`;
        }
      });
    }

    if (journey.final_outcome) {
      const outcomeEmoji = journey.final_outcome.success ? '🎉' : '😞';
      message += `\n${outcomeEmoji} **Final Result:** ${journey.final_outcome.message}\n`;
      message += `⏱️ **Total Time:** ${journey.execution_time.toFixed(1)}s\n`;
      
      if (journey.final_outcome.success) {
        message += `\n✨ **All ${journey.final_outcome.total_steps} agent steps completed successfully!**`;
      }
    } else if (journey.current_phase !== 'completed' && journey.current_phase !== 'failed') {
      message += `\n🔄 **Status:** Orchestration in progress... (${journey.steps.filter(s => s.status === 'completed').length}/${5} agents completed)`;
    }

    return message;
  };

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

  const updateMessage = (id: string, updates: Partial<OrchestrationMessage>) => {
    setMessages(prev => 
      prev.map(msg => msg.id === id ? { ...msg, ...updates } : msg)
    );
  };

  const addMessage = (message: Omit<OrchestrationMessage, 'id' | 'timestamp'>) => {
    const newMessage: OrchestrationMessage = {
      ...message,
      id: Date.now().toString(),
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, newMessage]);
    return newMessage.id;
  };

  async function sendMessageToBackend(message: string) {
    // Convert messages to format expected by backend
    const formattedMessages = messages.slice(-5).map(msg => ({
      role: msg.sender === 'user' ? 'user' : 'assistant',
      content: msg.content
    }));
    
    const res = await fetch(`/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message,
        messages: formattedMessages 
      }),
    });
    
    if (!res.ok) {
      throw new Error(`Chat API error: ${res.status}`);
    }
    
    const data = await res.json();
    return data.response;
  }

  const handleSendMessage = async (content: string) => {
    const userMessage: OrchestrationMessage = {
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

    const lowerContent = content.toLowerCase().trim();

    // Check if this should trigger manual options discovery
    if (isManualOptionsRequest(content)) {
      try {
        // Determine option type from message
        let optionType = 'both';
        if (lowerContent.includes('put')) optionType = 'put';
        if (lowerContent.includes('call')) optionType = 'call';

        // Add manual trading message with options table
        const manualMessageId = addMessage({
          content: `🎯 **SPY Options Discovery**\n\nSearching for ${optionType === 'both' ? 'PUT and CALL' : optionType.toUpperCase()} options...\n\nSelect a contract below to configure your manual trade with full AI analysis.`,
          sender: 'ai',
          isManualTrading: true,
          showOptionsTable: true,
        });

        // Fetch current SPY price for reference
        fetch(`http://localhost:8002/api/market/insights`)
          .then(response => response.json())
          .then(data => {
            setSpyPrice(data.spy_price || 0);
            updateMessage(manualMessageId, {
              spyPrice: data.spy_price || 0
            });
          })
          .catch(err => console.error('Failed to fetch SPY price:', err));

      } catch (error) {
        addMessage({
          content: `❌ **Failed to Load Options**\n\nUnable to fetch SPY options chain:\n\n${error instanceof Error ? error.message : 'Unknown error'}\n\nPlease check that the API server is running.`,
          sender: 'ai',
        });
      }
      
      setIsProcessing(false);
      return;
    }

    // Check if this should trigger trade orchestration (now for strategy analysis only)
    if (isTradeRequest(content)) {
      try {
        // Add initial orchestration message
        const orchestrationMessageId = addMessage({
          content: `🚀 **Starting Trade Orchestration**\n\nAnalyzing your request: "${content}"\n\nThe AI agents are now collaborating to find the best trading opportunity...`,
          sender: 'ai',
          isTradeOrchestration: true,
        });

        // Start orchestration
        const result = await orchestratorClient.startTradeOrchestration(content);
        setActiveTradeId(result.trade_id);

        // Update message with trade ID
        updateMessage(orchestrationMessageId, {
          content: `🚀 **Trade Orchestration Started**\n\n**Trade ID:** ${result.trade_id}\n**Status:** ${result.status}\n\nThe 5-agent AI system is now processing your request:\n\n⏳ EnvironmentWatcher: Analyzing market conditions...\n⏳ StrategicPlanner: Formulating optimal strategy...\n⏳ RewardModel: Optimizing for your preferences...\n⏳ Executor: Preparing trade execution...\n⏳ Evaluator: Setting up performance monitoring...\n\n🔄 **Live updates will appear below...**`,
          tradeId: result.trade_id,
        });

        // Start polling for updates
        orchestratorClient.pollTradeProgress(
          result.trade_id,
          // On update
          (journey) => {
            setCurrentJourney(journey);
            updateMessage(orchestrationMessageId, {
              content: formatJourneyForChat(journey),
              journeyData: journey,
            });
          },
          // On complete
          (journey) => {
            setActiveTradeId(null);
            setCurrentJourney(journey);
            updateMessage(orchestrationMessageId, {
              content: formatJourneyForChat(journey),
              journeyData: journey,
            });
            
            // Add final summary message
            const successEmoji = journey.final_outcome?.success ? '🎉' : '😞';
            const summaryMessage = journey.final_outcome?.success 
              ? `${successEmoji} **Orchestration Complete!**\n\n${journey.final_outcome.message}\n\nYour trade analysis is ready! Check the stepper above for detailed agent insights and execution steps.`
              : `${successEmoji} **Orchestration Failed**\n\n${journey.final_outcome?.message || 'The orchestration encountered an error.'}\n\nPlease try rephrasing your request or check the system status.`;
              
            addMessage({
              content: summaryMessage,
              sender: 'ai',
            });
          },
          // On error
          (error) => {
            setActiveTradeId(null);
            setCurrentJourney(null);
            addMessage({
              content: `❌ **Orchestration Error**\n\nSorry, there was an error processing your trade request:\n\n${error}\n\nPlease try again or contact support if the issue persists.`,
              sender: 'ai',
            });
          }
        );

      } catch (error) {
        addMessage({
          content: `❌ **Failed to Start Orchestration**\n\nUnable to start the trading agent system:\n\n${error instanceof Error ? error.message : 'Unknown error'}\n\nPlease check that the orchestration API is running on port 8000.`,
          sender: 'ai',
        });
      }
      
      setIsProcessing(false);
      return;
    }

    // Handle SPY options chain request (existing code)
    if (
      (lowerContent.includes("option chain") || lowerContent.includes("options chain")) &&
      lowerContent.includes("spy")
    ) {
      const loadingMsg: OrchestrationMessage = {
        id: (Date.now() + 1).toString(),
        content: "Fetching SPY options chain...",
        sender: 'ai',
        timestamp: new Date(),
        type: 'text'
      };
      setMessages(prev => [...prev, loadingMsg]);

      try {
        const aiReply = await sendMessageToBackend(content);
        const aiResponse: OrchestrationMessage = {
          id: (Date.now() + 2).toString(),
          content: aiReply,
          sender: 'ai',
          timestamp: new Date(),
          type: 'text'
        };
        setMessages(prev => [...prev, aiResponse]);
      } catch (error) {
        const aiResponse: OrchestrationMessage = {
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

    // Handle activate/inactivate commands (existing code)
    if (lowerContent === 'activate') {
      setIsActive(true);
      setTimeout(() => {
        const aiResponse: OrchestrationMessage = {
          id: (Date.now() + 1).toString(),
          content: '🔴 **FNTX Computer Activated**\n\nAll trading agents are now online and ready to process your requests.\n\nTry asking: "What\'s the best SPY trade today?" to see the full orchestration in action!',
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
        const aiResponse: OrchestrationMessage = {
          id: (Date.now() + 1).toString(),
          content: '⚫ **FNTX Computer Deactivated**\n\nTrading agents are now offline. Waiting for activation.',
          sender: 'ai',
          timestamp: new Date(),
          type: 'text'
        };
        setMessages(prev => [...prev, aiResponse]);
        setIsProcessing(false);
      }, 1000);
      return;
    }

    // Route to regular chat API for all other messages
    try {
      const aiReply = await sendMessageToBackend(content);
      const aiResponse: OrchestrationMessage = {
        id: (Date.now() + 1).toString(),
        content: aiReply,
        sender: 'ai',
        timestamp: new Date(),
        type: 'text'
      };
      setMessages(prev => [...prev, aiResponse]);
    } catch (error) {
      const aiResponse: OrchestrationMessage = {
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

  // Handle contract selection from options table
  const handleContractSelect = (contract: any) => {
    setSelectedContract(contract);
    setShowTradeConfig(true);

    // Add trade configuration message
    addMessage({
      content: `⚙️ **Trade Configuration**\n\n**Selected Contract:** ${contract.symbol}\n**Strike:** $${contract.strike}\n**Last Price:** $${contract.last.toFixed(2)}\n**AI Score:** ${contract.ai_score?.toFixed(1)}/10\n\nConfigure your trade parameters, risk management, and review AI analysis below.`,
      sender: 'ai',
      isManualTrading: true,
      showTradeConfig: true,
      selectedContract: contract,
      spyPrice: spyPrice
    });
  };

  // Handle trade execution
  const handleExecuteTrade = async (analysis: any) => {
    try {
      setIsProcessing(true);
      
      // Execute the trade
      const response = await fetch(`http://localhost:8002/api/trade/manual-execute/${analysis.trade_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to execute trade: ${response.statusText}`);
      }

      const result = await response.json();

      // Add execution result message
      addMessage({
        content: `✅ **Trade Executed Successfully!**\n\n**Trade ID:** ${result.trade_id}\n**Order ID:** ${result.order_id}\n**Status:** ${result.status}\n\n**Next Steps:**\n${result.next_steps?.map((step: string) => `• ${step}`).join('\n') || '• Monitor position until expiration'}\n\n**Position Details:**\n• Contract: ${analysis.config.contract_symbol}\n• Quantity: ${analysis.config.quantity} contract(s)\n• Entry Price: $${analysis.config.entry_price.toFixed(2)}\n• Stop Loss: $${(analysis.config.entry_price * analysis.config.stop_loss_multiplier).toFixed(2)}\n• Take Profit: $${(analysis.config.entry_price * analysis.config.take_profit_percentage).toFixed(2)}\n\n🎯 **Risk Management Active:** Your position is now being monitored with automatic stop-loss and take-profit orders.`,
        sender: 'ai',
      });

      // Reset manual trading state
      setSelectedContract(null);
      setShowTradeConfig(false);

    } catch (error) {
      addMessage({
        content: `❌ **Trade Execution Failed**\n\nUnable to execute the trade:\n\n${error instanceof Error ? error.message : 'Unknown error'}\n\nPlease try again or contact support if the issue persists.`,
        sender: 'ai',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle trade configuration cancel
  const handleCancelTradeConfig = () => {
    setSelectedContract(null);
    setShowTradeConfig(false);
    
    addMessage({
      content: `🚫 **Trade Configuration Cancelled**\n\nYou can select another contract from the options table above or start a new search.`,
      sender: 'ai',
    });
  };

  return (
    <div className="h-screen flex flex-col bg-white relative">
      {/* Main chat area with fixed height and scroll */}
      <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full min-h-0">
        <div className="flex-1 overflow-y-auto p-4 pb-4">
          {messages.length === 1 ? (
            // Welcome state
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
                <h1 className="text-4xl font-medium text-gray-800 mb-4">Hello Jimmy Hou</h1>
                <p className="text-xl text-gray-500 mb-8">
                  What can I do for you?
                </p>
                
                {/* Enhanced suggestion buttons for manual trading and orchestration */}
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
              {messages.map((message, index) => {
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
                    
                    {/* Show trade stepper for orchestration messages */}
                    {message.isTradeOrchestration && message.journeyData && (
                      <div className="mt-4 ml-0">
                        <Card>
                          <CardHeader>
                            <CardTitle className="text-sm flex items-center gap-2">
                              <Activity className="w-4 h-4" />
                              Live Agent Orchestration
                            </CardTitle>
                          </CardHeader>
                          <CardContent className="p-0">
                            <TradeStepper 
                              journeyData={message.journeyData}
                              onRefresh={() => {/* Refresh handled by polling */}}
                              className="border-0 shadow-none"
                            />
                          </CardContent>
                        </Card>
                      </div>
                    )}

                    {/* Show SPY Options Table for manual trading */}
                    {message.isManualTrading && message.showOptionsTable && (
                      <div className="mt-4 ml-0">
                        <SPYOptionsTable 
                          onContractSelect={handleContractSelect}
                          optionType="both" // Could be dynamic based on message
                          className="border-0 shadow-sm"
                        />
                      </div>
                    )}

                    {/* Show Trade Configuration Panel */}
                    {message.isManualTrading && message.showTradeConfig && message.selectedContract && (
                      <div className="mt-4 ml-0">
                        <TradeConfigurationPanel
                          contract={message.selectedContract}
                          spyPrice={message.spyPrice || spyPrice}
                          onExecuteTrade={handleExecuteTrade}
                          onCancel={handleCancelTradeConfig}
                          className="border-0 shadow-sm"
                        />
                      </div>
                    )}
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
            {activeTradeId && <Activity className="w-4 h-4 animate-pulse text-blue-500" />}
            <Maximize2 className="w-4 h-4" />
          </div>
          {(isProcessing || activeTradeId) && (
            <div className="mt-2 text-xs text-gray-500 text-center">
              {activeTradeId ? `Orchestrating: ${activeTradeId}` : 'Processing...'}
            </div>
          )}
        </div>
      )}
    </div>
  );
};