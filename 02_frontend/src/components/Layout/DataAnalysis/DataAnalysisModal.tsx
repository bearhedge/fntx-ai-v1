
import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { X } from 'lucide-react';
import { DataAnalysisContent } from './DataAnalysisContent';

interface DataAnalysisModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const DataAnalysisModal: React.FC<DataAnalysisModalProps> = ({
  open,
  onOpenChange
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl h-[80vh] overflow-hidden p-0">
        <DialogHeader className="px-6 py-4 border-b flex flex-row items-center justify-between">
          <DialogTitle className="text-2xl font-light text-center text-zinc-950 flex-1">
            DATA ANALYSIS
          </DialogTitle>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => onOpenChange(false)} 
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-4 h-4" />
          </Button>
        </DialogHeader>
        <div className="flex-1 overflow-auto">
          <DataAnalysisContent />
        </div>
      </DialogContent>
    </Dialog>
  );
};
