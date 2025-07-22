import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { User, Settings as SettingsIcon, BarChart3, Shield, Mail, X } from 'lucide-react';
interface SettingsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialSection?: string;
}
export const SettingsModal = ({
  open,
  onOpenChange,
  initialSection = 'settings'
}: SettingsModalProps) => {
  const [activeSection, setActiveSection] = useState(initialSection);
  const [language, setLanguage] = useState('english');
  const [theme, setTheme] = useState('follow-system');
  const [exclusiveContent, setExclusiveContent] = useState(true);
  const [emailNotifications, setEmailNotifications] = useState(true);

  // Update activeSection when initialSection changes
  useEffect(() => {
    setActiveSection(initialSection);
  }, [initialSection]);

  const sidebarItems = [{
    id: 'account',
    label: 'Account',
    icon: User
  }, {
    id: 'settings',
    label: 'Settings',
    icon: SettingsIcon
  }, {
    id: 'usage',
    label: 'Usage',
    icon: BarChart3
  }, {
    id: 'data-controls',
    label: 'Data controls',
    icon: Shield
  }, {
    id: 'contact',
    label: 'Contact us',
    icon: Mail,
    external: true
  }];
  const handleContactUsClick = () => {
    window.open('https://bearhedge.com/reach-out', '_blank');
  };
  const renderContent = () => {
    switch (activeSection) {
      case 'account':
        return <div className="space-y-6">
            <div className="flex items-center space-x-4">
              <div className="w-16 h-16 bg-gray-600 rounded-full flex items-center justify-center text-white text-2xl font-bold">
                J
              </div>
              <div>
                <h2 className="text-xl font-semibold text-white">Jimmy Hou</h2>
                <p className="text-gray-400">info@bearhedge.com</p>
              </div>
              <div className="ml-auto flex space-x-2">
                <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
                  <User className="w-4 h-4" />
                </Button>
                <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>

            <div className="bg-gray-800 rounded-lg p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Free</h3>
                <Button variant="outline" size="sm" className="bg-gray-600 text-white border-gray-500 hover:bg-gray-500">
                  Upgrade
                </Button>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <BarChart3 className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-300">Credits</span>
                  </div>
                  <span className="text-white font-semibold">152</span>
                </div>
                <div className="text-right">
                  <span className="text-gray-400 text-sm">Free credits</span>
                  <span className="text-white text-sm ml-2">152</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <BarChart3 className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-300">Daily refresh credits</span>
                  </div>
                  <span className="text-white font-semibold">0</span>
                </div>
                <div className="text-right">
                  <span className="text-gray-400 text-sm">Refresh to 300 at 08:00 every day</span>
                </div>
              </div>
            </div>
          </div>;
      case 'settings':
        return <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-white mb-4">General</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-gray-300 text-sm mb-2 block">Language</label>
                  <Select value={language} onValueChange={setLanguage}>
                    <SelectTrigger className="bg-gray-800 border-gray-600 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-800 border-gray-600">
                      <SelectItem value="english">English</SelectItem>
                      <SelectItem value="spanish">Spanish</SelectItem>
                      <SelectItem value="french">French</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-gray-300 text-sm mb-3 block">Appearance</label>
                  <div className="grid grid-cols-3 gap-3">
                    <div className={`p-3 rounded-lg border-2 cursor-pointer ${theme === 'light' ? 'border-gray-400' : 'border-gray-600'}`} onClick={() => setTheme('light')}>
                      <div className="w-full h-12 bg-gray-200 rounded mb-2"></div>
                      <p className="text-center text-sm text-gray-300">Light</p>
                    </div>
                    <div className={`p-3 rounded-lg border-2 cursor-pointer ${theme === 'dark' ? 'border-gray-400' : 'border-gray-600'}`} onClick={() => setTheme('dark')}>
                      <div className="w-full h-12 bg-gray-800 rounded mb-2"></div>
                      <p className="text-center text-sm text-gray-300">Dark</p>
                    </div>
                    <div className={`p-3 rounded-lg border-2 cursor-pointer ${theme === 'follow-system' ? 'border-gray-400' : 'border-gray-600'}`} onClick={() => setTheme('follow-system')}>
                      <div className="w-full h-12 bg-gradient-to-r from-gray-200 to-gray-800 rounded mb-2"></div>
                      <p className="text-center text-sm text-gray-300">Follow System</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-4">Personalization</h3>
              
              <div className="space-y-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="text-white font-medium">Receive exclusive content</h4>
                    <p className="text-gray-400 text-sm mt-1">
                      Get exclusive offers, event updates, excellent case examples and new feature guides.
                    </p>
                  </div>
                  <Switch checked={exclusiveContent} onCheckedChange={setExclusiveContent} className="ml-4" />
                </div>

                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="text-white font-medium">Email me when my queued task starts processing</h4>
                    <p className="text-gray-400 text-sm mt-1">
                      When enabled, we'll send you a timely email once your task finishes queuing and begins processing,
                      so you can easily check its progress. You can change this setting anytime.
                    </p>
                  </div>
                  <Switch checked={emailNotifications} onCheckedChange={setEmailNotifications} className="ml-4" />
                </div>
              </div>
            </div>
          </div>;
      case 'usage':
        return <div className="space-y-6">
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Free</h3>
                <Button variant="outline" size="sm" className="bg-gray-600 text-white border-gray-500 hover:bg-gray-500">
                  Upgrade
                </Button>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <BarChart3 className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-300">Credits</span>
                  </div>
                  <span className="text-white font-semibold">152</span>
                </div>
                <div className="text-right">
                  <span className="text-gray-400 text-sm">Free credits</span>
                  <span className="text-white text-sm ml-2">152</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <BarChart3 className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-300">Daily refresh credits</span>
                  </div>
                  <span className="text-white font-semibold">0</span>
                </div>
                <div className="text-right">
                  <span className="text-gray-400 text-sm">Refresh to 300 at 08:00 every day</span>
                </div>
              </div>
            </div>

            <div className="bg-gray-800 rounded-lg p-4">
              <div className="grid grid-cols-3 gap-4 text-center text-sm text-gray-400 mb-4">
                <div>Details</div>
                <div>Date</div>
                <div>Credits change</div>
              </div>
              <div className="flex items-center justify-center py-8">
                <div className="w-6 h-6 border-2 border-gray-500 border-t-white rounded-full animate-spin"></div>
              </div>
            </div>
          </div>;
      case 'data-controls':
        return <div className="space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between py-4 border-b border-gray-700">
                <span className="text-white font-thin">Shared tasks</span>
                <Button variant="outline" size="sm" className="border-gray-600 text-zinc-950 bg-zinc-50">
                  Manage
                </Button>
              </div>
              
              <div className="flex items-center justify-between py-4 border-b border-gray-700">
                <span className="text-white font-thin">Shared files</span>
                <Button variant="outline" size="sm" className="border-gray-600 bg-zinc-50 text-zinc-950">
                  Manage
                </Button>
              </div>
              
              <div className="flex items-center justify-between py-4">
                <span className="text-white text-base font-thin">Deployed websites</span>
                <Button variant="outline" size="sm" className="border-gray-600 bg-zinc-50 text-zinc-950">
                  Manage
                </Button>
              </div>
            </div>
          </div>;
      default:
        return null;
    }
  };
  return <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl h-[80vh] bg-gray-600  text-white overflow-hidden">
        <DialogHeader className="flex flex-row items-center justify-between border-b border-gray-200 pb-2">
          <div className="flex items-center space-x-3">
            <div className="w-32 h-32 flex items-center justify-center overflow-hidden">
              <img src="/lovable-uploads/92bad265-1348-45e0-89bf-24a59c3872bf.png" alt="Logo" className="w-full h-full object-contain" />
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)} className="text-gray-400 hover:text-white bg-transparent">
            <X className="w-4 h-4" />
          </Button>
        </DialogHeader>

        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <div className="w-64 border-r border-gray-700 pr-4">
            <nav className="space-y-2">
              {sidebarItems.map(item => <button key={item.id} onClick={() => {
              if (item.external && item.id === 'contact') {
                handleContactUsClick();
              } else {
                setActiveSection(item.id);
              }
            }} className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-left transition-colors ${activeSection === item.id ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'}`}>
                  <item.icon className="w-4 h-4" />
                  <span>{item.label}</span>
                  {item.external && <span className="ml-auto">↗</span>}
                </button>)}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 pl-6 overflow-y-auto">
            <div className="mb-4">
              <h1 className="text-2xl text-white capitalize font-thin">
                {activeSection === 'data-controls' ? 'Data controls' : activeSection}
              </h1>
            </div>
            {renderContent()}
          </div>
        </div>
      </DialogContent>
    </Dialog>;
};
