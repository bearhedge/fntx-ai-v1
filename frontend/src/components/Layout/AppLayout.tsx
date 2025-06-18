
import React, { useState, useCallback } from 'react';
import { Sidebar } from './Sidebar';
import { OrchestratedChatBot } from '../Chat/OrchestratedChatBot';
import { ContextPanel } from './ContextPanel';

interface AppLayoutProps {
  children: React.ReactNode;
}

interface ChatContextState {
  showContextPanel: boolean;
  isContextPanelExpanded: boolean;
  isActive: boolean;
}

export const AppLayout = ({ children }: AppLayoutProps) => {
  const [activeChatId, setActiveChatId] = useState<string>('default');
  const [chatContextStates, setChatContextStates] = useState<Record<string, ChatContextState>>({});
  const [activeTradeId, setActiveTradeId] = useState<string | null>(null);
  
  // Get current chat context or initialize with defaults
  const getCurrentChatContext = useCallback((chatId: string): ChatContextState => {
    return chatContextStates[chatId] || {
      showContextPanel: false,
      isContextPanelExpanded: false,
      isActive: false
    };
  }, [chatContextStates]);

  const currentChatContext = getCurrentChatContext(activeChatId);

  // Update specific chat context
  const updateChatContext = useCallback((chatId: string, updates: Partial<ChatContextState>) => {
    setChatContextStates(prev => ({
      ...prev,
      [chatId]: {
        ...getCurrentChatContext(chatId),
        ...updates
      }
    }));
  }, [getCurrentChatContext]);

  const setShowContextPanel = useCallback((show: boolean) => {
    updateChatContext(activeChatId, { showContextPanel: show });
  }, [activeChatId, updateChatContext]);

  const setIsContextPanelExpanded = useCallback((expanded: boolean) => {
    updateChatContext(activeChatId, { isContextPanelExpanded: expanded });
  }, [activeChatId, updateChatContext]);

  const setIsActive = useCallback((active: boolean) => {
    updateChatContext(activeChatId, { isActive: active });
  }, [activeChatId, updateChatContext]);

  const toggleContextPanel = useCallback(() => {
    setIsContextPanelExpanded(!currentChatContext.isContextPanelExpanded);
  }, [currentChatContext.isContextPanelExpanded, setIsContextPanelExpanded]);

  const handleChatChange = useCallback((chatId: string) => {
    setActiveChatId(chatId);
  }, []);

  return (
    <div className="h-screen bg-white flex w-full overflow-hidden">
      <Sidebar onChatChange={handleChatChange} />
      <div className="flex-1 flex min-w-0">
        {/* Main chat area */}
        <div className={`flex-1 ${currentChatContext.isContextPanelExpanded ? 'max-w-[60%]' : 'w-full'} transition-all duration-300 min-w-0`}>
          <main className="h-full min-w-0">
            <OrchestratedChatBot 
              chatId={activeChatId}
              onShowContextPanel={setShowContextPanel} 
              onToggleContextPanel={toggleContextPanel} 
              showContextPanel={currentChatContext.showContextPanel} 
              isContextPanelExpanded={currentChatContext.isContextPanelExpanded} 
              onActivateChange={setIsActive}
            />
          </main>
        </div>
        
        {/* Context Panel - enlarged to 40% */}
        {currentChatContext.showContextPanel && currentChatContext.isContextPanelExpanded && (
          <div className="w-[40%] min-w-[400px] max-w-[600px] border-l border-gray-200 h-full">
            <ContextPanel 
              isOpen={true} 
              onToggle={() => setIsContextPanelExpanded(false)} 
              isActive={currentChatContext.isActive}
              activeTradeId={activeTradeId}
            />
          </div>
        )}
      </div>
      
      {/* Bottom left user indicator - JH only */}
      <div className="absolute bottom-4 left-4 z-20">
        
      </div>
    </div>
  );
};
