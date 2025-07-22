import React, { useState, useEffect } from 'react';
import { MessageSquare, Plus, User, ChevronUp, Settings, Home, Mail, LogOut, PanelLeftClose, PanelLeftOpen, Search, Lock, Unlock, Bell, Zap, ScrollText, Trash2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Command, CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { ShareSection } from './ShareSection';
import { Notifications } from './Notifications';
import { RecordsModal } from './RecordsModal';
import { PermissionsModal } from './Permissions/PermissionsModal';
import { AutomationModal } from './Automation/AutomationModal';
import { DataAnalysisModal } from './DataAnalysis/DataAnalysisModal';
import { SettingsModal } from './Settings/SettingsModal';
import { useNavigate } from 'react-router-dom';
import Cookies from 'js-cookie';

interface Chat {
  id: string;
  title: string;
  preview: string;
  date: string;
  icon: string;
  active: boolean;
  is_active?: boolean;
}
interface SidebarProps {
  onChatChange?: (chatId: string) => void;
  activeChatId?: string;
}
// Demo chats for guest users
const demoChats: Chat[] = [{
  id: 'demo-1',
  title: 'Welcome to FNTX AI',
  preview: 'How can I help you trade SPY options today?',
  date: 'Now',
  icon: '🧠',
  active: true
}, {
  id: 'demo-2',
  title: 'SPY Options Example',
  preview: 'Show me SPY put options',
  date: 'Demo',
  icon: '🧠',
  active: false
}, {
  id: 'demo-3',
  title: 'Market Analysis Demo',
  preview: 'What is the best SPY strategy today?',
  date: 'Demo',
  icon: '🧠',
  active: false
}];
export const Sidebar = ({
  onChatChange,
  activeChatId
}: SidebarProps) => {
  const navigate = useNavigate();
  const { user, signOut: authSignOut } = useAuth();
  
  const signOut = async () => {
    await authSignOut();
    navigate('/');
  };
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isDocked, setIsDocked] = useState(true);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showRecords, setShowRecords] = useState(false);
  const [showPermissions, setShowPermissions] = useState(false);
  const [showAutomation, setShowAutomation] = useState(false);
  const [showDataAnalysis, setShowDataAnalysis] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [settingsInitialSection, setSettingsInitialSection] = useState('settings');
  const [chats, setChats] = useState<Chat[]>([]);
  const [isLoadingChats, setIsLoadingChats] = useState(false);
  
  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };
  const toggleDock = () => {
    setIsDocked(!isDocked);
    if (isDocked) {
      setIsCollapsed(true);
    } else {
      setIsCollapsed(false);
    }
  };
  const openSearch = () => {
    setIsSearchOpen(true);
  };
  
  // Fetch chat sessions from backend
  const fetchChatSessions = async (immediate = false) => {
    if (!user) {
      // Show demo chats for guest users
      setChats(demoChats);
      return;
    }
    
    // No delay when immediate is requested
    // Small delay only for non-immediate requests to avoid too many API calls
    if (!immediate) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    setIsLoadingChats(true);
    try {
      const token = Cookies.get('fntx_token');
      if (!token) {
        setChats(demoChats);
        return;
      }
      
      const apiUrl = import.meta.env.VITE_API_URL || '/api';
      const response = await fetch(`${apiUrl}/chat/sessions`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Chat sessions received:', data.sessions);
        const sessions = data.sessions.map((session: any) => ({
          id: session.id,
          title: session.title,
          preview: session.preview || 'New conversation...',
          date: session.date,
          icon: '🧠',
          active: session.id === activeChatId
        }));
        
        // Set the user's chat sessions (empty array if none exist)
        console.log('Setting chats to:', sessions);
        setChats(sessions);
      } else {
        // For authenticated users, show empty list on error
        console.error('Failed to fetch chat sessions, status:', response.status);
        setChats([]);
      }
    } catch (error) {
      console.error('Failed to fetch chat sessions:', error);
      // For authenticated users, show empty list on error
      setChats([]);
    } finally {
      setIsLoadingChats(false);
    }
  };
  
  // Create a new chat session
  const createNewChat = async () => {
    if (!user) {
      // For guests, just add a local demo chat
      const newChat: Chat = {
        id: `demo-${Date.now()}`,
        title: 'New Chat',
        preview: 'Start a conversation...',
        date: 'Now',
        icon: '🧠',
        active: true
      };
      setChats([newChat, ...chats.map(c => ({ ...c, active: false }))]);
      onChatChange?.(newChat.id);
      return;
    }
    
    try {
      const token = Cookies.get('fntx_token');
      if (!token) return;
      
      const apiUrl = import.meta.env.VITE_API_URL || '/api';
      const response = await fetch(`${apiUrl}/chat/sessions`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title: (() => {
            const now = new Date();
            const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
            const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
            return `${now.getDate()} ${months[now.getMonth()]} ${now.getFullYear()}, ${days[now.getDay()]}`;
          })(),
          preview: 'New conversation...'
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        const newChat: Chat = {
          id: data.session.id,
          title: data.session.title,
          preview: data.session.preview,
          date: 'Now',
          icon: '🧠',
          active: true
        };
        
        // Update existing chats to be inactive
        const updatedChats = chats.map(chat => ({ ...chat, active: false }));
        setChats([newChat, ...updatedChats]);
        onChatChange?.(newChat.id);
      }
    } catch (error) {
      console.error('Failed to create chat session:', error);
    }
  };
  
  // Load chat sessions when component mounts or user changes
  useEffect(() => {
    fetchChatSessions(true); // Immediate fetch on mount
  }, [user]);

  // Update active states when activeChatId changes
  useEffect(() => {
    if (activeChatId) {
      setChats(prevChats => prevChats.map(chat => ({
        ...chat,
        active: chat.id === activeChatId
      })));
    }
  }, [activeChatId]);

  // Listen for refresh events
  useEffect(() => {
    const handleRefresh = () => {
      console.log('Sidebar: refreshChatSessions event received');
      fetchChatSessions(true); // Use immediate refresh
    };

    window.addEventListener('refreshChatSessions', handleRefresh);
    return () => {
      window.removeEventListener('refreshChatSessions', handleRefresh);
    };
  }, [user]); // Re-subscribe when user changes
  const handleNewDay = () => {
    // Navigate to default chat to show welcome screen with buttons
    onChatChange?.('default');
  };
  const handleChatClick = async (chatId: string) => {
    // Update local state immediately
    setChats(chats.map(chat => ({
      ...chat,
      active: chat.id === chatId
    })));

    // Notify parent of active chat change
    onChatChange?.(chatId);
    
    // Update backend if authenticated
    if (user && !chatId.startsWith('demo-')) {
      try {
        const token = Cookies.get('fntx_token');
        if (token) {
          const apiUrl = import.meta.env.VITE_API_URL || '/api';
          await fetch(`${apiUrl}/chat/sessions/${chatId}/activate`, {
            method: 'PUT',
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
        }
      } catch (error) {
        console.error('Failed to activate chat session:', error);
      }
    }
  };

  const handleDeleteChat = async (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent chat from being selected
    
    if (chatId.startsWith('demo-')) {
      // Don't allow deleting demo chats
      return;
    }

    if (!user) return;

    try {
      const token = Cookies.get('fntx_token');
      if (token) {
        const apiUrl = import.meta.env.VITE_API_URL || '/api';
        const response = await fetch(`${apiUrl}/chat/sessions/${chatId}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          // Remove chat from local state
          const newChats = chats.filter(chat => chat.id !== chatId);
          setChats(newChats);
          
          // If this was the active chat, or if all chats are deleted, 
          // set to 'default' to show welcome screen
          if (activeChatId === chatId || newChats.length === 0) {
            onChatChange?.('default');
          }
        }
      }
    } catch (error) {
      console.error('Failed to delete chat:', error);
    }
  };

  const handleKnowledgeClick = () => {
    // Knowledge functionality to be implemented
  };
  const handleNotificationClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowNotifications(true);
  };
  const handleAutomationClick = () => {
    setShowAutomation(true);
  };
  const handleDataAnalyticsClick = () => {
    setShowDataAnalysis(true);
  };
  const handleRecordsClick = () => {
    setShowRecords(true);
  };
  const handlePermissionsClick = () => {
    setShowPermissions(true);
  };
  const handleSettingsClick = () => {
    setSettingsInitialSection('settings');
    setShowSettings(true);
  };
  const handleAccountsClick = () => {
    setSettingsInitialSection('account');
    setShowSettings(true);
  };
  const handleHomepageClick = () => {
    window.open('https://www.bearhedge.com', '_blank');
  };
  const handleContactUsClick = () => {
    window.open('https://bearhedge.com/reach-out', '_blank');
  };
  
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault();
        openSearch();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);
  useEffect(() => {
    if (!isDocked) {
      if (isHovering) {
        setIsCollapsed(false);
      } else {
        const timer = setTimeout(() => {
          setIsCollapsed(true);
        }, 300);
        return () => clearTimeout(timer);
      }
    }
  }, [isHovering, isDocked]);
  
  const sidebarWidth = isCollapsed ? 'w-16' : 'w-80';

  // Simple SVG icons as components
  const UserIcon = ({
    size = "w-20 h-20"
  }: {
    size?: string;
  }) => <img src="/user-avatar.svg" alt="User Avatar" className={`${size} object-contain`} style={{
    transform: 'translateY(1px)'
  }} />;
  const SimpleLightbulb = ({
    size = "w-4 h-4"
  }: {
    size?: string;
  }) => <svg className={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M9 21h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M12 3a6 6 0 0 1 6 6c0 3-2 4-2 6H8c0-2-2-3-2-6a6 6 0 0 1 6-6z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M9 18h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>;

  return <div className={`${sidebarWidth} bg-gray-100 border-r border-gray-300 flex flex-col relative transition-all duration-300`} onMouseEnter={() => !isDocked && setIsHovering(true)} onMouseLeave={() => !isDocked && setIsHovering(false)}>
      {/* Header with dock/undock, collapse, New day button, and search */}
      <div className="p-4 border-b border-gray-300">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <button onClick={toggleDock} className="p-2 hover:bg-gray-200 rounded-lg transition-colors" title={isDocked ? "Undock sidebar" : "Dock sidebar"}>
              {isDocked ? <Lock className="w-4 h-4 text-gray-600" /> : <Unlock className="w-4 h-4 text-gray-600" />}
            </button>
            {!isCollapsed && <button onClick={toggleCollapse} className="p-2 hover:bg-gray-200 rounded-lg transition-colors">
                <PanelLeftClose className="w-4 h-4 text-gray-600" />
              </button>}
          </div>
          {!isCollapsed && <button onClick={openSearch} className="p-2 hover:bg-gray-200 rounded-lg transition-colors">
              <Search className="w-4 h-4 text-gray-600" />
            </button>}
        </div>
        {!isCollapsed && <button onClick={handleNewDay} className="flex items-center space-x-2 px-3 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg transition-colors w-full">
            <Plus className="w-4 h-4" />
            <span className="text-sm font-medium text-gray-700 flex-1">New day</span>
            <div className="flex items-center space-x-1 text-xs text-gray-500">
              <span className="px-1 py-0.5 bg-gray-300 rounded text-xs">⌘</span>
              <span className="px-1 py-0.5 bg-gray-300 rounded text-xs">K</span>
            </div>
          </button>}
      </div>

      {isCollapsed ? <>
          {/* Collapsed search button */}
          <div className="p-2">
            <button onClick={openSearch} className="w-full p-2 hover:bg-gray-200 rounded-lg transition-colors flex items-center justify-center">
              <Search className="w-4 h-4 text-gray-600" />
            </button>
          </div>

          {/* Collapsed chat items */}
          <div className="flex-1 overflow-y-auto p-2">
            {chats.map(chat => <button key={chat.id} onClick={() => handleChatClick(chat.id)} className={`w-full p-2 rounded-lg transition-colors mb-2 ${chat.active ? 'bg-gray-200 border border-gray-400' : 'hover:bg-gray-200'}`}>
                <div className="w-6 h-6 rounded-full text-white text-xs flex items-center justify-center mx-auto bg-neutral-300">
                  🧠
                </div>
              </button>)}
          </div>

          <ShareSection isCollapsed={true} />

          {/* Collapsed user profile without notification and knowledge icons */}
          <div className="border-t border-gray-300 p-2 space-y-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="w-full p-2 rounded-lg hover:bg-gray-200 transition-colors flex items-center justify-center">
                  <Avatar className="w-8 h-8">
                    <AvatarFallback className="bg-white border border-gray-300 flex items-center justify-center">
                      <UserIcon size="w-4 h-4" />
                    </AvatarFallback>
                  </Avatar>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-64 mb-2 ml-4" align="start" side="right">
                {/* Plan Section */}
                <div className="p-3 bg-gray-50 rounded-lg mb-2">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">Free</span>
                    <button className="px-3 py-1 bg-black text-white text-xs rounded-full hover:bg-gray-800 transition-colors">
                      Upgrade
                    </button>
                  </div>
                  <div className="flex items-center justify-between text-xs text-gray-600">
                    <span className="flex items-center space-x-1">
                      <span>✨</span>
                      <span>Credits</span>
                    </span>
                    <span>190 + 291 →</span>
                  </div>
                </div>
                
                <DropdownMenuSeparator />
                
                <DropdownMenuItem onClick={handleAccountsClick} className="flex items-center space-x-2 px-3 py-2 cursor-pointer">
                  <User className="w-4 h-4" />
                  <span>Accounts</span>
                </DropdownMenuItem>
                
                <DropdownMenuItem className="flex items-center space-x-2 px-3 py-2" onClick={handleAutomationClick}>
                  <Zap className="w-4 h-4" />
                  <span>Automation</span>
                </DropdownMenuItem>
                
                <DropdownMenuItem className="flex items-center space-x-2 px-3 py-2" onClick={handleDataAnalyticsClick}>
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M3 3v18h18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M7 12l3-3 2 2 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span>Data analysis</span>
                </DropdownMenuItem>
                
                <DropdownMenuItem className="flex items-center space-x-2 px-3 py-2" onClick={handleRecordsClick}>
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    <polyline points="14,2 14,8 20,8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    <line x1="16" y1="13" x2="8" y2="13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    <line x1="16" y1="17" x2="8" y2="17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    <polyline points="10,9 9,9 8,9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span>Records</span>
                </DropdownMenuItem>
                
                <DropdownMenuItem className="flex items-center space-x-2 px-3 py-2" onClick={handlePermissionsClick}>
                  <ScrollText className="w-4 h-4" />
                  <span>Permissions</span>
                </DropdownMenuItem>
                
                <DropdownMenuSeparator />
                
                <DropdownMenuItem className="flex items-center space-x-2 px-3 py-2" onClick={handleSettingsClick}>
                  <Settings className="w-4 h-4" />
                  <span>Settings</span>
                </DropdownMenuItem>
                
                <DropdownMenuSeparator />
                
                <DropdownMenuItem className="flex items-center space-x-2 px-3 py-2">
                  <Home className="w-4 h-4" />
                  <span>Homepage</span>
                  <span className="ml-auto">↗</span>
                </DropdownMenuItem>
                
                <DropdownMenuItem className="flex items-center space-x-2 px-3 py-2">
                  <Mail className="w-4 h-4" />
                  <span>Contact us</span>
                  <span className="ml-auto">↗</span>
                </DropdownMenuItem>
                
                <DropdownMenuSeparator />
                
                <DropdownMenuItem onClick={signOut} className="flex items-center space-x-2 px-3 py-2 text-red-600 cursor-pointer">
                  <LogOut className="w-4 h-4" />
                  <span>Sign out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </> : <>
          {/* Previous chats list */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-4 space-y-2">
              {chats.length === 0 && !isLoadingChats && !user && (
              <div className="p-4 text-center">
                <p className="text-sm text-gray-500 mb-3">Sign in to save your chat history</p>
                <button
                  onClick={() => navigate('/')}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  Sign in →
                </button>
              </div>
            )}
            {chats.length === 0 && !isLoadingChats && user && (
              <div className="p-4 text-center">
                <p className="text-sm text-gray-500 mb-3">No chats yet</p>
                <p className="text-xs text-gray-400">Start a conversation to begin</p>
              </div>
            )}
            {chats.map(chat => (
              <div key={chat.id} className={`group w-full flex items-start space-x-3 p-3 rounded-lg text-left transition-colors ${chat.active ? 'bg-gray-200 border border-gray-400' : 'hover:bg-gray-200'}`}>
                <button onClick={() => handleChatClick(chat.id)} className="flex items-start space-x-3 flex-1 min-w-0">
                  <div className="w-8 h-8 rounded-full text-white text-xs flex items-center justify-center flex-shrink-0 mt-0.5 bg-neutral-300">
                    🧠
                  </div>
                  <div className="flex-1 min-w-0 text-left">
                    <p className="text-gray-800 truncate font-light text-sm text-left">
                      {chat.title}
                    </p>
                    <p className="text-xs text-gray-600 mt-1 truncate font-light text-left">
                      {chat.preview}
                    </p>
                  </div>
                  <div className="text-xs text-gray-500 flex-shrink-0 mt-0.5">
                    {chat.date}
                  </div>
                </button>
                {!chat.id.startsWith('demo-') && user && (
                  <button 
                    onClick={(e) => handleDeleteChat(chat.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-100 transition-all duration-200 flex-shrink-0"
                    title="Delete chat"
                  >
                    <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-600" />
                  </button>
                )}
              </div>
            ))}
            </div>
          </div>

          <ShareSection isCollapsed={false} />

          {/* User Profile Section with icons */}
          <div className="border-t border-gray-300 p-4">
            <div className="flex items-center space-x-3">
              {/* Dropdown trigger for user profile FIRST */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex-1 flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-200 transition-colors text-left">
                    <Avatar className="w-8 h-8">
                      <AvatarFallback className="bg-white border border-gray-300 flex items-center justify-center">
                        <UserIcon size="w-4 h-4" />
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-gray-900 truncate">{user?.name || 'Guest User'}</p>
                      <p className="text-xs text-gray-600 truncate">{user?.email || 'Sign in to save your chats'}</p>
                    </div>
                    <ChevronUp className="w-4 h-4 text-gray-400" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-64 mb-2 ml-4" align="start" side="top">
                  {/* Plan Section */}
                  <div className="p-3 bg-gray-50 rounded-lg mb-2">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold">Free</span>
                      <button className="px-3 py-1 bg-black text-white text-xs rounded-full hover:bg-gray-800 transition-colors">
                        Upgrade
                      </button>
                    </div>
                    <div className="flex items-center justify-between text-xs text-gray-600">
                      <span className="flex items-center space-x-1">
                        <span>✨</span>
                        <span>Credits</span>
                      </span>
                      <span>1,000 →</span>
                    </div>
                  </div>
                  
                  <DropdownMenuSeparator />
                  
                  <DropdownMenuItem className="flex items-center space-x-2 px-3 py-2" onClick={handleAutomationClick}>
                    <Zap className="w-4 h-4" />
                    <span>Automation</span>
                  </DropdownMenuItem>
                  
                  <DropdownMenuItem className="flex items-center space-x-2 px-3 py-2" onClick={handleDataAnalyticsClick}>
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M3 3v18h18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      <path d="M7 12l3-3 2 2 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span>Data analysis</span>
                  </DropdownMenuItem>
                  
                  <DropdownMenuItem className="flex items-center space-x-2 px-3 py-2" onClick={handleRecordsClick}>
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      <polyline points="14,2 14,8 20,8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      <line x1="16" y1="13" x2="8" y2="13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      <line x1="16" y1="17" x2="8" y2="17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      <polyline points="10,9 9,9 8,9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span>Records</span>
                  </DropdownMenuItem>
                  
                  <DropdownMenuItem className="flex items-center space-x-2 px-3 py-2" onClick={handlePermissionsClick}>
                    <ScrollText className="w-4 h-4" />
                    <span>Permissions</span>
                  </DropdownMenuItem>
                  
                  <DropdownMenuSeparator />
                  
                  <DropdownMenuItem onClick={handleAccountsClick} className="flex items-center space-x-2 px-3 py-2 cursor-pointer">
                    <User className="w-4 h-4" />
                    <span>Accounts</span>
                  </DropdownMenuItem>
                  
                  <DropdownMenuItem className="flex items-center space-x-2 px-3 py-2" onClick={handleSettingsClick}>
                    <Settings className="w-4 h-4" />
                    <span>Settings</span>
                  </DropdownMenuItem>
                  
                  <DropdownMenuSeparator />
                  
                  <DropdownMenuItem onClick={handleHomepageClick} className="flex items-center space-x-2 px-3 py-2 cursor-pointer">
                    <Home className="w-4 h-4" />
                    <span>Homepage</span>
                    <span className="ml-auto">↗</span>
                  </DropdownMenuItem>
                  
                  <DropdownMenuItem onClick={handleContactUsClick} className="flex items-center space-x-2 px-3 py-2 cursor-pointer">
                    <Mail className="w-4 h-4" />
                    <span>Contact us</span>
                    <span className="ml-auto">↗</span>
                  </DropdownMenuItem>
                  
                  <DropdownMenuSeparator />
                  
                  <DropdownMenuItem onClick={signOut} className="flex items-center space-x-2 px-3 py-2 text-red-600 cursor-pointer">
                    <LogOut className="w-4 h-4" />
                    <span>Sign out</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              
              {/* Bell icon SECOND */}
              <button onClick={handleNotificationClick} className="p-2 rounded-lg hover:bg-gray-300 transition-colors" style={{
            marginLeft: '-2px'
          }}>
                <Bell className="w-4 h-4 text-gray-600" />
              </button>
              
              {/* Permissions icon THIRD - moved left by 5mm */}
              <button onClick={handlePermissionsClick} className="p-2 rounded-lg hover:bg-gray-300 transition-colors" style={{
            marginLeft: '1px'
          }}>
                <ScrollText className="w-4 h-4 text-gray-600" />
              </button>
            </div>
          </div>
        </>}

      {/* Search Dialog with enhanced information */}
      <CommandDialog open={isSearchOpen} onOpenChange={setIsSearchOpen}>
        <CommandInput placeholder="Search chats..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Recent Chats">
            {chats.map(chat => <CommandItem key={chat.id} className="flex items-center justify-between px-3 py-2">
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  <MessageSquare className="h-4 w-4 text-gray-500 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium text-gray-900 truncate block">{chat.title}</span>
                    <span className="text-xs text-gray-500 truncate block">{chat.preview}</span>
                  </div>
                </div>
                <span className="text-xs text-gray-400 flex-shrink-0 ml-2">{chat.date}</span>
              </CommandItem>)}
          </CommandGroup>
        </CommandList>
      </CommandDialog>

      {/* Notifications Modal */}
      {showNotifications && <Notifications isOpen={showNotifications} onClose={() => setShowNotifications(false)} />}

      {/* Records Modal */}
      {showRecords && <RecordsModal isOpen={showRecords} onClose={() => setShowRecords(false)} />}

      {/* Permissions Modal */}
      {showPermissions && <PermissionsModal open={showPermissions} onOpenChange={setShowPermissions} />}
      
      {/* Automation Modal */}
      {showAutomation && <AutomationModal open={showAutomation} onOpenChange={setShowAutomation} />}
      
      {/* Data Analysis Modal */}
      {showDataAnalysis && <DataAnalysisModal open={showDataAnalysis} onOpenChange={setShowDataAnalysis} />}
      
      {/* Settings Modal */}
      {showSettings && <SettingsModal 
        open={showSettings} 
        onOpenChange={setShowSettings}
        initialSection={settingsInitialSection}
      />}
    </div>;
};