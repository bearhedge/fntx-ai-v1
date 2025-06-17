// Enhanced chat hook that integrates with the orchestration system
import { useState, useCallback } from 'react';
import { OrchestratorClient, TradeJourney } from '@/lib/orchestrator-client';
import { useTradeUpdates } from './useWebSocket';

export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: Date;
  tradeId?: string;
  isTradeOrchestration?: boolean;
  journeyData?: TradeJourney;
}

export const useOrchestratedChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTradeId, setActiveTradeId] = useState<string | null>(null);
  
  const orchestratorClient = new OrchestratorClient();
  const { messages: wsMessages, lastMessage } = useTradeUpdates(activeTradeId);

  const addMessage = useCallback((message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: Date.now().toString(),
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, newMessage]);
    return newMessage.id;
  }, []);

  const updateMessage = useCallback((id: string, updates: Partial<ChatMessage>) => {
    setMessages(prev => 
      prev.map(msg => msg.id === id ? { ...msg, ...updates } : msg)
    );
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    // Add user message
    const userMessageId = addMessage({
      content,
      role: 'user',
    });

    setIsLoading(true);

    try {
      // Check if this should trigger trade orchestration
      if (orchestratorClient.isTradeRequest(content)) {
        // Add initial orchestration message
        const orchestrationMessageId = addMessage({
          content: `🚀 Starting trade orchestration for: "${content}"`,
          role: 'assistant',
          isTradeOrchestration: true,
        });

        // Start orchestration
        const result = await orchestratorClient.startTradeOrchestration(content);
        setActiveTradeId(result.trade_id);

        // Update message with trade ID
        updateMessage(orchestrationMessageId, {
          content: `🚀 **Trade Orchestration Started**\n\nTrade ID: ${result.trade_id}\nStatus: ${result.status}\n\nThe AI agents are now analyzing your request...`,
          tradeId: result.trade_id,
        });

        // Start polling for updates
        orchestratorClient.pollTradeProgress(
          result.trade_id,
          // On update
          (journey) => {
            updateMessage(orchestrationMessageId, {
              content: orchestratorClient.formatJourneyForChat(journey),
              journeyData: journey,
            });
          },
          // On complete
          (journey) => {
            setActiveTradeId(null);
            updateMessage(orchestrationMessageId, {
              content: orchestratorClient.formatJourneyForChat(journey),
              journeyData: journey,
            });
            
            // Add final summary message
            const successEmoji = journey.final_outcome?.success ? '🎉' : '😞';
            addMessage({
              content: `${successEmoji} **Trade Orchestration Complete**\n\n${journey.final_outcome?.message || 'Orchestration finished.'}`,
              role: 'assistant',
            });
          },
          // On error
          (error) => {
            setActiveTradeId(null);
            addMessage({
              content: `❌ **Orchestration Error**: ${error}`,
              role: 'assistant',
            });
          }
        );

      } else {
        // Regular chat message - send to your existing chat API
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8002';
        const response = await fetch(`${apiUrl}/api/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: content,
            messages: messages.slice(-5), // Send last 5 messages for context
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to send message');
        }

        const data = await response.json();
        
        addMessage({
          content: data.response,
          role: 'assistant',
        });
      }

    } catch (error) {
      console.error('Chat error:', error);
      addMessage({
        content: `❌ Sorry, there was an error processing your message: ${error instanceof Error ? error.message : 'Unknown error'}`,
        role: 'assistant',
      });
    } finally {
      setIsLoading(false);
    }
  }, [messages, addMessage, updateMessage, orchestratorClient]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setActiveTradeId(null);
  }, []);

  return {
    messages,
    isLoading,
    activeTradeId,
    sendMessage,
    clearChat,
    addMessage,
  };
};