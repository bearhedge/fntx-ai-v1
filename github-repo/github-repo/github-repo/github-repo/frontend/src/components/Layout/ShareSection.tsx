import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Copy, Mail } from 'lucide-react';
interface ShareSectionProps {
  isCollapsed: boolean;
}
export const ShareSection = ({
  isCollapsed
}: ShareSectionProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const HandHeartIcon = () => <div className="w-6 h-6 flex items-center justify-center">
      <img src="/hand-heart.svg" alt="Hand Heart" className="w-5 h-5" />
    </div>;
  if (isCollapsed) {
    return <div className="border-t border-gray-300 p-2">
        <button onClick={() => setIsOpen(true)} className="w-full p-2 rounded-lg hover:bg-gray-200 transition-colors flex items-center justify-center">
          <HandHeartIcon />
        </button>
      </div>;
  }
  return <>
      <div className="border-t border-gray-100 p-4">
        <button onClick={() => setIsOpen(true)} className="w-full flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-200 transition-colors text-left">
          <div className="w-8 h-8 rounded-full bg-white border border-gray-300 flex items-center justify-center flex-shrink-0">
            <HandHeartIcon />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-gray-900 font-light">Share FNTX with a friend</p>
            <p className="text-xs text-gray-600 font-light">Get 500 credits each</p>
          </div>
          <span className="text-gray-400">→</span>
        </button>
      </div>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-2xl mx-auto bg-white rounded-2xl shadow-xl border-0 p-0">
          <div className="flex flex-col">
            {/* Header with FNTX logo */}
            <div className="flex justify-center items-center pt-12 pb-8">
              <img src="/fntx-logo-complete.svg" alt="FNTX Logo" className="h-16 w-auto mx-auto" />
            </div>
            
            {/* Content */}
            <div className="px-8 pb-8">
              <div className="grid grid-cols-3 gap-8 text-center mb-8">
                <div>
                  <h3 className="mb-4 text-gray-400 text-base text-left font-normal">     Invitation code</h3>
                </div>
                <div>
                  <h3 className="mb-4 text-gray-400 text-base font-normal">Friends invited</h3>
                </div>
                <div>
                  <h3 className="mb-4 text-gray-400 text-base font-normal">Share</h3>
                </div>
              </div>
              
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-8 items-center py-4 px-6 bg-gray-50 rounded-lg ">
                  <div className="text-left">
                    <span className="font-mono text-sm text-gray-400 font-thin">FXBXHKSL8XR7</span>
                  </div>
                  <div className="text-center">
                    <span className="text-sm text-gray-400 font-thin">0 / 1</span>
                  </div>
                  <div className="flex justify-center space-x-3">
                    <Button variant="ghost" size="sm" className="h-10 w-10 p-0 hover:bg-gray-200 font-normal">
                      <Copy className="w-5 h-5 text-gray-600" />
                    </Button>
                    <Button variant="ghost" size="sm" className="h-10 w-10 p-0 hover:bg-gray-200">
                      <Mail className="w-5 h-5 text-gray-600" />
                    </Button>
                  </div>
                </div>
                
                <div className="grid grid-cols-3 gap-8 items-center py-4 px-6 bg-gray-50 rounded-lg ">
                  <div className="text-left">
                    <span className="font-mono text-sm text-gray-400 font-thin">L05OUHWNAXE7W9</span>
                  </div>
                  <div className="text-center">
                    <span className="text-sm text-gray-400 font-thin">0 / 1</span>
                  </div>
                  <div className="flex justify-center space-x-3">
                    <Button variant="ghost" size="sm" className="h-10 w-10 p-0 hover:bg-gray-200">
                      <Copy className="w-5 h-5 text-gray-600" />
                    </Button>
                    <Button variant="ghost" size="sm" className="h-10 w-10 p-0 hover:bg-gray-200">
                      <Mail className="w-5 h-5 text-gray-600" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>;
};